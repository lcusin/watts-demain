"""Prévision horaire par profil hebdomadaire pondéré et ajustement de niveau.

À 14 h le jour J, prévoir les 24 valeurs horaires de D = J + 1.
Pour chaque heure h du lendemain, on construit un profil à partir des mêmes
heures des K semaines précédentes, avec des poids proportionnels à
``decay**(k-1)``. On ajuste ensuite les 24 heures par l'écart moyen observé
entre 00 h et 08 h inclus le jour J et les matins historiques comparables.

    P[D,h] = somme_k w_k C[D-7k,h]
    delta_J = moyenne_{h=0..8}(C[J,h] - somme_k w_k C[J-7k,h])
    prevision[D,h] = P[D,h] + correction * delta_J

Les observations de J + 1 ne servent qu'à calculer les erreurs a posteriori.
Les changements d'heure sont masqués avant la constitution des historiques.
L'évaluation porte sur les dates communes de validation 2024 ; le test 2025
n'est pas consulté. L'usage des archives RTE définitives constitue une
simulation rétrospective, et non une garantie de disponibilité à J, 14 h.

Usage (depuis la racine du dépôt) :
    python src/benchmark_hebdomadaire_adaptatif.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd


RACINE = Path(__file__).resolve().parent.parent
DONNEES = RACINE / "data" / "merge"
JOURS_REFERENCE = RACINE / "results" / "analyse_2024" / "benchmarks" / "jours_evalues.csv"
SCORES_EXISTANTS = RACINE / "results" / "analyse_2024" / "comparaison_globale.csv"
SORTIE_DEFAUT = RACINE / "results" / "analyse_2024" / "benchmark_hebdomadaire_adaptatif"
MATIN = tuple(range(9))  # 00 h, 01 h, ..., 08 h inclus
MODELE = "Moyenne hebdomadaire adaptative"


def empreinte(chemin: Path) -> str:
    """Empreinte SHA256 pour pouvoir retracer les entrees de l'experience."""
    h = hashlib.sha256()
    with chemin.open("rb") as fichier:
        for bloc in iter(lambda: fichier.read(1024 * 1024), b""):
            h.update(bloc)
    return h.hexdigest()


def charger_profils() -> pd.DataFrame:
    """Lit TRAIN + VALIDATION 2024, jamais TEST 2025."""
    colonnes = ["horodatage", "consommation_MW", "jour_changement_heure"]
    morceaux = []
    for nom in ("train.csv", "validation.csv"):
        chemin = DONNEES / nom
        if not chemin.is_file():
            raise FileNotFoundError(f"Fichier absent : {chemin}")
        morceaux.append(pd.read_csv(chemin, usecols=colonnes, parse_dates=["horodatage"]))

    df = pd.concat(morceaux, ignore_index=True).sort_values("horodatage")
    if df["horodatage"].isna().any() or df["horodatage"].duplicated().any():
        raise ValueError("Horodatages invalides ou dupliques dans train/validation.")
    df["date"] = df["horodatage"].dt.normalize()
    # La colonne 'heure' du CSV peut etre une chaine '08:00:00'.
    # On recupere l'heure directement a partir de l'horodatage.
    df["heure"] = df["horodatage"].dt.hour

    # Garder les 24 emplacements par jour, sans exploiter les valeurs ambigues.
    transitions = df["jour_changement_heure"].astype(str).str.lower().isin(
        ("true", "1", "1.0")
    )
    df.loc[transitions, "consommation_MW"] = np.nan

    profils = df.pivot(index="date", columns="heure", values="consommation_MW")
    profils = profils.sort_index().reindex(columns=range(24))
    if profils.shape[1] != 24:
        raise ValueError("Le tableau ne contient pas 24 heures par jour.")
    return profils


def charger_jours_validation() -> pd.DatetimeIndex:
    """Récupère les jours communs aux modèles de la validation 2024."""
    if not JOURS_REFERENCE.is_file():
        raise FileNotFoundError(
            f"Fichier de dates communes absent : {JOURS_REFERENCE}\n"
            "Executer d'abord src/benchmarks.py pour creer les jours de reference."
        )
    tableau = pd.read_csv(JOURS_REFERENCE)
    if "jour" not in tableau.columns:
        raise ValueError(f"La colonne 'jour' est absente de {JOURS_REFERENCE}")
    dates = pd.DatetimeIndex(pd.to_datetime(tableau["jour"])).normalize().sort_values()
    if dates.has_duplicates or not (dates.year == 2024).all():
        raise ValueError("Les dates de reference doivent etre distinctes et dans l'annee 2024.")
    return dates


