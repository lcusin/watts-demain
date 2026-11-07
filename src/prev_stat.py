"""
Projet Watts Demain : modèles statistiques de prévision horaire.

Objectif : à 14 h le jour J, prévoir les 24 heures du jour J+1.
Modèles : AR(1), AR(2), ARMA(1,1).
Train : 2012-2023 ; validation : 2024.

On travaille sur la différence hebdomadaire :
Y(t) = X(t) - X(t-168), puis on revient à la consommation en MW.

Le benchmark est traité séparément dans benchmark.py.
Hypothèse : les horodatages sont continus, sans heure manquante ou doublon.
"""

from pathlib import Path
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

# Dossiers du projet
BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data" / "merge"
SORTIE = BASE / "data_temp" / "graphiques" / "previsions_statistiques_horaires"
SORTIE.mkdir(parents=True, exist_ok=True)

# ARIMA(p, 0, q) est utilisé sur la série déjà différenciée de 168 h.
# p = nombre de retards AR ; q = nombre de retards MA.
MODELES = {
    "AR(1)": (1, 0, 0),
    "AR(2)": (2, 0, 0),
    "ARMA(1,1)": (1, 0, 1),
}


def charger(nom):
    """Charger un CSV et vérifier que la consommation est bien horaire."""
    df = pd.read_csv(DATA / nom, parse_dates=["horodatage"])

    # On a besoin de la date/heure et de la consommation.
    if not {"horodatage", "consommation_MW"}.issubset(df.columns):
        raise ValueError(f"Colonnes manquantes dans {nom}")

    # Une heure ne doit pas apparaître deux fois.
    if df["horodatage"].duplicated().any():
        raise ValueError(f"Horodatages dupliqués dans {nom}")

    # Mettre les heures dans l'ordre et en index.
    serie = (
        df.set_index("horodatage")["consommation_MW"]
        .sort_index()
        .astype(float)
        .asfreq("h")
    )

    # asfreq('h') fait apparaître les heures absentes comme NaN.
    if serie.isna().any() or not np.isfinite(serie.to_numpy()).all():
        raise ValueError(f"Heures ou consommations manquantes dans {nom}")

    return serie


def preparer():
    """Charger train/validation et calculer la différence de 168 heures."""
    train = charger("train.csv")
    val = charger("validation.csv")

    # Les deux périodes doivent se suivre sans trou.
    if train.index[-1] + pd.Timedelta(hours=1) != val.index[0]:
        raise ValueError("Train et validation ne sont pas contigus")

    # On garde les valeurs de validation pour les comparer aux prévisions
    # et pour actualiser le modèle seulement quand elles sont déjà connues.
    x = pd.concat([train, val])

    # Différence entre la consommation actuelle et celle d'il y a 7 jours.
    # Exemple : 55 000 - 52 000 = 3 000 MW.
    y = x.diff(168)
    return train, val, x, y


