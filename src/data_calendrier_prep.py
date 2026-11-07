import pandas as pd
from pathlib import Path

# Racine du projet watts-demain
BASE_DIR = Path(__file__).resolve().parent.parent

# Fichiers sources dans data/raw
FICHIER_FERIES = BASE_DIR / "data" / "raw" / "om-referentiel-jours-feries (1).csv"
FICHIER_VACANCES = BASE_DIR / "data" / "raw" / "data (3).csv"

DATE_DEBUT = "2012-01-01"
DATE_FIN = "2026-12-31"

# Fichier de sortie dans data/processed
FICHIER_SORTIE = BASE_DIR / "data" / "processed" / "calendrier_france_2012_2026.csv"

FICHIER_SORTIE.parent.mkdir(parents=True, exist_ok=True)


# ==================================================
# 2. CHARGER LES DEUX FICHIERS
# ==================================================

# Le fichier des jours fériés utilise le séparateur ;
feries = pd.read_csv(
    FICHIER_FERIES,
    sep=";",
    encoding="utf-8-sig" #lire correctement les caractères accentués
)

vacances = pd.read_csv(
    FICHIER_VACANCES,
    encoding="utf-8-sig"
)

# Nettoyer les noms des colonnes : supprime les espaces inutiles au début et à la fin des noms des colonnes.
feries.columns = feries.columns.str.strip()
vacances.columns = vacances.columns.str.strip()

# Convertir les dates : 
# Le problème : lorsqu'un fichier CSV est lu, les dates sont souvent considérées comme du texte (str) et non comme de véritables dates.
# Pour cela : on a réalisé la convertion les valeurs en dates.
# errors="coerce" signifie que si une valeur ne peut pas être convertie en date, Pandas la remplace par NaT (Not a Time), qui représente une date manquante ou invalide.
feries["date"] = pd.to_datetime(
    feries["date"],
    errors="coerce"
)

vacances["date"] = pd.to_datetime(
    vacances["date"],
    errors="coerce"
)


# ==================================================
# 3. CRÉER TOUTES LES DATES DE LA PÉRIODE
# ==================================================
# Générer une suite de dates quotidiennes entre DATE_DEBUT et DATE_FIN
# freq="D" signifie qu'une nouvelle date est générée chaque jour
# pd.DataFrame transforme cette suite de dates en tableau
calendrier = pd.DataFrame({
    "date": pd.date_range(
        start=DATE_DEBUT,
        end=DATE_FIN,
        freq="D"
    )
})


# ==================================================
# 4. AJOUTER LES JOURS FÉRIÉS
# ==================================================

# Ajouter une colonne qui vaut 1 pour les jours fériés
## Créer un indicateur égal à 1 pour chaque jour présent dans le fichier
# des jours fériés : 1 signifie que la date est un jour férié
feries["jour_ferie"] = 1

# Ne conserver que les colonnes nécessaires
feries = feries[
    ["date", "jour_ferie", "férié"]
].rename(columns={
    "férié": "nom_ferie"
})
# Garder uniquement les jours fériés compris dans la période choisie
# & signifie que les deux conditions doivent être vraies

feries = feries[
    (feries["date"] >= DATE_DEBUT)
    & (feries["date"] <= DATE_FIN)
]

# Fusionner le calendrier complet avec le tableau des jours fériés
# on="date" utilise la date comme clé de correspondance
# how="left" conserve toutes les dates du calendrier
calendrier = calendrier.merge(
    feries,
    on="date",
    how="left"
)

# Remplacer les valeurs manquantes de "jour_ferie" par 0
# Une date sans correspondance dans le fichier est considérée ici
# comme un jour non férié
# astype(int) convertit les valeurs en entiers : 0 ou 1
calendrier["jour_ferie"] = (
    calendrier["jour_ferie"]
    .fillna(0)
    .astype(int)
)


# ==================================================
# 5. AJOUTER LES VACANCES SCOLAIRES
# ==================================================
# Sélectionner uniquement les colonnes utiles du fichier des vacances
# copy() crée une copie du tableau sélectionné
vacances = vacances[
    [
        "date",
        "vacances_zone_a",
        "vacances_zone_b",
        "vacances_zone_c",
        "nom_vacances"
    ]
].copy()

# Renommer les colonnes pour le projet
vacances = vacances.rename(columns={
    "vacances_zone_a": "vacances_A",
    "vacances_zone_b": "vacances_B",
    "vacances_zone_c": "vacances_C"
})

# Garder la période demandée : Conserver uniquement les vacances comprises dans la période choisie
vacances = vacances[
    (vacances["date"] >= DATE_DEBUT)
    & (vacances["date"] <= DATE_FIN)
]

# Vérifier qu'aucune date n'apparaît plusieurs fois
# duplicated() repère les dates répétées
# any() vérifie si au moins un doublon existe
# assert déclenche une erreur si la condition n'est pas respectée
assert not vacances["date"].duplicated().any(), (
    "Le fichier vacances contient des dates dupliquées."
)

