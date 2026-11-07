"""Vérifier les sorties de Nada, puis produire une comparaison commune."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from protocole import HEURE_COUPURE, jours_communs, provenance

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "results/analyse_2024"
FICHIERS = {
    "benchmarks": ("benchmarks.py", "previsions_horaires_2024.csv", "comparaison_2024.csv",
                   {"persistance", "semaine_precedente", "moyenne_4_semaines"}),
    "statistiques": ("modeles_statistiques.py", "previsions_horaires_2024.csv", "comparaison_2024.csv",
                     {"AR(1)", "AR(2)", "ARMA(1,1)"}),
    "ml": ("modeles_ml.py", "previsions_ml_2024.csv", "comparaison_ml_2024.csv",
           {"Regression lineaire", "Ridge", "Random Forest", "Gradient Boosting"}),
}


def scores(groupe):
    erreur = groupe.reel_MW - groupe.prediction_MW
    return {"heures": len(groupe), "MAE_MW": erreur.abs().mean(),
            "RMSE_MW": np.sqrt((erreur**2).mean()), "biais_MW": erreur.mean()}


def verifier():
    train = pd.read_csv(RACINE / "data/merge/train.csv", parse_dates=["horodatage"])
    val = pd.read_csv(RACINE / "data/merge/validation.csv", parse_dates=["horodatage"])
    assert train.horodatage.between("2012-01-01", "2023-12-31 23:00:00").all()
    assert val.horodatage.between("2024-01-01", "2024-12-31 23:00:00").all()
    donnees = pd.concat([train, val], ignore_index=True)
    jours = jours_communs(donnees, "2024-01-01", "2024-12-31")
    assert len(jours) > 0
    heures = pd.DatetimeIndex([j + pd.Timedelta(hours=h) for j in jours for h in range(24)])
    y = donnees.set_index("horodatage").consommation_MW
    previsions, bilans = [], []
    for famille, (script, fichier, fichier_scores, modeles) in FICHIERS.items():
        dossier = SORTIE / famille
        execution = json.loads((dossier / "execution.json").read_text(encoding="utf-8"))
        assert execution == provenance(RACINE / "src" / script), f"Sorties périmées ou environnement différent : {famille}"
        annonces = pd.read_csv(dossier / "jours_evalues.csv", parse_dates=["jour"])
        assert pd.DatetimeIndex(annonces.jour).equals(jours), famille
        p = pd.read_csv(dossier / fichier, parse_dates=["horodatage"])
        assert set(p.modele) == modeles
        assert not p.duplicated(["modele", "horodatage"]).any()
        assert np.isfinite(p[["reel_MW", "prediction_MW"]]).all().all()
        declares = pd.read_csv(dossier / fichier_scores).set_index("modele")
        for nom, g in p.groupby("modele"):
            g = g.sort_values("horodatage")
            assert pd.DatetimeIndex(g.horodatage).equals(heures), nom
            np.testing.assert_allclose(g.reel_MW, y.reindex(heures), rtol=0, atol=1e-8)
            bilan = scores(g)
            np.testing.assert_allclose([bilan["MAE_MW"], bilan["RMSE_MW"]],
                                       declares.loc[nom, ["MAE_MW", "RMSE_MW"]].to_numpy(dtype=float),
                                       rtol=1e-10, atol=1e-6)
            if nom == "semaine_precedente":
                attendu = y.reindex(heures - pd.Timedelta(days=7)).to_numpy()
            elif nom == "moyenne_4_semaines":
                attendu = np.mean([y.reindex(heures - pd.Timedelta(days=k)).to_numpy()
                                   for k in [7, 14, 21, 28]], axis=0)
            elif nom == "persistance":
                coupures = heures.normalize() - pd.Timedelta(days=1) + pd.Timedelta(hours=HEURE_COUPURE)
                attendu = y.reindex(coupures).to_numpy()
            else:
                attendu = None
            if attendu is not None:
                np.testing.assert_allclose(g.prediction_MW, attendu, rtol=0, atol=1e-8)
            bilans.append({"famille": famille, "modele": nom, **bilan})
        p["famille"] = famille
        previsions.append(p[["horodatage", "modele", "famille", "reel_MW", "prediction_MW"]])
    return pd.concat(previsions, ignore_index=True), pd.DataFrame(bilans).sort_values("RMSE_MW"), jours


def main():
    previsions, bilan, jours = verifier()
    previsions.to_csv(SORTIE / "previsions_communes.csv", index=False)
    bilan.to_csv(SORTIE / "comparaison_globale.csv", index=False)
    (SORTIE / "CONTROLES.json").write_text(json.dumps({
        "jours_communs": len(jours), "heures_par_modele": len(jours)*24,
        "modeles": len(bilan), "scores_et_benchmarks": "vérifiés",
        "provenance": "scripts, données et versions vérifiés",
        "test_2025": "non chargé et non évalué"}, indent=2, ensure_ascii=False), encoding="utf-8")
    meilleur = bilan.iloc[0]
    texte = (f"# Synthèse de validation 2024\n\n{len(jours)} journées communes, {len(bilan)} modèles et benchmarks.\n\n"
             f"Plus faible RMSE : **{meilleur.modele}**, {meilleur.RMSE_MW:.1f} MW.\n\n"
             "| Modèle | MAE (MW) | RMSE (MW) | Biais (MW) |\n|---|---:|---:|---:|\n")
    for ligne in bilan.itertuples():
        texte += f"| {ligne.modele} | {ligne.MAE_MW:.1f} | {ligne.RMSE_MW:.1f} | {ligne.biais_MW:.1f} |\n"
    texte += ("\nClassement sur la validation, pas sur un test indépendant. Test 2025 non évalué. "
              "Les délais de publication restent des hypothèses ; les contrôles numériques ne prouvent pas "
              "la disponibilité historique des données. Les diagnostics complètent ces scores.\n")
    (SORTIE / "SYNTHESE.md").write_text(texte, encoding="utf-8")


if __name__ == "__main__":
    main()
