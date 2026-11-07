"""Règles communes aux benchmarks, modèles statistiques et ML de Nada."""
import hashlib
import json
import platform
from pathlib import Path
from importlib.metadata import version

import numpy as np
import pandas as pd

HEURE_COUPURE = 8


def masquer_transitions(df):
    """Conserver la grille horaire, mais masquer les mesures des jours ambigus."""
    df = df.sort_values("horodatage").copy()
    assert df.horodatage.is_unique
    assert df.horodatage.diff().dropna().eq(pd.Timedelta(hours=1)).all()
    transition = df.jour_changement_heure.astype(str).str.lower().isin(["true", "1", "1.0"])
    mesures = [c for c in df if c.startswith(("consommation_", "temperature_", "precipitation_"))]
    df.loc[transition, mesures] = np.nan
    return df


def disponibilite_meteo(utc):
    # Pluie sur [h,h+1], mesure SYNOP suivante, puis délai supposé de 3 h.
    # Borne conservatrice également utilisée pour la température interpolée.
    return (pd.to_datetime(utc, utc=True) + pd.Timedelta(hours=1)).dt.ceil("3h") + pd.Timedelta(hours=3)


def jours_communs(df, debut, fin):
    """Mêmes journées complètes pour les trois scripts, sans consulter la météo cible."""
    df = masquer_transitions(df)
    y = df.set_index("horodatage").consommation_MW
    calendrier = pd.date_range(y.index.min().normalize(), y.index.max().normalize(), freq="D")
    complet = y.notna().resample("D").sum().reindex(calendrier).eq(24)
    matin = y[y.index.hour <= HEURE_COUPURE].notna().resample("D").sum().reindex(calendrier).eq(9)
    # Cible D ; matin de J=D-1 ; journées historiques du ML : J-1, J-7, J-14, J-28.
    valide = complet & matin.shift(1, fill_value=False)
    for retard in [2, 8, 15, 29, 7, 14, 21, 28]:
        valide &= complet.shift(retard, fill_value=False)
    # Historique continu d'une semaine jusqu'à J8, et différence à J8 disponible.
    coupures = calendrier - pd.Timedelta(days=1) + pd.Timedelta(hours=HEURE_COUPURE)
    passe = y.notna().rolling(169).sum().eq(169) & y.shift(168).notna()
    valide &= passe.reindex(coupures, fill_value=False).to_numpy()
    return calendrier[valide & (calendrier >= pd.Timestamp(debut)) & (calendrier <= pd.Timestamp(fin))]


def empreinte(fichier):
    return hashlib.sha256(Path(fichier).read_bytes()).hexdigest()


def provenance(script):
    racine = Path(__file__).resolve().parent.parent
    fichiers = [racine / "data/merge/train.csv", racine / "data/merge/validation.csv",
                Path(__file__), Path(script)]
    return {"fichiers": {str(p.resolve().relative_to(racine)): empreinte(p) for p in fichiers},
            "python": platform.python_version(),
            "versions": {nom: version(nom) for nom in ["numpy", "pandas", "scikit-learn", "statsmodels"]}}


def enregistrer_execution(sortie, script):
    # Permet de refuser des scores produits avant une modification des scripts ou données.
    (Path(sortie) / "execution.json").write_text(json.dumps(provenance(script), indent=2), encoding="utf-8")
