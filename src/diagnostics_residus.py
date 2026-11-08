"""Diagnostiquer les erreurs de prevision des modeles AR et ARMA."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from statsmodels.stats.diagnostic import acorr_ljungbox


RACINE = Path(__file__).resolve().parent.parent
ENTREE = RACINE / "results" / "analyse_2024" / "statistiques" / "previsions_horaires_2024.csv"
SORTIE = RACINE / "results" / "analyse_2024" / "diagnostics_residus"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--graphique-seul", action="store_true")
    args = parser.parse_args()
    previsions = pd.read_csv(ENTREE, parse_dates=["horodatage"])
    previsions["residu_MW"] = previsions.reel_MW - previsions.prediction_MW
    SORTIE.mkdir(parents=True, exist_ok=True)

    criteres = previsions.groupby("modele", as_index=False)[["AIC", "BIC"]].first()
    if not args.graphique_seul:
        criteres.to_csv(SORTIE / "aic_bic.csv", index=False)

    tests = []
    modeles = sorted(previsions.modele.unique())
    fig, axes = plt.subplots(len(modeles), 1, figsize=(11, 3.5 * len(modeles)), squeeze=False)
    for ax, nom in zip(axes[:, 0], modeles):
        residus = previsions.loc[previsions.modele.eq(nom)].set_index("horodatage")
        residus = residus.residu_MW.sort_index().asfreq("h")
        # Plus long bloc horaire continu pour les erreurs de prevision.
        groupes = residus.dropna().groupby(residus.isna().cumsum())
        bloc = groupes.get_group(groupes.size().idxmax())
        retards = range(1, 169)
        ax.vlines(retards, 0, [bloc.autocorr(h) for h in retards])
        ax.axhline(0, color="black", linewidth=0.7)
        ax.set_title(f"Erreurs de prevision - {nom} - bloc continu : {len(bloc):,} h".replace(",", " "))
        ax.set(xlabel="Retard (heures)", ylabel="Autocorrelation")

        if args.graphique_seul:
            continue
        lags = [h for h in (24, 168) if h < len(bloc)]
        if not lags:
            continue
        test = acorr_ljungbox(bloc, lags=lags, return_df=True)
        for retard, ligne in test.iterrows():
            tests.append({
                "modele": nom,
                "retard": retard,
                "statistique": ligne.lb_stat,
                "p_value": ligne.lb_pvalue,
                "debut_bloc": bloc.index.min(),
                "fin_bloc": bloc.index.max(),
                "heures_bloc": len(bloc),
            })
    fig.suptitle("ACF des erreurs de prevision (pas des innovations des modeles ajustes)")
    fig.tight_layout()
    fig.savefig(SORTIE / "acf_residus.png", dpi=180)
    plt.close(fig)

    if args.graphique_seul:
        return
    tests = pd.DataFrame(tests)
    tests.to_csv(SORTIE / "ljung_box.csv", index=False)
    print(criteres.round(1).to_string(index=False))
    print("\nTest de Ljung-Box sur le plus long bloc continu :")
    print(tests.to_string(index=False))


if __name__ == "__main__":
    main()
