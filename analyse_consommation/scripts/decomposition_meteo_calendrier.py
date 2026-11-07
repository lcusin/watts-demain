"""Regressions additives conjointes : saisons, calendrier et meteo observee."""

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.stattools import acovf, levinson_durbin
from threadpoolctl import threadpool_limits

from aligner_meteo_calendrier import preparer, SORTIE
from resume import ecrire_resume

AUDIT_AJUSTEMENTS = []
# Par defaut : calendrier complet, sans meteo ni interactions.
MODELES = {
    "M00_saisons": {"semaine": False, "ferie": False, "vacances": False},
    "M01_semaine": {"ferie": False, "vacances": False},
    "M02_feries": {"vacances": False},
    "M03_vacances": {},
    "M04_temperature_lineaire": {"temperature": "lineaire"},
    "M05_temperature_seuils": {"temperature": "seuils"},
    "M06_pluie_seule": {"pluie": True},
    "M07_seuils_pluie": {"temperature": "seuils", "pluie": True},
    "M08_splines_pluie": {"temperature": "splines", "pluie": True},
    "M09_interactions": {"temperature": "splines", "pluie": True, "interactions": True},
    "M10_tendance_flexible": {"temperature": "splines", "pluie": True, "interactions": True, "flexible": True},
    "M11_sans_pluie": {"temperature": "splines", "interactions": True, "flexible": True},
    "M12_sans_vacances": {"vacances": False, "temperature": "splines", "pluie": True, "interactions": True, "flexible": True},
    "M13_sans_feries": {"ferie": False, "temperature": "splines", "pluie": True, "interactions": True, "flexible": True},
    "M14_M09_sans_pluie": {"temperature": "splines", "interactions": True},
    "M15_M09_sans_vacances": {"vacances": False, "temperature": "splines", "pluie": True, "interactions": True},
    "M16_M09_sans_feries": {"ferie": False, "temperature": "splines", "pluie": True, "interactions": True},
    "M17_M09_sans_temperature": {"pluie": True, "interactions": True},
}


def variables(d, config):
    semaine = config.get("semaine", True)
    ferie = config.get("ferie", True)
    vacances = config.get("vacances", True)
    temperature = config.get("temperature", "aucune")
    pluie = config.get("pluie", False)
    interactions = config.get("interactions", False)
    flexible = config.get("flexible", False)
    t = (d.index - pd.Timestamp("2012-01-01")).total_seconds().to_numpy() / (365.2425 * 86400)
    colonnes = {"tendance_t": t}
    if flexible:
        for annee in [2015, 2018, 2020]:
            noeud = (pd.Timestamp(f"{annee}-01-01") - pd.Timestamp("2012-01-01")).days / 365.2425
            colonnes[f"tendance_{annee}"] = np.maximum(t - noeud, 0)
    for k in range(1, 4):
        colonnes[f"annuel_sin{k}"] = np.sin(2 * np.pi * k * t)
        colonnes[f"annuel_cos{k}"] = np.cos(2 * np.pi * k * t)
    for h in range(1, 24):
        colonnes[f"heure_{h}"] = (d.index.hour == h).astype(float)
    if semaine:
        for jour in range(1, 7):
            for h in range(24):
                colonnes[f"semaine_{jour}_{h}"] = ((d.index.dayofweek == jour) & (d.index.hour == h)).astype(float)
    if ferie:
        colonnes["ferie_principal"] = d.jour_ferie.to_numpy()
        if interactions:
            for h in range(1, 24):
                colonnes[f"ferie_heure_{h}"] = d.jour_ferie.to_numpy() * (d.index.hour == h)
    if vacances:
        for zone in "ABC":
            colonnes[f"vacances_{zone}"] = d[f"vacances_{zone}"].to_numpy()
    if temperature == "lineaire":
        colonnes["temperature_lineaire"] = d.temperature.to_numpy()
    elif temperature == "seuils":
        colonnes["temperature_froid"] = np.maximum(18 - d.temperature.to_numpy(), 0)
        colonnes["temperature_chaud"] = np.maximum(d.temperature.to_numpy() - 22, 0)
    elif temperature == "splines":
        colonnes["temperature_lineaire"] = d.temperature.to_numpy()
        for seuil in [0, 5, 10, 15, 20, 25]:
            colonnes[f"temperature_noeud_{seuil}"] = np.maximum(d.temperature.to_numpy() - seuil, 0)
    if interactions and temperature != "aucune":
        for h in [6, 12, 18]:
            plage = (d.index.hour >= h) & (d.index.hour < h + 6)
            colonnes[f"temperature_froid_heure_{h}"] = np.maximum(18 - d.temperature.to_numpy(), 0) * plage
            colonnes[f"temperature_chaud_heure_{h}"] = np.maximum(d.temperature.to_numpy() - 22, 0) * plage
    if pluie:
        colonnes["pluie_log"] = np.log1p(d.pluie.to_numpy())
    x = pd.DataFrame(colonnes, index=d.index)
    return x


