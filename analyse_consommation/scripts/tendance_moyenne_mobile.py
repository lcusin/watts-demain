"""Estimer la tendance longue par une moyenne mobile centree sur 365 jours."""


import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from resume import ecrire_resume
from chemins_analyse import RESULTATS as DOSSIER, PROJET
SORTIE = DOSSIER / "02_tendance"
FENETRE = 365  # Jour courant et 182 jours de chaque cote.


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    x = pd.read_csv(PROJET / "data/merge/train.csv",
                    usecols=["horodatage", "consommation_MW"], parse_dates=["horodatage"])
    y = x.set_index("horodatage").consommation_MW.sort_index()
    assert y.index.is_unique and np.isfinite(y).all()
    assert y.index.equals(pd.date_range(y.index.min(), y.index.max(), freq="h"))
    assert y.resample("D").count().eq(24).all()

    # La moyenne quotidienne conserve l'unite MW : ce n'est pas une energie.
    quotidien = y.resample("D").mean()
    tendance = quotidien.rolling(FENETRE, center=True, min_periods=FENETRE).mean()
    tableau = pd.DataFrame({"consommation_moyenne_MW": quotidien,
                            "tendance_MW": tendance,
                            "ecart_a_la_tendance_MW": quotidien - tendance})
    tableau.to_csv(SORTIE / "tendance_quotidienne.csv", index_label="date")

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    axes[0].plot(quotidien, color="steelblue", alpha=.45, linewidth=.6,
                 label="Consommation moyenne quotidienne")
    axes[0].plot(tendance, color="darkorange", linewidth=2,
                 label="Moyenne mobile centree sur 365 jours")
    axes[0].set(title="Tendance de long terme — apprentissage 2012–2023", ylabel="MW")
    axes[0].legend()
    axes[1].plot(tableau.ecart_a_la_tendance_MW, color="steelblue", linewidth=.6)
    axes[1].axhline(0, color="black", linewidth=.6)
    axes[1].set(title="Ecart quotidien a la tendance (saisonnalites conservees)",
                 ylabel="MW", xlabel="Date enregistree")
    for ax in axes:
        ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(SORTIE / "tendance_long_terme.png", dpi=180)
    plt.close(fig)

    t = tendance.dropna()
    assert tendance.isna().sum() == FENETRE - 1
    assert np.allclose((tableau.tendance_MW + tableau.ecart_a_la_tendance_MW).loc[t.index],
                       quotidien.loc[t.index])
    ecrire_resume(SORTIE, "Tendance de long terme",
                  "Moyennes quotidiennes en MW, puis moyenne mobile centree sur 365 jours. "
                  "Les 182 jours de chaque bord sont laisses manquants. "
                  "Cette tendance-cycle utilise le futur et sert uniquement a decrire la serie. "
                  f"Entre le {t.index[0]:%Y-%m-%d} et le {t.index[-1]:%Y-%m-%d}, "
                  f"elle passe de {t.iloc[0]:.1f} a {t.iloc[-1]:.1f} MW. "
                  "Cela ne signifie pas que la baisse est reguliere ni corrigee de la meteo.")



if __name__ == "__main__":
    main()