def prevoir_modele(nom, ordre, val, x, y):
    """Entraîner un modèle, puis prévoir chaque journée de validation."""

    # Pour prévoir le 1er janvier 2024, on se place le 31 décembre
    # 2023 à 14 h. La dernière heure supposée connue est 13 h.
    premier_jour = val.index[0].normalize()
    premier_cutoff = premier_jour - pd.Timedelta(days=1) + pd.Timedelta(hours=13)

    # On entraîne uniquement sur les différences disponibles à cette date.
    # dropna() retire les 168 premières heures sans différence calculable.
    y_train = y.loc[:premier_cutoff].dropna()
    print(f"\nEntraînement de {nom} sur {len(y_train)} heures...")

    # fit() estime les coefficients du modèle (AR et éventuellement MA).
    # trend='n' : pas de constante dans le modèle.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        etat = ARIMA(y_train, order=ordre, trend="n").fit()

    aic = float(etat.aic)
    bic = float(etat.bic)
    print(f"{nom} : AIC={aic:.1f}, BIC={bic:.1f}")
    print("Paramètres estimés :")
    print(etat.params)

    # On mémorise jusqu'à quelle heure le modèle connaît les observations.
    dernier_cutoff = premier_cutoff
    lignes = []
    jours = pd.date_range(val.index[0].normalize(), val.index[-1].normalize(), freq="D")

    for numero, jour_cible in enumerate(jours, start=1):
        # La prévision du jour cible est faite la veille à 14 h.
        cutoff = jour_cible - pd.Timedelta(days=1) + pd.Timedelta(hours=13)

        if cutoff > dernier_cutoff:
            # Ajouter seulement les différences observées depuis
            # la dernière prévision, jusqu'à l'heure connue de 13 h.
            nouvelles_y = y.loc[
                dernier_cutoff + pd.Timedelta(hours=1):cutoff
            ]

            # extend() met à jour l'état du modèle sans réestimer
            # ses coefficients sur les données de validation.
            etat = etat.extend(nouvelles_y)
            dernier_cutoff = cutoff

        # De J 13 h à J+1 00 h : 11 pas.
        # De J 13 h à J+1 23 h : 34 pas.
        horizon = int(
            (jour_cible + pd.Timedelta(hours=23) - cutoff)
            / pd.Timedelta(hours=1)
        )

        # Le modèle prédit d'abord les différences Y(t), pas encore X(t).
        differences_prevues = etat.forecast(steps=horizon)

        for heure in range(24):
            # Heure du lendemain que l'on souhaite prévoir.
            cible = jour_cible + pd.Timedelta(hours=heure)
            y_prevu = float(differences_prevues.loc[cible])

            # La consommation à la même heure 7 jours plus tôt
            # est déjà connue au moment de la prévision.
            reference = float(x.loc[cible - pd.Timedelta(hours=168)])

            # Revenir à la consommation originale :
            # X_prévu(t) = X(t-168) + Y_prévu(t).
            prevision_MW = reference + y_prevu

            # Enregistrer le réel et le prévu pour évaluer le modèle.
            lignes.append({
                "horodatage": cible,
                "modele": nom,
                "reel_MW": float(val.loc[cible]),
                "prediction_MW": prevision_MW,
                "AIC": aic,
                "BIC": bic,
            })

        if numero % 60 == 0:
            print(f"{nom} : {numero}/{len(jours)} jours évalués")

    return lignes


def main():
    """Lancer les modèles, comparer leurs erreurs et tracer les prévisions."""
    train, val, x, y = preparer()
    print(f"Train : {len(train)} heures ; validation : {len(val)} heures")

    # Stocker les prévisions des trois modèles statistiques.
    # Le benchmark naïf n'est plus calculé ici : il est dans benchmark.py.
    lignes = []

    for nom, ordre in MODELES.items():
        predictions = prevoir_modele(nom, ordre, val, x, y)
        lignes.extend(predictions)

    # Transformer les résultats en tableau.
    resultats = pd.DataFrame(lignes)

    # Calculer les erreurs de chaque prévision horaire.
    resultats["erreur_absolue"] = (
        resultats["reel_MW"] - resultats["prediction_MW"]
    ).abs()
    resultats["erreur_carree"] = (
        resultats["reel_MW"] - resultats["prediction_MW"]
    ) ** 2

    # Enregistrer toutes les prévisions horaires de 2024.
    resultats.to_csv(SORTIE / "previsions_horaires_2024.csv", index=False)

    # Calculer la MAE et la RMSE de chaque modèle.
    scores = resultats.groupby("modele").agg(
        MAE_MW=("erreur_absolue", "mean"),
        MSE=("erreur_carree", "mean"),
    )
    scores["RMSE_MW"] = np.sqrt(scores.pop("MSE"))
    scores = scores.sort_values("MAE_MW")
    scores.to_csv(SORTIE / "comparaison_2024.csv")

    print("\nComparaison des modèles statistiques sur 2024 :")
    print(scores.round(2))

    # Tracer les consommations réelles et les prévisions du modèle
    # qui a la plus petite MAE, sur les trois premiers jours de 2024.
    gagnant = scores.index[0]
    debut = val.index[0]
    fin = debut + pd.Timedelta(days=3)
    extrait = resultats[
        (resultats["modele"] == gagnant)
        & (resultats["horodatage"] >= debut)
        & (resultats["horodatage"] < fin)
    ].sort_values("horodatage")

    plt.figure(figsize=(12, 5))
    plt.plot(extrait["horodatage"], extrait["reel_MW"], label="Réel")
    plt.plot(
        extrait["horodatage"], extrait["prediction_MW"],
        label=f"Prévu : {gagnant}",
    )
    plt.xlabel("Date et heure")
    plt.ylabel("Consommation (MW)")
    plt.title("Validation 2024 : prévisions horaires sur 3 jours")
    plt.legend()
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(SORTIE / "previsions_3_jours.png", dpi=200)
    plt.close()

    print("\nRésultats enregistrés dans :", SORTIE)


# Exécuter main() seulement si on lance ce fichier directement.
if __name__ == "__main__":
    main()
