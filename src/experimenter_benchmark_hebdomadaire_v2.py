"""Étude contrôlée des corrections du profil hebdomadaire adaptatif.

Les variantes évaluent le filtrage des jours fériés, les corrections de niveau
additive/proportionnelle/hybride et les analogues de fêtes à date fixe.
Une grille prédéfinie est évaluée sur 2023 (partie de l'apprentissage), puis
le réglage retenu est évalué sans ajustement supplémentaire sur 2024.
Les autres variantes sur 2024 servent d'ablation exploratoire ; elles ne
constituent pas des validations indépendantes supplémentaires.

Une journée est prévue à J 14 h uniquement à partir de mesures antérieures
(et du calendrier connu d'avance). Les données du lendemain servent de cible,
et la météo du lendemain aux diagnostics a posteriori uniquement.
Le test 2025 n'est ni lu ni modifié.

Usage (à la racine du dépôt) :
    python src/benchmark_hebdomadaire_adaptatif.py
    python src/experimenter_benchmark_hebdomadaire_v2.py
"""

from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from benchmark_hebdomadaire_adaptatif import charger_profils, charger_jours_validation

RACINE = Path(__file__).resolve().parent.parent
DATA = RACINE / "data" / "merge"
REF = RACINE / "results" / "analyse_2024"
SORTIE = REF / "benchmark_hebdomadaire_adaptatif_v2"
V1_SCORES = REF / "benchmark_hebdomadaire_adaptatif" / "comparaison_2024.csv"
V1_PRED = REF / "benchmark_hebdomadaire_adaptatif" / "previsions_horaires_2024.csv"
PREVISIONS_COMMUNES = REF / "previsions_communes.csv"

N_SEMAINES = 8
DECROISSANCE = 0.7
MIN_SEMAINES = 4
HEURES_MATIN = list(range(9))


@dataclass(frozen=True)
class Reglage:
    calendrier: bool
    mode: str                  # additif, proportionnel ou hybride
    intensite: float
    analogues_feries: bool = False


# Les premiers réglages sont fixés avant l'évaluation 2024.
VARIANTES = {
    "V1 - Adaptative": Reglage(False, "additif", 1.0),
    "V2 - Calendrier": Reglage(True, "additif", 1.0),
    "V2 - Proportionnelle": Reglage(False, "proportionnel", 1.0),
    "V2 - Combinee": Reglage(True, "proportionnel", 1.0),
    "V2 - Feries annuels": Reglage(False, "additif", 1.0, True),
    "V2 - Filtre et feries": Reglage(True, "additif", 1.0, True),
}


@dataclass
class JourPret:
    jour: pd.Timestamp
    reel: np.ndarray
    matin_reel: np.ndarray
    ferie_cible: bool
    ferie_origine: bool
    profils: dict[bool, np.ndarray]
    matins: dict[bool, np.ndarray]
    n_semaines: dict[bool, int]
    facteur_ferie: float


def empreinte(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloc)
    return h.hexdigest()


def charger_calendrier() -> pd.DataFrame:
    """Vérifie les indicateurs journaliers sur train et validation seulement."""
    colonnes = ["horodatage", "jour_ferie", "weekend", "vacances_scolaires", "temperature_moyenne"]
    pieces = []
    for nom in ("train.csv", "validation.csv"):
        chemin = DATA / nom
        if not chemin.is_file():
            raise FileNotFoundError(chemin)
        pieces.append(pd.read_csv(chemin, usecols=colonnes, parse_dates=["horodatage"]))
    df = pd.concat(pieces, ignore_index=True)
    df["jour"] = df["horodatage"].dt.normalize()
    for col in ("jour_ferie", "weekend", "vacances_scolaires"):
        if df.groupby("jour")[col].nunique(dropna=False).gt(1).any():
            raise ValueError(f"Indicateur {col} non constant sur une journée.")
        if not df[col].isin([0, 1]).all():
            raise ValueError(f"Indicateur {col} non binaire.")
    quotidien = df.groupby("jour", sort=True).agg(
        jour_ferie=("jour_ferie", "first"),
        weekend=("weekend", "first"),
        vacances_scolaires=("vacances_scolaires", "first"),
        temperature_moyenne=("temperature_moyenne", "mean"),
    )
    return quotidien


FETES_FIXES = {(1, 1), (5, 1), (5, 8), (7, 14), (8, 15), (11, 1), (11, 11), (12, 25)}