def construire_previsions(
    profils: pd.DataFrame,
    jours: pd.DatetimeIndex,
    weeks: int,
    decay: float,
    correction: float,
    min_weeks: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Construit les predictions et les diagnostics pour chaque jour de 2024."""
    predictions = []
    bilans = []

    for jour_cible in jours:
        # La decision est prise la veille, jour J, a 14 h.
        jour_origine = jour_cible - pd.Timedelta(days=1)
        if jour_cible not in profils.index or jour_origine not in profils.index:
            raise ValueError(f"Jour cible ou origine absent : {jour_cible.date()}")

        reel = profils.loc[jour_cible].to_numpy(dtype=float)
        matin_reel = profils.loc[jour_origine, list(MATIN)].to_numpy(dtype=float)
        if not (np.isfinite(reel).all() and np.isfinite(matin_reel).all()):
            raise ValueError(f"Jour de validation incomplet : {jour_cible.date()}")

        profils_historiques = []
        matins_historiques = []
        poids = []
        semaines_retenues = []

        for k in range(1, weeks + 1):
            date_profil = jour_cible - pd.Timedelta(days=7 * k)
            date_matin = jour_origine - pd.Timedelta(days=7 * k)
            if date_profil not in profils.index or date_matin not in profils.index:
                continue

            profil_passe = profils.loc[date_profil].to_numpy(dtype=float)
            matin_passe = profils.loc[date_matin, list(MATIN)].to_numpy(dtype=float)
            if not (np.isfinite(profil_passe).all() and np.isfinite(matin_passe).all()):
                continue

            # Garde-fou : toutes les mesures sources precedent l'origine J a 14 h.
            if not (date_profil < jour_origine and date_matin < jour_origine):
                raise ValueError("Une mesure historique ne précède pas l'origine de prévision.")
            profils_historiques.append(profil_passe)
            matins_historiques.append(matin_passe)
            poids.append(decay ** (k - 1))
            semaines_retenues.append(k)

        if len(poids) < min_weeks:
            raise ValueError(
                f"{jour_cible.date()} : seulement {len(poids)} semaines utilisables "
                f"(minimum : {min_weeks})."  # Ne jamais ignorer un jour sans le signaler.
            )

        poids_norm = np.asarray(poids, dtype=float)
        poids_norm /= poids_norm.sum()
        # Des moyennes ponderees separees pour chaque heure de la cible et du matin.
        profil_reference = np.average(
            np.vstack(profils_historiques), axis=0, weights=poids_norm
        )
        matin_reference = np.average(
            np.vstack(matins_historiques), axis=0, weights=poids_norm
        )
        delta = float(np.mean(matin_reel - matin_reference))
        predit = profil_reference + correction * delta

        heures = [jour_cible + pd.Timedelta(hours=h) for h in range(24)]
        predictions.append(pd.DataFrame({
            "horodatage": heures,
            "modele": MODELE,
            "reel_MW": reel,
            "prediction_MW": predit,
            "correction_niveau_MW": correction * delta,
            "semaines_utilisees": len(semaines_retenues),
        }))
        erreur = reel - predit
        bilans.append({
            "jour": jour_cible.date().isoformat(),
            "semaines_utilisees": len(semaines_retenues),
            "semaines_k": ",".join(map(str, semaines_retenues)),
            "correction_niveau_MW": correction * delta,
            "MAE_MW": float(np.mean(np.abs(erreur))),
            "RMSE_MW": float(np.sqrt(np.mean(erreur ** 2))),
            "biais_MW": float(np.mean(erreur)),
        })

    return pd.concat(predictions, ignore_index=True), pd.DataFrame(bilans)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weeks", type=int, default=8,
                        help="Nombre de semaines anterieures (defaut : 8)")
    parser.add_argument("--decay", type=float, default=0.7,
                        help="Decroissance des poids, dans ]0, 1] (defaut : 0.7)")
    parser.add_argument("--correction", type=float, default=1.0,
                        help="Coefficient de correction du niveau du matin (defaut : 1)")
    parser.add_argument("--min-weeks", type=int, default=4,
                        help="Nombre minimal de semaines valides par cible (defaut : 4)")
    parser.add_argument("--output", type=Path, default=SORTIE_DEFAUT,
                        help="Dossier de resultats de cette methode uniquement")
    args = parser.parse_args()

    if args.weeks < 1 or not (0 < args.decay <= 1) or args.min_weeks < 1:
        parser.error("Exiger weeks >= 1, min-weeks >= 1 et 0 < decay <= 1.")
    if args.min_weeks > args.weeks or not np.isfinite(args.correction):
        parser.error("min-weeks doit etre <= weeks, et correction doit etre finie.")
    sortie = args.output if args.output.is_absolute() else RACINE / args.output
    # Ne pas autoriser une ecriture involontaire dans les dossiers d'autres modeles.
    sortie = sortie.resolve()
    # Les sorties restent isolées pour protéger les résultats du projet commun.
    dossier_experience = SORTIE_DEFAUT.resolve()
    if sortie != dossier_experience and dossier_experience not in sortie.parents:
        parser.error("La sortie doit être située dans le dossier du benchmark adaptatif.")

    profils = charger_profils()
    jours = charger_jours_validation()
    previsions, quotidiens = construire_previsions(
        profils, jours, args.weeks, args.decay, args.correction, args.min_weeks
    )
    if len(previsions) != 24 * len(jours):
        raise AssertionError("Le nombre de previsions n'est pas egal a 24 x jours evalues.")

    erreurs = previsions["reel_MW"].to_numpy() - previsions["prediction_MW"].to_numpy()
    mae = float(np.mean(np.abs(erreurs)))
    rmse = float(np.sqrt(np.mean(erreurs ** 2)))
    biais = float(np.mean(erreurs))
    score = pd.DataFrame([{
        "modele": MODELE,
        "jours": len(jours),
        "heures": len(previsions),
        "MAE_MW": mae,
        "RMSE_MW": rmse,
        "biais_MW": biais,
        "weeks": args.weeks,
        "decay": args.decay,
        "correction": args.correction,
    }])

    sortie.mkdir(parents=True, exist_ok=True)
    previsions.to_csv(sortie / "previsions_horaires_2024.csv", index=False)
    quotidiens.to_csv(sortie / "scores_quotidiens_2024.csv", index=False)
    score.to_csv(sortie / "comparaison_2024.csv", index=False)

    configuration = {
        "objectif": "Prévision de J+1 à J 14 h, validation 2024 uniquement",
        "statut": "Expérience rétrospective ; résultats 2024 déjà consultés lors du développement",
        "weeks": args.weeks,
        "decay": args.decay,
        "correction": args.correction,
        "min_weeks": args.min_weeks,
        "jours_evalues": len(jours),
        "heures_evaluees": len(previsions),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "sha256_fichiers": {
            str(f.relative_to(RACINE)): empreinte(f)
            for f in (DONNEES / "train.csv", DONNEES / "validation.csv", JOURS_REFERENCE,
                      Path(__file__).resolve())
        },
    }
    (sortie / "execution.json").write_text(
        json.dumps(configuration, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n===== BENCHMARK HEBDOMADAIRE ADAPTATIF — VALIDATION 2024 =====")
    print(f"Reglage : weeks={args.weeks}, decay={args.decay}, correction={args.correction}")
    print(f"Jours evalues : {len(jours)} | Heures evaluees : {len(previsions)}")
    print(f"Semaines historiques : {quotidiens.semaines_utilisees.min()} a "
          f"{quotidiens.semaines_utilisees.max()} selon la journee")
    print(f"MAE  : {mae:,.2f} MW")
    print(f"RMSE : {rmse:,.2f} MW")
    print(f"Biais: {biais:,.2f} MW (reel - predit)")

    if SCORES_EXISTANTS.is_file():
        base = pd.read_csv(SCORES_EXISTANTS)
        colonne = ["modele", "MAE_MW", "RMSE_MW"]
        if set(colonne).issubset(base.columns):
            nouveau = pd.DataFrame([{"modele": MODELE, "MAE_MW": mae, "RMSE_MW": rmse}])
            classement = pd.concat([base[colonne], nouveau], ignore_index=True)
            classement = classement.sort_values("RMSE_MW", kind="stable")
            classement.to_csv(sortie / "classement_avec_modeles_2024.csv", index=False)
            print("\n===== CLASSEMENT PAR RMSE 2024 (MEMES JOURS) =====")
            print(classement.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    print(f"\nResultats enregistres : {sortie}")
    print("Test 2025 non utilise ni modifie.")


if __name__ == "__main__":
    main()
