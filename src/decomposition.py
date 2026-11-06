"""Analyse descriptive sur train.csv : trois cycles saisonniers et ACF/PACF.
Execution : python src/decomposition.py
Les ajustements utilisent toute la periode d'apprentissage : pas des previsions.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.tsa.stattools import acovf, levinson_durbin
from modele_decomposition import matrices

racine = Path(__file__).resolve().parent.parent
sortie = racine / "results/decomposition"
sortie.mkdir(parents=True, exist_ok=True)

x = pd.read_csv(racine / "data/merge/train.csv", parse_dates=["horodatage"])
x = x.set_index("horodatage").sort_index()
y = x["consommation_MW"]

# Methode retenue apres validation chronologique interne (voir COMPARAISON_METHODES.md).
X, _ = matrices(x, x, "seuils")
manquants = x[["temperature_moyenne", "precipitation_moyenne"]].isna()

# Un seul ajustement sur la consommation brute.
beta = pd.Series(np.linalg.lstsq(X, y, rcond=None)[0], index=X.columns)
resultats = pd.DataFrame({"consommation_MW": y})
composantes = {
    "cycle_annuel": [v for v in X if v.startswith("annuel_")],
    "effet_temperature": ["temperature_froid", "temperature_chaud"],
    "effet_precipitations": ["pluie"],
}
for nom, colonnes in composantes.items():
    effet = X[colonnes].dot(beta[colonnes])
    resultats[nom] = effet - effet.mean()

# Separer le profil de semaine en profil journalier moyen et ecarts selon le jour.
profil = np.r_[0, beta[[f"semaine_{h}" for h in range(1, 168)]]].reshape(7, 24)
journalier = profil.mean(axis=0)
hebdomadaire = profil - journalier
resultats["cycle_journalier"] = journalier[x.index.hour]
resultats["cycle_hebdomadaire"] = hebdomadaire[x.index.dayofweek, x.index.hour]
for nom in ["cycle_journalier", "cycle_hebdomadaire"]:
    resultats[nom] -= resultats[nom].mean()

# Soustraire les contributions choisies, sans retirer la tendance.
resultats["sans_annuel"] = y - resultats["cycle_annuel"]
resultats["sans_annuel_hebdomadaire"] = resultats["sans_annuel"] - resultats["cycle_hebdomadaire"]
resultats["sans_saisonnalites"] = resultats["sans_annuel_hebdomadaire"] - resultats["cycle_journalier"]
for nom in ["temperature", "precipitations"]:
    resultats["sans_" + nom] = resultats["sans_saisonnalites"] - resultats["effet_" + nom]
resultats["sans_meteo"] = resultats["sans_temperature"] - resultats["effet_precipitations"]
comparaison = ["sans_saisonnalites", "sans_temperature", "sans_precipitations", "sans_meteo"]


def tracer(tableau, fichier):
    axes = tableau.plot(subplots=True, figsize=(12, 2 * len(tableau.columns)), legend=False)
    for ax, nom in zip(axes, tableau.columns):
        ax.set_title(nom.replace("_", " "))
        ax.set_ylabel("MW")
    plt.tight_layout()
    plt.savefig(sortie / fichier, dpi=160)
    plt.close()


# Vue longue pour le cycle annuel, puis quatre semaines pour les cycles courts.
tracer(resultats[["consommation_MW", "cycle_annuel", "sans_saisonnalites"]]
       .resample("D").mean(), "01_decomposition_annuelle.png")
tracer(resultats[["consommation_MW", "cycle_annuel", "cycle_hebdomadaire",
                  "cycle_journalier", "sans_saisonnalites"]].iloc[24 * 31:24 * 59], "02_decomposition_saisonniere.png")
tracer(resultats[comparaison].resample("D").mean(), "05_correction_meteo_annuelle.png")
tracer(resultats[comparaison].iloc[24 * 31:24 * 59], "06_correction_meteo_horaire.png")

# Meme grille temporelle et memes observations pour toutes les comparaisons.
groupes = {
    "03_acf_pacf.png": ["consommation_MW", "sans_annuel",
                        "sans_annuel_hebdomadaire", "sans_saisonnalites"],
    "04_acf_pacf_composantes.png": ["cycle_annuel",
                                   "cycle_hebdomadaire", "cycle_journalier"],
    "07_acf_pacf_meteo.png": comparaison,
    "08_acf_pacf_effets_meteo.png": ["effet_temperature", "effet_precipitations"],
}
for fichier, series in groupes.items():
    fig, axes = plt.subplots(len(series), 2, figsize=(14, 3 * len(series)))
    for ligne, v in enumerate(series):
        plot_acf(resultats[v], lags=336, fft=True, zero=False, ax=axes[ligne, 0], title=f"ACF - {v}")
        covariances = acovf(resultats[v], fft=True, nlag=336)
        pacf = levinson_durbin(covariances, nlags=336, isacov=True)[2][1:]
        ax = axes[ligne, 1]
        ax.vlines(np.arange(1, 337), 0, pacf)
        ax.axhline(0, color="black", linewidth=0.5)
        seuil = 1.96 / np.sqrt(len(resultats))
        ax.axhspan(-seuil, seuil, alpha=0.2)
        ax.set(title=f"PACF - {v}", ylim=(-1, 1))
        for ax in axes[ligne]:
            ax.set_xlabel("Retard (heures)")
            for retard in (24, 168):
                ax.axvline(retard, color="grey", linestyle=":", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(sortie / fichier, dpi=160)
    plt.close(fig)

resultats.to_csv(sortie / "composantes.csv", index_label="horodatage", date_format="%Y-%m-%d %H:%M:%S")
beta.rename("coefficient").to_csv(sortie / "coefficients_regression.csv", index_label="variable")
beta[["temperature_froid", "temperature_chaud", "pluie"]].rename("coefficient").to_csv(sortie / "coefficients_meteo.csv", index_label="variable")
manquants.to_csv(sortie / "imputations_meteo.csv", index_label="horodatage")
diagnostic = pd.DataFrame({"ecart_type_MW": resultats[comparaison].std()})
for retard in (1, 24, 168):
    diagnostic[f"autocorrelation_{retard}h"] = [resultats[v].autocorr(retard) for v in comparaison]
diagnostic.to_csv(sortie / "comparaison_meteo.csv", index_label="serie")