def facteur_fete_annuelle(jour: pd.Timestamp, conso: pd.DataFrame,
                           calendrier: pd.DataFrame) -> float:
    """Ratio historique de charge d'une fête fixe versus semaines comparables.

    Seules les années strictement antérieures sont interrogées. Les fêtes
    mobiles ne sont pas traitées par cette correction spécifique.
    """
    if (jour.month, jour.day) not in FETES_FIXES or not bool(calendrier.loc[jour, "jour_ferie"]):
        return 1.0
    rapports, poids = [], []
    for k in range(1, 9):
        annee = jour.year - k
        if annee < 2013:
            continue
        historique = jour.replace(year=annee)
        if historique not in conso.index or not bool(calendrier.loc[historique, "jour_ferie"]):
            continue
        valeurs = conso.loc[historique].to_numpy(dtype=float)
        if not np.isfinite(valeurs).all():
            continue
        references = []
        for semaine in range(1, 5):
            date_reference = historique - pd.Timedelta(days=7 * semaine)
            if date_reference not in conso.index or bool(calendrier.loc[date_reference, "jour_ferie"]):
                continue
            v = conso.loc[date_reference].to_numpy(dtype=float)
            if np.isfinite(v).all():
                references.append(float(v.mean()))
        if len(references) < 2:
            continue
        rapports.append(float(valeurs.mean() / np.mean(references)))
        poids.append(0.75 ** (k - 1))
    if len(rapports) < 2:
        return 1.0
    return float(np.clip(np.average(rapports, weights=poids), 0.70, 1.10))


def preparer_jour(jour: pd.Timestamp, conso: pd.DataFrame,
                   calendrier: pd.DataFrame) -> JourPret | None:
    origine = jour - pd.Timedelta(days=1)
    if origine not in conso.index or jour not in conso.index:
        return None
    reel = conso.loc[jour].to_numpy(dtype=float)
    matin = conso.loc[origine, HEURES_MATIN].to_numpy(dtype=float)
    if not (np.isfinite(reel).all() and np.isfinite(matin).all()):
        return None

    ferie_cible = bool(calendrier.loc[jour, "jour_ferie"])
    ferie_origine = bool(calendrier.loc[origine, "jour_ferie"])
    couples: list[tuple[int, np.ndarray, np.ndarray, bool]] = []
    for semaine in range(1, N_SEMAINES + 1):
        date_cible = jour - pd.Timedelta(days=7 * semaine)
        date_origine = origine - pd.Timedelta(days=7 * semaine)
        if date_cible not in conso.index or date_origine not in conso.index:
            continue
        y = conso.loc[date_cible].to_numpy(dtype=float)
        x = conso.loc[date_origine, HEURES_MATIN].to_numpy(dtype=float)
        if not (np.isfinite(y).all() and np.isfinite(x).all()):
            continue
        if not (date_cible < origine and date_origine < origine):
            raise AssertionError("Une observation future est entrée dans les historiques.")
        couples.append((semaine, y, x, bool(calendrier.loc[date_cible, "jour_ferie"])))
    if len(couples) < MIN_SEMAINES:
        return None

    profils = {}
    matins = {}
    nombres = {}
    for filtre in (False, True):
        conserves = couples
        if filtre and not ferie_cible:
            # Écarter les jours fériés historiques pour une cible non fériée.
            candidats = [item for item in couples if not item[3]]
            if len(candidats) >= MIN_SEMAINES:
                conserves = candidats
        poids = np.array([DECROISSANCE ** (k - 1) for k, _, _, _ in conserves])
        poids /= poids.sum()
        profils[filtre] = np.average(
            np.stack([x for _, x, _, _ in conserves]), axis=0, weights=poids
        )
        matins[filtre] = np.average(
            np.stack([x for _, _, x, _ in conserves]), axis=0, weights=poids
        )
        nombres[filtre] = len(conserves)

    return JourPret(jour, reel, matin, ferie_cible, ferie_origine,
                    profils, matins, nombres,
                    facteur_fete_annuelle(jour, conso, calendrier))


