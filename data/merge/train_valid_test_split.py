import pandas as pd
from pathlib import Path

# Racine du projet watts-demain
BASE_DIR = Path(__file__).resolve().parents[2]

# Dossier contenant les données préparées
DOSSIER_DATA = BASE_DIR / "data" / "merge"

# Charger le dataset final
df = pd.read_csv(
    DOSSIER_DATA / "donnees_combinees.csv",
    parse_dates=["horodatage", "date"]
)
if df[["horodatage", "date"]].isna().any().any() or df.horodatage.duplicated().any():
    raise ValueError("Dates ou horodatages manquants ou dupliqués")
if not df.horodatage.dt.normalize().eq(df.date).all():
    raise ValueError("Dates et horodatages incohérents")
grille = pd.date_range("2012-01-01", "2025-12-31 23:00", freq="h")
if not pd.DatetimeIndex(df.horodatage.sort_values()).equals(grille):
    raise ValueError("Grille horaire 2012-2025 incomplète ou hors période")

# ==================================================
# 1. DÉCOUPAGE CHRONOLOGIQUE
# ==================================================

# Train : données de 2012 à 2023
train = df[(df["date"] >= "2012-01-01") & (df["date"] < "2024-01-01")].copy()

# Validation : données de 2024
validation = df[
    (df["date"] >= "2024-01-01") &
    (df["date"] < "2025-01-01")
].copy()

# Test : données de 2025
test = df[
    (df["date"] >= "2025-01-01") & (df["date"] < "2026-01-01")
].copy()
if len(train) + len(validation) + len(test) != len(df):
    raise ValueError("Périodes d'apprentissage, validation et test incomplètes")
if not (train.horodatage.max() < validation.horodatage.min() < test.horodatage.min()):
    raise ValueError("Chevauchement entre les trois périodes")

# ==================================================
# 2. VÉRIFICATION
# ==================================================

print("Train :", train.shape)
print("Validation :", validation.shape)
print("Test :", test.shape)

print("Train :", train["date"].min(), "->", train["date"].max())
print("Validation :", validation["date"].min(), "->", validation["date"].max())
print("Test :", test["date"].min(), "->", test["date"].max())

print("Total :", len(train) + len(validation) + len(test))

# ==================================================
# 3. SAUVEGARDE DES DATASETS
# ==================================================

# Sauvegarder les données d'entraînement
train.to_csv(
    DOSSIER_DATA / "train.csv",
    index=False
)

# Sauvegarder les données de validation
validation.to_csv(
    DOSSIER_DATA / "validation.csv",
    index=False
)

# Sauvegarder les données de test
test.to_csv(
    DOSSIER_DATA / "test.csv",
    index=False
)

print("\nLes trois datasets ont été sauvegardés.")
