"""Diagnostics comparatifs des réglages ML sur la validation 2024.

Exécution : python src/analyser_optimisation_ml.py
Lit exclusivement les prévisions sauvegardées : aucun réentraînement et aucun accès à 2025.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
BASE = RACINE / "results" / "analyse_2024"
PREVISIONS_INITIALES = BASE / "ml" / "previsions_ml_2024.csv"
PREVISIONS_OPTIMISEES = BASE / "optimisation_hyperparametres_ml" / "previsions_2024.csv"
VALIDATION = RACINE / "data" / "merge" / "validation.csv"
SORTIE = BASE / "optimisation_hyperparametres_ml" / "diagnostics"
MODELES = ("Random Forest", "Gradient Boosting", "Ridge")
CLES = ["jour_cible", "horodatage", "occurrence_heure"]
MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre")
JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
GROUPES = {
    "saison": "saison",
    "mois": "mois",
    "heure": "heure",
    "jour_semaine": "jour_semaine",
    "type_jour": "type_jour",
    "ferie": "ferie",
    "vacances": "vacances",
    "temperature": "classe_temperature",
}


def lire_previsions(path: Path, noms: tuple[str, ...]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Prévisions manquantes : {path}")
    df = pd.read_csv(path)
    colonnes = set(CLES + ["modele", "reel_MW", "prediction_MW"])
    if colonnes - set(df):
        raise ValueError(f"Colonnes absentes dans {path.name} : {sorted(colonnes - set(df))}")
    df = df.loc[df.modele.isin(noms), list(colonnes)].copy()
    for c in ("horodatage", "jour_cible"):
        df[c] = pd.to_datetime(df[c], errors="raise")
    if df.empty or not df["jour_cible"].dt.year.eq(2024).all():
        raise ValueError(f"Prévisions absentes ou hors 2024 dans {path.name}")
    if not df["horodatage"].dt.normalize().eq(df["jour_cible"].dt.normalize()).all():
        raise ValueError("Incohérence entre horodatage et jour cible")
    for c in ("reel_MW", "prediction_MW", "occurrence_heure"):
        df[c] = pd.to_numeric(df[c], errors="raise")
    if not np.isfinite(df[["reel_MW", "prediction_MW"]].to_numpy()).all():
        raise ValueError(f"Valeurs réelles ou prédites non finies dans {path.name}")
    if df.duplicated(["modele", *CLES]).any():
        raise ValueError(f"Prévisions dupliquées dans {path.name}")
    return df


def comparer_previsions(initiales: pd.DataFrame, optimisees: pd.DataFrame) -> pd.DataFrame:
    blocs = []
    dates_reference = None
    for modele in MODELES:
        a = initiales.loc[initiales.modele.eq(modele), [*CLES, "reel_MW", "prediction_MW"]]
        b = optimisees.loc[optimisees.modele.eq(modele), [*CLES, "reel_MW", "prediction_MW"]]
        if a.empty or b.empty:
            raise ValueError(f"Le modèle {modele} manque dans une des deux prévisions")
        j = a.merge(b, on=CLES, how="outer", indicator=True, validate="one_to_one",
                    suffixes=("_initial", "_optimise"))
        if not j._merge.eq("both").all():
            raise ValueError(f"Dates/heures différentes pour {modele} : "
                             f"{j._merge.value_counts().to_dict()}")
        if not np.allclose(j.reel_MW_initial, j.reel_MW_optimise, atol=1e-5, rtol=0):
            raise ValueError(f"Les valeurs réelles sont différentes pour {modele}")
        jours = pd.DatetimeIndex(sorted(j.jour_cible.unique()))
        if dates_reference is None:
            dates_reference = jours
        elif not dates_reference.equals(jours):
            raise ValueError("Les modèles ne sont pas évalués sur les mêmes journées")
        if len(jours) != 338 or len(j) != 8112:
            raise ValueError(f"Échantillon inattendu pour {modele} : {len(jours)} jours, {len(j)} heures")
        if not j.groupby("jour_cible").size().eq(24).all():
            raise ValueError(f"Une journée ne contient pas 24 heures pour {modele}")
        j["modele"] = modele
        j["reel_MW"] = j.pop("reel_MW_initial")
        j = j.drop(columns=["reel_MW_optimise", "_merge"])
        j = j.rename(columns={"prediction_MW_initial": "initial_MW",
                              "prediction_MW_optimise": "optimise_MW"})
        blocs.append(j)
    return pd.concat(blocs, ignore_index=True).sort_values(["modele", *CLES]).reset_index(drop=True)


def to_bool(s: pd.Series, colonne: str) -> pd.Series:
    vals = s.astype("string").str.strip().str.lower()
    resultat = vals.map({"true": 1, "false": 0, "1": 1, "0": 0,
                         "1.0": 1, "0.0": 0})
    if resultat.isna().any():
        raise ValueError(f"Valeurs manquantes ou inconnues dans {colonne}")
    return resultat.astype(bool)


def ajouter_contextes(df: pd.DataFrame, chemin_validation: Path) -> pd.DataFrame:
    cols = ["horodatage", "jour_ferie", "weekend", "vacances_scolaires",
            "temperature_moyenne"]
    if not chemin_validation.exists():
        raise FileNotFoundError(f"Fichier de validation absent : {chemin_validation}")
    cal = pd.read_csv(chemin_validation, usecols=cols, parse_dates=["horodatage"])
    if not cal.horodatage.dt.year.eq(2024).all() or cal.horodatage.duplicated().any():
        raise ValueError("Horodatages de validation incohérents ou dupliqués")
    cal["jour_cible"] = cal.horodatage.dt.normalize()
    for col in ("jour_ferie", "weekend", "vacances_scolaires"):
        cal[col] = to_bool(cal[col], col)
        if not cal.groupby("jour_cible")[col].nunique().eq(1).all():
            raise ValueError(f"La variable {col} change au cours d'une journée")
    cal["temperature_moyenne"] = pd.to_numeric(cal["temperature_moyenne"], errors="coerce")
    metadonnees = cal.groupby("jour_cible", as_index=False).agg(
        jour_ferie=("jour_ferie", "first"),
        weekend=("weekend", "first"),
        vacances_scolaires=("vacances_scolaires", "first"),
        temperature_jour_C=("temperature_moyenne", "mean"),
    )
    result = df.merge(metadonnees, on="jour_cible", validate="many_to_one", how="left")
    if result[["jour_ferie", "weekend", "vacances_scolaires"]].isna().any().any():
        raise ValueError("Journées prévues absentes du calendrier de validation")
    m = result.jour_cible.dt.month
    result["saison"] = np.select([m.isin([12, 1, 2]), m.isin([3, 4, 5]),
                                   m.isin([6, 7, 8])],
                                  ["Hiver", "Printemps", "Été"], default="Automne")
    result["mois"] = m.map({i + 1: f"{i+1:02d} - {nom}" for i, nom in enumerate(MOIS)})
    result["heure"] = result.horodatage.dt.hour
    result["jour_semaine"] = result.jour_cible.dt.dayofweek.map(
        {i: f"{i+1} - {nom}" for i, nom in enumerate(JOURS)})
    result["type_jour"] = np.where(result.weekend, "Week-end", "Semaine")
    result["ferie"] = np.where(result.jour_ferie, "Férié", "Non férié")
    result["vacances"] = np.where(result.vacances_scolaires,
                                  "Vacances scolaires", "Hors vacances")
    result["classe_temperature"] = pd.cut(
        result.temperature_jour_C, bins=[-np.inf, 0, 5, 10, 15, 20, np.inf],
        labels=["< 0 °C", "0–5 °C", "5–10 °C", "10–15 °C", "15–20 °C", ">= 20 °C"],
        right=False).astype("string").fillna("Météo indisponible")
    for version, col in (("initial", "initial_MW"), ("optimise", "optimise_MW")):
        result[f"erreur_{version}"] = result.reel_MW - result[col]
    return result


def metriques(erreurs: pd.Series | np.ndarray) -> dict:
    e = np.asarray(erreurs, float)
    if not len(e):
        raise ValueError("Groupe sans observation")
    return {"MAE_MW": float(np.mean(np.abs(e))),
            "RMSE_MW": float(np.sqrt(np.mean(e ** 2))),
            "biais_MW": float(np.mean(e))}


def score_par_groupe(df: pd.DataFrame, colonne: str | None = None) -> pd.DataFrame:
    groupes = ["modele"] + ([colonne] if colonne else [])
    reponses = []
    for cles, g in df.groupby(groupes, dropna=False, sort=True):
        if not isinstance(cles, tuple):
            cles = (cles,)
        base = dict(zip(groupes, cles))
        ancien, nouveau = metriques(g.erreur_initial), metriques(g.erreur_optimise)
        jour = g.groupby("jour_cible")[["erreur_initial", "erreur_optimise"]].agg(
            lambda x: np.mean(np.asarray(x) ** 2))
        jours_gagnes = int((np.sqrt(jour.erreur_initial) - np.sqrt(jour.erreur_optimise) > 0.01).sum())
        base.update({
            "jours": int(g.jour_cible.nunique()), "heures": int(len(g)),
            "MAE_initial_MW": ancien["MAE_MW"], "MAE_optimise_MW": nouveau["MAE_MW"],
            "gain_MAE_MW": ancien["MAE_MW"] - nouveau["MAE_MW"],
            "RMSE_initial_MW": ancien["RMSE_MW"], "RMSE_optimise_MW": nouveau["RMSE_MW"],
            "gain_RMSE_MW": ancien["RMSE_MW"] - nouveau["RMSE_MW"],
            "gain_RMSE_pct": 100 * (ancien["RMSE_MW"] - nouveau["RMSE_MW"]) / ancien["RMSE_MW"],
            "biais_initial_MW": ancien["biais_MW"], "biais_optimise_MW": nouveau["biais_MW"],
            "jours_ameliores": jours_gagnes,
            "part_jours_ameliores_pct": 100 * jours_gagnes / len(jour),
        })
        reponses.append(base)
    return pd.DataFrame(reponses)


def scores_journaliers(df: pd.DataFrame) -> pd.DataFrame:
    res = []
    for (modele, jour), g in df.groupby(["modele", "jour_cible"], sort=True):
        if len(g) != 24:
            raise ValueError(f"Pas 24 heures le {jour} : {modele}")
        ligne = {"modele": modele, "jour": jour,
                 "saison": g.saison.iloc[0], "ferie": g.ferie.iloc[0],
                 "type_jour": g.type_jour.iloc[0], "vacances": g.vacances.iloc[0],
                 "temperature_jour_C": g.temperature_jour_C.iloc[0]}
        heures = g.horodatage.dt.hour.to_numpy()
        y = g.reel_MW.to_numpy()
        ligne["pointe_reelle_MW"] = float(y.max())
        ligne["heure_pointe_reelle"] = int(heures[np.argmax(y)])
        for version, pred in (("initial", g.initial_MW.to_numpy()),
                              ("optimise", g.optimise_MW.to_numpy())):
            e = y - pred
            ligne[f"RMSE_{version}_MW"] = float(np.sqrt(np.mean(e ** 2)))
            ligne[f"MAE_{version}_MW"] = float(np.mean(np.abs(e)))
            ligne[f"biais_{version}_MW"] = float(np.mean(e))
            # 24 créneaux de 1 h : MW x h = MWh.
            ligne[f"erreur_energie_{version}_MWh"] = float(np.sum(e))
            ligne[f"MAE_energie_{version}_MWh"] = abs(float(np.sum(e)))
            ligne[f"MAE_pointe_{version}_MW"] = float(abs(y.max() - pred.max()))
            ligne[f"erreur_heure_pointe_{version}_h"] = int(
                abs(heures[np.argmax(y)] - heures[np.argmax(pred)]))
        ligne["gain_RMSE_MW"] = ligne["RMSE_initial_MW"] - ligne["RMSE_optimise_MW"]
        res.append(ligne)
    return pd.DataFrame(res)


def bootstrap_hebdomadaire(df: pd.DataFrame, repetitions: int = 2000,
                             graine: int = 42) -> pd.DataFrame:
    """IC exploratoire sur le gain de RMSE, en rééchantillonnant des semaines."""
    lignes = []
    for i, modele in enumerate(MODELES):
        g = df.loc[df.modele.eq(modele)].copy()
        g["semaine"] = g.jour_cible.dt.to_period("W-SUN").astype(str)
        s = g.groupby("semaine", sort=True).agg(
            somme_sq_initial=("erreur_initial", lambda x: float(np.square(x).sum())),
            somme_sq_optimise=("erreur_optimise", lambda x: float(np.square(x).sum())),
            n=("erreur_initial", "size"))
        chiffres = s.to_numpy(float)
        rng = np.random.default_rng(graine + i)
        indices = rng.integers(0, len(s), size=(repetitions, len(s)))
        tirages = chiffres[indices].sum(axis=1)
        gain = (np.sqrt(tirages[:, 0] / tirages[:, 2]) -
                np.sqrt(tirages[:, 1] / tirages[:, 2]))
        lignes.append({"modele": modele, "semaines": len(s),
                       "IC95_gain_RMSE_bas_MW": float(np.quantile(gain, .025)),
                       "IC95_gain_RMSE_haut_MW": float(np.quantile(gain, .975)),
                       "prob_gain_positif_bootstrap_pct": 100 * float((gain > 0).mean())})
    return pd.DataFrame(lignes)


def scores_energie_pointe(jours: pd.DataFrame) -> pd.DataFrame:
    sorties = []
    for modele, g in jours.groupby("modele"):
        ligne = {"modele": modele, "jours": len(g)}
        for version in ("initial", "optimise"):
            for nom in ("MAE_energie", "MAE_pointe", "erreur_heure_pointe"):
                suffixe = "MWh" if nom == "MAE_energie" else ("MW" if nom == "MAE_pointe" else "h")
                ligne[f"{nom}_{version}_{suffixe}"] = float(g[f"{nom}_{version}_{suffixe}"].mean())
        sorties.append(ligne)
    return pd.DataFrame(sorties)


def tracer_barres(df: pd.DataFrame, colonne: str, titre: str, chemin: Path,
                  noms: tuple[str, ...] = MODELES) -> None:
    fig, axes = plt.subplots(1, len(noms), figsize=(5 * len(noms), 4), constrained_layout=True)
    if len(noms) == 1:
        axes = [axes]
    for ax, nom in zip(axes, noms):
        g = df[df.modele.eq(nom)].sort_values(colonne)
        x = np.arange(len(g))
        ax.bar(x - .2, g.RMSE_initial_MW, width=.4, label="Initial")
        ax.bar(x + .2, g.RMSE_optimise_MW, width=.4, label="Optimisé")
        ax.set_xticks(x, g[colonne].astype(str), rotation=45, ha="right")
        ax.set_title(nom)
        ax.set_ylabel("RMSE (MW)")
        ax.legend()
        ax.grid(axis="y", alpha=.2)
    fig.suptitle(titre)
    fig.savefig(chemin, dpi=150)
    plt.close(fig)


def tracer_heure(df: pd.DataFrame, chemin: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharex=True, constrained_layout=True)
    for ax, nom in zip(axes, MODELES):
        g = df[df.modele.eq(nom)].sort_values("heure")
        ax.plot(g.heure, g.RMSE_initial_MW, label="Initial")
        ax.plot(g.heure, g.RMSE_optimise_MW, label="Optimisé")
        ax.set_title(nom)
        ax.set_xlabel("Heure cible")
        ax.set_ylabel("RMSE (MW)")
        ax.set_xticks(range(0, 24, 3))
        ax.legend()
        ax.grid(alpha=.25)
    fig.suptitle("Erreurs horaires sur les mêmes journées de 2024")
    fig.savefig(chemin, dpi=150)
    plt.close(fig)


def tracer_carte_heure_saison(df: pd.DataFrame, chemin: Path) -> None:
    saisons = ["Hiver", "Printemps", "Été", "Automne"]
    tableau = df.pivot_table(index="saison", columns="heure", values="gain_RMSE_MW")
    tab = tableau.reindex(index=saisons, columns=range(24))
    fig, ax = plt.subplots(figsize=(11, 3.7), constrained_layout=True)
    valeurs = tab.to_numpy(dtype=float)
    limite = np.nanmax(np.abs(valeurs))
    im = ax.imshow(valeurs, aspect="auto", interpolation="nearest", cmap="RdBu",
                   vmin=-limite, vmax=limite)
    ax.set_yticks(np.arange(4), saisons)
    ax.set_xticks(np.arange(0, 24, 2), list(range(0, 24, 2)))
    ax.set_xlabel("Heure cible")
    ax.set_title("Gain de RMSE : initial - optimisé (MW) ; positif = amélioration")
    fig.colorbar(im, ax=ax, label="Gain de RMSE (MW)")
    fig.savefig(chemin, dpi=150)
    plt.close(fig)


def tableau_md(df: pd.DataFrame, colonnes: dict[str, str], n: int | None = None) -> str:
    if n:
        df = df.head(n)
    entetes = list(colonnes.values())
    lignes = ["| " + " | ".join(entetes) + " |", "| " + " | ".join(["---"] * len(entetes)) + " |"]
    for _, row in df.iterrows():
        valeurs = []
        for col in colonnes:
            v = row[col]
            if isinstance(v, (float, np.floating)):
                valeurs.append("—" if pd.isna(v) else f"{v:,.1f}".replace(",", " "))
            else:
                valeurs.append(str(v)[:10] if isinstance(v, pd.Timestamp) else str(v))
        lignes.append("| " + " | ".join(valeurs) + " |")
    return "\n".join(lignes)


def ecrire_analyse(sortie: Path, global_: pd.DataFrame, groupes: dict[str, pd.DataFrame],
                    quotidien: pd.DataFrame, energie: pd.DataFrame,
                    incertitude: pd.DataFrame) -> None:
    lignes = [
        "# Étude détaillée des modèles ML optimisés — validation 2024", "",
        "## Protocole et périmètre", "",
        "Les modèles de référence et les modèles optimisés sont comparés **heure par heure, "
        "sur les mêmes 338 journées (8 112 heures)** de 2024. Les hyperparamètres ont été choisis "
        "sur 2023, après entraînement sur 2012–2022, puis réentraînés sur 2012–2023. "
        "Cette recherche est complémentaire et exploratoire, car les premiers scores 2024 "
        "avaient déjà été consultés. Le jeu 2025 n'est ni lu ni modifié.", "",
        "La version *initiale* provient de `results/analyse_2024/ml/previsions_ml_2024.csv` ; "
        "la version *optimisée* de `optimisation_hyperparametres_ml/previsions_2024.csv`. "
        "L'égalité des observations réelles, des dates et des heures est contrôlée avant toute comparaison.", "",
        "**Convention :** gain = RMSE initiale − RMSE optimisée ; un gain positif traduit une amélioration. "
        "Biais = consommation réelle − consommation prédite : positif signifie sous-prédiction.", "",
        "## Résultats globaux", "",
        tableau_md(global_.sort_values("RMSE_optimise_MW"), {
            "modele": "Modèle", "RMSE_initial_MW": "RMSE initiale", "RMSE_optimise_MW": "RMSE optimisée",
            "gain_RMSE_pct": "Gain (%)", "MAE_optimise_MW": "MAE optimisée",
            "biais_optimise_MW": "Biais optimisé", "part_jours_ameliores_pct": "Jours améliorés (%)"}), "",
    ]
    for _, r in global_.iterrows():
        if abs(r.gain_RMSE_MW) < .01:
            description = "ne change pratiquement pas"
        elif r.gain_RMSE_MW > 0:
            description = "améliore"
        else:
            description = "dégrade"
        lignes.append(f"- **{r.modele}** {description} la RMSE globale : "
                      f"gain de {r.gain_RMSE_MW:+.1f} MW "
                      f"({r.gain_RMSE_pct:+.1f} %), avec {int(r.jours_ameliores)} journées "
                      f"améliorées sur {int(r.jours)}. Ce dernier indicateur évite de réduire "
                      "la comparaison aux seules grosses erreurs.")
    lignes += ["", "## Saisons", "",
               tableau_md(groupes["saison"].sort_values(["modele", "saison"]), {
                   "modele": "Modèle", "saison": "Saison", "jours": "Jours",
                   "RMSE_initial_MW": "Avant", "RMSE_optimise_MW": "Après",
                   "gain_RMSE_MW": "Gain MW", "gain_RMSE_pct": "Gain %"}), ""]
    for nom in MODELES:
        d = groupes["saison"].loc[groupes["saison"].modele.eq(nom)]
        meilleur = d.loc[d.gain_RMSE_MW.idxmax()]
        pire = d.loc[d.gain_RMSE_MW.idxmin()]
        lignes.append(f"- **{nom}** : le gain est le plus élevé en {meilleur.saison.lower()} "
                      f"({meilleur.gain_RMSE_MW:+.1f} MW) et le plus faible en "
                      f"{pire.saison.lower()} ({pire.gain_RMSE_MW:+.1f} MW). "
                      "Ces contrastes décrivent 2024 ; ils ne prouvent pas une cause saisonnière.")
    lignes += ["", "## Jours fériés, week-ends et vacances", ""]
    for groupe, titre in (("ferie", "Jours fériés"), ("type_jour", "Semaine et week-end"),
                          ("vacances", "Vacances scolaires")):
        tab = groupes[groupe]
        lignes += [f"### {titre}", "", tableau_md(tab.sort_values(["modele", GROUPES[groupe]]), {
            "modele": "Modèle", GROUPES[groupe]: "Catégorie", "jours": "Jours",
            "RMSE_initial_MW": "Avant", "RMSE_optimise_MW": "Après",
            "gain_RMSE_MW": "Gain MW", "part_jours_ameliores_pct": "Jours améliorés %"}), ""]
    feries = groupes["ferie"].query('ferie == "Férié"')
    if not feries.empty:
        n = int(feries.jours.min())
        lignes.append(f"**Prudence : {n} journée(s) fériée(s) seulement** sont évaluables dans "
                      "cet échantillon. Une erreur exceptionnelle peut faire varier fortement "
                      "la RMSE de ce groupe. Il ne faut pas généraliser à tous les jours fériés.")
    lignes += ["", "## Heures de la journée", "",
               "Le fichier `comparaison_par_heure.csv` détaille les 24 heures pour chaque modèle ; "
               "le graphique `rmse_par_heure.png` compare les deux versions.", ""]
    for nom in MODELES:
        tab = groupes["heure"].loc[groupes["heure"].modele.eq(nom)]
        meilleur = tab.loc[tab.gain_RMSE_MW.idxmax()]
        pire = tab.loc[tab.gain_RMSE_MW.idxmin()]
        n_gagnees = int((tab.gain_RMSE_MW > 0).sum())
        lignes.append(f"- **{nom}** : RMSE améliorée à {n_gagnees}/24 heures ; "
                      f"gain maximal à {int(meilleur.heure):02d} h "
                      f"({meilleur.gain_RMSE_MW:+.1f} MW), minimal à "
                      f"{int(pire.heure):02d} h ({pire.gain_RMSE_MW:+.1f} MW).")
    lignes += ["", "## Température et mois", "",
               "Les groupes de température utilisent la **température effectivement observée "
               "en 2024**, uniquement pour analyser les erreurs *après coup*. Ce n'est pas une "
               "météo prévisionnelle accessible à J 14 h. Les données manquantes restent "
               "identifiées et les moyennes sont calculées par journée.", "",
               tableau_md(groupes["temperature"].sort_values(["modele", "classe_temperature"]), {
                   "modele": "Modèle", "classe_temperature": "Température journalière",
                   "jours": "Jours", "RMSE_initial_MW": "Avant", "RMSE_optimise_MW": "Après",
                   "gain_RMSE_MW": "Gain MW"}), "",
               "Consulter aussi `comparaison_par_mois.csv`, `comparaison_par_jour_semaine.csv` "
               "et les cartes `gain_saison_heure_*.png`.", "",
               "## Énergie quotidienne et pointes", "",
               "Somme des 24 valeurs horaires : énergie en MWh ; les indicateurs de "
               "pointe comparent la valeur maximale et son heure, sans hypothèse de "
               "continuité entre 23 h et 0 h. Seules les 24 heures retenues par "
               "le protocole sont évaluées.", "",
               tableau_md(energie.sort_values("modele"), {
                   "modele": "Modèle", "MAE_energie_initial_MWh": "Énergie avant (MWh)",
                   "MAE_energie_optimise_MWh": "Énergie après (MWh)",
                   "MAE_pointe_optimise_MW": "Erreur de pointe après (MW)",
                   "erreur_heure_pointe_optimise_h": "Erreur heure pointe après (h)"}), "",
               "## Journées difficiles", ""]
    for nom in MODELES:
        d = quotidien.loc[quotidien.modele.eq(nom)]
        pires = d.nlargest(3, "RMSE_optimise_MW")
        plus_fortes_degradations = d.nsmallest(3, "gain_RMSE_MW")
        lignes += [f"### {nom}", "", "Trois plus fortes erreurs après optimisation :", "",
                   tableau_md(pires, {"jour": "Jour", "ferie": "Férié ?",
                       "RMSE_initial_MW": "Avant", "RMSE_optimise_MW": "Après",
                       "gain_RMSE_MW": "Gain MW"}), "",
                   "Trois journées où l'optimisation dégrade le plus la RMSE :", "",
                   tableau_md(plus_fortes_degradations, {"jour": "Jour", "saison": "Saison",
                       "RMSE_initial_MW": "Avant", "RMSE_optimise_MW": "Après",
                       "gain_RMSE_MW": "Gain MW"}), ""]
    lignes += ["Ces dates sont des **cas à examiner** : la métrique ne permet pas à elle "
               "seule d'attribuer l'erreur à un événement externe, à la météo ou au modèle.", "",
               "## Incertitude des gains", "",
               "Intervalle indicatif à 95 % obtenu en rééchantillonnant des blocs "
               "de semaines, pour conserver une part de la dépendance temporelle. "
               "Il ne s'agit ni d'un nouveau test hors échantillon ni d'une preuve "
               "de causalité ; une seule année 2024 est étudiée.", "",
               tableau_md(incertitude, {"modele": "Modèle", "semaines": "Blocs semaines",
                   "IC95_gain_RMSE_bas_MW": "IC bas (MW)",
                   "IC95_gain_RMSE_haut_MW": "IC haut (MW)"}), "",
               "## Limites et conclusion", "",
               "- Le choix numérique des réglages a été fait en 2023, mais l'expérience "
               "a été imaginée après examen de 2024 : elle reste exploratoire.",
               "- Les résultats utilisent les fichiers horaires **actuels** ; la "
               "convention d'agrégation des demi-heures RTE identifiée ensuite n'est "
               "pas corrigée dans cette expérience.",
               "- Les fichiers définitifs RTE ne reconstituent pas exactement ce qui "
               "était publié à J 14 h lors de chaque date historique.",
               "- Les températures observées du lendemain servent seulement à "
               "segmenter *a posteriori* les erreurs, jamais à générer les prévisions.",
               "- Des moyennes par saison, vacances et fériés ne suffisent pas pour "
               "affirmer la robustesse hors de 2024.", "",
               "Les tableaux détaillés et graphiques sont rangés dans ce dossier. "
               "La lecture des cas d'échec doit accompagner la comparaison des scores.", ""]
    (sortie / "analyse_detaillee.md").write_text("\n".join(lignes), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial", type=Path, default=PREVISIONS_INITIALES)
    parser.add_argument("--optimise", type=Path, default=PREVISIONS_OPTIMISEES)
    parser.add_argument("--validation", type=Path, default=VALIDATION)
    parser.add_argument("--sortie", type=Path, default=SORTIE)
    parser.add_argument("--bootstrap", type=int, default=2000,
                        help="Nombre de tirages de semaines (défaut 2000)")
    args = parser.parse_args()
    if args.bootstrap < 100:
        parser.error("--bootstrap doit être au moins 100")
    sortie = args.sortie.resolve()
    test = (RACINE / "results" / "test_2025").resolve()
    if sortie == test or test in sortie.parents:
        parser.error("Le dossier du test final 2025 est protégé")

    print("Comparaison des prévisions enregistrées, sans réentraîner les modèles...")
    initiales = lire_previsions(args.initial, MODELES)
    optimisees = lire_previsions(args.optimise, MODELES)
    previsions = comparer_previsions(initiales, optimisees)
    tableau = ajouter_contextes(previsions, args.validation)
    sortie.mkdir(parents=True, exist_ok=True)

    global_ = score_par_groupe(tableau)
    groupes = {nom: score_par_groupe(tableau, col) for nom, col in GROUPES.items()}
    # Les cartes par saison/heure utilisent les 4 x 24 groupes directement.
    tableau_sh = []
    for (modele, saison, heure), bloc in tableau.groupby(["modele", "saison", "heure"]):
        mesure = score_par_groupe(bloc).iloc[0].to_dict()
        mesure.update({"modele": modele, "saison": saison, "heure": heure})
        tableau_sh.append(mesure)
    par_saison_heure = pd.DataFrame(tableau_sh)
    quotidien = scores_journaliers(tableau)
    energie = scores_energie_pointe(quotidien)
    incertitude = bootstrap_hebdomadaire(tableau, args.bootstrap)

    global_.to_csv(sortie / "comparaison_globale.csv", index=False)
    for nom, tab in groupes.items():
        tab.to_csv(sortie / f"comparaison_par_{nom}.csv", index=False)
    par_saison_heure.to_csv(sortie / "comparaison_saison_heure.csv", index=False)
    quotidien.to_csv(sortie / "scores_quotidiens.csv", index=False)
    energie.to_csv(sortie / "energie_et_pointes.csv", index=False)
    incertitude.to_csv(sortie / "bootstrap_hebdomadaire.csv", index=False)
    tracer_barres(groupes["saison"], "saison", "Erreurs par saison", sortie / "rmse_par_saison.png")
    tracer_barres(groupes["ferie"], "ferie", "Erreurs selon les jours fériés", sortie / "rmse_jours_feries.png")
    tracer_barres(groupes["type_jour"], "type_jour", "Semaine et week-end", sortie / "rmse_type_jour.png")
    tracer_heure(groupes["heure"], sortie / "rmse_par_heure.png")
    for nom in MODELES:
        tracer_carte_heure_saison(par_saison_heure.query("modele == @nom"),
                                 sortie / f"gain_saison_heure_{nom.lower().replace(' ', '_')}.png")
    ecrire_analyse(sortie, global_, groupes, quotidien, energie, incertitude)
    print("\n=== GAINS DE RMSE EN 2024 (MW, positif = mieux) ===")
    print(global_[["modele", "jours", "RMSE_initial_MW", "RMSE_optimise_MW",
                   "gain_RMSE_MW", "gain_RMSE_pct", "part_jours_ameliores_pct"]]
          .round(2).to_string(index=False))
    print("\n=== JOURS FÉRIÉS (attention au petit effectif) ===")
    print(groupes["ferie"][["modele", "ferie", "jours", "RMSE_initial_MW",
                            "RMSE_optimise_MW", "gain_RMSE_MW"]].round(2).to_string(index=False))
    print(f"\nRapport et figures : {sortie}")
    print("Consulter : analyse_detaillee.md")
    print("Aucun entraînement ; aucun accès à 2025.")


if __name__ == "__main__":
    main()