def prevoir(jour: JourPret, reglage: Reglage) -> np.ndarray:
    """Les corrections utilisent uniquement le matin de J et les semaines passées."""
    p = jour.profils[reglage.calendrier]
    m = jour.matins[reglage.calendrier]
    delta = float(np.mean(jour.matin_reel - m))
    ratio = float(np.mean(jour.matin_reel) / np.mean(m))
    # Borner le facteur multiplicatif pour ne pas amplifier un matin atypique.
    ratio = float(np.clip(ratio, 0.75, 1.25))

    if reglage.calendrier and jour.ferie_origine and not jour.ferie_cible:
        # Le matin férié de J n'est pas une référence pour un lendemain ordinaire.
        delta, ratio = 0.0, 1.0

    correction_additive = p + reglage.intensite * delta
    correction_proportionnelle = p * (1 + reglage.intensite * (ratio - 1))
    if reglage.mode == "additif":
        prediction = correction_additive
    elif reglage.mode == "proportionnel":
        prediction = correction_proportionnelle
    elif reglage.mode == "hybride":
        prediction = (correction_additive + correction_proportionnelle) / 2
    else:
        raise ValueError(f"Mode inconnu : {reglage.mode}")

    if reglage.analogues_feries and jour.ferie_cible:
        # Intensité fixée à 0,5 : réduction de moitié de l'effet historique.
        prediction = prediction * (1 + 0.5 * (jour.facteur_ferie - 1))
    return prediction


def metriques(e: np.ndarray) -> dict:
    return {
        "MAE_MW": float(np.mean(np.abs(e))),
        "RMSE_MW": float(np.sqrt(np.mean(e ** 2))),
        "biais_MW": float(np.mean(e)),
    }


def config_2023(jours: list[JourPret]) -> tuple[Reglage, pd.DataFrame]:
    """Choisit un réglage sans consulter les résultats de 2024."""
    configurations = [
        Reglage(cal, mode, intensite, analogues)
        for cal in (False, True)
        for mode in ("additif", "proportionnel", "hybride")
        for intensite in (0.5, 0.75, 1.0)
        for analogues in (False, True)
    ]
    lignes = []
    for cfg in configurations:
        erreurs = np.concatenate([d.reel - prevoir(d, cfg) for d in jours])
        lignes.append({"filtre_feries": cfg.calendrier,
                       "correction": cfg.mode,
                       "intensite": cfg.intensite,
                       "analogues_feries": cfg.analogues_feries,
                       "jours": len(jours), **metriques(erreurs)})
    tableau = pd.DataFrame(lignes).sort_values(["RMSE_MW", "MAE_MW"], kind="stable")
    meilleur = tableau.iloc[0]
    return Reglage(bool(meilleur.filtre_feries), str(meilleur.correction),
                   float(meilleur.intensite), bool(meilleur.analogues_feries)), tableau


def evaluer(jours: list[JourPret], variantes: dict[str, Reglage]) -> pd.DataFrame:
    lignes = []
    for nom, cfg in variantes.items():
        for jour in jours:
            predit = prevoir(jour, cfg)
            for heure, (reel, estimation) in enumerate(zip(jour.reel, predit)):
                lignes.append({
                    "horodatage": jour.jour + pd.Timedelta(hours=heure),
                    "jour": jour.jour,
                    "heure": heure,
                    "modele": nom,
                    "reel_MW": float(reel),
                    "prediction_MW": float(estimation),
                    "semaines_utilisees": jour.n_semaines[cfg.calendrier],
                })
    return pd.DataFrame(lignes)


def comparer_autres_modeles(previsions: pd.DataFrame) -> pd.DataFrame:
    """Lecture facultative des autres prévisions, sur exactement les mêmes heures."""
    if not PREVISIONS_COMMUNES.is_file():
        return previsions
    cols = ["horodatage", "modele", "reel_MW", "prediction_MW"]
    autres = pd.read_csv(PREVISIONS_COMMUNES, usecols=cols, parse_dates=["horodatage"])
    autres = autres[autres["modele"].isin(["Random Forest", "Regression lineaire", "Ridge", "semaine_precedente"])].copy()
    nouveaux = previsions[previsions["modele"].eq("V1 - Adaptative")]
    reference = nouveaux.set_index("horodatage")["reel_MW"].sort_index()
    if autres.empty:
        return previsions
    for nom, groupe in autres.groupby("modele"):
        ref = groupe.set_index("horodatage")["reel_MW"].sort_index()
        if not ref.index.equals(reference.index) or not np.allclose(
                ref.to_numpy(), reference.to_numpy(), rtol=0, atol=1e-5):
            raise ValueError(f"Horodatages/cibles incompatibles pour {nom}.")
    autres["jour"] = autres["horodatage"].dt.normalize()
    autres["heure"] = autres["horodatage"].dt.hour
    return pd.concat([previsions, autres], ignore_index=True)


