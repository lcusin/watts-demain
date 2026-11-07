"""Lancer la chaine d analyse complete dans l ordre."""
import argparse
from pathlib import Path
import subprocess
import sys

RACINE = Path(__file__).resolve().parent
ETAPES = [
    ("Préparation", ["data/conso/preparer_dataset_eco2mix.py",
                     "data/calendrier/data_calendrier_prep.py",
                     "data/temperature/extraction_meteo.py",
                     "data/merge/merge.py", "data/merge/train_valid_test_split.py"]),
    ("Exploration du train", ["src/exploration.py"]),
    ("Couverture geographique", ["src/couverture_geographique.py"]),
    ("Benchmarks", ["src/benchmarks.py"]),
    ("AR et ARMA", ["src/modeles_statistiques.py"]),
    ("Machine learning", ["src/modeles_ml.py"]),
    ("Contrôles et synthèse", ["src/synthese.py"]),
    ("Diagnostics complémentaires", ["src/diagnostics.py"]),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--depuis", type=int, choices=range(len(ETAPES)), default=0)
    parser.add_argument("--jusqua", type=int, choices=range(len(ETAPES)), default=len(ETAPES)-1)
    args = parser.parse_args()
    assert args.depuis <= args.jusqua
    for numero in range(args.depuis, args.jusqua + 1):
        nom, scripts = ETAPES[numero]
        print(f"{numero} — {nom}", flush=True)
        for script in scripts:
            subprocess.run([sys.executable, "-B", str(RACINE / script)], cwd=RACINE, check=True)


if __name__ == "__main__":
    main()
