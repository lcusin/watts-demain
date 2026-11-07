"""Validation 2024 gelee : sans meteo, persistance 48 h, meteo parfaite."""

import hashlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from decomposition_meteo_calendrier import variables, ajuster, MODELES, correlations_blocs, sauver_audit
from prevision_residus_ar import prevoir_ar
from benchmarks import prevoir_benchmarks

from resume import ecrire_resume
from chemins_analyse import RESULTATS as DOSSIER, PROJET
SORTIE = DOSSIER / "08_validation_2024"
RETARDS = [1, 2, 3, 24, 25, 48, 168]
FIN_APPRENTISSAGE = pd.Timestamp("2023-12-31")


def borne_disponibilite(utc):
    # La pluie datee a h couvre [h,h+1] : sa mesure source peut etre le SYNOP suivant h+1.
    # Delai de publication suppose : 3 heures (hypothese, pas archive de disponibilite).
    return (pd.DatetimeIndex(utc) + pd.Timedelta(hours=1)).ceil("3h") + pd.Timedelta(hours=3)


def meteo_persistante(dates_utc, origine_utc, observations):
    sources = pd.DatetimeIndex(dates_utc) - pd.Timedelta(hours=48)
    disponibilite = borne_disponibilite(sources)
    assert (disponibilite <= origine_utc).all()
    return observations.reindex(sources).to_numpy(), disponibilite.max()


