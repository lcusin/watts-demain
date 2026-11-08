"""Figures du test final, à partir des seules prévisions déjà enregistrées."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


RACINE = Path(__file__).resolve().parent.parent
TEST = RACINE / "results/test_2025"
FIGURES = TEST / "figures"
NOM = "Random Forest"


def tracer_semaines(previsions):
    # Sept jours admis, lundi-dimanche, dans le mois indiqué ; semaine centrale
    # choisie par proximité du jeudi avec le 15, jamais selon les erreurs.
    jours = previsions.horodatage.dt.normalize()
    complets = previsions.groupby(jours).horodatage.nunique().eq(24)
    saisons = [("Hiver", 1), ("Printemps", 4), ("Été", 7), ("Automne", 10)]
    choix = []
    for saison, mois in saisons:
        centre = pd.Timestamp(2025, mois, 15)
        candidats = [jour for jour in complets.index if jour.weekday() == 0
                     and all(complets.get(jour + pd.Timedelta(days=i), False) for i in range(7))]
        dans_mois = [jour for jour in candidats if jour.month == mois
                     and (jour + pd.Timedelta(days=6)).month == mois]
        if dans_mois:
            candidats = dans_mois
        if not candidats:
            raise ValueError(f"Aucune semaine complète admissible pour {saison.lower()}")
        debut = min(candidats, key=lambda jour: (abs((jour + pd.Timedelta(days=3) - centre).days), jour))
        choix.append((saison, debut))
        print(f"{saison} : {debut:%d/%m/%Y} au {debut + pd.Timedelta(days=6):%d/%m/%Y} "
              f"(jeudi le plus proche du 15/{mois:02d} ; mois voisin si aucune semaine admissible dans le mois)")

    minimum = previsions[["reel_MW", "prediction_MW"]].min().min()
    maximum = previsions[["reel_MW", "prediction_MW"]].max().max()
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharey=True, layout="constrained")
    for ax, (saison, debut) in zip(axes.flat, choix):
        semaine = previsions.loc[jours.between(debut, debut + pd.Timedelta(days=6))]
        ax.plot(semaine.horodatage, semaine.reel_MW, label="Observé", color="#263c56", linewidth=1.2)
        ax.plot(semaine.horodatage, semaine.prediction_MW, label="Prédit", color="#c36b40", linewidth=1.2)
        ax.set(title=f"{saison} : {debut:%d/%m}–{debut + pd.Timedelta(days=6):%d/%m/%Y}",
               ylim=(minimum * 0.95, maximum * 1.05))
        ax.set_xlim(debut, debut + pd.Timedelta(days=7))
        ax.set_xticks([debut + pd.Timedelta(days=i) for i in range(7)],
                      [f"{nom} {(debut + pd.Timedelta(days=i)).day:02d}"
                       for i, nom in enumerate(["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"])])
        ax.tick_params(axis="x", labelrotation=35)
        ax.grid(alpha=0.15)
    for ax in axes[:, 0]:
        ax.set_ylabel("Consommation (MW)")
    fig.legend(*axes[0, 0].get_legend_handles_labels(), loc="outside upper center", ncol=2, frameon=False)
    fig.savefig(FIGURES / "observe_vs_predit_2025.png", dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annee-seule", action="store_true")
    parser.add_argument("--semaines-seules", action="store_true")
    args = parser.parse_args()
    validation = pd.read_csv(RACINE / "results/analyse_2024/comparaison_globale.csv")
    test = pd.read_csv(TEST / "comparaison_test_2025.csv")
    previsions = pd.read_csv(TEST / "previsions_test_2025.csv", parse_dates=["horodatage"])
    v = validation.loc[(validation.famille == "ml") & (validation.modele == NOM)]
    t = test.loc[(test.famille == "ml") & (test.modele == NOM)]
    if len(v) != 1 or len(t) != 1 or set(previsions.modele) != {NOM} or len(previsions) != int(t.heures.iloc[0]):
        raise ValueError("Résultats Random Forest absents ou incohérents")
    previsions = previsions.sort_values("horodatage")
    if previsions.horodatage.duplicated().any() or not np.isfinite(previsions[["reel_MW", "prediction_MW"]]).all().all():
        raise ValueError("Horodatages dupliqués ou valeurs non finies")
    erreur = previsions.reel_MW - previsions.prediction_MW
    if not np.isclose(np.abs(erreur).mean(), t.MAE_MW.iloc[0]) or not np.isclose(
            np.sqrt(np.mean(erreur ** 2)), t.RMSE_MW.iloc[0]):
        raise ValueError("Les scores 2025 ne correspondent pas aux prévisions")

    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    if args.semaines_seules:
        tracer_semaines(previsions)
        return

    # Les jours non évalués restent absents des courbes, sans interpolation.
    quotidien = previsions.groupby(previsions.horodatage.dt.normalize())[
        ["reel_MW", "prediction_MW"]].mean()
    quotidien = quotidien.reindex(pd.date_range("2025-01-01", "2025-12-31", freq="D"))
    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.plot(quotidien.index, quotidien.reel_MW, label="Observé", color="#263c56", linewidth=1.2)
    ax.plot(quotidien.index, quotidien.prediction_MW, label="Prédit", color="#c36b40", linewidth=1.2)
    ax.set(title="Test 2025 : consommation moyenne journalière",
           xlabel="Date (heure française)", ylabel="Consommation moyenne journalière (MW)")
    ax.legend(frameon=False)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(FIGURES / "observe_vs_predit_annee_2025.png", dpi=200)
    plt.close(fig)
    if args.annee_seule:
        return

    metriques = ["MAE_MW", "RMSE_MW"]
    x = np.arange(2)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for decalage, donnees, annee, couleur in [(-0.18, v, "Validation 2024", "#516b8b"),
                                               (0.18, t, "Test 2025", "#c36b40")]:
        valeurs = donnees[metriques].iloc[0].to_numpy(dtype=float)
        barres = ax.bar(x + decalage, valeurs, width=0.34, color=couleur, label=annee)
        ax.bar_label(barres, fmt="%.0f", padding=3)
    ax.set(xticks=x, xticklabels=["MAE", "RMSE"], ylabel="Erreur (MW)",
           title="Random Forest : validation et test final")
    ax.legend(frameon=False)
    ax.set_ylim(0, max(v[metriques].max(axis=1).iloc[0], t[metriques].max(axis=1).iloc[0]) * 1.18)
    fig.tight_layout()
    fig.savefig(FIGURES / "comparaison_2024_2025.png", dpi=200)
    plt.close(fig)

    tracer_semaines(previsions)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(erreur, bins=45, color="#516b8b", edgecolor="white", linewidth=0.4)
    ax.axvline(0, color="#c36b40", linewidth=1.5)
    ax.set(title="Distribution des erreurs horaires — test 2025",
           xlabel="Observé − prédit (MW)", ylabel="Nombre d'heures")
    fig.tight_layout()
    fig.savefig(FIGURES / "distribution_erreurs_2025.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    main()
