"""Télécharger les archives nationales annuelles définitives éCO2mix de RTE.

Usage (depuis la racine du projet) :
    python data/conso/telecharger_eco2mix.py --years 2025 --dest data/conso/test_telechargement
    python data/conso/telecharger_eco2mix.py
    python data/conso/telecharger_eco2mix.py --force

Les archives contiennent des fichiers .xls en réalité textuels et tabulés,
compatibles avec data/conso/preparer_dataset_eco2mix.py (version qui lit *.xls).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZipFile, BadZipFile, is_zipfile
import requests

DEST_DEFAUT = Path(__file__).resolve().parent / "raw"
URL_BASE = "https://eco2mix.rte-france.com/download/eco2mix"


def telecharger_annee(annee: int, destination: Path, force: bool = False) -> Path:
    if not 2012 <= annee <= 2025:
        raise ValueError(f"Année hors de la période du projet : {annee}")

    destination.mkdir(parents=True, exist_ok=True)
    nom = f"eCO2mix_RTE_Annuel-Definitif_{annee}"
    fichier = destination / f"{nom}.xls"

    if fichier.is_file() and fichier.stat().st_size > 0 and not force:
        print(f"{annee} : fichier déjà présent — {fichier.name}")
        return fichier

    url = f"{URL_BASE}/{nom}.zip"
    print(f"{annee} : téléchargement de {url}", flush=True)
    archive_temp = None
    extrait_temp = None

    try:
        # Un téléchargement temporaire évite de laisser un fichier partiel.
        with NamedTemporaryFile(dir=destination, suffix=".zip.part", delete=False) as f:
            archive_temp = Path(f.name)
            with requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Watts-Demain academic project)"},
                stream=True,
                timeout=(20, 180),
            ) as reponse:
                if not reponse.ok:
                    raise RuntimeError(
                        f"HTTP {reponse.status_code} pour {url}\n"
                        "Vérifier le lien sur la page officielle RTE."
                    )
                for bloc in reponse.iter_content(chunk_size=1024 * 1024):
                    if bloc:
                        f.write(bloc)

        if not is_zipfile(archive_temp):
            raise ValueError(f"Le téléchargement {annee} n'est pas une archive ZIP valide")

        with ZipFile(archive_temp) as archive:
            # Ne jamais décompresser de chemins fournis par l'archive.
            membres = [
                x for x in archive.infolist()
                if not x.is_dir() and Path(x.filename).suffix.lower() == ".xls"
            ]
            if len(membres) != 1:
                raise ValueError(
                    f"Année {annee} : attendu un seul fichier .xls, trouvé {len(membres)} : "
                    f"{archive.namelist()}"
                )
            if str(annee) not in Path(membres[0].filename).name:
                raise ValueError(f"Année inattendue dans le ZIP : {membres[0].filename}")

            with NamedTemporaryFile(dir=destination, suffix=".xls.part", delete=False) as f:
                extrait_temp = Path(f.name)
                with archive.open(membres[0]) as entree:
                    while bloc := entree.read(1024 * 1024):
                        f.write(bloc)

        if extrait_temp.stat().st_size == 0:
            raise ValueError(f"Fichier XLS vide pour {annee}")
        extrait_temp.replace(fichier)
        print(f"{annee} : OK — {fichier.name}")
        return fichier

    except (requests.RequestException, BadZipFile, OSError, ValueError, RuntimeError):
        print(f"{annee} : ÉCHEC — le fichier existant n'a pas été remplacé")
        raise
    finally:
        if archive_temp is not None:
            archive_temp.unlink(missing_ok=True)
        if extrait_temp is not None:
            extrait_temp.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--years", nargs="+", type=int, default=list(range(2012, 2026)),
        help="Années à télécharger (défaut : 2012 à 2025)",
    )
    parser.add_argument(
        "--dest", type=Path, default=DEST_DEFAUT,
        help="Dossier de sortie (défaut : data/conso/raw)",
    )
    parser.add_argument("--force", action="store_true", help="Retélécharger les fichiers existants")
    args = parser.parse_args()

    for annee in args.years:
        telecharger_annee(annee, destination=args.dest, force=args.force)
    print("\nTéléchargement terminé. Tu peux maintenant lancer :")
    print("python data/conso/preparer_dataset_eco2mix.py")


if __name__ == "__main__":
    main()
