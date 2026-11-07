"""Lire la fusion canonique et auditer les conventions horaires."""

import json

import numpy as np
import pandas as pd

from chemins_analyse import RESULTATS as DOSSIER, PROJET, SOURCES
SORTIE = DOSSIER / "06_meteo_calendrier"
CALENDRIER = ["jour_ferie", "vacances_A", "vacances_B", "vacances_C"]


def verifier_reference_rte():
    # Rejouer hors ligne les huit controles a partir des reponses API archivees.
    reponses = json.loads((SOURCES / "verification_rte_api.json").read_text(encoding="utf-8"))
    bruts, lignes = {}, []
    for reponse in reponses:
        assert len(reponse["results"]) == 1
        r = reponse["results"][0]
        annee = r["date"][:4]
        if annee not in bruts:
            bruts[annee] = pd.read_csv(PROJET / f"data/conso/raw/eCO2mix_RTE_Annuel-Definitif_{annee}.xls",
                                      sep="\t", encoding="cp1252", index_col=False, low_memory=False)
        brut = bruts[annee]
        valeur = brut.loc[brut.Date.eq(r["date"]) & brut.Heures.eq(r["heure"]), "Consommation"].iloc[0]
        locale = pd.Timestamp(r["date"] + " " + r["heure"]).tz_localize("Europe/Paris")
        assert locale.tz_convert("UTC") == pd.Timestamp(r["date_heure"])
        assert valeur == r["consommation"]
        lignes.append({"date": r["date"], "heure": r["heure"], "date_heure_utc": r["date_heure"],
                       "consommation_api": r["consommation"], "consommation_brut": valeur, "identique": True})
    pd.DataFrame(lignes).to_csv(SORTIE / "verification_rte_api.csv", index=False)


def preparer():
    """Lire le train deja aligne par data/merge/merge.py, sans nouvelle fusion."""
    d = pd.read_csv(PROJET / "data/merge/train.csv", parse_dates=["horodatage"])
    d = d.set_index("horodatage").sort_index()
    d["date_utc"] = pd.to_datetime(d.date_utc, utc=True)
    assert d.index.is_unique and d.index.max() < pd.Timestamp("2024-01-01")
    assert d.index.equals(pd.date_range(d.index.min(), d.index.max(), freq="h"))
    d = d.rename(columns={"temperature_moyenne": "temperature",
                          "precipitation_moyenne": "pluie"})
    # Le filtre appartient a l'analyse ; le merge conserve toutes les lignes.
    d["utilisable"] = (~d.jour_changement_heure & d.date_utc.notna()
                       & d[["consommation_MW", "temperature", "pluie"]].notna().all(axis=1))
    d["jour_semaine"] = d.index.dayofweek
    d["heure"] = d.index.hour
    assert d[CALENDRIER].isin([0, 1]).all().all()
    return d


def verifier_donnees():
    SORTIE.mkdir(parents=True, exist_ok=True)
    verifier_reference_rte()
    d = preparer()
    np.testing.assert_allclose(d.consommation_MW, (d.consommation_00_MW + d.consommation_30_MW) / 2)
    utc = d.index.tz_localize("Europe/Paris", ambiguous="NaT", nonexistent="NaT").tz_convert("UTC")
    assert pd.DatetimeIndex(d.date_utc).equals(utc)
    feries = pd.read_csv(PROJET / "data/calendrier/raw/om-referentiel-jours-feries (1).csv", sep=";")
    assert np.array_equal(d.jour_ferie.to_numpy(), d.index.normalize().isin(pd.to_datetime(feries.date)))
    vac = pd.read_csv(PROJET / "data/calendrier/raw/data (3).csv", parse_dates=["date"]).set_index("date")
    assert vac.index.is_unique
    for zone in "ABC":
        source = vac[f"vacances_zone_{zone.lower()}"].reindex(d.index.normalize())
        assert source.notna().all()
        assert np.array_equal(source.astype(int).to_numpy(), d[f"vacances_{zone}"].to_numpy())
    m = pd.read_csv(PROJET / "data/temperature/processed/moyennes_reseau_horaires.csv")
    m["date_utc"] = pd.to_datetime(m.date_utc, utc=True)
    m = m.set_index("date_utc")
    valides = d.utilisable
    u = pd.DatetimeIndex(d.loc[valides, "date_utc"])
    t = m.temperature_c_moyenne.reindex(u).to_numpy()
    r = m.precipitation_1h_mm_moyenne.reindex(u).to_numpy()
    np.testing.assert_allclose(d.loc[valides, "temperature"], t)
    np.testing.assert_allclose(d.loc[valides, "pluie"], r)
    d.loc[~valides, ["date_utc", "jour_changement_heure", "temperature", "pluie"]].to_csv(
        SORTIE / "heures_exclues.csv", index_label="heure_locale")
    bilan = {"n_total": len(d), "n_utilisable": int(valides.sum()),
             "n_heures_changement": int(d.jour_changement_heure.sum()),
             "n_autres_heures_meteo_manquante": int((~d.jour_changement_heure & ~valides).sum()),
             "controles": "UTC, agregation conso, temperature, pluie, calendrier et huit references RTE conformes"}
    (SORTIE / "audit_alignement.json").write_text(json.dumps(bilan, indent=2), encoding="utf-8")


if __name__ == "__main__":
    verifier_donnees()
