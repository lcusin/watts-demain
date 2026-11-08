"""Mesurer l'apport du calendrier, de la consommation et de la meteo."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline

from modeles_ml import charger, creer_exemples
from protocole import jours_communs


RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "results" / "analyse_2024" / "ablation"


def tracer(resultats):
    fig, ax = plt.subplots(figsize=(9, 5))
    barres = ax.barh(resultats.variables, resultats.RMSE_MW, color="steelblue")
    ax.bar_label(barres, labels=[f"{valeur:.2f}" for valeur in resultats.RMSE_MW], padding=4)
    ax.set_xlim(0, resultats.RMSE_MW.max() * 1.16)
    ax.invert_yaxis()
    ax.set(title="Ablation des groupes de variables - validation 2024",
           xlabel="RMSE (MW)")
    ax.grid(axis="x", alpha=.2)
    fig.tight_layout()
    fig.savefig(SORTIE / "comparaison_ablation.png", dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--graphique-seul", action="store_true")
    args = parser.parse_args()
    if args.graphique_seul:
        tracer(pd.read_csv(SORTIE / "comparaison_ablation.csv"))
        return
    train = charger("train.csv")
    validation = charger("validation.csv")
    donnees = pd.concat([train, validation], ignore_index=True)
    donnees = donnees.sort_values(["horodatage", "ordre_original"]).reset_index(drop=True)
    donnees["occurrence"] = donnees.groupby("horodatage").cumcount()

    debut_train = train.jour.min() + pd.Timedelta(days=30)
    fin_train = validation.jour.min() - pd.Timedelta(days=2)
    jours_train = jours_communs(donnees, debut_train, fin_train)
    jours_validation = jours_communs(donnees, validation.jour.min(), validation.jour.max())
    X_train, y_train, _ = creer_exemples(donnees, jours_train)
    X_validation, y_validation, _ = creer_exemples(donnees, jours_validation)

    calendrier = [
        c for c in X_train
        if c in ["jour_changement_heure", "lundi", "mardi", "mercredi", "jeudi",
                 "vendredi", "samedi", "dimanche", "weekend", "jour_ferie",
                 "vacances_A", "vacances_B", "vacances_C", "vacances_scolaires",
                 "mois", "jour_annee_sin", "jour_annee_cos", "heure_cible",
                 "heure_sin", "heure_cos", "occurrence_heure"]
    ]
    sans_meteo = [
        c for c in X_train
        if "temperature" not in c and "precipitation" not in c
    ]
    groupes = {
        "Calendrier": calendrier,
        "Calendrier + consommation": sans_meteo,
        "Calendrier + consommation + meteo": list(X_train.columns),
    }

    lignes = []
    for nom, colonnes in groupes.items():
        print(nom, "-", len(colonnes), "variables", flush=True)
        modele = make_pipeline(
            SimpleImputer(strategy="median", keep_empty_features=True),
            RandomForestRegressor(
                n_estimators=100, max_depth=15, min_samples_leaf=3,
                random_state=42, n_jobs=-1,
            ),
        )
        modele.fit(X_train[colonnes], y_train)
        prediction = modele.predict(X_validation[colonnes])
        erreur = y_validation - prediction
        lignes.append({
            "variables": nom,
            "nb_variables": len(colonnes),
            "MAE_MW": mean_absolute_error(y_validation, prediction),
            "RMSE_MW": np.sqrt(mean_squared_error(y_validation, prediction)),
            "biais_MW": erreur.mean(),
        })

    resultats = pd.DataFrame(lignes)
    SORTIE.mkdir(parents=True, exist_ok=True)
    resultats.to_csv(SORTIE / "comparaison_ablation.csv", index=False)

    tracer(resultats)
    print(resultats.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