def ajuster(x, y, masque):
    # Moindres carres ordinaires avec constante, sans penalisation.
    apprentissage = x.loc[masque]
    modele = LinearRegression().fit(apprentissage, y.loc[masque])
    assert modele.rank_ == len(x.columns), "Variables redondantes dans la regression"
    AUDIT_AJUSTEMENTS.append({"debut": str(apprentissage.index.min()),
                              "fin": str(apprentissage.index.max()),
                              "n": len(apprentissage), "variables": len(x.columns),
                              "rang": int(modele.rank_), "estimateur": "moindres_carres"})
    return pd.Series(modele.coef_, index=x.columns), float(modele.intercept_)


def sauver_audit(dossier):
    pd.DataFrame(AUDIT_AJUSTEMENTS).to_csv(dossier / "audit_moindres_carres.csv", index=False)


def correlations_blocs(s, retards=336):
    # Ne jamais recoller deux heures separees par une exclusion.
    dates = s.index.to_series()
    blocs = (dates.diff().ne(pd.Timedelta(hours=1)) | dates.dt.year.ne(dates.dt.year.shift())).cumsum()
    numerateur = np.zeros(retards + 1)
    paires = np.zeros(retards + 1, dtype=int)
    moyenne = s.mean()
    for _, bloc in s.groupby(blocs.to_numpy()):
        z = bloc.to_numpy() - moyenne
        taille = min(retards, len(z) - 1)
        numerateur[:taille + 1] += acovf(z, demean=False, fft=True, nlag=taille) * len(z)
        paires[:taille + 1] += len(z) - np.arange(taille + 1)
    # Somme des autocovariances biaisees des blocs : pas de correlation a travers les trous.
    a = numerateur / numerateur[0]
    p = levinson_durbin(a, nlags=retards, isacov=True)[2]
    return a, p, paires


def dessiner_acf(residus, nom):
    mesures, toutes = [], []
    noms = list(residus)
    for debut in range(0, len(noms), 4):
        page = noms[debut:debut + 4]
        fig, axes = plt.subplots(len(page), 2, figsize=(14, len(page) * 3), squeeze=False)
        for ligne, modele in enumerate(page):
            s = residus[modele].dropna()
            a, p, paires = correlations_blocs(s)
            mesures.append({"modele": modele, "n": len(s), "ACF_1": a[1], "ACF_24": a[24],
                            "ACF_168": a[168], "moyenne_ACF_carree": np.mean(a[1:]**2)})
            toutes.extend({"modele": modele, "retard": k, "ACF": a[k], "PACF": p[k], "paires": paires[k]}
                          for k in range(len(a)))
            for ax, v, titre in zip(axes[ligne], [a, p], ["ACF", "PACF"]):
                ax.vlines(range(1, 337), 0, v[1:], linewidth=.7)
                ax.axhline(0, color="black", linewidth=.5)
                for k in [24, 168]:
                    ax.axvline(k, color="grey", linestyle=":")
                ax.set(title=f"{titre} — {modele}", xlabel="Retard (heures)", ylim=(-1, 1))
        fig.suptitle(f"{nom} — correlations calculees par blocs horaires continus")
        fig.tight_layout(rect=(0, 0, 1, .97))
        fig.savefig(SORTIE / f"acf_pacf_{nom}_{debut // 4 + 1:02}.png", dpi=160)
        plt.close(fig)
    pd.DataFrame(mesures).to_csv(SORTIE / f"diagnostics_{nom}.csv", index=False)
    pd.DataFrame(toutes).to_csv(SORTIE / f"correlations_{nom}.csv", index=False)


