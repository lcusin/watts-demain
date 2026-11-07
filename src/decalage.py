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
DOSSIER_DATA = BASE_DIR / "data" / "processed"

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

# Garder ton décalage original
prediction_semaine = conso.shift(7)

# Afficher la date réelle et la date utilisée pour prédire
verification = pd.DataFrame({
    "date_prediction": conso.index,
    "jour_prediction": conso.index.day_name(),
    "date_utilisee": conso.index.to_series().shift(7).values
})

verification["jour_utilise"] = (
    pd.to_datetime(verification["date_utilisee"]).dt.day_name()
)

# Afficher toutes les lignes de validation 2024
verification = verification[
    verification["date_prediction"].dt.year == 2024
]

print(verification.to_string(index=False))