def main():
    SORTIE.mkdir(exist_ok=True)
    test = PROJET / "data/merge/test.csv"
    empreinte = hashlib.sha256(test.read_bytes()).hexdigest()  # Integrite uniquement, aucune analyse.
    d = pd.read_csv(PROJET / "data/merge/donnees_combinees.csv", parse_dates=["horodatage"])
    d = d.loc[d.horodatage.lt("2025-01-01")].set_index("horodatage").sort_index()
    assert d.index.max() < pd.Timestamp("2025-01-01")
    assert d.index.equals(pd.date_range(d.index.min(), d.index.max(), freq="h"))
    d["date_utc"] = pd.to_datetime(d.date_utc, utc=True)
    d = d.rename(columns={"temperature_moyenne": "temperature", "precipitation_moyenne": "pluie"})
    valide = (~d.jour_changement_heure & d.date_utc.notna()
              & d[["consommation_MW", "temperature", "pluie"]].notna().all(axis=1))
    # Masquer les valeurs, sans supprimer de lignes : les retards restent horaires.
    # La meme serie sert aux modeles et aux benchmarks.
    y = d.consommation_MW.mask(d.jour_changement_heure)
    observations = d.loc[valide].set_index("date_utc")[["temperature", "pluie"]]
    assert observations.index.is_unique
    configurations = {"sans_meteo": {"interactions": True},
                      "meteo": MODELES["M09_interactions"]}
    bases, residus, ar, parametres = {}, {}, {}, {}
    for nom, config in configurations.items():
        x = variables(d.loc[valide], config)
        apprentissage = x.index < FIN_APPRENTISSAGE
        coef, constante = ajuster(x, y.reindex(x.index), apprentissage)
        moyenne = pd.Series(np.nan, index=d.index)
        moyenne.loc[x.index] = x @ coef + constante
        e = y - moyenne
        z = pd.DataFrame({str(r): e.shift(r) for r in RETARDS})
        complet = e.notna() & z.notna().all(axis=1)
        ca, ba = ajuster(z.loc[complet], e.loc[complet], z.loc[complet].index < FIN_APPRENTISSAGE)
        bases[nom] = (config, coef, constante)
        residus[nom] = e
        ar[nom] = (ca.to_numpy(), ba)
        parametres[nom] = {"constante": float(constante), "coefficients": coef.to_dict(),
                           "constante_ar": float(ba), "coefficients_ar": ca.to_dict()}
    lignes, exclusions, audit, erreurs_meteo = [], [], [], []
    for jour in pd.date_range("2024-01-01", "2024-12-31", freq="D"):
        origine = jour - pd.Timedelta(days=1) + pd.Timedelta(hours=14)
        origine_utc = origine.tz_localize("Europe/Paris").tz_convert("UTC")
        coupure = origine - pd.Timedelta(hours=6)  # J,8 h pour les trois scenarios.
        cible = pd.date_range(jour, periods=24, freq="h")
        passe = pd.date_range(coupure - pd.Timedelta(hours=167), coupure, freq="h")
        if not valide.reindex(cible, fill_value=False).all():
            exclusions.append({"jour": jour, "motif": "cible ou meteo parfaite incomplete"})
            continue
        if any(residus[nom].reindex(passe).isna().any() for nom in residus):
            exclusions.append({"jour": jour, "motif": "historique commun incomplet"})
            continue
        meteo_prevue, derniere_source = meteo_persistante(d.loc[cible, "date_utc"], origine_utc, observations)
        if not np.isfinite(meteo_prevue).all():
            exclusions.append({"jour": jour, "motif": "persistance 48 h indisponible"})
            continue
        benchmarks = prevoir_benchmarks(y, cible, coupure)
        if benchmarks is None:
            exclusions.append({"jour": jour, "motif": "Historique des benchmarks incomplet ou changement heure"})
            continue
        disponibilite_passee = borne_disponibilite(d.loc[passe, "date_utc"]).max()
        assert disponibilite_passee <= origine_utc
        assert passe.max() < origine and FIN_APPRENTISSAGE <= origine
        # La cible et le passe sont complets, aucun decalage de ligne a travers les trous.
        horizon = int((cible[-1] - coupure) / pd.Timedelta(hours=1))
        positions = ((cible - coupure) / pd.Timedelta(hours=1)).astype(int) - 1
        corrections = {}
        for nom in residus:
            coefficients, constante = ar[nom]
            historique = residus[nom].loc[passe].to_numpy()
            correction = prevoir_ar(historique, RETARDS, coefficients, constante, horizon)
            corrections[nom] = correction[positions]
        scenarios = {"sans_meteo": d.loc[cible].copy(), "meteo_parfaite": d.loc[cible].copy(),
                     "meteo_persistance_48h": d.loc[cible].copy()}
        scenarios["meteo_persistance_48h"][["temperature", "pluie"]] = meteo_prevue
        for nom, valeurs in benchmarks.items():
            for date, valeur in zip(cible, valeurs):
                lignes.append({"origine_locale": origine, "cible_locale": date, "scenario": nom,
                               "observe_MW": y.loc[date], "prevision_MW": valeur})
        for nom, scenario in scenarios.items():
            base = "sans_meteo" if nom == "sans_meteo" else "meteo"
            config, coef, constante = bases[base]
            prevision = variables(scenario, config) @ coef + constante + corrections[base]
            assert np.isfinite(prevision).all()
            for date, valeur in prevision.items():
                lignes.append({"origine_locale": origine, "cible_locale": date, "scenario": nom,
                               "observe_MW": y.loc[date], "prevision_MW": valeur})
        audit.append({"origine_locale": origine, "origine_utc": origine_utc,
                      "derniere_conso_locale": coupure, "disponibilite_meteo_historique_max": disponibilite_passee,
                      "disponibilite_meteo_persistance_max": derniere_source})
        for date, prevue, vraie in zip(cible, meteo_prevue, d.loc[cible, ["temperature", "pluie"]].to_numpy()):
            erreurs_meteo.append({"cible_locale": date, "erreur_temperature_C": vraie[0] - prevue[0],
                                  "erreur_pluie_mm": vraie[1] - prevue[1]})
    p = pd.DataFrame(lignes)
    p["erreur_MW"] = p.observe_MW - p.prevision_MW
    assert p.groupby(["scenario", "origine_locale"]).size().eq(24).all()
    assert p.groupby("scenario").size().nunique() == 1
    p.to_csv(SORTIE / "previsions.csv", index=False)
    pd.DataFrame(audit).to_csv(SORTIE / "audit_disponibilite.csv", index=False)
    pd.DataFrame(exclusions).to_csv(SORTIE / "jours_exclus.csv", index=False)
    pd.DataFrame(erreurs_meteo).to_csv(SORTIE / "erreurs_meteo.csv", index=False)
    (SORTIE / "parametres.json").write_text(json.dumps(parametres, indent=2), encoding="utf-8")
    bilan = p.groupby("scenario").erreur_MW.agg(n="size", MAE_MW=lambda s: s.abs().mean(),
                                               RMSE_MW=lambda s: np.sqrt((s**2).mean()), biais_MW="mean")
    bilan.to_csv(SORTIE / "comparaison.csv")
    p.assign(mois=p.cible_locale.dt.month).groupby(["scenario", "mois"]).erreur_MW.agg(
        MAE_MW=lambda s: s.abs().mean(), RMSE_MW=lambda s: np.sqrt((s**2).mean())).to_csv(SORTIE / "scores_mensuels.csv")
    jours = p.groupby(["scenario", "origine_locale"]).erreur_MW.agg(MAE_MW=lambda s: s.abs().mean(),
        RMSE_MW=lambda s: np.sqrt((s**2).mean()), erreur_energie_MWh=lambda s: abs(s.sum()))
    jours.to_csv(SORTIE / "scores_journaliers.csv")
    nb = p.scenario.nunique()
    fig, axes = plt.subplots(nb, 2, figsize=(14, 3 * nb))
    correlations = []
    for ligne, (nom, bloc) in enumerate(p.groupby("scenario")):
        a, pac, n = correlations_blocs(bloc.set_index("cible_locale").erreur_MW.sort_index())
        correlations.extend({"scenario": nom, "retard": k, "ACF": a[k], "PACF": pac[k], "paires": n[k]}
                            for k in range(len(a)))
        for ax, valeurs, titre in zip(axes[ligne], [a, pac], ["ACF", "PACF"]):
            ax.vlines(range(1,337),0,valeurs[1:],linewidth=.8)
            ax.axhline(0,color="black",linewidth=.5)
            ax.set(title=f"{titre} — {nom}", ylim=(-1,1), xlabel="Retard (heures)")
    fig.tight_layout()
    fig.savefig(SORTIE / "acf_pacf.png", dpi=170)
    plt.close(fig)
    pd.DataFrame(correlations).to_csv(SORTIE / "correlations.csv", index=False)
    fig, ax = plt.subplots(figsize=(12,5))
    for nom, bloc in p.groupby("scenario"):
        profil = bloc.groupby(bloc.cible_locale.dt.hour).erreur_MW.apply(lambda s:s.abs().mean())
        ax.plot(profil.index, profil,label=nom)
    ax.set(xlabel="Heure cible",ylabel="MAE (MW)",title="Validation 2024 — origine J,14 h")
    ax.legend()
    ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(SORTIE / "erreurs_par_heure.png", dpi=180)
    plt.close(fig)
    # Trois echecs de la meteo prevue, choisis apres evaluation pour diagnostic uniquement.
    mauvaises = jours.loc["meteo_persistance_48h"].nlargest(3,"RMSE_MW")
    fig, axes = plt.subplots(3,1,figsize=(12,10))
    details = []
    for ax, origine in zip(axes, mauvaises.index):
        bloc = p.loc[p.origine_locale.eq(origine)]
        verite = bloc.drop_duplicates("cible_locale").set_index("cible_locale").observe_MW
        ax.plot(verite.index.hour,verite,label="Observe",color="black")
        for nom, s in bloc.groupby("scenario"):
            ax.plot(s.cible_locale.dt.hour,s.prevision_MW,label=nom)
        dates = verite.index
        ecart = d.loc[dates,"temperature"].to_numpy() - observations.reindex(pd.DatetimeIndex(d.loc[dates,"date_utc"])-pd.Timedelta(hours=48)).temperature.to_numpy()
        details.append({"jour": dates[0].date(), "jour_ferie": int(d.loc[dates[0],"jour_ferie"]),
                        "erreur_temperature_moyenne_C": float(ecart.mean()),
                        "RMSE_persistance": mauvaises.loc[origine,"RMSE_MW"]})
        ax.set(title=str(dates[0].date()),ylabel="MW",xlabel="Heure")
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(SORTIE / "trois_echecs.png", dpi=170)
    plt.close(fig)
    pd.DataFrame(details).to_csv(SORTIE / "trois_echecs.csv",index=False)
    assert hashlib.sha256(test.read_bytes()).hexdigest() == empreinte
    (SORTIE / "integrite_test_2025.txt").write_text(empreinte + "\n",encoding="utf-8")
    ecrire_resume(SORTIE, "Validation 2024",
                  "Parametres fixes avant 2024 ; previsions J+1 emises a J14, coupure commune J8. "
                  "La meteo parfaite n'est pas deployable. Les delais de publication sont supposes. "
                  "Le test 2025 n'est pas evalue. Voir ../../docs/08_validation_2024.md.", bilan.reset_index())


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
        sauver_audit(SORTIE)
