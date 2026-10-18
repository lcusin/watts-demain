"""
Préparation du dataset horaire de consommation électrique éCO2mix.

Entrée :
    fichiers éCO2mix au format texte tabulé, placés dans ./data/raw/conso
    (les fichiers fournis portent l'extension .xls).

Sortie :
    ./data/processed/consommation_horaire_eco2mix_2012_2025.csv

Traitements appliqués :
- lecture et regroupement des fichiers ;
- retrait des lignes sans date/heure exploitable (pieds de fichier) ;
- conversion de la date/heure et de la consommation ;
- retrait des lignes sans consommation ;
- conservation uniquement de la mesure à l'heure pile (:00).
La mesure à :30 n'est pas moyennée avec celle de :00.
"""

from pathlib import Path

import pandas as pd


# Les chemins sont définis par rapport à l'emplacement de ce script.
DOSSIER_PROJET = Path(__file__).resolve().parent.parent
DOSSIER_DONNEES = DOSSIER_PROJET / "data" / "raw" / "conso"
DOSSIER_SORTIE = DOSSIER_PROJET / "data" / "processed"
NOM_SORTIE = "consommation_horaire_eco2mix_2012_2025.csv"


def main():
    fichiers = sorted(DOSSIER_DONNEES.glob("*.xls"))

    if not fichiers:
        raise FileNotFoundError(
            f"Aucun fichier .xls trouvé dans {DOSSIER_DONNEES}. "
            "Place les fichiers éCO2mix dans le dossier data/raw/conso."
        )

    # Lire les fichiers éCO2mix (fichiers texte séparés par des tabulations).
    tableaux = []
    for fichier in fichiers:
        tableau = pd.read_csv(
            fichier,
            sep="\\t",
            encoding="cp1252",
            index_col=False,
            na_values=["ND"],
        )
        tableau.columns = tableau.columns.str.strip()
        tableaux.append(tableau)

    source = pd.concat(tableaux, ignore_index=True)

    colonnes_requises = {"Date", "Heures", "Consommation"}
    colonnes_absentes = colonnes_requises - set(source.columns)
    if colonnes_absentes:
        raise ValueError(
            "Colonnes indispensables absentes : "
            + ", ".join(sorted(colonnes_absentes))
        )

    print(f"Fichiers lus : {len(fichiers)}")
    print(f"Lignes brutes : {len(source):,}")

    # Retirer les lignes sans date ou heure, notamment les pieds de fichier.
    donnees = source.dropna(subset=["Date", "Heures"]).copy()
    donnees["horodatage"] = pd.to_datetime(
        donnees["Date"].astype(str) + " " + donnees["Heures"].astype(str),
        errors="coerce",
    )
    donnees = donnees.dropna(subset=["horodatage"]).copy()

    # Convertir la consommation en valeur numérique et retirer les valeurs absentes.
    donnees["Consommation"] = pd.to_numeric(
        donnees["Consommation"], errors="coerce"
    )
    donnees = donnees.dropna(subset=["Consommation"]).copy()

    # Conserver directement la mesure enregistrée à :00, sans moyenne horaire.
    dataset = donnees.loc[
        donnees["horodatage"].dt.minute == 0,
        ["horodatage", "Consommation"],
    ].copy()

    dataset = dataset.rename(columns={"Consommation": "consommation_MW"})
    dataset = dataset.sort_values("horodatage").reset_index(drop=True)

    # Vérifier que chaque heure n'apparaît qu'une seule fois.
    doublons = dataset["horodatage"].duplicated().sum()
    if doublons:
        raise ValueError(
            f"{doublons} horodatage(s) dupliqué(s) à l'heure pile. "
            "Vérifie les fichiers sources avant l'export."
        )

    # Exporter le dataset préparé.
    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
    chemin_sortie = DOSSIER_SORTIE / NOM_SORTIE
    dataset.to_csv(chemin_sortie, index=False, encoding="utf-8")

    print(f"Lignes après préparation : {len(dataset):,}")
    print(f"Période : {dataset['horodatage'].min()} -> {dataset['horodatage'].max()}")
    print(f"Valeurs de consommation manquantes : {dataset['consommation_MW'].isna().sum()}")
    print(f"Fichier créé : {chemin_sortie}")
    print("\nAperçu :")
    print(dataset.head())


if __name__ == "__main__":
    main()