def preparer_diagnostics(df: pd.DataFrame, calendrier: pd.DataFrame) -> pd.DataFrame:
    dates = calendrier.reset_index().rename(columns={"index": "jour"})
    df = df.merge(dates, on="jour", how="left", validate="many_to_one", indicator=True)
    if df["_merge"].ne("both").any():
        raise ValueError("Contexte calendaire absent pour certains jours.")
    df.drop(columns="_merge", inplace=True)
    df["saison"] = df["horodatage"].dt.month.map({
        12: "Hiver", 1: "Hiver", 2: "Hiver", 3: "Printemps", 4: "Printemps", 5: "Printemps",
        6: "Été", 7: "Été", 8: "Été", 9: "Automne", 10: "Automne", 11: "Automne"
    })
    df["type_jour"] = np.where(df["weekend"].eq(1), "Week-end", "Semaine")
    df["ferie"] = np.where(df["jour_ferie"].eq(1), "Férié", "Non férié")
    df["vacances"] = np.where(df["vacances_scolaires"].eq(1), "Vacances", "Hors vacances")
    df["classe_temperature"] = pd.cut(
        df["temperature_moyenne"], [-np.inf, 5, 15, np.inf], right=False,
        labels=["Moins de 5 °C", "5 à moins de 15 °C", "15 °C et plus"]
    ).astype(object).fillna("Météo manquante")
    return df


def groupes(df: pd.DataFrame, variable: str | None = None) -> pd.DataFrame:
    colonnes = ["modele"] + ([variable] if variable else [])
    lignes = []
    for cle, groupe in df.groupby(colonnes, dropna=False, sort=True):
        cle = cle if isinstance(cle, tuple) else (cle,)
        erreurs = groupe["reel_MW"].to_numpy() - groupe["prediction_MW"].to_numpy()
        lignes.append({**dict(zip(colonnes, cle)), "jours": int(groupe["jour"].nunique()),
                       "heures": len(groupe), **metriques(erreurs)})
    return pd.DataFrame(lignes)


