"""Trois références de consommation, calculées uniquement sur le passé local."""
import numpy as np
import pandas as pd

NOMS = {
    "benchmark_persistance": "Persistance consommation",
    "benchmark_semaine": "Semaine précédente",
    "benchmark_4_semaines": "Moyenne des 4 semaines",
}


def prevoir_benchmarks(y, cibles, coupure):
    """Index local naïf ; y exclut les jours de changement d'heure.

    Aucun remplacement si une des quatre semaines manque : le jour est exclu
    de la comparaison commune. La coupure est celle du protocole (J12 ou J8).
    """
    assert y.index.is_unique and y.index.tz is None and cibles.tz is None
    sources = [cibles - pd.DateOffset(weeks=k) for k in range(1, 5)]
    assert all(dates.max() <= coupure for dates in sources)
    semaines = np.array([y.reindex(dates).to_numpy(dtype=float) for dates in sources])
    derniere = y.get(coupure, np.nan)
    if not np.isfinite(derniere) or not np.isfinite(semaines).all():
        return None
    return {"benchmark_persistance": np.full(len(cibles), derniere),
            "benchmark_semaine": semaines[0],
            "benchmark_4_semaines": semaines.mean(axis=0)}
