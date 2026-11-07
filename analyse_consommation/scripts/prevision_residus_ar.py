"""Comparer M09 seul et avec correction AR, a 14 h pour les 24 heures de J+1.

Meteo observee (scenario a meteo parfaite), consommation limitee au passe.
"""

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from aligner_meteo_calendrier import preparer
from benchmarks import prevoir_benchmarks
from decomposition_meteo_calendrier import variables, ajuster, MODELES, correlations_blocs, sauver_audit

from resume import ecrire_resume
from chemins_analyse import RESULTATS as DOSSIER
SORTIE = DOSSIER / "07_prevision_ar"
RETARDS = {"M09_AR_court": [1, 2, 3], "M09_AR_saisonnier": [1, 2, 3, 24, 25, 48, 168]}


def prevoir_ar(historique, retards, coefficients, constante, horizon):
    # La fonction ne recoit aucune observation posterieure a la coupure.
    valeurs = list(historique)
    previsions = []
    for _ in range(horizon):
        correction = 0
        for retard, coefficient in zip(retards, coefficients):
            correction += coefficient * valeurs[-retard]
        valeur = constante + correction
        valeurs.append(valeur)
        previsions.append(valeur)
    return np.asarray(previsions)


def graphiques_acf(series, nom):
    fig, axes = plt.subplots(len(series), 2, figsize=(14, 3 * len(series)), squeeze=False)
    lignes = []
    for i, (modele, s) in enumerate(series.items()):
        a, p, n = correlations_blocs(s.dropna())
        lignes.extend({"modele": modele, "retard": k, "ACF": a[k], "PACF": p[k], "paires": n[k]}
                      for k in range(len(a)))
        for ax, valeurs, titre in zip(axes[i], [a, p], ["ACF", "PACF"]):
            ax.vlines(range(1, 337), 0, valeurs[1:], linewidth=.8)
            ax.axhline(0, color="black", linewidth=.5)
            for r in [24, 168]:
                ax.axvline(r, color="grey", linestyle=":")
            ax.set(title=f"{titre} : {modele}", ylim=(-1, 1), xlabel="Retard (heures)")
    fig.suptitle(nom)
    fig.tight_layout(rect=(0, 0, 1, .97))
    fig.savefig(SORTIE / f"acf_pacf_{nom}.png", dpi=170)
    plt.close(fig)
    pd.DataFrame(lignes).to_csv(SORTIE / f"correlations_{nom}.csv", index=False)


