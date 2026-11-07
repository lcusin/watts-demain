"""Chemins et lectures/ecritures CSV communs aux scripts.
Les colonnes date_utc sont en UTC, meme si le CSV ne porte pas de suffixe.
La conversion vers le calendrier local et la jointure RTE sont faites dans data/merge/merge.py.
"""
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parent
METEO = RACINE
BRUT = RACINE / "raw"
PREPARE = RACINE / "processed"
GRAPHIQUES = RACINE / "graphiques"
FOND_CARTE = RACINE / "fond_carte/france.geojson"
DEBUT = pd.Timestamp("2012-01-01", tz="UTC")
FIN = pd.Timestamp("2026-10-16", tz="UTC")  # Borne exclusive.
CLE = ["geo_id_wmo", "date_utc"]
VARIABLES = ["t", "tn12", "tn24", "tx12", "tx24", "rr1", "rr3", "rr6", "rr12", "rr24"]


def lire(fichier):
    texte = ["geo_id_wmo", "geo_id_wigos", "name", "validity_time",
             "reference_time", "insert_time", "fichier_source"]
    x = pd.read_csv(fichier, dtype={nom: "string" for nom in texte})
    for nom in ["date_utc", "source_temperature_fin_utc", "source_pluie_fin_utc"]:
        if nom in x:
            x[nom] = pd.to_datetime(x[nom], utc=True)
    return x


def sauver(x, fichier):
    fichier.parent.mkdir(parents=True, exist_ok=True)
    x.to_csv(fichier, index=False, na_rep="", date_format="%Y-%m-%d %H:%M:%S")


def noms_station(x):
    return " / ".join(sorted(x.dropna().unique()))
