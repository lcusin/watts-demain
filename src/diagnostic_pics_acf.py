"""Reperer les pics positifs et negatifs des series differenciees."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from statsmodels.tsa.stattools import acf

sortie = Path(__file__).resolve().parent.parent / "results/differenciation"
x = pd.read_csv(sortie / "series_differenciees.csv")
noms = ["difference_52_semaines", "difference_52_semaines_puis_24h",
        "difference_52_semaines_puis_24h_puis_1h"]
fig, axes = plt.subplots(len(noms), 2, figsize=(15, 4.5 * len(noms)))
pics, reperes = [], []
for ligne, nom in enumerate(noms):
    a = acf(x[nom], nlags=9000, fft=True)
    ax = axes[ligne, 0]
    ax.plot(np.arange(1, 337), a[1:337])
    for signe, etiquette in [(1, "maximum"), (-1, "minimum")]:
        positions, details = find_peaks(signe * a[:338], prominence=.02)
        for k, proeminence in zip(positions, details["prominences"]):
            if 1 <= k <= 336:
                pics.append({"serie": nom, "type": etiquette, "retard_heures": k,
                             "ACF": a[k], "proeminence": proeminence})
        positions = [k for k in positions if 1 <= k <= 336]
        meilleurs = sorted(positions, key=lambda k: signe * a[k], reverse=True)[:5]
        ax.scatter(meilleurs, a[meilleurs], s=20)
        for k in meilleurs:
            ax.annotate(f"{k} h", (k, a[k]), xytext=(0, 10 if signe == 1 else -17),
                        textcoords="offset points", ha="center", fontsize=8)
    ax.set_title(nom + " : retards courts")
    ax = axes[ligne, 1]
    ax.plot(np.arange(1, 9001), a[1:])
    ax.axvline(8736, linestyle=":", color="red", label="52 semaines")
    ax.scatter([8736], [a[8736]], color="red", s=20)
    ax.set_title(nom + " : retards longs")
    ax.legend()
    for ax in axes[ligne]:
        seuil = 1.96 / np.sqrt(len(x))
        ax.axhspan(-seuil, seuil, alpha=.15)
        ax.axhline(0, color="grey", linewidth=.5)
        ax.set(xlabel="Retard (heures)", ylabel="ACF")
    for k in [1, 6, 12, 15, 24, 48, 72, 168, 336, 8736, 8760, 8784]:
        reperes.append({"serie": nom, "retard_heures": k, "ACF": a[k]})
fig.tight_layout()
fig.savefig(sortie / "04_pics_acf.png", dpi=160)
plt.close(fig)
pd.DataFrame(pics).to_csv(sortie / "pics_acf.csv", index=False)
pd.DataFrame(reperes).to_csv(sortie / "reperes_acf.csv", index=False)