def main():
    SORTIE.mkdir(exist_ok=True)
    d = preparer()
    # Masquer les valeurs, sans supprimer de lignes : les retards restent horaires.
    # La meme serie sert aux modeles et aux benchmarks.
    y = d.consommation_MW.mask(d.jour_changement_heure)
    valide = d.utilisable
    x = variables(d.loc[valide], MODELES["M09_interactions"])
    lignes, exclusions, coefficients, erreurs_1h = [], [], [], []
    for annee in [2021, 2022, 2023]:
        # Premier J = 31 decembre : ne pas ajuster sur des observations de ce jour.
        fin_apprentissage = pd.Timestamp(f"{annee}-01-01") - pd.Timedelta(days=1)
        masque = x.index < fin_apprentissage
        coef, constante = ajuster(x, y.reindex(x.index), masque)
        moyenne = pd.Series(np.nan, index=d.index)
        moyenne.loc[x.index] = x @ coef + constante
        e = y - moyenne
        modeles_ar = {}
        diagnostic = pd.DataFrame({"M09_seul": e})
        for nom, retards in RETARDS.items():
            z = pd.DataFrame({str(r): e.shift(r) for r in retards})
            complet = e.notna() & z.notna().all(axis=1)
            entrainement = complet & (z.index < fin_apprentissage)
            c, b = ajuster(z.loc[complet], e.loc[complet], entrainement.loc[complet])
            modeles_ar[nom] = (c.to_numpy(), b)
            diagnostic[nom] = e - (z @ c + b)
            coefficients.append({"annee": annee, "modele": nom,
                                 "fin_apprentissage_exclusive": str(fin_apprentissage),
                                 "n_apprentissage_ar": int(entrainement.sum()),
                                 "constante": float(b), "coefficients": c.to_dict()})
        # Innovations conditionnelles a 1 h : diagnostic distinct des scores J+1.
        diagnostic = diagnostic.loc[diagnostic.index.year == annee].dropna()
        erreurs_1h.append(diagnostic)
        for jour in pd.date_range(f"{annee}-01-01", f"{annee}-12-31", freq="D"):
            origine = jour - pd.Timedelta(days=1) + pd.Timedelta(hours=14)
            coupure = origine - pd.Timedelta(hours=2)  # Derniere etiquette conso : J,12 h.
            dates = pd.date_range(jour, periods=24, freq="h")
            dates_histoire = pd.date_range(coupure - pd.Timedelta(hours=167), coupure, freq="h")
            historique = e.reindex(dates_histoire)
            if not valide.reindex(dates, fill_value=False).all():
                exclusions.append({"jour": jour, "motif": "Cible incomplete ou changement heure"})
                continue
            if historique.isna().any():
                exclusions.append({"jour": jour, "motif": "Historique commun 168 h incomplet"})
                continue
            benchmarks = prevoir_benchmarks(y, dates, coupure)
            if benchmarks is None:
                exclusions.append({"jour": jour, "motif": "Historique des benchmarks incomplet ou changement heure"})
                continue
            # Tous les points du modele de base sont ajustes avant l'origine.
            assert fin_apprentissage <= origine
            assert dates_histoire.max() < origine
            horizon = int((dates[-1] - coupure) / pd.Timedelta(hours=1))
            positions = ((dates - coupure) / pd.Timedelta(hours=1)).astype(int) - 1
            previsions = {"M09_seul": moyenne.loc[dates].to_numpy(), **benchmarks}
            assert (dates[-1] - pd.Timedelta(days=7)) < origine
            for nom, retards in RETARDS.items():
                c, b = modeles_ar[nom]
                correction = prevoir_ar(historique.to_numpy(), retards, c, b, horizon)
                previsions[nom] = previsions["M09_seul"] + correction[positions]
            for nom, valeurs in previsions.items():
                assert np.isfinite(valeurs).all()
                for date, valeur in zip(dates, valeurs):
                    lignes.append({"origine_locale": origine, "derniere_conso_locale": coupure,
                                   "cible_locale": date, "modele": nom,
                                   "observe_MW": y.loc[date], "prevision_MW": valeur})
    p = pd.DataFrame(lignes)
    p["erreur_MW"] = p.observe_MW - p.prevision_MW
    p.to_csv(SORTIE / "previsions.csv", index=False)
    pd.DataFrame(exclusions).to_csv(SORTIE / "jours_exclus.csv", index=False)
    (SORTIE / "coefficients_ar.json").write_text(json.dumps(coefficients, indent=2), encoding="utf-8")
    assert p.groupby(["modele", "origine_locale"]).size().eq(24).all()
    assert p.groupby("modele").size().nunique() == 1
    quotidien = []
    for (nom, origine), bloc in p.groupby(["modele", "origine_locale"]):
        quotidien.append({"modele": nom, "origine_locale": origine,
                          "erreur_energie_MWh": abs(bloc.erreur_MW.sum()),
                          "erreur_pointe_MW": abs(bloc.observe_MW.max() - bloc.prevision_MW.max()),
                          "erreur_heure_pointe": abs(bloc.loc[bloc.observe_MW.idxmax(), "cible_locale"].hour
                                                       - bloc.loc[bloc.prevision_MW.idxmax(), "cible_locale"].hour)})
    q = pd.DataFrame(quotidien)
    q.to_csv(SORTIE / "erreurs_journalieres.csv", index=False)
    bilan = []
    for nom, bloc in p.groupby("modele"):
        jours = q.loc[q.modele.eq(nom)]
        bilan.append({"modele": nom, "jours": len(jours), "MAE_MW": bloc.erreur_MW.abs().mean(),
                      "RMSE_MW": np.sqrt((bloc.erreur_MW**2).mean()), "biais_MW": bloc.erreur_MW.mean(),
                      "MAE_energie_MWh": jours.erreur_energie_MWh.mean(),
                      "MAE_pointe_MW": jours.erreur_pointe_MW.mean(),
                      "MAE_heure_pointe": jours.erreur_heure_pointe.mean()})
    bilan = pd.DataFrame(bilan).sort_values("RMSE_MW")
    bilan.to_csv(SORTIE / "comparaison.csv", index=False)
    annuel = p.assign(annee=p.cible_locale.dt.year).groupby(["modele", "annee"]).erreur_MW.agg(
        MAE_MW=lambda s: s.abs().mean(), RMSE_MW=lambda s: np.sqrt((s**2).mean()))
    annuel.to_csv(SORTIE / "comparaison_annuelle.csv")
    erreurs = p.pivot(index="cible_locale", columns="modele", values="erreur_MW")
    graphiques_acf({nom: erreurs[nom] for nom in ["M09_seul", *RETARDS]}, "erreurs_J_plus_1")
    innovations = pd.concat(erreurs_1h)
    innovations.to_csv(SORTIE / "innovations_conditionnelles_1h.csv", index_label="cible_locale")
    graphiques_acf({nom: innovations[nom] for nom in innovations}, "innovations_conditionnelles_1h")
    fig, ax = plt.subplots(figsize=(12, 5))
    for nom, bloc in p.groupby("modele"):
        profil = bloc.groupby(bloc.cible_locale.dt.hour).erreur_MW.apply(lambda s: s.abs().mean())
        ax.plot(profil.index, profil, label=nom)
    ax.set(xlabel="Heure cible du lendemain", ylabel="MAE (MW)", title="Previsions emises a J,14 h — meteo parfaite")
    ax.legend()
    ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(SORTIE / "erreur_par_heure.png", dpi=180)
    plt.close(fig)
    ecrire_resume(SORTIE, "Correction autoregressive",
                  "Previsions J+1 emises a J14, consommation disponible jusqu'a J12, meteo parfaite. "
                  "Les methodes sont comparees sur les memes jours de 2021-2023. "
                  "Les erreurs J+1 sont distinctes des innovations a un pas. "
                  "Voir ../../docs/07_prevision_ar.md.", bilan)


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
        sauver_audit(SORTIE)
