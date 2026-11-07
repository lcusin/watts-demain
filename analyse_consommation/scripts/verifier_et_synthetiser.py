"""Verifier la coherence des livrables et actualiser la synthese pour le rapport."""
import ast
import hashlib
import json
import platform
import re
import struct
from importlib.metadata import version

import numpy as np
import pandas as pd

from chemins_analyse import ANALYSE, PROJET, RESULTATS, SOURCES
from benchmarks import NOMS, prevoir_benchmarks


def verifier_cours(y):
    """Recalcul des scores, des references et d'une prevision AR(2) sans filtre."""
    dossier = RESULTATS / "10_modeles_cours"
    if not (dossier / "controles.json").exists():
        return None
    p = pd.read_csv(dossier / "predictions.csv", parse_dates=["horodatage", "coupure"])
    assert p.horodatage.max() < pd.Timestamp("2025-01-01")
    assert p.groupby(["modele", "jour"]).size().eq(24).all()
    grilles = [set(g.horodatage) for _, g in p.groupby("modele")]
    assert len(grilles) == 7 and all(g == grilles[0] for g in grilles)
    np.testing.assert_allclose(p.observe, y.reindex(p.horodatage), atol=1e-8)
    np.testing.assert_allclose(p.erreur_MW, p.observe-p.prevision, atol=1e-8)
    for jour, g in p[p.modele.isin(NOMS)].groupby("jour"):
        cibles = pd.DatetimeIndex(sorted(g.horodatage.unique()))
        coupure = pd.Timestamp(jour)-pd.Timedelta(hours=16)
        assert g.coupure.eq(coupure).all()
        references = prevoir_benchmarks(y, cibles, coupure)
        for nom, valeurs in references.items():
            np.testing.assert_allclose(g[g.modele==nom].sort_values("horodatage").prevision, valeurs)
    s = pd.read_csv(dossier / "scores.csv")
    for r in s.itertuples():
        g = p[(p.modele == r.modele) & (p.annee.lt(2024) if r.periode.startswith("interne") else p.annee.eq(2024))]
        assert len(g) == r.n
        np.testing.assert_allclose([r.MAE_MW, r.RMSE_MW, r.biais_MW],
            [g.erreur_MW.abs().mean(), np.sqrt((g.erreur_MW**2).mean()), g.erreur_MW.mean()])
    audit = pd.read_csv(dossier / "ajustements.csv")
    assert len(audit) == 16 and audit.convergence.all()
    # Calcul independant des previsions AR2 et inversion a une origine ordinaire.
    params = json.loads(audit[(audit.annee==2024)&(audit.modele=="AR2")].iloc[0].parametres)
    coupure = pd.Timestamp("2024-02-13 08:00:00")
    z = y.diff(24).diff().loc[:coupure].iloc[-2:].tolist()
    historique = y.loc[coupure-pd.Timedelta(hours=24):coupure].tolist()
    for _ in range(39):
        z.append(params["ar.L1"]*z[-1]+params["ar.L2"]*z[-2])
        historique.append(z[-1]+historique[-1]+historique[-24]-historique[-25])
    obtenu = p[(p.modele=="AR2") & (p.jour=="2024-02-14")].sort_values("horodatage").prevision
    np.testing.assert_allclose(obtenu, historique[-24:], rtol=1e-8, atol=1e-6)
    controle = json.loads((dossier / "controles.json").read_text())
    assert hashlib.sha256((PROJET / "data/merge/test.csv").read_bytes()).hexdigest() == controle["test_2025_sha256"]
    candidats = s[s.periode.str.startswith("interne") & ~s.modele.isin(NOMS)]
    assert candidats.sort_values("RMSE_MW").iloc[0].modele == controle["choix_sur_2021_2023"]
    return controle


