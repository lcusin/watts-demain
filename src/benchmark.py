
# ============================================================
# BENCHMARKS : PRÉVISION DE LA CONSOMMATION ÉLECTRIQUE
# ============================================================

# Objectif :
# Prédire les 24 consommations horaires du lendemain
# avec deux méthodes simples :
#
# 1. Même consommation que la semaine précédente
# 2. Moyenne des consommations des 4 semaines précédentes
#
# Validation : 2024
# Test final : 2025


# ============================================================
# 1. IMPORTER LES BIBLIOTHÈQUES
# ============================================================

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt


# ============================================================
# 2. CHARGER LES TROIS DATASETS
# ============================================================

# Récupérer le dossier racine du projet watts-demain.
BASE_DIR = Path(__file__).resolve().parent.parent

# Chemin du dossier contenant les données préparées.
DOSSIER_DATA = BASE_DIR / "data" / "merge"

# Charger les données d'entraînement (2012-2023).
train = pd.read_csv(
    DOSSIER_DATA / "train.csv",
    parse_dates=["horodatage", "date"]
)

# Charger les données de validation (2024).
validation = pd.read_csv(
    DOSSIER_DATA / "validation.csv",
    parse_dates=["horodatage", "date"]
)



# Vérifier les dimensions des trois ensembles.
print("Train :", train.shape)
print("Validation :", validation.shape)



# ============================================================
# 3. RÉUNIR TEMPORAIREMENT LES DONNÉES
# ============================================================

# Pourquoi réunir les datasets ?
#
# Pour prédire le 1er janvier 2024,
# on doit utiliser les consommations de décembre 2023.
#
# Si on applique shift(7) directement à validation,
# les 7 premiers jours de 2024 n'auront pas de prévisions.
#
# pd.concat() permet de réunir les trois tableaux
# en un seul tableau.
#
# ignore_index=True crée un nouvel index numérique.

df = pd.concat(
    [train, validation],
    ignore_index=True
)

# Trier les observations par horodatage.
df = df.sort_values("horodatage")

print("\nDimensions des données réunies :", df.shape)


# ============================================================
# 4. TRANSFORMER LES DONNÉES EN PROFILS JOURNALIERS
# ============================================================

# Actuellement :
# Une ligne = une heure.
#
# Après pivot :
# Une ligne = une journée.
# Une colonne = une heure.
#
# Exemple :
#
# date        00:00    01:00    ...    23:00
# 2024-01-01  50000    48000    ...    53000
# 2024-01-02  51000    49000    ...    54000

conso = df.pivot(
    index="date",
    columns="heure",
    values="consommation_MW"
)

# Trier les heures dans l'ordre chronologique.
conso = conso.reindex(
    sorted(conso.columns),
    axis=1
)

# Trier les journées par ordre chronologique.
conso = conso.sort_index()

print("\nDimensions après pivot :", conso.shape)

# Vérifier le nombre de colonnes horaires.
print("Nombre d'heures :", len(conso.columns))

# Vérifier le nombre de valeurs manquantes.
print("Valeurs manquantes :", conso.isna().sum().sum())

# Vérifier que les dates sont consécutives.
dates_attendues = pd.date_range(
    conso.index.min(),
    conso.index.max(),
    freq="D"
)

jours_manquants = dates_attendues.difference(conso.index)

print("Journées manquantes :", len(jours_manquants))

# Arrêter le programme si les données ne permettent
# pas de calculer correctement les benchmarks.
if (
    len(conso.columns) != 24
    or conso.isna().any().any()
    or len(jours_manquants) > 0
):
    raise ValueError(
        "Vérifier les heures, les valeurs manquantes "
        "et les journées absentes avant les benchmarks."
    )


# ============================================================
# 5. BENCHMARK 1 : SEMAINE PRÉCÉDENTE
# ============================================================

# Pour prédire une journée,
# on reprend les 24 consommations du même jour
# de la semaine précédente.
#
# Exemple :
# Pour prédire le mardi 14 janvier,
# on utilise le mardi 7 janvier.
#
# shift(7) décale les valeurs de 7 lignes.
#
# Ici, une ligne = une journée.
# Donc shift(7) correspond à 7 jours.

prediction_semaine = conso.shift(7)


# ============================================================
# 6. BENCHMARK 2 : MOYENNE DES 4 SEMAINES
# ============================================================

# On utilise les consommations :
#
# - 7 jours avant
# - 14 jours avant
# - 21 jours avant
# - 28 jours avant
#
# On calcule leur moyenne heure par heure.

prediction_moyenne = (
    conso.shift(7)
    + conso.shift(14)
    + conso.shift(21)
    + conso.shift(28)
) / 4


# ============================================================
# 7. SÉLECTIONNER LA VALIDATION : 2024
# ============================================================

# Récupérer les consommations réellement observées
# pendant l'année 2024.
reel = conso.loc[
    "2024-01-01":"2024-12-31"
]

# Récupérer les prévisions du premier benchmark.
pred1 = prediction_semaine.loc[
    "2024-01-01":"2024-12-31"
]

# Récupérer les prévisions du deuxième benchmark.
pred2 = prediction_moyenne.loc[
    "2024-01-01":"2024-12-31"
]

# Vérifier que les tableaux ont les mêmes dimensions.
print("\nDimensions validation :")

print("Réel :", reel.shape)
print("Benchmark 1 :", pred1.shape)
print("Benchmark 2 :", pred2.shape)


# ============================================================
# 8. FONCTION D'ÉVALUATION
# ============================================================

