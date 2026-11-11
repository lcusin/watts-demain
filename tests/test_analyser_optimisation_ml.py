"""Tests des contrôles de comparabilité et des métriques de diagnostic."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analyser_optimisation_ml import (comparer_previsions, metriques, score_par_groupe)


class DiagnosticsMLTest(unittest.TestCase):
    def test_metriques_et_signe_du_biais(self):
        resultat = metriques(np.array([3.0, -1.0]))
        self.assertAlmostEqual(resultat["MAE_MW"], 2.0)
        self.assertAlmostEqual(resultat["RMSE_MW"], np.sqrt(5))
        self.assertAlmostEqual(resultat["biais_MW"], 1.0)

    def test_gains_par_groupes(self):
        tab = pd.DataFrame({
            "modele": ["Ridge"] * 4,
            "jour_cible": pd.to_datetime(["2024-01-01"] * 2 + ["2024-01-02"] * 2),
            "saison": ["Hiver"] * 4,
            "erreur_initial": [4., -4., 2., -2.],
            "erreur_optimise": [2., -2., 1., -1.],
        })
        ligne = score_par_groupe(tab, "saison").iloc[0]
        self.assertAlmostEqual(ligne.gain_RMSE_pct, 50.0)
        self.assertEqual(ligne.jours_ameliores, 2)
        self.assertEqual(ligne.heures, 4)

    def test_rejet_des_dates_de_prevision_differentes(self):
        # Construit 338 jours x 24 heures pour vérifier le contrôle des paires.
        heures = pd.date_range("2024-01-01", periods=338 * 24, freq="h")
        blocs = []
        for nom in ("Random Forest", "Gradient Boosting", "Ridge"):
            blocs.append(pd.DataFrame({
                "modele": nom,
                "jour_cible": heures.normalize(),
                "horodatage": heures,
                "occurrence_heure": 0,
                "reel_MW": 100.0,
                "prediction_MW": 101.0,
            }))
        initial = pd.concat(blocs, ignore_index=True)
        optimise = initial.copy()
        masque = optimise.modele.eq("Ridge") & optimise.horodatage.eq(pd.Timestamp("2024-01-01 00:00"))
        optimise.loc[masque, "horodatage"] = pd.Timestamp("2024-01-01 00:30")
        with self.assertRaisesRegex(ValueError, "Dates/heures différentes"):
            comparer_previsions(initial, optimise)


if __name__ == "__main__":
    unittest.main()
