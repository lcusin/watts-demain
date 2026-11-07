
"""
Préparation du dataset horaire de consommation électrique RTE éCO2mix.

Entrée :
    data/conso/raw/*.xls
    Fichiers éCO2mix au format texte tabulé.

Sortie :
    data/conso/processed/consommation_horaire_eco2mix_2012_2025.csv

Traitements :
    1. Lecture et regroupement des fichiers annuels.
    2. Nettoyage des dates, heures et consommations.
    3. Vérification des doublons demi-horaires.
    4. Agrégation : moyenne des valeurs à :00 et :30.
    5. Identification des journées de changement d'heure.
    6. Contrôles de qualité et export CSV.

Important :
    Les horodatages représentent les créneaux publiés par RTE.
    Ils correspondent a l'heure legale francaise (Europe/Paris).
    La conversion UTC est centralisee dans data/merge/merge.py ; les journees
    de changement d'heure sont signalees et exclues des analyses horaires.
"""

from pathlib import Path
from datetime import date, timedelta
import pandas as pd


# ============================================================
# 1. CHEMINS
# ============================================================

DOSSIER_PROJET = Path(__file__).resolve().parents[2]

DOSSIER_DONNEES = DOSSIER_PROJET / "data" / "conso" / "raw"
DOSSIER_SORTIE = DOSSIER_PROJET / "data" / "conso" / "processed"

NOM_SORTIE = "consommation_horaire_eco2mix_2012_2025.csv"


# ============================================================
# 2. FONCTIONS POUR LES CHANGEMENTS D'HEURE
# ============================================================

def dernier_dimanche(annee, mois):
    """Retourne le dernier dimanche du mois indiqué."""

    if mois == 12:
        dernier_jour = date(annee + 1, 1, 1) - timedelta(days=1)
    else:
        dernier_jour = date(annee, mois + 1, 1) - timedelta(days=1)

    return dernier_jour - timedelta(days=(dernier_jour.weekday() + 1) % 7)


def dates_changement_heure(annees):
    """
    En France :
    - dernier dimanche de mars : passage à l'heure d'été ;
    - dernier dimanche d'octobre : passage à l'heure d'hiver.
    """

    transitions = set()

    for annee in annees:
        transitions.add(dernier_dimanche(int(annee), 3))
        transitions.add(dernier_dimanche(int(annee), 10))

    return transitions


# ============================================================
# 3. PRÉPARATION DES DONNÉES
# ============================================================

