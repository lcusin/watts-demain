from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parents[2]

conso = pd.read_csv(RACINE / "data/conso/processed/consommation_horaire_eco2mix_2012_2025.csv")
calendrier = pd.read_csv(RACINE / "data/calendrier/processed/calendrier_france_2012_2026.csv")
meteo = pd.read_csv(RACINE / "data/temperature/processed/moyennes_reseau_horaires.csv")

meteo = meteo.rename(columns={"date_utc": "horodatage"})

for tableau in [conso, calendrier, meteo]:
    tableau["horodatage"] = pd.to_datetime(tableau["horodatage"], errors="raise")
    if tableau["horodatage"].isna().any() or tableau["horodatage"].duplicated().any():
        raise ValueError(f"Horodatages manquants ou dupliques : {tableau}")

donnees = conso.merge(calendrier, on="horodatage", how="left", validate="one_to_one")
donnees = donnees.merge(meteo, on="horodatage", how="left", validate="one_to_one")
donnees = donnees.sort_values("horodatage")

donnees = donnees.drop(columns=["date_y", "heure_y", "jour_semaine"])
donnees["heure_x"] = donnees["heure_x"].apply(lambda h: f"{int(h):02d}:00:00")
donnees =  donnees.rename(columns={"date_x": "date", "heure_x": "heure"})
donnees = donnees.rename(columns={"temperature_c_moyenne": "temperature_moyenne", 
                                  "temperature_c_ecart_type": "temperature_ecart_type", 
                                  "precipitation_1h_mm_moyenne": "precipitation_moyenne",
                                    "precipitation_1h_mm_ecart_type": "precipitation_ecart_type"})

donnees.to_csv(RACINE / "data/merge/donnees_combinees.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")