def analyse_journaliere(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    lignes = []
    for (modele, jour), g in df.groupby(["modele", "jour"], sort=True):
        g = g.sort_values("heure")
        if len(g) != 24 or not np.array_equal(g["heure"].to_numpy(), np.arange(24)):
            raise ValueError(f"24 heures attendues pour {modele}, {jour}.")
        vrai = g["reel_MW"].to_numpy()
        pred = g["prediction_MW"].to_numpy()
        e = vrai - pred
        lignes.append({"modele": modele, "jour": jour, **metriques(e),
                       "erreur_energie_MWh": float(e.sum()),
                       "erreur_pointe_MW": float(vrai.max() - pred.max()),
                       "erreur_heure_pointe_h": int(abs(np.argmax(vrai) - np.argmax(pred)))})
    quotidien = pd.DataFrame(lignes)
    lignes = []
    for nom, g in quotidien.groupby("modele"):
        lignes.append({"modele": nom, "jours": len(g),
                       "MAE_energie_MWh": float(g.erreur_energie_MWh.abs().mean()),
                       "MAE_pointe_MW": float(g.erreur_pointe_MW.abs().mean()),
                       "MAE_heure_pointe_h": float(g.erreur_heure_pointe_h.mean())})
    return quotidien, pd.DataFrame(lignes)


def tracer(saisons: pd.DataFrame, heures: pd.DataFrame, sortie: Path) -> None:
    choix = ["V1 - Adaptative", "V2 - Calendrier", "V2 - Proportionnelle", "V2 - Combinee", "V2 - Feries annuels", "V2 - Filtre et feries",
            "V2 - Choix 2023", "Random Forest"]
    choix = [n for n in choix if n in saisons["modele"].unique()]
    tab = saisons.pivot(index="saison", columns="modele", values="RMSE_MW")
    tab = tab.reindex(index=["Hiver", "Printemps", "Été", "Automne"], columns=choix)
    fig, ax = plt.subplots(figsize=(11, 5))
    tab.plot.bar(ax=ax, rot=0)
    ax.set(xlabel="", ylabel="RMSE (MW)", title="Comparaison des variantes par saison — 2024")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(sortie / "comparaison_saisons.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5))
    for nom in choix:
        g = heures[heures["modele"].eq(nom)].sort_values("heure")
        ax.plot(g["heure"], g["RMSE_MW"], label=nom)
    ax.set(xlabel="Heure française du lendemain", ylabel="RMSE (MW)",
           title="Comparaison horaire des variantes — 2024", xticks=range(0, 24, 2))
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(sortie / "comparaison_heures.png", dpi=150)
    plt.close(fig)


def tracer_calendrier(analyses: dict[str, pd.DataFrame], sortie: Path) -> None:
    """Montre les différences de comportement selon les catégories calendaires."""
    variables = [("type_jour", "Semaine / week-end"),
                 ("ferie", "Jours fériés"), ("vacances", "Vacances scolaires")]
    noms = ["V1 - Adaptative", "V2 - Feries annuels", "V2 - Choix 2023", "Random Forest"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    for ax, (variable, titre) in zip(axes, variables):
        tableau = analyses[variable].pivot(index=variable, columns="modele", values="RMSE_MW")
        tableau.reindex(columns=noms).plot.bar(ax=ax, rot=0, legend=False)
        ax.set(xlabel="", ylabel="RMSE (MW)", title=titre)
        ax.tick_params(axis="x", labelsize=8)
        ax.grid(axis="y", alpha=0.25)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8)
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    fig.savefig(sortie / "comparaison_calendrier.png", dpi=150)
    plt.close(fig)


def tracer_pires_jours(df: pd.DataFrame, quotidien: pd.DataFrame, sortie: Path) -> None:
    """Compare les profils horaires pour les trois principales erreurs de la V2 choisie."""
    pires = quotidien[quotidien.modele.eq("V2 - Choix 2023")].nlargest(3, "RMSE_MW")
    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    for ax, jour in zip(axes, pires["jour"]):
        g = df[df.jour.eq(jour)]
        observation = g[g.modele.eq("V1 - Adaptative")].sort_values("heure")
        ax.plot(observation.heure, observation.reel_MW, label="Observé", linewidth=2.2)
        for nom in ("V1 - Adaptative", "V2 - Feries annuels", "V2 - Choix 2023", "Random Forest"):
            bloc = g[g.modele.eq(nom)].sort_values("heure")
            if not bloc.empty:
                ax.plot(bloc.heure, bloc.prediction_MW, label=nom, linewidth=1.5)
        ax.set(title=f"{jour.date()} — trois journées difficiles de la variante sélectionnée",
               ylabel="Puissance (MW)")
        ax.grid(alpha=0.25)
    axes[-1].set(xlabel="Heure du lendemain", xticks=range(0, 24, 2))
    axes[0].legend(ncol=3, fontsize=8)
    fig.tight_layout()
    fig.savefig(sortie / "trois_jours_difficiles.png", dpi=150)
    plt.close(fig)


def rapport(
    scores: pd.DataFrame,
    choix: Reglage,
    cal2023: pd.DataFrame,
    analyses: dict[str, pd.DataFrame],
    quotidiens: pd.DataFrame,
    pointes: pd.DataFrame,
) -> str:
    """Rapport calculé sur les scores de l'exécution (aucun résultat figé)."""
    q = scores.set_index("modele")
    v1 = q.loc["V1 - Adaptative"]
    retenue = q.loc["V2 - Choix 2023"]
    fete = q.loc["V2 - Feries annuels"]
    delta = retenue.RMSE_MW - v1.RMSE_MW
    effet = "diminue" if delta < -1e-8 else "augmente" if delta > 1e-8 else "ne modifie pas"

    texte = [
        "# Étude de corrections du benchmark hebdomadaire — validation 2024", "",
        "*Rapport recalculé automatiquement à partir des prévisions et de leurs diagnostics.*", "",
        "## 1. Définition de l'expérience", "",
        "- Origine : jour J à 14 h ; cible : les 24 heures de J+1.",
        f"- Profil hebdomadaire de {N_SEMAINES} semaines, poids décroissants 0,7^(k−1), normalisés après exclusion des historiques incomplets.",
        "- V1 : correction additive basée sur la moyenne de l'écart des consommations du matin de J (00–08 h) par rapport aux matins historiques.",
        "- Calendrier : filtrage des fêtes historiques pour une cible non fériée ; neutralisation de l'ajustement du matin lorsque J est férié et J+1 ordinaire.",
        "- Proportionnelle : facteur issu du rapport des consommations matinales, borné dans [0,75 ; 1,25] avant correction ; hybride : moyenne des versions additive et proportionnelle.",
        "- Analogues annuels : sur les seules fêtes légales à date fixe, ratio entre la charge d'une fête historique et celle de semaines précédentes non fériées. Le ratio est borné dans [0,70 ; 1,10], puis appliqué avec une intensité de 0,5. Fêtes mobiles inchangées.",
        f"- Sélection du réglage sur {int(cal2023.iloc[0].jours)} journées de 2023, dans l'ensemble d'apprentissage, par RMSE minimale parmi {len(cal2023)} configurations ; évaluation séparée sur {int(v1.jours)} journées de 2024.",
        "- Les seules observations disponibles avant l'origine entrent dans les prévisions ; les températures du lendemain ne servent qu'à la description rétrospective.",
        "- Le test 2025 est réservé à l'étude principale et n'est pas consulté.", "",
        "## 2. Réglage retenu sur l'année interne 2023", "",
        f"- Filtrage des fêtes historiques : {'oui' if choix.calendrier else 'non'} ; mode : **{choix.mode}** ; intensité : **{choix.intensite:g}** ; analogues de fêtes annuelles : {'oui' if choix.analogues_feries else 'non'}.",
        f"- RMSE interne 2023 : **{cal2023.iloc[0].RMSE_MW:,.2f} MW**.",
        "- 2023 fait partie de l'apprentissage initial 2012–2023 ; il sert ici à calibrer, pas à tester l'algorithme en finale.", "",
        "## 3. Résultats de validation 2024", "",
        "| Méthode | MAE (MW) | RMSE (MW) | Biais (MW) |",
        "|---|---:|---:|---:|",
    ]
    for nom, r in scores.sort_values("RMSE_MW").set_index("modele").iterrows():
        texte.append(f"| {nom} | {r.MAE_MW:,.2f} | {r.RMSE_MW:,.2f} | {r.biais_MW:+,.2f} |")
    texte += [
        "",
        f"- Le réglage retenu sur 2023 **{effet}** la RMSE 2024 de **{abs(delta):,.2f} MW** par rapport à la V1.",
        f"- La variante 'fêtes annuelles' obtient une RMSE de {fete.RMSE_MW:,.2f} MW (V1 : {v1.RMSE_MW:,.2f} MW). Son score 2024 ne doit pas être utilisé rétrospectivement pour sélectionner les paramètres.",
        f"- Le Random Forest obtient {q.loc['Random Forest'].RMSE_MW:,.2f} MW ; il reste devant la configuration choisie sur 2023.", "",
        "## 4. D'où viennent les gains et les échecs ?", "",
    ]

    def ligne(table: pd.DataFrame, modele: str, variable: str, valeur: str) -> pd.Series:
        return table.loc[(table["modele"] == modele) & (table[variable] == valeur)].iloc[0]

    for variable, label in (("saison", "Saisons"), ("type_jour", "Semaine et week-end"),
                            ("ferie", "Jours fériés"), ("vacances", "Vacances scolaires")):
        tab = analyses[variable]
        selection = tab[tab["modele"].eq("V2 - Choix 2023")]
        tableau = [f"{r[variable]} : RMSE {r.RMSE_MW:,.0f} MW (n={int(r.jours)} jours)"
                   for _, r in selection.iterrows()]
        texte.append(f"- **{label} (configuration retenue)** : " + " ; ".join(tableau) + ".")

    v1_ferie = ligne(analyses["ferie"], "V1 - Adaptative", "ferie", "Férié")
    v2_ferie = ligne(analyses["ferie"], "V2 - Feries annuels", "ferie", "Férié")
    v1_ord = ligne(analyses["ferie"], "V1 - Adaptative", "ferie", "Non férié")
    v2_ord = ligne(analyses["ferie"], "V2 - Feries annuels", "ferie", "Non férié")
    cho_ord = ligne(analyses["ferie"], "V2 - Choix 2023", "ferie", "Non férié")
    texte += [
        "",
        f"- **Effet des fêtes annuelles** : sur les {int(v1_ferie.jours)} jours fériés évalués, la RMSE passe de {v1_ferie.RMSE_MW:,.0f} MW (V1) à {v2_ferie.RMSE_MW:,.0f} MW (variante fêtes annuelles).",
        f"- Les {int(v1_ord.jours)} jours non fériés sont **inchangés par cette variante** : RMSE V1 {v1_ord.RMSE_MW:,.2f} MW ; variante fêtes {v2_ord.RMSE_MW:,.2f} MW.",
        f"- La configuration choisie sur 2023 a une RMSE de {cho_ord.RMSE_MW:,.2f} MW les jours non fériés, contre {v1_ord.RMSE_MW:,.2f} MW pour la V1 : le gain global ne signifie donc pas un gain sur tous les sous-groupes.",
    ]
    hp = analyses["heure"]
    hp = hp[hp["modele"].eq("V2 - Choix 2023")]
    difficile = hp.loc[hp["RMSE_MW"].idxmax()]
    p = pointes.set_index("modele").loc["V2 - Choix 2023"]
    texte += [
        f"- Heure la plus difficile (configuration retenue) : {int(difficile.heure):02d} h, RMSE {difficile.RMSE_MW:,.0f} MW.",
        f"- Énergie quotidienne : MAE {p.MAE_energie_MWh:,.0f} MWh ; valeur de la pointe : MAE {p.MAE_pointe_MW:,.0f} MW ; heure de pointe : MAE {p.MAE_heure_pointe_h:.2f} h (distance non circulaire).",
        "", "### Trois journées les plus difficiles du réglage retenu", "",
    ]
    pires = quotidiens[quotidiens["modele"].eq("V2 - Choix 2023")].nlargest(3, "RMSE_MW")
    for r in pires.itertuples(index=False):
        sens = "sous-estimation" if r.biais_MW > 0 else "surestimation"
        texte.append(f"- {r.jour.date()} : RMSE {r.RMSE_MW:,.0f} MW ; {sens} moyenne {abs(r.biais_MW):,.0f} MW.")
    texte += [
        "", "## 5. Interprétation scientifique", "",
        "- Une correction n'est pas nécessairement bénéfique : les variantes proportionnelles et combinées doivent être jugées d'après leurs résultats, pas d'après leur complexité.",
        "- La réduction d'erreur sur un petit nombre de journées atypiques peut améliorer la RMSE globale sans améliorer les journées ordinaires.",
        "- Les huit jours fériés sont peu nombreux ; les sous-groupes ne sont pas indépendants et le diagnostic est descriptif, non causal.",
        "- La RMSE globale n'est pas une moyenne simple des RMSE des saisons ou des catégories.",
        "- Les réglages de la V1 et la conception des variantes ont bénéficié de l'examen de résultats 2024 antérieurs. Le réglage 2023 réduit le choix direct sur 2024, mais ne rend pas cette expérience entièrement indépendante de 2024.",
        "- Les hyperparamètres des autres modèles ML du dépôt sont pour la plupart fixés, sans recherche équivalente sur 2023 : la comparaison mesure des configurations concrètes, non une supériorité intrinsèque des familles de modèles.",
        "- La disponibilité effective des données RTE définitives et des observations météo à J 14 h n'est pas historiquement démontrée. Les jours de changement d'heure sont masqués.",
        "- Aucune significativité statistique n'est revendiquée et le test final 2025 n'est pas consulté.", "",
    ]
    return "\n".join(texte)


def main() -> None:
    for chemin in (DATA / "train.csv", DATA / "validation.csv", REF / "benchmarks/jours_evalues.csv"):
        if not chemin.is_file():
            raise FileNotFoundError(f"Donnée de référence absente : {chemin}")
    conso = charger_profils()
    calendrier = charger_calendrier()
    jours2024 = charger_jours_validation()
    candidats2023 = list(conso.index[conso.index.year == 2023])
    prets2023 = [x for jour in candidats2023 if (x := preparer_jour(jour, conso, calendrier)) is not None]
    prets2024 = []
    for jour in jours2024:
        element = preparer_jour(jour, conso, calendrier)
        if element is None:
            raise ValueError(f"Journée de validation attendue mais non admissible : {jour}")
        prets2024.append(element)
    choix, calib2023 = config_2023(prets2023)
    variantes = {**VARIANTES, "V2 - Choix 2023": choix}
    previsions = evaluer(prets2024, variantes)
    if len(previsions) != len(variantes) * 24 * len(prets2024):
        raise AssertionError("Nombre de prévisions de validation inattendu.")

    # La V1 est figée : toute divergence arrête le pipeline avant écriture.
    if not V1_PRED.is_file():
        raise FileNotFoundError(
            "Les prévisions V1 sont requises pour vérifier l'identité du benchmark. "
            "Exécuter d'abord src/benchmark_hebdomadaire_adaptatif.py."
        )
    original = pd.read_csv(V1_PRED, usecols=["horodatage", "prediction_MW"], parse_dates=["horodatage"])
    nouvelle = previsions.loc[previsions.modele.eq("V1 - Adaptative"), ["horodatage", "prediction_MW"]]
    o = original.set_index("horodatage")["prediction_MW"].sort_index()
    n = nouvelle.set_index("horodatage")["prediction_MW"].sort_index()
    if not o.index.equals(n.index) or not np.allclose(o.to_numpy(), n.to_numpy(), rtol=0, atol=1e-6):
        raise ValueError("La V1 reproduite diffère de la version validée. Aucune sortie écrite.")

    ensemble = comparer_autres_modeles(previsions)
    df = preparer_diagnostics(ensemble, calendrier)
    scores = groupes(df).sort_values("RMSE_MW").reset_index(drop=True)
    analyses = {c: groupes(df, c) for c in
                ("saison", "heure", "type_jour", "ferie", "vacances", "classe_temperature")}
    quotidiens, pointes = analyse_journaliere(df)
    SORTIE.mkdir(parents=True, exist_ok=True)
    previsions.to_csv(SORTIE / "previsions_horaires_2024.csv", index=False)
    calib2023.to_csv(SORTIE / "reglages_evalues_2023.csv", index=False)
    scores.to_csv(SORTIE / "comparaison_2024.csv", index=False)
    reference_v1 = scores.loc[scores.modele.eq("V1 - Adaptative")].iloc[0]
    gains = scores.copy()
    gains["gain_RMSE_vs_V1_MW"] = reference_v1.RMSE_MW - gains["RMSE_MW"]
    gains["gain_MAE_vs_V1_MW"] = reference_v1.MAE_MW - gains["MAE_MW"]
    gains.to_csv(SORTIE / "gains_vs_v1.csv", index=False)
    for nom, tab in analyses.items():
        tab.to_csv(SORTIE / f"scores_par_{nom}.csv", index=False)
    quotidiens.to_csv(SORTIE / "scores_quotidiens.csv", index=False)
    pointes.to_csv(SORTIE / "energie_et_pointes.csv", index=False)
    quotidiens[quotidiens.modele.eq("V2 - Choix 2023")].nlargest(10, "RMSE_MW").to_csv(
        SORTIE / "jours_difficiles_top10.csv", index=False)
    tracer(analyses["saison"], analyses["heure"], SORTIE)
    tracer_calendrier(analyses, SORTIE)
    tracer_pires_jours(df, quotidiens, SORTIE)
    (SORTIE / "analyse.md").write_text(
        rapport(scores, choix, calib2023, analyses, quotidiens, pointes), encoding="utf-8"
    )
    infos = {"annee_reglage": 2023, "annee_validation": 2024,
             "jours_reglage": len(prets2023), "jours_validation": len(prets2024),
             "statut": "Validation 2024 exploratoire ; conception des corrections informée par l'analyse de 2024",
             "semaines": N_SEMAINES, "decroissance": DECROISSANCE,
             "grille": [dict(filtre_feries=bool(r.filtre_feries), correction=r.correction,
                            intensite=float(r.intensite), analogues_feries=bool(r.analogues_feries),
                            RMSE_MW=float(r.RMSE_MW))
                        for r in calib2023.itertuples(index=False)],
             "selection_2023": vars(choix),
             "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
             "sha256": {str(p.relative_to(RACINE)): empreinte(p) for p in
                        [DATA / "train.csv", DATA / "validation.csv",
                         REF / "benchmarks" / "jours_evalues.csv", V1_PRED,
                         PREVISIONS_COMMUNES, Path(__file__).resolve()] if p.exists()}}
    (SORTIE / "execution.json").write_text(
        json.dumps(infos, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== ÉTUDE DE CORRECTIONS — VALIDATION 2024 ===")
    print(f"Réglage sur 2023 : {len(prets2023)} jours ; sélection : "
          f"calendrier={choix.calendrier}, mode={choix.mode}, intensite={choix.intensite}, "
          f"analogues_feries={choix.analogues_feries}")
    print(f"Validation 2024 : {len(prets2024)} jours ; {len(prets2024)*24} heures par méthode")
    print(scores[["modele", "MAE_MW", "RMSE_MW", "biais_MW"]].to_string(
        index=False, float_format=lambda x: f"{x:,.2f}"))
    v1 = float(scores.set_index("modele").loc["V1 - Adaptative", "RMSE_MW"])
    v2 = float(scores.set_index("modele").loc["V2 - Choix 2023", "RMSE_MW"])
    print(f"\nDifférence RMSE du choix 2023 versus V1 en 2024 : {v2-v1:+,.2f} MW")
    print(f"Analyse, tableaux et graphiques actualisés : {SORTIE}")
    print("Aucun fichier du test final 2025 n'a été consulté ni modifié.")


if __name__ == "__main__":
    main()