def main():
    controles = {}
    for f in (ANALYSE / "scripts").glob("*.py"):
        ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
    fusion = pd.read_csv(PROJET / "data/merge/donnees_combinees.csv")
    jeux = {nom: pd.read_csv(PROJET / f"data/merge/{nom}.csv") for nom in ["train", "validation", "test"]}
    reconstruit = pd.concat(jeux.values(), ignore_index=True)
    assert fusion.horodatage.is_unique and fusion.horodatage.equals(reconstruit.horodatage)
    np.testing.assert_array_equal(fusion.consommation_MW, reconstruit.consommation_MW)
    for c in ["temperature_moyenne", "precipitation_moyenne"]:
        np.testing.assert_allclose(fusion[c], reconstruit[c], rtol=1e-12, equal_nan=True)
    controles["lignes_donnees"] = {nom: len(d) for nom, d in jeux.items()}
    assert jeux["train"].horodatage.max() < "2024-01-01"
    assert jeux["validation"].horodatage.min() >= "2024-01-01"
    assert jeux["validation"].horodatage.max() < "2025-01-01"
    assert jeux["test"].horodatage.min() >= "2025-01-01"
    # Les anciennes références Ridge restent historiques : vérifier désormais
    # les scores MCO depuis les erreurs exportées et les rangs des ajustements.
    erreurs = pd.read_csv(RESULTATS / "06_meteo_calendrier/residus_2021_2023.csv", index_col=0)
    scores = pd.read_csv(RESULTATS / "06_meteo_calendrier/comparaison_2021_2023.csv").set_index("modele")
    for nom in erreurs:
        e = erreurs[nom].dropna()
        np.testing.assert_allclose(scores.loc[nom, ["MAE_MW", "RMSE_MW", "biais_MW"]].to_numpy(dtype=float),
                                   [e.abs().mean(), np.sqrt((e**2).mean()), e.mean()])
    controles["estimateur"] = "Extensions : moindres carres ; modeles du cours : maximum de vraisemblance gaussienne"
    for dossier in ["06_meteo_calendrier", "07_prevision_ar", "08_validation_2024"]:
        audit = pd.read_csv(RESULTATS / dossier / "audit_moindres_carres.csv")
        assert audit.rang.eq(audit.variables).all() and audit.estimateur.eq("moindres_carres").all()
        controles[dossier + "_ajustements_identifiables"] = len(audit)
    source = pd.concat([jeux["train"], jeux["validation"]], ignore_index=True)
    source["horodatage"] = pd.to_datetime(source.horodatage)
    source = source.set_index("horodatage")
    y = source.consommation_MW.mask(source.jour_changement_heure)
    controles["modeles_cours"] = verifier_cours(y)
    for dossier, cle, heure in [("07_prevision_ar", "modele", 12), ("08_validation_2024", "scenario", 8)]:
        p = pd.read_csv(RESULTATS / dossier / "previsions.csv", parse_dates=["origine_locale", "cible_locale"])
        assert p.groupby([cle, "origine_locale"]).size().eq(24).all()
        grilles = [set(b.cible_locale) for _, b in p.groupby(cle)]
        assert len(grilles) == 6 and all(g == grilles[0] for g in grilles)
        np.testing.assert_allclose(p.erreur_MW, p.observe_MW - p.prevision_MW, atol=1e-8)
        for origine, bloc in p.loc[p[cle].isin(NOMS)].groupby("origine_locale"):
            cibles = pd.DatetimeIndex(sorted(bloc.cible_locale.unique()))
            attendues = prevoir_benchmarks(y, cibles, origine.normalize() + pd.Timedelta(hours=heure))
            assert attendues is not None
            for nom, valeurs in attendues.items():
                np.testing.assert_allclose(bloc.loc[bloc[cle].eq(nom)].sort_values("cible_locale").prevision_MW, valeurs)
        scores = pd.read_csv(RESULTATS / dossier / "comparaison.csv").set_index(cle)
        for nom, bloc in p.groupby(cle):
            np.testing.assert_allclose(scores.loc[nom, ["MAE_MW", "RMSE_MW", "biais_MW"]].to_numpy(dtype=float),
                                       [bloc.erreur_MW.abs().mean(), np.sqrt((bloc.erreur_MW**2).mean()), bloc.erreur_MW.mean()])
        controles[dossier + "_benchmarks"] = {"jours_communs": p.origine_locale.nunique(),
                                               "definitions_et_scores": "verifies depuis les observations"}
    empreinte = hashlib.sha256((PROJET / "data/merge/test.csv").read_bytes()).hexdigest()
    assert empreinte == (RESULTATS / "08_validation_2024/integrite_test_2025.txt").read_text().strip()
    controles["test_2025"] = "Donnees realignees, aucune evaluation ; empreinte stable pendant la validation."
    controles["versions"] = {nom: version(nom) for nom in ["numpy", "pandas", "matplotlib", "scipy", "scikit-learn", "statsmodels", "threadpoolctl"]}
    controles["python"] = platform.python_version()
    # Chaque resultat est non vide, avec un format CSV ou PNG lisible.
    inventaire = []
    hashes = {}
    for f in sorted(RESULTATS.rglob("*")):
        if not f.is_file() or f.name in ["CONTROLES.json", "INVENTAIRE.csv"]:
            continue
        assert f.stat().st_size > 0
        if f.suffix == ".csv":
            assert not pd.read_csv(f).empty, str(f)
        if f.suffix == ".png":
            with f.open("rb") as flux:
                entete = flux.read(24)
            assert entete[:8] == b"\x89PNG\r\n\x1a\n"
            assert min(struct.unpack(">II", entete[16:24])) > 0
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        hashes.setdefault(digest, []).append(str(f.relative_to(ANALYSE)))
        inventaire.append({"fichier": str(f.relative_to(ANALYSE)), "octets": f.stat().st_size, "sha256": digest})
    controles["doublons_exacts"] = [noms for noms in hashes.values() if len(noms) > 1]
    assert not controles["doublons_exacts"]
    pd.DataFrame(inventaire).to_csv(RESULTATS / "INVENTAIRE.csv", index=False)
    # Recopier les scores des CSV, sans conclusions ecrites a l'avance.
    texte = ["# Synthese des resultats", "",
             "Les tableaux ci-dessous ont des supports differents : comparer les modeles au sein de chaque experience.",
             "Le test 2025 n'est pas evalue. La meteo parfaite n'est pas disponible en conditions reelles.",
             "Voir [le guide](README.md) pour les methodes, figures et limites."]
    tableaux = {
        "Modeles du cours et benchmarks": "10_modeles_cours/scores.csv",
        "Regression meteo et calendrier": "06_meteo_calendrier/comparaison_2021_2023.csv",
        "Correction AR, meteo parfaite": "07_prevision_ar/comparaison.csv",
        "Validation des scenarios meteo": "08_validation_2024/comparaison.csv",
    }
    for titre, fichier in tableaux.items():
        tableau = pd.read_csv(RESULTATS / fichier)
        texte += ["", f"## {titre}", "", "```text", tableau.round(3).to_string(index=False), "```"]
    (ANALYSE / "SYNTHESE.md").write_text("\n".join(texte) + "\n", encoding="utf-8")
    for fichier in ANALYSE.rglob("*.md"):
        contenu = fichier.read_text(encoding="utf-8")
        for cible in re.findall(r"\]\(([^)]+)\)", contenu):
            if not cible.startswith(("http:", "https:", "#")):
                assert (fichier.parent / cible.split("#")[0]).exists(), f"Lien absent : {fichier} -> {cible}"
        if fichier.name != "NETTOYAGE.md":
            assert not any(t in contenu for t in ["results/description/", "donnees_combinees_2012_2024.csv", "Voir METHODE.md"]), str(fichier)
    controles["liens_documentation"] = "valides ; aucune reference obsolete hors journal de nettoyage"
    (RESULTATS / "CONTROLES.json").write_text(json.dumps(controles, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
