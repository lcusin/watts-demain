"""Reproduire les analyses dans l'ordre, depuis n'importe quel dossier."""
from pathlib import Path
import argparse
import subprocess
import sys

DOSSIER = Path(__file__).resolve().parent
PROJET = DOSSIER.parent
ETAPES = [
    ("Donnees et audit horaire", [PROJET / "data/merge/merge.py",
                                  PROJET / "data/merge/train_valid_test_split.py",
                                  DOSSIER / "scripts/aligner_meteo_calendrier.py"]),
    ("Exploration et decomposition classique", [DOSSIER / "scripts/description.py"]),
    ("Tendance longue", [DOSSIER / "scripts/tendance_moyenne_mobile.py"]),
    ("STL", [DOSSIER / "scripts/stl.py"]),
    ("Difference annuelle", [DOSSIER / "scripts/differenciation_annuelle.py"]),
    ("Comparaison des decompositions", [DOSSIER / "scripts/comparer_methodes.py"]),
    ("Meteo et calendrier", [DOSSIER / "scripts/decomposition_meteo_calendrier.py"]),
    ("Correction autoregressive", [DOSSIER / "scripts/prevision_residus_ar.py"]),
    ("Validation 2024", [DOSSIER / "scripts/validation_meteo_2024.py"]),
    ("Modeles du cours et benchmarks", [DOSSIER / "scripts/modeles_cours.py",
                                          DOSSIER / "scripts/criteres_information.py"]),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--depuis", type=int, choices=range(len(ETAPES)), default=0)
    parser.add_argument("--jusqua", type=int, choices=range(len(ETAPES)), default=len(ETAPES)-1)
    args = parser.parse_args()
    assert args.depuis <= args.jusqua
    for numero in range(args.depuis, args.jusqua + 1):
        nom, scripts = ETAPES[numero]
        print(f"{numero}/{len(ETAPES)-1} - {nom}", flush=True)
        for script in scripts:
            subprocess.run([sys.executable, "-B", str(script)], cwd=PROJET, check=True)
    if args.jusqua == len(ETAPES) - 1:
        subprocess.run([sys.executable, "-B", str(DOSSIER / "scripts/verifier_et_synthetiser.py")],
                       cwd=PROJET, check=True)


if __name__ == "__main__":
    main()
