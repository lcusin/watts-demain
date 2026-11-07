"""Preparation SYNOP complete : anciennes etapes 01 a 07, sorties en CSV.

Reconstruction retrospective : les heures intermediaires utilisent la mesure
suivante. Les ecarts-types decrivent la dispersion entre stations.
"""

import gzip
import shutil
from urllib.request import urlopen

import numpy as np
import pandas as pd

from chemins import (BRUT, METEO, PREPARE, DEBUT, FIN,
                     CLE, VARIABLES, sauver, noms_station)

# Parametres de telechargement et de selection.
URL = "https://object.files.data.gouv.fr/meteofrance/data/synchro_ftp/OBS/SYNOP/"
SEUIL = 95
EXPORT_DIAGNOSTICS = False  # True pour conserver les tableaux intermediaires.

def valide(fichier):
    if not fichier.exists():
        return False
    try:
        return "validity_time" in pd.read_csv(fichier, sep=";", nrows=0).columns
    except (OSError, ValueError, UnicodeError):
        return False

# 1. Recuperer les archives et les decompresser en CSV.
def telecharger():
    BRUT.mkdir(parents=True, exist_ok=True)
    journal = []
    for annee in range(2012, 2027):
        nom = f"synop_{annee}.csv"
        destination = BRUT / nom
        statut, erreur, source = "deja_present", "", str(destination)
        if not valide(destination):
            temporaire = BRUT / f"synop_{annee}_temporaire.csv"
            try:
                source = URL + nom + ".gz"
                with urlopen(source, timeout=1800) as reponse:
                    with gzip.GzipFile(fileobj=reponse) as entree, temporaire.open("wb") as sortie:
                        shutil.copyfileobj(entree, sortie)
                statut = "telecharge"
                if not valide(temporaire):
                    raise ValueError("En-tete CSV SYNOP invalide")
                temporaire.replace(destination)
            except Exception as e:
                statut, erreur = "erreur", str(e)
                temporaire.unlink(missing_ok=True)
        journal.append({"annee": annee, "fichier": nom, "statut": statut, "source": source, "erreur": erreur})
    sauver(pd.DataFrame(journal), PREPARE / "journal_telechargement.csv")


# 2. Importer les observations et inventorier les stations.
def importer():
    texte = ["geo_id_wmo", "geo_id_wigos", "name", "validity_time", "reference_time", "insert_time"]
    colonnes = ["geo_id_wmo", "geo_id_wigos", "name", "lat", "lon",
                "validity_time", "reference_time", "insert_time"] + VARIABLES
    types = {v: "string" if v in texte else "float64" for v in colonnes}
    archives = []
    for annee in range(2012, 2027):
        x = pd.read_csv(BRUT / f"synop_{annee}.csv", sep=";", usecols=colonnes,
                        dtype=types, na_values=["", "NA", "mq"], keep_default_na=False)
        x = x[colonnes]
        for v in ["geo_id_wmo", "geo_id_wigos", "name"]:
            x[v] = x[v].str.strip()
        x["date_utc"] = pd.to_datetime(x.validity_time, format="%Y-%m-%dT%H:%M:%SZ", utc=True)
        assert x.date_utc.notna().all() and x.geo_id_wmo.notna().all() and x.geo_id_wmo.ne("").all()
        x = x.loc[x.date_utc.ge(DEBUT) & x.date_utc.lt(FIN)].copy()
        x["fichier_source"] = f"synop_{annee}.csv.gz"  # Nom de l'archive source publiee.
        archives.append(x)
    meteo = pd.concat(archives, ignore_index=True).sort_values(CLE, kind="stable")
    assert not meteo.empty
    if EXPORT_DIAGNOSTICS:
        doublons = meteo.groupby(CLE).size().rename("N").reset_index()
        doublons = doublons.loc[doublons.N > 1]
        inventaire = []
        for identifiant, s in meteo.groupby("geo_id_wmo"):
            inventaire.append({
                "geo_id_wmo": identifiant, "noms": noms_station(s["name"]),
                "latitude": s.lat.iloc[0], "longitude": s.lon.iloc[0],
                "premiere_date": s.date_utc.min(), "derniere_date": s.date_utc.max(),
                "nb_lignes": len(s), "nb_dates_distinctes": s.date_utc.nunique(),
                "nb_temperature": s.t.count(), "nb_precipitation_1h": s.rr1.count(),
                "nb_precipitation_3h": s.rr3.count(),
            })
        sauver(meteo, PREPARE / "synop_variables_brutes.csv")
        sauver(pd.DataFrame(inventaire), PREPARE / "inventaire_stations.csv")
        sauver(doublons, PREPARE / "doublons_station_date.csv")
    return meteo


