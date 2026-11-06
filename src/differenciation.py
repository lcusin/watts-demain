"""Comparer les differences a 52 semaines, puis 24 heures et 1 heure sur train.csv.
Execution depuis la racine : python src/differenciation.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.tsa.stattools import acovf, levinson_durbin

racine = Path(__file__).resolve().parent.parent
sortie = racine / "results/differenciation"
sortie.mkdir(parents=True, exist_ok=True)

x = pd.read_csv(racine / "data/merge/train.csv", parse_dates=["horodatage"])
y = x.set_index("horodatage")["consommation_MW"].sort_index().asfreq("h")

# Tendance lineaire descriptive sur les douze annees, sans imposer son signe.
annees = (y.index - y.index[0]).total_seconds() / (365.2425 * 86400)
pente, niveau = np.polyfit(annees, y, 1)
tendance = pd.Series(niveau + pente * annees, index=y.index)
sans_tendance = y - tendance

# 364 jours = 52 semaines : meme jour de semaine et meme heure UTC.
series = pd.DataFrame({
    "consommation_MW": y,
    "sans_tendance": sans_tendance,
    "difference_52_semaines": y - y.shift(freq="364D"),
    "difference_52_semaines_sans_tendance": sans_tendance - sans_tendance.shift(freq="364D"),
}).reindex(y.index)
# Appliquer les deux differences successivement : (1 - B^24)(1 - B^8736).
annuelle = series["difference_52_semaines"]
series["difference_52_semaines_puis_24h"] = annuelle - annuelle.shift(freq="24h")
# Ajouter la difference premiere apres les deux differences saisonnieres.
journaliere = series["difference_52_semaines_puis_24h"]
series["difference_52_semaines_puis_24h_puis_1h"] = journaliere - journaliere.shift(freq="h")
# Comparaison commune apres 364 jours + 24 heures + 1 heure.
series = series.loc[y.index[0] + pd.Timedelta(days=365, hours=1):]

# Apercu horaire de quatre semaines, sans agreger les valeurs.
axes = series.iloc[:24 * 28].plot(subplots=True, figsize=(13, 3 * len(series.columns)), legend=False)
for ax, nom in zip(axes, series.columns):
    ax.set_title(nom.replace("_", " "))
    ax.set_ylabel("MW")
plt.tight_layout()
plt.savefig(sortie / "01_series.png", dpi=160)
plt.close()

# Correlogrammes sur toute la periode commune, jusqu'a deux semaines de retard.
fig, axes = plt.subplots(len(series.columns), 2, figsize=(14, 3 * len(series.columns)))
for ligne, nom in enumerate(series):
    valeurs = series[nom]
    plot_acf(valeurs, lags=336, fft=True, zero=False, bartlett_confint=False,
             ax=axes[ligne, 0], title=f"ACF - {nom}")
    pacf = levinson_durbin(acovf(valeurs, fft=True, nlag=336), nlags=336, isacov=True)[2][1:]
    ax = axes[ligne, 1]
    ax.vlines(np.arange(1, 337), 0, pacf)
    ax.axhline(0, color="black", linewidth=0.5)
    seuil = 1.96 / np.sqrt(len(valeurs))
    ax.axhspan(-seuil, seuil, alpha=0.2)
    ax.set_title(f"PACF - {nom}")
    for ax in axes[ligne]:
        ax.set(xlabel="Retard (heures)", ylim=(-1, 1))
        for retard in (24, 168):
            ax.axvline(retard, color="grey", linestyle=":", linewidth=0.8)
fig.tight_layout()
fig.savefig(sortie / "02_acf_pacf.png", dpi=160)
plt.close(fig)

# Vue longue : verifier visuellement si une droite resume bien l'evolution.
evolution = pd.DataFrame({"consommation_MW": y, "tendance_MW": tendance,
                          "sans_tendance": sans_tendance})
quotidien = evolution.resample("D").mean()
fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True)
quotidien[["consommation_MW", "tendance_MW"]].plot(ax=axes[0])
quotidien["sans_tendance"].plot(ax=axes[1])
axes[0].set_title(f"Tendance lineaire 2012-2023 : {pente:.0f} MW/an")
axes[1].set_title("Consommation moins la tendance lineaire")
for ax in axes:
    ax.set_ylabel("MW")
fig.tight_layout()
fig.savefig(sortie / "03_tendance_12_ans.png", dpi=160)
plt.close(fig)
evolution.to_csv(sortie / "tendance.csv", index_label="horodatage", date_format="%Y-%m-%d %H:%M:%S")
pd.Series({"pente_MW_par_an": pente, "niveau_initial_MW": niveau}).to_csv(sortie / "coefficients_tendance.csv", header=["valeur"])

series.to_csv(sortie / "series_differenciees.csv", index_label="horodatage",
              date_format="%Y-%m-%d %H:%M:%S")
