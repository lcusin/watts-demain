"""Chemins communs : independants du dossier depuis lequel Python est lance."""
from pathlib import Path

PROJET = Path(__file__).resolve().parents[2]
ANALYSE = PROJET / "analyse_consommation"
RESULTATS = ANALYSE / "resultats"
SOURCES = ANALYSE / "sources"
CLASSIQUE = RESULTATS / "01_classique"