def main():

    # --------------------------------------------------------
    # Étape 1 : lecture des fichiers
    # --------------------------------------------------------

    fichiers = sorted(DOSSIER_DONNEES.glob("*.xls"))

    if not fichiers:
        raise FileNotFoundError(
            f"Aucun fichier .xls trouvé dans {DOSSIER_DONNEES}"
        )

    tableaux = []

    for fichier in fichiers:

        tableau = pd.read_csv(
            fichier,
            sep="\t",
            encoding="cp1252",
            index_col=False,
            na_values=["ND"]
        )

        tableau.columns = tableau.columns.str.strip()

        tableaux.append(tableau)

    source = pd.concat(tableaux, ignore_index=True)

    colonnes_requises = {"Date", "Heures", "Consommation"}

    colonnes_absentes = colonnes_requises - set(source.columns)

    if colonnes_absentes:
        raise ValueError(
            f"Colonnes absentes : {sorted(colonnes_absentes)}"
        )

    print(f"Fichiers lus : {len(fichiers)}")
    print(f"Lignes brutes : {len(source):,}")


    # --------------------------------------------------------
    # Étape 2 : nettoyage
    # --------------------------------------------------------

    # Supprimer les lignes sans date ou heure.
    donnees = source.dropna(
        subset=["Date", "Heures"]
    ).copy()

    # Construire l'horodatage selon les étiquettes RTE.
    donnees["horodatage"] = pd.to_datetime(
        donnees["Date"].astype(str)
        + " "
        + donnees["Heures"].astype(str),
        errors="coerce"
    )

    # Supprimer les dates non exploitables.
    donnees = donnees.dropna(
        subset=["horodatage"]
    ).copy()

    # Convertir la consommation en numérique.
    donnees["Consommation"] = pd.to_numeric(
        donnees["Consommation"],
        errors="coerce"
    )

    # Ne conserver que les créneaux :00 et :30.
    donnees = donnees[
        donnees["horodatage"].dt.minute.isin([0, 30])
    ].copy()

    # Colonnes pour identifier les créneaux.
    donnees["date"] = donnees["horodatage"].dt.normalize()
    donnees["heure"] = donnees["horodatage"].dt.hour
    donnees["minute"] = donnees["horodatage"].dt.minute


    # --------------------------------------------------------
    # Étape 3 : contrôle des doublons
    # --------------------------------------------------------

    doublons = donnees.duplicated(
        subset=["date", "heure", "minute"]
    )

    if doublons.any():

        exemples = donnees.loc[
            doublons,
            ["date", "heure", "minute"]
        ].head()

        raise ValueError(
            f"{doublons.sum()} créneaux demi-horaires dupliqués.\n"
            f"Exemples :\n{exemples}"
        )


    # --------------------------------------------------------
    # Étape 4 : moyenne horaire
    # --------------------------------------------------------

    # Mettre les consommations à :00 et :30
    # dans deux colonnes différentes.
    dataset = donnees.pivot(
        index=["date", "heure"],
        columns="minute",
        values="Consommation"
    )

    # Vérifier que les colonnes :00 et :30 existent.
    if 0 not in dataset.columns or 30 not in dataset.columns:
        raise ValueError(
            "Les mesures à :00 ou :30 sont absentes du dataset."
        )

    dataset = dataset.rename(
        columns={
            0: "consommation_00_MW",
            30: "consommation_30_MW"
        }
    ).reset_index()

    # Contrôle des demi-heures manquantes.
    heures_incompletes = (
        dataset["consommation_00_MW"].isna()
        | dataset["consommation_30_MW"].isna()
    )

    nb_incompletes = int(heures_incompletes.sum())

    print(f"Heures avec une demi-heure manquante : {nb_incompletes}")

    # Ne pas calculer de moyenne sur une seule demi-heure.
    dataset["consommation_MW"] = (
        dataset["consommation_00_MW"]
        + dataset["consommation_30_MW"]
    ) / 2

    # Reconstruire une étiquette horaire RTE.
    dataset["horodatage"] = (
        dataset["date"]
        + pd.to_timedelta(dataset["heure"], unit="h")
    )


    # --------------------------------------------------------
    # Étape 5 : changements d'heure
    # --------------------------------------------------------

    annees = dataset["date"].dt.year.unique()

    transitions = dates_changement_heure(annees)

    dataset["jour_changement_heure"] = (
        dataset["date"].dt.date.isin(transitions)
    )


    # --------------------------------------------------------
    # Étape 6 : contrôles de qualité
    # --------------------------------------------------------

    dataset = dataset.sort_values(
        ["date", "heure"]
    ).reset_index(drop=True)

    # Contrôle des clés horaires.
    doublons_horaires = dataset.duplicated(
        subset=["date", "heure"]
    ).sum()

    if doublons_horaires:
        raise ValueError(
            f"{doublons_horaires} créneaux horaires dupliqués."
        )

    # Compter le nombre de créneaux horaires par jour.
    heures_par_jour = dataset.groupby("date")["heure"].nunique()

    jours_incomplets = heures_par_jour[
        heures_par_jour != 24
    ]

    print(f"Journées avec moins ou plus de 24 créneaux : {len(jours_incomplets)}")

    if len(jours_incomplets) > 0:
        print("Exemples de journées incomplètes :")
        print(jours_incomplets.head(10))

    print(
        "Nombre de valeurs horaires manquantes :",
        dataset["consommation_MW"].isna().sum()
    )

    print(
        "Nombre de journées de changement d'heure :",
        dataset.loc[
            dataset["jour_changement_heure"], "date"
        ].nunique()
    )


    # --------------------------------------------------------
    # Étape 7 : export
    # --------------------------------------------------------

    dataset = dataset[
        [
            "horodatage",
            "date",
            "heure",
            "consommation_MW",
            "consommation_00_MW",
            "consommation_30_MW",
            "jour_changement_heure"
        ]
    ]

    DOSSIER_SORTIE.mkdir(
        parents=True,
        exist_ok=True
    )

    chemin_sortie = DOSSIER_SORTIE / NOM_SORTIE

    dataset.to_csv(
        chemin_sortie,
        index=False,
        encoding="utf-8"
    )

    print("\n========== BILAN ==========")

    print(f"Lignes horaires : {len(dataset):,}")

    print(
        f"Période : {dataset['horodatage'].min()} "
        f"-> {dataset['horodatage'].max()}"
    )

    print(f"Fichier créé : {chemin_sortie}")

    print("\nAperçu :")
    print(dataset.head())


# ============================================================
# 4. EXÉCUTION
# ============================================================

if __name__ == "__main__":
    main()
