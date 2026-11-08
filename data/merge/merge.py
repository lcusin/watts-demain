from pathlib import Path
import pandas as pd

RACINE = Path(__file__).resolve().parents[2]

conso = pd.read_csv(RACINE / "data/conso/processed/consommation_horaire_eco2mix_2012_2025.csv")
calendrier = pd.read_csv(RACINE / "data/calendrier/processed/calendrier_france_2012_2026.csv")
meteo = pd.read_csv(RACINE / "data/temperature/processed/moyennes_reseau_horaires.csv")

for tableau in [conso, calendrier]:
    tableau["horodatage"] = pd.to_datetime(tableau["horodatage"], errors="raise")
    if tableau["horodatage"].isna().any() or tableau["horodatage"].duplicated().any():
        raise ValueError("Horodatages manquants ou dupliqués")
    if not pd.DatetimeIndex(tableau.horodatage.sort_values()).equals(
        pd.date_range(tableau.horodatage.min(), tableau.horodatage.max(), freq="h")
    ):
        raise ValueError("Grille horaire incomplète")
    if not tableau.horodatage.dt.normalize().eq(pd.to_datetime(tableau.date)).all():
        raise ValueError("Date et horodatage incohérents")

if not {"jour_ferie", "weekend", "vacances_scolaires"}.issubset(calendrier.columns):
    raise ValueError("Variables calendaires manquantes")

meteo["date_utc"] = pd.to_datetime(meteo["date_utc"], utc=True, errors="raise")
if meteo["date_utc"].isna().any() or meteo["date_utc"].duplicated().any():
    raise ValueError("Dates météo manquantes ou dupliquées")

# Consommation et calendrier : heure française ; météo : UTC.
# Les heures locales ambiguës ou inexistantes restent sans correspondance météo.
conso["date_utc"] = conso["horodatage"].dt.tz_localize(
    "Europe/Paris", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
transition = conso.jour_changement_heure.astype(str).str.lower().isin(["true", "1", "1.0"])
if (conso.date_utc.isna() & (~transition | conso.horodatage.dt.hour.ne(2))).any():
    raise ValueError("Heure locale ambiguë ou inexistante hors transition")

donnees = conso.merge(calendrier, on="horodatage", how="left", validate="one_to_one")
if donnees.date_y.isna().any() or donnees[["jour_ferie", "weekend", "vacances_scolaires"]].isna().any().any():
    raise ValueError("Calendrier absent après jointure")
if not pd.to_datetime(donnees.date_x).eq(pd.to_datetime(donnees.date_y)).all():
    raise ValueError("Dates incohérentes après jointure")
donnees = donnees.merge(meteo, on="date_utc", how="left", validate="many_to_one")
if len(donnees) != len(conso):
    raise ValueError("La jointure a changé le nombre d'heures")
donnees = donnees.sort_values("horodatage")

donnees = donnees.drop(columns=["date_y", "heure_y", "jour_semaine"])
donnees["heure_x"] = donnees["heure_x"].apply(lambda h: f"{int(h):02d}:00:00")
donnees = donnees.rename(columns={"date_x": "date", "heure_x": "heure",
    "temperature_c_moyenne": "temperature_moyenne",
    "temperature_c_ecart_type": "temperature_ecart_type",
    "precipitation_1h_mm_moyenne": "precipitation_moyenne",
    "precipitation_1h_mm_ecart_type": "precipitation_ecart_type"})

donnees.to_csv(RACINE / "data/merge/donnees_combinees.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
