"""Evaluation finale sur 2025. Ne pas lancer avant le gel du protocole."""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
from modeles_ml import charger as charger_ml, creer_exemples, creer_modeles
from modeles_statistiques import charger as charger_stat, prevoir_modele, MODELES
from protocole import HEURE_COUPURE, jours_communs, empreinte, provenance
from synthese import FICHIERS, scores, verifier


RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "results" / "test_2025"


def ajouter_resultat(liste, meta, reel, prediction, nom, famille):
    liste.append(pd.DataFrame({
        "horodatage": meta.horodatage.to_numpy(),
        "modele": nom,
        "famille": famille,
        "reel_MW": reel,
        "prediction_MW": prediction,
    }))


def calculer_scores(previsions, heures, consommation):
    attendus = {(famille, nom) for famille, (_, _, _, noms) in FICHIERS.items()
                for nom in noms}
    groupes = previsions.groupby(["famille", "modele"], dropna=False)
    if set(groupes.groups) != attendus:
        raise ValueError("Modeles manquants ou inattendus dans le test.")
    if not np.isfinite(previsions[["reel_MW", "prediction_MW"]]).all().all():
        raise ValueError("Valeurs manquantes ou non finies dans les previsions.")

    bilans = []
    for (famille, nom), groupe in groupes:
        groupe = groupe.sort_values("horodatage")
        if not pd.DatetimeIndex(groupe.horodatage).equals(heures):
            raise ValueError(f"Horodatages manquants, dupliques ou inattendus : {nom}")
        np.testing.assert_allclose(groupe.reel_MW, consommation.reindex(heures),
                                   rtol=0, atol=1e-8, err_msg=nom)
        bilans.append({"famille": famille, "modele": nom, **scores(groupe)})
    return pd.DataFrame(bilans).sort_values("RMSE_MW")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirmer-test", action="store_true")
    args = parser.parse_args()
    if not args.confirmer_test:
        raise SystemExit(
            "Test 2025 non execute. Relancer avec --confirmer-test apres le gel du protocole."
        )
    if SORTIE.exists():
        raise SystemExit("Des resultats de test existent deja. Evaluation interrompue.")
    verifier()  # Controler les sorties 2024 avant de charger le test.

    # Construction des memes variables que pour la validation 2024.
    train = charger_ml("train.csv")
    validation = charger_ml("validation.csv")
    test = charger_ml("test.csv")
    grille = pd.date_range("2025-01-01", "2025-12-31 23:00", freq="h")
    if not pd.DatetimeIndex(test.horodatage).equals(grille):
        raise ValueError("Le fichier test doit couvrir toute la grille horaire de 2025.")
    donnees = pd.concat([train, validation, test], ignore_index=True)
    donnees = donnees.sort_values(["horodatage", "ordre_original"]).reset_index(drop=True)
    donnees["occurrence"] = donnees.groupby("horodatage").cumcount()
    jours_train = jours_communs(
        donnees, train.jour.min() + pd.Timedelta(days=30),
        test.jour.min() - pd.Timedelta(days=2),
    )
    jours_test = jours_communs(donnees, test.jour.min(), test.jour.max())
    X_train, y_train, _ = creer_exemples(donnees, jours_train)
    X_test, y_test, meta_test = creer_exemples(donnees, jours_test)

    resultats = []
    modeles = creer_modeles()
    for nom, modele in modeles.items():
        print("Entrainement :", nom, flush=True)
        modele.fit(X_train, y_train)
        ajouter_resultat(resultats, meta_test, y_test, modele.predict(X_test), nom, "ml")

    # Trois benchmarks calcules sur les memes heures de test.
    consommation = donnees.set_index("horodatage").consommation_MW
    heures = pd.DatetimeIndex(meta_test.horodatage)
    pred_semaine = consommation.reindex(heures - pd.Timedelta(days=7)).to_numpy()
    pred_4_semaines = np.mean([
        consommation.reindex(heures - pd.Timedelta(days=retard)).to_numpy()
        for retard in [7, 14, 21, 28]
    ], axis=0)
    coupures = heures.normalize() - pd.Timedelta(days=1) + pd.Timedelta(hours=HEURE_COUPURE)
    pred_persistance = consommation.reindex(coupures).to_numpy()
    for nom, prediction in [
        ("persistance", pred_persistance),
        ("semaine_precedente", pred_semaine),
        ("moyenne_4_semaines", pred_4_semaines),
    ]:
        ajouter_resultat(resultats, meta_test, y_test, prediction, nom, "benchmarks")

    # Reestimer les modeles statistiques avec les donnees disponibles avant 2025.
    train_s = charger_stat("train.csv")
    validation_s = charger_stat("validation.csv")
    test_s = charger_stat("test.csv")
    consommation_s = pd.concat([train_s, validation_s, test_s])
    differences = consommation_s.diff(168)
    for nom, ordre in MODELES.items():
        lignes = prevoir_modele(nom, ordre, test_s, consommation_s, differences, jours_test)
        bloc = pd.DataFrame(lignes)
        bloc["famille"] = "statistiques"
        resultats.append(bloc[["horodatage", "modele", "famille", "reel_MW", "prediction_MW"]])

    previsions = pd.concat(resultats, ignore_index=True)
    heures_attendues = grille[grille.normalize().isin(jours_test)]
    bilan = calculer_scores(previsions, heures_attendues, consommation)

    trace = provenance(__file__)
    for nom in ["data/merge/test.csv", "src/modeles_ml.py", "src/modeles_statistiques.py",
                "src/synthese.py", "data/merge/merge.py", "data/merge/train_valid_test_split.py",
                "data/temperature/extraction_meteo.py", "data/temperature/chemins.py",
                "data/conso/preparer_dataset_eco2mix.py", "data/calendrier/data_calendrier_prep.py",
                "requirements.txt"]:
        trace["fichiers"][nom] = empreinte(RACINE / nom)
    trace["parametres_ml"] = {nom: repr(modele) for nom, modele in modeles.items()}
    trace["ordres_statistiques"] = {nom: list(ordre) for nom, ordre in MODELES.items()}
    trace["heure_coupure"] = HEURE_COUPURE

    # Publier ensemble les trois CSV une fois tous les controles passes.
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=SORTIE.parent) as temporaire:
        dossier = Path(temporaire) / SORTIE.name
        dossier.mkdir()
        previsions.to_csv(dossier / "previsions_test_2025.csv", index=False)
        bilan.to_csv(dossier / "comparaison_test_2025.csv", index=False)
        pd.Series(jours_test, name="jour").to_csv(dossier / "jours_evalues.csv", index=False)
        (dossier / "execution.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
        dossier.rename(SORTIE)
    print("Evaluation 2025 terminee. Ne plus modifier les modeles selon ces resultats.")


if __name__ == "__main__":
    main()
