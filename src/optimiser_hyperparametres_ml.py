"""Recherche d'hyperparamètres pour la prévision électrique à J 14 h.

Le script réutilise les variables, les modèles et le filtrage temporel de
``src/modeles_ml.py`` et ``src/protocole.py``. Il n'accède jamais à test.csv.

Protocole :
    2012–2022 : apprentissage pour comparer les réglages ;
    2023      : validation interne, sélection par RMSE horaire ;
    2012–2023 : réapprentissage du réglage choisi ;
    2024      : évaluation sur les journées communes aux méthodes du projet.

Cette optimisation est une analyse complémentaire : certaines idées ont été
formulées après consultation des scores de 2024. Aucun score de 2025 n'est utilisé.

Depuis la racine du projet :
    python src/optimiser_hyperparametres_ml.py --modeles ridge
    python src/optimiser_hyperparametres_ml.py --modeles ridge foret boosting
    python src/optimiser_hyperparametres_ml.py --modeles foret --rapide
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, mean_squared_error

from modeles_ml import charger, creer_exemples, creer_modeles
from protocole import jours_communs

RACINE = Path(__file__).resolve().parents[1]
DONNEES = RACINE / "data" / "merge"
REFERENCE = RACINE / "results" / "analyse_2024" / "ml" / "comparaison_ml_2024.csv"
JOURS_REFERENCE = RACINE / "results" / "analyse_2024" / "benchmarks" / "jours_evalues.csv"
SORTIE = RACINE / "results" / "analyse_2024" / "optimisation_hyperparametres_ml"

NOMS = {
    "ridge": "Ridge",
    "foret": "Random Forest",
    "boosting": "Gradient Boosting",
}

# Chaque famille inclut le réglage de référence déjà utilisé dans le projet.
REGLAGES = {
    "ridge": [
        {"ridge__alpha": float(a)} for a in (100, 0.1, 1, 10, 1000)
    ],
    "foret": [
        {"randomforestregressor__n_estimators": 100,
         "randomforestregressor__max_depth": 15,
         "randomforestregressor__min_samples_leaf": 3,
         "randomforestregressor__max_features": 1.0},
        {"randomforestregressor__n_estimators": 100,
         "randomforestregressor__max_depth": 20,
         "randomforestregressor__min_samples_leaf": 3,
         "randomforestregressor__max_features": 1.0},
        {"randomforestregressor__n_estimators": 120,
         "randomforestregressor__max_depth": 15,
         "randomforestregressor__min_samples_leaf": 2,
         "randomforestregressor__max_features": 0.7},
        {"randomforestregressor__n_estimators": 120,
         "randomforestregressor__max_depth": 20,
         "randomforestregressor__min_samples_leaf": 5,
         "randomforestregressor__max_features": 0.7},
    ],
    "boosting": [
        {"gradientboostingregressor__n_estimators": 80,
         "gradientboostingregressor__learning_rate": 0.08,
         "gradientboostingregressor__max_depth": 2},
        {"gradientboostingregressor__n_estimators": 150,
         "gradientboostingregressor__learning_rate": 0.06,
         "gradientboostingregressor__max_depth": 2},
        {"gradientboostingregressor__n_estimators": 200,
         "gradientboostingregressor__learning_rate": 0.05,
         "gradientboostingregressor__max_depth": 2},
        {"gradientboostingregressor__n_estimators": 150,
         "gradientboostingregressor__learning_rate": 0.08,
         "gradientboostingregressor__max_depth": 3},
    ],
}


def scores(y_reel: np.ndarray, y_predit: np.ndarray) -> dict:
    erreur = np.asarray(y_reel, float) - np.asarray(y_predit, float)
    return {
        "MAE_MW": float(mean_absolute_error(y_reel, y_predit)),
        "RMSE_MW": float(np.sqrt(mean_squared_error(y_reel, y_predit))),
        "biais_MW": float(erreur.mean()),
    }


def empreinte(fichier: Path) -> str:
    return hashlib.sha256(fichier.read_bytes()).hexdigest()


def version_lib(nom: str) -> str:
    try:
        return version(nom)
    except PackageNotFoundError:
        return "non installé"


def jours_evaluation(df: pd.DataFrame) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex]:
    debut = df["jour"].min() + pd.Timedelta(days=30)
    fin = pd.Timestamp("2023-12-30")
    jours_apprentissage = jours_communs(df, debut, fin)
    jours_validation = jours_communs(df, pd.Timestamp("2024-01-01"),
                                    pd.Timestamp("2024-12-31"))

    # La comparaison du projet repose sur des dates strictement identiques.
    if JOURS_REFERENCE.exists():
        attendus = pd.DatetimeIndex(pd.to_datetime(
            pd.read_csv(JOURS_REFERENCE)["jour"]))
        if not jours_validation.equals(attendus):
            raise ValueError("Les journées 2024 diffèrent des journées de référence. "
                             "Vérifier les données et les filtres avant comparaison.")
    else:
        raise FileNotFoundError(f"Journées communes introuvables : {JOURS_REFERENCE}")
    return jours_apprentissage, jours_validation


def charger_features():
    print("Chargement des CSV 2012–2024 et construction des variables...", flush=True)
    train = charger("train.csv")
    validation = charger("validation.csv")
    if not train["jour"].dt.year.between(2012, 2023).all():
        raise ValueError("La période d'apprentissage n'est pas 2012–2023")
    if not validation["jour"].dt.year.eq(2024).all():
        raise ValueError("La validation doit couvrir exclusivement 2024")
    donnees = pd.concat([train, validation], ignore_index=True)
    donnees = donnees.sort_values(["horodatage", "ordre_original"],
                                  kind="stable").reset_index(drop=True)
    donnees["occurrence"] = donnees.groupby("horodatage", sort=False).cumcount()

    jours_train, jours_val = jours_evaluation(donnees)
    X_train, y_train, meta_train = creer_exemples(donnees, jours_train)
    X_2024, y_2024, meta_2024 = creer_exemples(donnees, jours_val)
    if list(X_train.columns) != list(X_2024.columns):
        raise ValueError("Colonnes différentes entre apprentissage et validation")

    dates_train = pd.to_datetime(meta_train["jour_cible"])
    selection_2022 = dates_train.le(pd.Timestamp("2022-12-30")).to_numpy()
    selection_2023 = dates_train.dt.year.eq(2023).to_numpy()
    if not (selection_2022.any() and selection_2023.any()):
        raise ValueError("Périodes 2012–2022 / 2023 absentes")
    if len(y_2024) != len(jours_val) * 24:
        raise ValueError("Échantillon de validation incomplet")

    print(f"2012–2022 : {selection_2022.sum():,} heures d'apprentissage")
    print(f"2023 : {selection_2023.sum():,} heures de réglage interne")
    print(f"2012–2023 : {len(y_train):,} heures pour le réentraînement")
    print(f"2024 : {len(y_2024):,} heures, {len(jours_val)} journées communes")
    return (X_train, y_train, selection_2022, selection_2023,
            X_2024, y_2024, meta_2024)


def modele_configure(nom: str, parametres: dict, jobs: int):
    modele = clone(creer_modeles()[NOMS[nom]])
    if nom == "foret":
        modele.set_params(randomforestregressor__n_jobs=jobs)
    return modele.set_params(**parametres)


def enregistrer_provenance(sortie: Path, nom_script: Path, arguments: dict):
    fichiers = [DONNEES / "train.csv", DONNEES / "validation.csv",
                RACINE / "src" / "modeles_ml.py",
                RACINE / "src" / "protocole.py", nom_script]
    origine = {
        "protocole": "2012-2022 / choix 2023 / refit 2012-2023 / validation 2024",
        "test_2025": "non consulté",
        "options": arguments,
        "versions": {p: version_lib(p) for p in ("numpy", "pandas", "scikit-learn")},
        "python": platform.python_version(),
        "sha256": {str(p.relative_to(RACINE)): empreinte(p) for p in fichiers},
    }
    (sortie / "execution.json").write_text(
        json.dumps(origine, indent=2, ensure_ascii=False), encoding="utf-8")


def generer_analyse(reglages: pd.DataFrame, resultats: pd.DataFrame,
                     sortie: Path):
    lignes = [
        "# Optimisation des hyperparamètres — validation temporelle",
        "",
        "## Protocole",
        "",
        "- **2012–2022** : apprentissage des configurations candidates.",
        "- **2023** : sélection de la configuration minimisant la RMSE horaire.",
        "- **2012–2023** : réentraînement de la configuration retenue.",
        "- **2024** : comparaison sur les mêmes journées que l'étude principale.",
        "- **2025** : jeu de test non consulté.",
        "",
        "L'ensemble des prédicteurs et les règles de disponibilité proviennent de "
        "`src/modeles_ml.py` et `src/protocole.py`.",
        "",
        "Cette expérience de réglage a été engagée après consultation des résultats "
        "2024 : les scores constituent donc une analyse complémentaire exploratoire. "
        "La sélection numérique des paramètres utilise toutefois seulement 2023.",
        "",
        "## Résultats",
        "",
    ]
    for _, r in resultats.iterrows():
        nom = r["modele"]
        d = reglages[reglages["modele"] == nom]
        meilleur = d.loc[d["RMSE_2023_MW"].idxmin()]
        lignes += [
            f"### {nom}", "",
            f"- Configurations testées sur 2023 : **{len(d)}**.",
            f"- Meilleure RMSE interne 2023 : **{meilleur['RMSE_2023_MW']:.2f} MW**.",
            f"- Paramètres retenus : `{meilleur['parametres']}`.",
            f"- Validation 2024 : MAE **{r['MAE_2024_MW']:.2f} MW**, "
            f"RMSE **{r['RMSE_2024_MW']:.2f} MW**, "
            f"biais **{r['biais_2024_MW']:+.2f} MW**.",
        ]
        if pd.notna(r["RMSE_reference_2024_MW"]):
            diff = r["RMSE_2024_MW"] - r["RMSE_reference_2024_MW"]
            lignes.append(
                f"- Écart à la configuration originale **enregistrée** : "
                f"**{diff:+.2f} MW** de RMSE "
                f"({'amélioration' if diff < 0 else 'dégradation ou égalité'}).")
        if pd.notna(r["RMSE_reference_recalculee_2024_MW"]):
            diff = r["RMSE_2024_MW"] - r["RMSE_reference_recalculee_2024_MW"]
            lignes.append(
                f"- Écart à la référence **recalculée dans le même environnement** : "
                f"**{diff:+.2f} MW** de RMSE "
                f"({'amélioration' if diff < 0 else 'dégradation ou égalité'}).")
        lignes += ["", ""]
    lignes += [
        "## Interprétation et limites", "",
        "Une réduction de RMSE sur 2023 ne garantit pas une amélioration sur 2024. "
        "Comparer les écarts de RMSE et les métriques complémentaires avant de conclure.",
        "Les scores de référence historiques sont lus dans les résultats sauvegardés "
        "du projet. La référence recalculée est fournie uniquement lorsque "
        "l'option --recalculer-reference est utilisée.",
        "Les écarts faibles ne démontrent pas de supériorité statistique ; "
        "l'incertitude et la dépendance entre journées restent à étudier.",
        "Les données RTE définitives et le décalage de la convention d'agrégation "
        "horaire identifiés ensuite ne sont pas corrigés dans cette expérience : "
        "les scores concernent la cible horaire actuellement enregistrée dans les CSV.",
        "Les limites du scénario rétrospectif à J 14 h (publication effective des "
        "observations historiques non reconstruite) restent applicables.",
        "", "## Fichiers", "",
        "- `reglages_2023.csv` : toutes les configurations évaluées en 2023.",
        "- `comparaison_2024.csv` : scores des configurations retenues sur 2024.",
        "- `previsions_2024.csv` : prévisions horaires des modèles optimisés.",
        "- `execution.json` : versions et empreintes des scripts et données.",
    ]
    (sortie / "analyse.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modeles", nargs="+", choices=list(NOMS),
                        default=list(NOMS), help="Familles à optimiser")
    parser.add_argument("--rapide", action="store_true",
                        help="Essai réduit (réglage original + une variante par famille)")
    parser.add_argument("--recalculer-reference", action="store_true",
                        help="Réentraîne aussi le réglage initial pour comparer dans le même environnement")
    parser.add_argument("--jobs", type=int, default=2,
                        help="Parallélisme du Random Forest (défaut : 2 ; -1 = tous les CPU)")
    parser.add_argument("--sortie", type=Path, default=SORTIE,
                        help="Dossier pour enregistrer cette expérience")
    args = parser.parse_args()
    if args.jobs == 0 or args.jobs < -1:
        parser.error("--jobs doit être -1 ou un entier strictement positif")
    if len(set(args.modeles)) != len(args.modeles):
        parser.error("Chaque famille doit être indiquée une fois")
    sorties = args.sortie.resolve()
    # Sécurité : aucune sortie ne peut être écrite dans le dossier du test final.
    test = (RACINE / "results" / "test_2025").resolve()
    if sorties == test or test in sorties.parents:
        parser.error("Le répertoire results/test_2025 est protégé")
    if sorties == (RACINE / "results" / "analyse_2024" / "ml").resolve():
        parser.error("Le dossier de résultats ML d'origine est protégé")
    sorties.mkdir(parents=True, exist_ok=True)

    debut = perf_counter()
    X_train, y_train, masque_pre2023, masque_2023, X_2024, y_2024, meta_2024 = charger_features()
    X_2022 = X_train.loc[masque_pre2023]
    y_2022 = y_train[masque_pre2023]
    X_2023 = X_train.loc[masque_2023]
    y_2023 = y_train[masque_2023]

    references = {}
    if REFERENCE.exists():
        tab_ref = pd.read_csv(REFERENCE)
        references = dict(zip(tab_ref["modele"], tab_ref["RMSE_MW"]))
    else:
        print("Référence ML existante introuvable : comparaison sans score initial.")

    details, synthese, previsions = [], [], []
    for nom in args.modeles:
        candidats = REGLAGES[nom]
        if args.rapide:
            candidats = candidats[:2]
        print(f"\n=== {NOMS[nom]} : {len(candidats)} réglages sur 2023 ===", flush=True)
        essais = []
        for i, parametres in enumerate(candidats, start=1):
            modele = modele_configure(nom, parametres, args.jobs)
            depart = perf_counter()
            modele.fit(X_2022, y_2022)
            prediction = modele.predict(X_2023)
            valeurs = scores(y_2023, prediction)
            secondes = perf_counter() - depart
            lignes = {"modele": NOMS[nom], "reglage": i,
                      "parametres": json.dumps(parametres, sort_keys=True),
                      "MAE_2023_MW": valeurs["MAE_MW"],
                      "RMSE_2023_MW": valeurs["RMSE_MW"],
                      "biais_2023_MW": valeurs["biais_MW"],
                      "duree_secondes": round(secondes, 1)}
            essais.append(lignes)
            details.append(lignes)
            print(f" {i}/{len(candidats)} : RMSE 2023 = "
                  f"{valeurs['RMSE_MW']:.2f} MW ; paramètres = {parametres}", flush=True)

        # Choix défini UNIQUEMENT par la RMSE sur 2023 ; départage par ordre des candidats.
        gagnant = min(essais, key=lambda l: (l["RMSE_2023_MW"], l["reglage"]))
        parametres = candidats[gagnant["reglage"] - 1]
        print(f"Configuration choisie en 2023 : {parametres}", flush=True)
        modele_final = modele_configure(nom, parametres, args.jobs)
        print("Réentraînement sur 2012–2023 puis prévision 2024...", flush=True)
        depart = perf_counter()
        modele_final.fit(X_train, y_train)
        pred_2024 = modele_final.predict(X_2024)
        val = scores(y_2024, pred_2024)
        print(f"2024 : MAE={val['MAE_MW']:.2f} MW ; "
              f"RMSE={val['RMSE_MW']:.2f} MW ; "
              f"biais={val['biais_MW']:+.2f} MW", flush=True)
        rmse_reference_recalculee = np.nan
        if args.recalculer_reference:
            print("Recalcul du modèle de référence dans le même environnement...", flush=True)
            original = clone(creer_modeles()[NOMS[nom]])
            if nom == "foret":
                original.set_params(randomforestregressor__n_jobs=args.jobs)
            original.fit(X_train, y_train)
            rmse_reference_recalculee = scores(y_2024, original.predict(X_2024))["RMSE_MW"]
        synthese.append({
            "modele": NOMS[nom],
            "RMSE_reference_2024_MW": references.get(NOMS[nom], np.nan),
            "RMSE_reference_recalculee_2024_MW": rmse_reference_recalculee,
            "MAE_2024_MW": val["MAE_MW"],
            "RMSE_2024_MW": val["RMSE_MW"],
            "biais_2024_MW": val["biais_MW"],
            "RMSE_choix_2023_MW": gagnant["RMSE_2023_MW"],
            "parametres_retenus": json.dumps(parametres, sort_keys=True),
            "temps_refit_et_prediction_s": round(perf_counter()-depart, 1),
            "jours": int(meta_2024["jour_cible"].nunique()),
            "heures": len(y_2024),
        })
        res = meta_2024.copy()
        res["modele"] = NOMS[nom]
        res["reel_MW"] = y_2024
        res["prediction_MW"] = pred_2024
        previsions.append(res)

    df_details = pd.DataFrame(details).sort_values(["modele", "RMSE_2023_MW"])
    df_resultats = pd.DataFrame(synthese).sort_values("RMSE_2024_MW")
    df_previsions = pd.concat(previsions, ignore_index=True)
    df_details.to_csv(sorties / "reglages_2023.csv", index=False)
    df_resultats.to_csv(sorties / "comparaison_2024.csv", index=False)
    df_previsions.to_csv(sorties / "previsions_2024.csv", index=False)
    enregistrer_provenance(sorties, Path(__file__), vars(args) | {"sortie": str(sorties)})
    generer_analyse(df_details, df_resultats, sorties)

    print("\n=== RÉSULTATS 2024 — PARAMÈTRES CHOISIS SUR 2023 ===")
    print(df_resultats[["modele", "MAE_2024_MW", "RMSE_2024_MW",
                        "RMSE_reference_2024_MW",
                        "RMSE_reference_recalculee_2024_MW"]].round(2).to_string(index=False))
    print(f"\nFichiers sauvegardés : {sorties}")
    print(f"Temps total d'exécution : {perf_counter()-debut:.1f} s")
    print("Test 2025 non consulté ni modifié.")


if __name__ == "__main__":
    main()