# 3. Supprimer les doublons exacts et reperer les contradictions.
def diagnostiquer_doublons(x):
    nb_importees = len(x)
    x = x.drop_duplicates(subset=x.columns.drop("fichier_source"))
    repetitions = x.loc[x.duplicated(CLE, keep=False)]
    diagnostic = repetitions.groupby(CLE)[VARIABLES].nunique().reset_index()
    diagnostic["conflit"] = diagnostic[VARIABLES].gt(1).any(axis=1)
    bilan = {"lignes_importees": nb_importees,
             "doublons_exacts_supprimes": nb_importees - len(x),
             "couples_station_date_repetes": len(diagnostic),
             "couples_station_date_contradictoires": int(diagnostic.conflit.sum())}
    if EXPORT_DIAGNOSTICS:
        sauver(x, PREPARE / "synop_sans_doublons_exacts.csv")
        sauver(diagnostic, PREPARE / "diagnostic_conflits.csv")
    return x, bilan


# 4. Garder la metropole et fusionner les versions des observations.
def nettoyer(x, bilan):
    x = x.loc[x.geo_id_wmo.str.fullmatch(r"07[0-9]{3}", na=False)].copy()
    assert not x.empty
    stations = x[["geo_id_wmo", "geo_id_wigos", "name", "lat", "lon"]].drop_duplicates()
    repete = x.duplicated(CLE, keep=False)
    versions = x.loc[repete].copy()
    versions["N"] = versions.groupby(CLE)["geo_id_wmo"].transform("size")
    meteo = x.loc[~repete, CLE + VARIABLES].copy()
    meteo["nb_versions"] = 1
    meteo["conflit_present"] = False
    corrections, conflits = [], []
    for (identifiant, date), s in versions.groupby(CLE):
        ligne = {"geo_id_wmo": identifiant, "date_utc": date, "nb_versions": len(s), "conflit_present": False}
        for v in VARIABLES:
            valeurs = sorted(s[v].dropna().unique())
            ligne[v] = valeurs[0] if len(valeurs) == 1 else np.nan
            if len(valeurs) > 1:
                ligne["conflit_present"] = True
                conflits.append({"geo_id_wmo": identifiant, "date_utc": date, "nb_valeurs": len(valeurs),
                                 "valeurs": " | ".join(format(z, ".15g") for z in valeurs), "variable": v})
        corrections.append(ligne)
    if corrections:
        meteo = pd.concat([meteo, pd.DataFrame(corrections)], ignore_index=True)
    meteo = meteo.sort_values(CLE)
    bilan.update(lignes_metropole_avant_fusion=len(x),
                 lignes_metropole_apres_fusion=len(meteo),
                 couples_metropole_contradictoires=int(meteo.conflit_present.sum()),
                 cellules_metropole_contradictoires=len(conflits))
    sauver(pd.DataFrame([bilan]), PREPARE / "bilan_nettoyage.csv")
    if EXPORT_DIAGNOSTICS:
        sauver(meteo, PREPARE / "synop_metropole_nettoye.csv")
        sauver(versions, PREPARE / "versions_repetees_metropole.csv")
    sauver(stations, PREPARE / "stations_metropole.csv")
    sauver(pd.DataFrame(conflits, columns=CLE + ["nb_valeurs", "valeurs", "variable"]), PREPARE / "conflits_metropole.csv")
    return meteo, stations


# 5. Calculer la couverture annuelle de chaque station.
def calculer_couverture(x, stations):
    assert not x.empty and x.date_utc.notna().all() and not x.duplicated(CLE).any()
    assert x.date_utc.eq(x.date_utc.dt.floor("3h")).all()
    grille = pd.date_range(DEBUT, x.date_utc.max(), freq="3h")
    attendus = pd.Series(grille.year).value_counts().sort_index()
    x = x.assign(annee=x.date_utc.dt.year)
    comptages = x.groupby(["geo_id_wmo", "annee"]).agg(
        nb_observations=("date_utc", "size"), nb_temperature=("t", "count"),
        nb_rr1=("rr1", "count"), nb_rr3=("rr3", "count"))
    index = pd.MultiIndex.from_product([sorted(x.geo_id_wmo.unique()), attendus.index], names=["geo_id_wmo", "annee"])
    couverture = comptages.reindex(index, fill_value=0).reset_index()
    couverture["nb_attendus"] = couverture.annee.map(attendus)
    for v in ["observations", "temperature", "rr1", "rr3"]:
        couverture["couverture_" + v] = 100 * couverture["nb_" + v] / couverture.nb_attendus
    noms = stations.groupby("geo_id_wmo")["name"].agg(noms_station).rename("nom")
    couverture = couverture.join(noms, on="geo_id_wmo").sort_values(["geo_id_wmo", "annee"])
    sauver(couverture, PREPARE / "couverture_stations_par_annee.csv")
    if EXPORT_DIAGNOSTICS:
        tableau = couverture.pivot(index=["geo_id_wmo", "nom"], columns="annee", values="couverture_temperature").reset_index()
        sauver(tableau, PREPARE / "couverture_temperature_tableau.csv")
    return couverture