# MAE = moyenne des erreurs absolues.
#
# RMSE = racine de la moyenne des erreurs au carré.
#
# Plus ces métriques sont faibles,
# meilleures sont les prévisions.

def evaluer(y_reel, y_pred):

    # Transformer les DataFrames en tableaux NumPy.
    valeurs_reelles = y_reel.to_numpy()
    valeurs_predites = y_pred.to_numpy()

    # Vérifier qu'aucune valeur ne manque.
    if (
        not np.isfinite(valeurs_reelles).all()
        or not np.isfinite(valeurs_predites).all()
    ):
        raise ValueError("Valeurs manquantes dans l'évaluation.")

    # Calculer l'erreur :
    # consommation réelle - consommation prédite.
    erreur = valeurs_reelles - valeurs_predites

    # MAE : moyenne des valeurs absolues des erreurs.
    mae = np.mean(np.abs(erreur))

    # RMSE : racine carrée de la moyenne
    # des erreurs élevées au carré.
    rmse = np.sqrt(np.mean(erreur ** 2))

    # Retourner les deux résultats.
    return mae, rmse


# ============================================================
# 9. ÉVALUER LES BENCHMARKS SUR 2024
# ============================================================

# Calculer les métriques du premier benchmark.
mae1, rmse1 = evaluer(reel, pred1)

# Calculer les métriques du deuxième benchmark.
mae2, rmse2 = evaluer(reel, pred2)


# ============================================================
# 10. AFFICHER LES RÉSULTATS
# ============================================================

print("\n===== RÉSULTATS VALIDATION 2024 =====")

print("\nBenchmark 1 : semaine précédente")
print("MAE :", round(mae1, 2), "MW")
print("RMSE :", round(rmse1, 2), "MW")

print("\nBenchmark 2 : moyenne des 4 semaines")
print("MAE :", round(mae2, 2), "MW")
print("RMSE :", round(rmse2, 2), "MW")


# ============================================================
# 11. COMPARER LES DEUX BENCHMARKS
# ============================================================

# Le meilleur benchmark selon la MAE
# est celui qui a la plus petite erreur moyenne.

if mae1 < mae2:
    print("\nMeilleur benchmark selon la MAE :")
    print("Semaine précédente")

elif mae2 < mae1:
    print("\nMeilleur benchmark selon la MAE :")
    print("Moyenne des 4 semaines")

else:
    print("\nLes deux benchmarks ont la même MAE.")

# Si la RMSE du benchmark 1 est plus petite,
# alors le benchmark 1 est meilleur selon la RMSE.
if rmse1 < rmse2:
    print("Meilleur benchmark selon la RMSE : semaine précédente")
    print("RMSE :", round(rmse1, 2), "MW")

# Si la RMSE du benchmark 2 est plus petite,
# alors le benchmark 2 est meilleur selon la RMSE.
elif rmse2 < rmse1:
    print("Meilleur benchmark selon la RMSE : moyenne des 4 semaines")
  

# Si les deux RMSE sont égales,
# les benchmarks ont les mêmes performances selon la RMSE.
else:
    print("Les deux benchmarks ont la même RMSE.")





# 14. VISUALISATION DES PRÉDICTIONS de validation SUR PLUSIEURS JOURNÉES


import matplotlib.pyplot as plt

# Dossier où enregistrer les graphiques
DOSSIER_GRAPHIQUES = BASE_DIR / "data_temp" / "graphiques"

# Créer le dossier s'il n'existe pas
DOSSIER_GRAPHIQUES.mkdir(parents=True, exist_ok=True)

# Choisir plusieurs journées de validation en 2024
# Réparties sur différents mois et différentes saisons
dates_exemples = [
    "2024-01-15",  # Janvier : hiver
    "2024-03-20",  # Mars : printemps
    "2024-06-20",  # Juin : été (proche du solstice)
    "2024-08-15",  # Août : été, jour férié
    "2024-10-15",  # Octobre : automne
    "2024-12-15"   # Décembre : hiver
]

# Parcourir les journées sélectionnées
for date_exemple in dates_exemples:

    # Créer une nouvelle figure pour chaque journée
    plt.figure(figsize=(12, 5))

    # Consommations réellement observées
    plt.plot(
        range(24),
        reel.loc[date_exemple],
        label="Consommation réelle",
        linewidth=2
    )

    # Prédictions du benchmark 1
    plt.plot(
        range(24),
        pred1.loc[date_exemple],
        label="Semaine précédente",
        linestyle="--",
        linewidth=2
    )

    # Prédictions du benchmark 2
    plt.plot(
        range(24),
        pred2.loc[date_exemple],
        label="Moyenne des 4 semaines",
        linestyle=":",
        linewidth=2
    )

    # Titre et axes
    plt.title(
        f"Consommation réelle vs prévisions - {date_exemple}"
    )

    plt.xlabel("Heure")
    plt.ylabel("Consommation (MW)")

    # Afficher toutes les heures de 0 à 23
    plt.xticks(range(24))

    # Ajouter une légende
    plt.legend()

    # Ajouter une grille légère
    plt.grid(alpha=0.3)

    # Ajuster la mise en page
    plt.tight_layout()

    # Enregistrer le graphique dans le dossier graphiques
    plt.savefig(
        DOSSIER_GRAPHIQUES / f"benchmark_{date_exemple}.png",
        dpi=300,
        bbox_inches="tight"
    )

    # Afficher le graphique
    plt.show()

    # Fermer la figure pour libérer la mémoire
    plt.close()