def main():
    d = preparer()
    d = d.loc[d.utilisable].copy()  # Support identique pour toutes les variantes.
    y = d.consommation_MW
    residus, hors_echantillon, scores, parametres = {}, {}, [], {}
    for nom, config in MODELES.items():
        x = variables(d, config)
        erreurs = pd.Series(np.nan, index=d.index)
        for annee in [2021, 2022, 2023]:
            apprentissage = d.index.year < annee
            evaluation = d.index.year == annee
            coef, constante = ajuster(x, y, apprentissage)
            erreur = y.loc[evaluation] - (x.loc[evaluation] @ coef + constante)
            erreurs.loc[evaluation] = erreur
            scores.append({"modele": nom, "annee": annee, "n": len(erreur),
                           "MAE_MW": erreur.abs().mean(), "RMSE_MW": np.sqrt((erreur**2).mean()),
                           "biais_MW": erreur.mean(), "nb_variables": len(coef)})
        hors_echantillon[nom] = erreurs.dropna()
        coef, constante = ajuster(x, y, np.ones(len(d), dtype=bool))
        residus[nom] = y - (x @ coef + constante)
        parametres[nom] = {"constante": float(constante), "coefficients": coef.to_dict()}
    pd.DataFrame(scores).to_csv(SORTIE / "scores_par_annee.csv", index=False)
    bilan = pd.DataFrame([{"modele": nom, "MAE_MW": s.abs().mean(), "RMSE_MW": np.sqrt((s**2).mean()),
                           "biais_MW": s.mean(), "n": len(s)} for nom, s in hors_echantillon.items()])
    bilan = bilan.sort_values("RMSE_MW")
    bilan.to_csv(SORTIE / "comparaison_2021_2023.csv", index=False)
    pd.DataFrame(residus).to_csv(SORTIE / "residus_descriptifs.csv", index_label="heure_locale")
    pd.DataFrame(hors_echantillon).to_csv(SORTIE / "residus_2021_2023.csv", index_label="heure_locale")
    (SORTIE / "coefficients.json").write_text(json.dumps(parametres, indent=2), encoding="utf-8")
    dessiner_acf({"consommation_brute": y, **residus}, "descriptif_2012_2023")
    dates_evaluation = next(iter(hors_echantillon.values())).index
    dessiner_acf({"consommation_brute": y.loc[dates_evaluation], **hors_echantillon}, "evaluation_2021_2023")

    meilleur = bilan.iloc[0].modele
    x = variables(d, MODELES[meilleur])
    coef = pd.Series(parametres[meilleur]["coefficients"])
    constante = parametres[meilleur]["constante"]
    composantes = pd.DataFrame(index=d.index)
    for groupe in ["tendance", "annuel", "heure", "semaine", "ferie", "vacances", "temperature", "pluie"]:
        cols = [c for c in x if c.startswith(groupe + "_")]
        composantes[groupe] = x[cols] @ coef[cols] if cols else 0.
    # Centrer les composantes pour faciliter la lecture ; reporter le niveau dans la constante.
    centres = composantes.mean()
    composantes -= centres
    composantes["niveau"] = constante + centres.sum()
    composantes["ajustement"] = composantes.sum(axis=1)
    composantes["consommation"] = y
    composantes["residu"] = y - composantes.ajustement
    np.testing.assert_allclose(composantes.residu, residus[meilleur], atol=1e-7)
    composantes.to_csv(SORTIE / "composantes_modele_retenu.csv", index_label="heure_locale")
    fig, axes = plt.subplots(4, 1, figsize=(14, 11))
    mois = composantes.resample("MS").mean()
    axes[0].plot(mois.index, mois.consommation, label="Consommation")
    axes[0].plot(mois.index, mois.ajustement, label="Ajustement descriptif")
    for groupe in ["tendance", "annuel", "temperature", "pluie"]:
        axes[1].plot(mois.index, mois[groupe], label=groupe)
    for groupe in ["ferie", "vacances", "semaine"]:
        axes[2].plot(mois.index, mois[groupe], label=groupe)
    axes[3].plot(mois.index, mois.residu, label="Residu moyen mensuel")
    for ax in axes:
        ax.set(ylabel="MW")
        ax.legend(ncol=3)
        ax.grid(alpha=.2)
    fig.suptitle(f"{meilleur} — composantes estimees conjointement, non causales")
    fig.tight_layout(rect=(0, 0, 1, .97))
    fig.savefig(SORTIE / "decomposition_retenue.png", dpi=180)
    plt.close(fig)
    # Courbes de contribution meteo a contexte identique, aux heures 0, 6, 12 et 18.
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for heure in [0, 6, 12, 18]:
        for variable, groupe, ax, grille in [
            ("temperature", "temperature_", axes[0], np.linspace(d.temperature.quantile(.01), d.temperature.quantile(.99), 100)),
            ("pluie", "pluie_", axes[1], np.linspace(0, d.pluie.quantile(.99), 100))]:
            scenario = pd.concat([d.iloc[[0]]] * len(grille))
            scenario.index = pd.DatetimeIndex([pd.Timestamp("2019-01-07") + pd.Timedelta(hours=heure)] * len(grille))
            scenario[variable] = grille
            design = variables(scenario, MODELES[meilleur])
            cols = [c for c in design if c.startswith(groupe)]
            effet = (design[cols] @ coef[cols]).to_numpy() if cols else np.zeros(len(grille))
            ax.plot(grille, effet - effet[len(effet)//2], label=f"{heure} h")
            ax.set(xlabel="Temperature (C)" if variable == "temperature" else "Pluie (mm/h)", ylabel="Contribution relative (MW)")
    for ax in axes:
        ax.legend()
        ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(SORTIE / "effets_meteo.png", dpi=180)
    plt.close(fig)
    # Contributions calendaires : contexte fixe, pour ne pas confondre effet et meteo.
    scenario = pd.concat([d.iloc[[0]]] * 168)
    scenario.index = pd.date_range("2019-01-07", periods=168, freq="h")
    scenario["jour_ferie"] = 0
    for zone in "ABC":
        scenario[f"vacances_{zone}"] = 0
    design = variables(scenario, MODELES[meilleur])
    cols = [c for c in design if c.startswith(("heure_", "semaine_"))]
    prediction_reference = (design[cols] @ coef[cols]).to_numpy()
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    niveau = prediction_reference.reshape(7, 24)
    for jour, label in enumerate(["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]):
        axes[0].plot(range(24), niveau[jour] - niveau[0], label=label)
    axes[0].set(title="Profil relatif au lundi (contexte fixe)", xlabel="Heure", ylabel="MW")
    # Ne calculer que la contribution des colonnes calendaires, sans tendance/date.
    scenario["jour_ferie"] = 1
    f = variables(scenario, MODELES[meilleur])
    cols = [c for c in f if c.startswith("ferie_")]
    effet = (f[cols] @ coef[cols]).to_numpy() if cols else np.zeros(168)
    axes[1].plot(range(24), effet[:24])
    axes[1].set(title="Effet associe aux jours feries", xlabel="Heure", ylabel="MW")
    axes[2].bar(list("ABC"), [coef.get(f"vacances_{z}", 0) for z in "ABC"])
    axes[2].set(title="Effet associe aux vacances par zone", ylabel="MW")
    axes[0].legend(ncol=2)
    for ax in axes:
        ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(SORTIE / "effets_calendrier.png", dpi=180)
    plt.close(fig)
    ecrire_resume(SORTIE, "Meteo et calendrier",
                  f"Meilleure RMSE interne : {meilleur}. Estimation par moindres carres. "
                  "Evaluation 2021-2023 avec apprentissage sur les annees precedentes. "
                  "La meteo observee est un scenario a meteo parfaite. "
                  "La decomposition descriptive est reajustee sur 2012-2023. "
                  "Les contributions ne sont pas des effets causaux. Voir ../../docs/06_meteo_calendrier.md.", bilan)


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
        sauver_audit(SORTIE)