# 6. Retenir les stations avec plus de 95 % de temperature ET de pluie.
def selectionner(x, couverture):
    bilan = couverture.groupby(["geo_id_wmo", "nom"])[["nb_temperature", "nb_rr3", "nb_attendus"]].sum().reset_index()
    bilan["couverture_temperature"] = 100 * bilan.nb_temperature / bilan.nb_attendus
    bilan["couverture_rr3"] = 100 * bilan.nb_rr3 / bilan.nb_attendus
    bilan["selectionnee"] = bilan.couverture_temperature.gt(SEUIL) & bilan.couverture_rr3.gt(SEUIL)
    bilan = bilan.sort_values("couverture_temperature", ascending=False, kind="stable")
    selection = bilan.loc[bilan.selectionnee]
    x = x.loc[x.geo_id_wmo.isin(selection.geo_id_wmo), CLE + ["t", "rr3"]]
    sauver(bilan, PREPARE / "bilan_selection_stations.csv")
    sauver(selection, PREPARE / "stations_selectionnees.csv")
    if EXPORT_DIAGNOSTICS:
        sauver(x, PREPARE / "synop_stations_selectionnees.csv")
    return x, selection


# 7. Reconstruire les heures, puis calculer les moyennes et ecarts-types.
def calculer_moyennes_horaires(x, stations):
    assert not x.empty and not stations.geo_id_wmo.duplicated().any()
    assert set(x.geo_id_wmo) == set(stations.geo_id_wmo)
    assert x.date_utc.notna().all() and not x.duplicated(CLE).any()
    assert x.date_utc.eq(x.date_utc.dt.floor("3h")).all()
    assert (x[["t", "rr3"]].isna() | np.isfinite(x[["t", "rr3"]])).all().all()
    fin = x.date_utc.max()
    horaires = []
    for identifiant, z in x.groupby("geo_id_wmo"):
        z = z.sort_values("date_utc").reset_index(drop=True)
        temperature = pd.DataFrame({"geo_id_wmo": identifiant, "date_utc": z.date_utc,
            "temperature_c": z.t - 273.15, "temperature_interpolee": False,
            "source_temperature_fin_utc": z.date_utc})
        suivant = z.shift(-1)
        paires = suivant.date_utc.sub(z.date_utc).eq(pd.Timedelta(hours=3)) & z.t.notna() & suivant.t.notna()
        morceaux = [temperature]
        for h in (1, 2):
            ajout = temperature.loc[paires].copy()
            ajout["date_utc"] = z.loc[paires, "date_utc"] + pd.Timedelta(hours=h)
            ajout["temperature_c"] += h / 3 * (suivant.loc[paires, "t"] - z.loc[paires, "t"])
            ajout["temperature_interpolee"] = True
            ajout["source_temperature_fin_utc"] = suivant.loc[paires, "date_utc"]
            morceaux.append(ajout)
        temperature = pd.concat(morceaux, ignore_index=True)
        trace = z.rr3.eq(-0.1)
        cumul = z.rr3.mask(trace, 0)
        assert cumul.dropna().ge(0).all()
        # Cumul observe a 12 h : intervalles 9-10, 10-11 et 11-12 h.
        # La date horaire indique le debut de chaque intervalle.
        pluie = pd.concat([pd.DataFrame({"geo_id_wmo": identifiant,
            "date_utc": z.date_utc - pd.Timedelta(hours=h), "precipitation_1h_mm": cumul / 3,
            "trace_pluie": trace, "source_pluie_fin_utc": z.date_utc}) for h in (1, 2, 3)], ignore_index=True)
        station = temperature.merge(pluie, on=CLE, how="outer", validate="one_to_one")
        horaires.append(station.loc[station.date_utc.between(DEBUT, fin)])
    horaire = pd.concat(horaires, ignore_index=True).sort_values(CLE)
    if EXPORT_DIAGNOSTICS:
        sauver(horaire, PREPARE / "synop_stations_horaires.csv")
    resultats = pd.DataFrame(index=pd.date_range(DEBUT, fin, freq="h", name="date_utc"))
    for v in ["temperature_c", "precipitation_1h_mm"]:
        groupes = horaire.groupby("date_utc")[v]
        resultats[v + "_moyenne"] = groupes.mean()
        resultats[v + "_ecart_type"] = groupes.std(ddof=1)  # Ecart-type entre stations, avec correction n - 1.
    sauver(resultats.reset_index(), PREPARE / "moyennes_reseau_horaires.csv")

# Executer les sept etapes dans l'ordre.
if __name__ == "__main__":
    telecharger()
    x = importer()
    x, bilan = diagnostiquer_doublons(x)
    x, stations = nettoyer(x, bilan)
    couverture = calculer_couverture(x, stations)
    x, selection = selectionner(x, couverture)
    calculer_moyennes_horaires(x, selection)