# Ajouter les informations sur les vacances au calendrier
# how="left" conserve toutes les dates du calendrier
# validate="one_to_one" vérifie qu'il n'y a pas plusieurs lignes
# pour une même date dans l'un ou l'autre tableau
calendrier = calendrier.merge(
    vacances,
    on="date",
    how="left",
    validate="one_to_one"
)

colonnes_zones = [
    "vacances_A",
    "vacances_B",
    "vacances_C"
]
# Parcourir les trois colonnes pour convertir leurs valeurs en entiers
# Int64 est un type entier Pandas qui autorise aussi les valeurs manquantes
# Cette conversion suppose que les valeurs sont compatibles avec des entiers
# Convertir les indicateurs True/False en 1/0
for col in colonnes_zones:
    calendrier[col] = (
        calendrier[col]
        .astype("Int64")
    )


# ==================================================
# 6. CRÉER UN INDICATEUR GLOBAL DE VACANCES
# ==================================================
# Créer une colonne qui indique si au moins une zone est en vacance
# 1 si au moins une zone est en vacances 
calendrier["vacances_scolaires"] = (
    calendrier[colonnes_zones]
    .fillna(0)
    .max(axis=1)
    .astype(int)
)


# ==================================================
# 7. AJOUTER LES VARIABLES CALENDAIRES
# ==================================================

noms_jours = {
    0: "lundi",
    1: "mardi",
    2: "mercredi",
    3: "jeudi",
    4: "vendredi",
    5: "samedi",
    6: "dimanche"
}

calendrier["jour_semaine"] = (
    calendrier["date"]
    .dt.dayofweek
    .map(noms_jours)
)
# 7 colonnes binaires pour les jours de la semaine
jours = [
    "lundi", "mardi", "mercredi", "jeudi",
    "vendredi", "samedi", "dimanche"
]

for jour in jours:
    calendrier[jour] = (
        calendrier["jour_semaine"] == jour
    ).astype(int)

calendrier["weekend"] = (
    calendrier["date"]
    .dt.dayofweek
    .isin([5, 6])
    .astype(int)
)

calendrier["annee"] = calendrier["date"].dt.year
calendrier["mois"] = calendrier["date"].dt.month
calendrier["jour_mois"] = calendrier["date"].dt.day

# ==================================================
# 10. TRANSFORMER LE CALENDRIER EN DONNEES HORAIRES
# ==================================================

# Répéter chaque ligne du calendrier 24 fois
# Une ligne par heure, de 0 à 23
calendrier = calendrier.loc[
    calendrier.index.repeat(24)
].reset_index(drop=True)

# Ajouter les heures de 0 à 23 pour chaque journée
calendrier["heure"] = (
    calendrier.groupby("date").cumcount()
)

# Créer l'horodatage en combinant date et heure
calendrier["horodatage"] = (
    pd.to_datetime(calendrier["date"])
    + pd.to_timedelta(calendrier["heure"], unit="h")
)

# Formater l'horodatage comme le fichier électrique
calendrier["horodatage"] = (
    calendrier["horodatage"]
    .dt.strftime("%Y-%m-%d %H:%M:%S")
)
# ==================================================
# 8. ORGANISER LES COLONNES
# ==================================================

colonnes_finales = [
   "horodatage",
    "date",
    "heure",
    #"annee",
    #"mois", 
    "jour_semaine",
    "lundi",
    "mardi",
    "mercredi",
    "jeudi",
    "vendredi",
    "samedi",
    "dimanche",
    "weekend",
    "jour_ferie",
    "vacances_A",
    "vacances_B",
    "vacances_C",
    "vacances_scolaires"
]

calendrier = calendrier[colonnes_finales]

# Format de date adapté au CSV
calendrier["date"] = (
    calendrier["date"].dt.strftime("%Y-%m-%d")
)


# ==================================================
# 9. VÉRIFICATIONS
# ==================================================

print("Nombre de lignes :", len(calendrier))
print("Nombre de dates uniques :", calendrier["date"].nunique())
print("Premières lignes :")
print(calendrier.head(10).to_string(index=False))

print("\nNombre de jours fériés :")
print(calendrier["jour_ferie"].sum())

print("\nNombre de jours avec au moins une zone en vacances :")
print(calendrier["vacances_scolaires"].sum())

print("\nValeurs manquantes :")
print(calendrier.isna().sum())

# Vérifier qu'une seule colonne de jour vaut 1 par date
assert (calendrier[jours].sum(axis=1) == 1).all(), (
    "Erreur : chaque date doit correspondre à un seul jour."
)

# ==================================================
# 10. EXPORTER LE DATASET
# ==================================================

calendrier.to_csv(
    FICHIER_SORTIE,
    index=False,
    encoding="utf-8-sig"
)

print("\nDataset enregistré :", FICHIER_SORTIE)