"""Contrôles sur des données synthétiques : valeurs attendues et mécanismes V2.

Exécution : python -m unittest discover -s tests -p "test_benchmark_hebdomadaire.py"
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from benchmark_hebdomadaire_adaptatif import construire_previsions
from experimenter_benchmark_hebdomadaire_v2 import JourPret, Reglage, prevoir


class MethodeHebdomadaireTests(unittest.TestCase):
    def test_prevision_v1_sur_deux_semaines(self) -> None:
        """Le profil et la correction utilisent les dates décalées de 7 et 14 jours."""
        dates = pd.date_range("2023-02-01", "2023-03-15", freq="D")
        valeurs = np.vstack([
            40_000 + d * 150 + np.arange(24) * 30
            for d in range(len(dates))
        ]).astype(float)
        profils = pd.DataFrame(valeurs, index=dates, columns=range(24))
        cible = pd.Timestamp("2023-03-15")
        origine = cible - pd.Timedelta(days=1)

        previsions, bilans = construire_previsions(
            profils, pd.DatetimeIndex([cible]), weeks=2, decay=0.5,
            correction=1.0, min_weeks=2,
        )
        poids = np.array([2 / 3, 1 / 3])
        cible_passee = sum(poids[k-1] * profils.loc[cible-pd.Timedelta(days=7*k)].to_numpy()
                           for k in (1, 2))
        matins_passes = sum(poids[k-1] * profils.loc[origine-pd.Timedelta(days=7*k), list(range(9))].to_numpy()
                            for k in (1, 2))
        decalage = np.mean(profils.loc[origine, list(range(9))].to_numpy() - matins_passes)
        np.testing.assert_allclose(
            previsions.sort_values("horodatage")["prediction_MW"].to_numpy(),
            cible_passee + decalage, rtol=0, atol=1e-8,
        )
        self.assertEqual(len(previsions), 24)
        self.assertEqual(int(bilans["semaines_utilisees"].iloc[0]), 2)

    def test_semaine_masquee_est_exclue(self) -> None:
        dates = pd.date_range("2023-02-01", "2023-03-15", freq="D")
        profils = pd.DataFrame(50_000.0, index=dates, columns=range(24))
        cible = pd.Timestamp("2023-03-15")
        profils.loc[cible - pd.Timedelta(days=7), 9] = np.nan
        previsions, bilan = construire_previsions(
            profils, pd.DatetimeIndex([cible]), weeks=2, decay=0.7,
            correction=1.0, min_weeks=1,
        )
        self.assertEqual(int(bilan["semaines_utilisees"].iloc[0]), 1)
        np.testing.assert_allclose(previsions["prediction_MW"].to_numpy(), 50_000.0)

    def test_analogues_fetes_agissent_uniquement_sur_cible_feriee(self) -> None:
        configurations = [Reglage(False, "additif", 1.0, analogues_feries=True),
                          Reglage(False, "additif", 1.0, analogues_feries=False)]
        jour = JourPret(
            jour=pd.Timestamp("2024-12-25"), reel=np.full(24, 55_000.),
            matin_reel=np.full(9, 50_000.), ferie_cible=True, ferie_origine=False,
            profils={False: np.full(24, 51_000.), True: np.full(24, 51_000.)},
            matins={False: np.full(9, 50_000.), True: np.full(9, 50_000.)},
            n_semaines={False: 8, True: 8}, facteur_ferie=0.8,
        )
        np.testing.assert_allclose(prevoir(jour, configurations[0]), 51_000 * 0.9)
        np.testing.assert_allclose(prevoir(jour, configurations[1]), 51_000)
        jour.ferie_cible = False
        np.testing.assert_allclose(prevoir(jour, configurations[0]), 51_000)


if __name__ == "__main__":
    unittest.main()
