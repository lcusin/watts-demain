"""Analyse du benchmark hebdomadaire adaptatif (validation 2024).

Compare les prévisions horaires de la V1 aux méthodes du projet sur les mêmes
horodatages : saisons, heures, calendrier, températures observées, énergie
quotidienne, heures et valeurs de pointe, journées de forte erreur.
Les résultats et le rapport Markdown sont recalculés à chaque exécution.

La météo de la journée cible sert uniquement à l'analyse a posteriori et
n'entre jamais dans la prédiction. Aucun fichier de 2025 n'est chargé.

Usage : python src/analyser_benchmark_hebdomadaire_adaptatif.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_MODELE = RACINE / "results/analyse_2024/benchmark_hebdomadaire_adaptatif"
PREVISIONS = DOSSIER_MODELE / "previsions_horaires_2024.csv"
COMMUNES = RACINE / "results/analyse_2024/previsions_communes.csv"
VALIDATION = RACINE / "data/merge/validation.csv"
SORTIE_DEFAUT = DOSSIER_MODELE / "diagnostics"
NOUVEAU = "Moyenne hebdomadaire adaptative"
COMPARAISONS = [NOUVEAU, "Random Forest", "Regression lineaire", "Ridge", "semaine_precedente"]
SAISONS = ["Hiver", "Printemps", "Été", "Automne"]


def metriques(groupe: pd.DataFrame) -> dict:
    """MAE, RMSE et biais signés (réel moins prédit)."""
    erreur = groupe["reel_MW"].to_numpy(dtype=float) - groupe["prediction_MW"].to_numpy(dtype=float)
    return {
        "jours": int(groupe["jour"].nunique()),
        "heures": len(erreur),
        "MAE_MW": float(np.mean(np.abs(erreur))),
        "RMSE_MW": float(np.sqrt(np.mean(erreur**2))),
        "biais_MW": float(np.mean(erreur)),
    }


def charger() -> pd.DataFrame:
    """Aligne les prévisions du benchmark, les autres modèles et le calendrier."""
    for chemin in (PREVISIONS, COMMUNES, VALIDATION):
        if not chemin.is_file():
            raise FileNotFoundError(f"Fichier requis absent : {chemin}")

    colonnes = ["horodatage", "modele", "reel_MW", "prediction_MW"]
    nouveau = pd.read_csv(PREVISIONS, parse_dates=["horodatage"])
    nouveau = nouveau[colonnes + ["semaines_utilisees", "correction_niveau_MW"]]
    commun = pd.read_csv(COMMUNES, usecols=colonnes, parse_dates=["horodatage"])
    autres = commun[commun["modele"].isin(COMPARAISONS[1:])].copy()
    manquants = set(COMPARAISONS[1:]) - set(autres["modele"].unique())
    if manquants:
        raise ValueError(f"Modèles de comparaison manquants : {sorted(manquants)}")

    horodatages = pd.DatetimeIndex(nouveau["horodatage"])
    if horodatages.isna().any() or horodatages.has_duplicates or (horodatages.year != 2024).any():
        raise ValueError("Les prévisions de la nouvelle méthode doivent couvrir des heures uniques de 2024.")
    if len(horodatages) % 24:
        raise ValueError("Le nombre d'heures doit être multiple de 24.")
    ref = nouveau.set_index("horodatage")["reel_MW"].sort_index()
    for nom, valeurs in autres.groupby("modele"):
        if len(valeurs) != len(nouveau) or valeurs["horodatage"].duplicated().any():
            raise ValueError(f"Nombre d'heures incompatible pour {nom}.")
        verifie = valeurs.set_index("horodatage")["reel_MW"].sort_index()
        if not verifie.index.equals(ref.index) or not np.allclose(
            verifie.to_numpy(), ref.to_numpy(), atol=1e-6, rtol=0, equal_nan=False
        ):
            raise ValueError(f"Cibles ou horodatages différents pour {nom}.")

    toutes = pd.concat([nouveau, autres], ignore_index=True)
    contexte = pd.read_csv(
        VALIDATION,
        usecols=["horodatage", "weekend", "jour_ferie", "vacances_scolaires", "temperature_moyenne"],
        parse_dates=["horodatage"],
    )
    if contexte["horodatage"].duplicated().any():
        raise ValueError("Doublons dans les horaires de validation.")
    toutes = toutes.merge(contexte, on="horodatage", how="left", validate="many_to_one", indicator=True)
    if toutes["_merge"].ne("both").any():
        raise ValueError("Certaines heures n'ont pas de données calendaires dans validation.csv.")
    toutes.drop(columns="_merge", inplace=True)
    for col in ("weekend", "jour_ferie", "vacances_scolaires"):
        if not toutes[col].isin([0, 1]).all():
            raise ValueError(f"Valeurs non binaires dans {col}.")
    if toutes[["reel_MW", "prediction_MW"]].isna().any().any():
        raise ValueError("Prévisions ou observations manquantes.")

    toutes["jour"] = toutes["horodatage"].dt.normalize()
    toutes["heure"] = toutes["horodatage"].dt.hour
    toutes["mois"] = toutes["horodatage"].dt.month
    toutes["saison"] = toutes["mois"].map({
        12: "Hiver", 1: "Hiver", 2: "Hiver",
        3: "Printemps", 4: "Printemps", 5: "Printemps",
        6: "Été", 7: "Été", 8: "Été",
        9: "Automne", 10: "Automne", 11: "Automne",
    })
    toutes["type_jour"] = np.where(toutes["weekend"].eq(1), "Week-end", "Semaine")
    toutes["ferie"] = np.where(toutes["jour_ferie"].eq(1), "Férié", "Non férié")
    toutes["vacances"] = np.where(toutes["vacances_scolaires"].eq(1), "Vacances", "Hors vacances")
    toutes["classe_temperature"] = pd.cut(
        toutes["temperature_moyenne"],
        bins=[-np.inf, 5, 15, np.inf], right=False,
        labels=["Moins de 5 °C", "5 à moins de 15 °C", "15 °C et plus"],
    ).astype("object").fillna("Météo manquante")

    n_jours = nouveau["horodatage"].dt.normalize().nunique()
    if len(nouveau) != n_jours * 24:
        raise ValueError("Chaque journée doit contenir exactement 24 heures.")
    if any(len(g) != n_jours * 24 for _, g in toutes.groupby("modele")):
        raise ValueError("Les modèles ne couvrent pas le même nombre d'heures.")
    return toutes


def regrouper(df: pd.DataFrame, variable: str) -> pd.DataFrame:
    lignes = []
    for (modele, valeur), groupe in df.groupby(["modele", variable], observed=True, sort=False):
        lignes.append({"modele": modele, variable: valeur, **metriques(groupe)})
    return pd.DataFrame(lignes).sort_values([variable, "modele"]).reset_index(drop=True)


def calculer_quotidiens(df: pd.DataFrame) -> pd.DataFrame:
    lignes = []
    for (modele, jour), g in df.groupby(["modele", "jour"], sort=True):
        g = g.sort_values("heure")
        if len(g) != 24 or not np.array_equal(g["heure"].to_numpy(), np.arange(24)):
            raise ValueError(f"Journée non complète pour {modele} : {jour}.")
        reel = g["reel_MW"].to_numpy()
        predit = g["prediction_MW"].to_numpy()
        err = reel - predit
        h_reel, h_predit = int(np.argmax(reel)), int(np.argmax(predit))
        lignes.append({
            "modele": modele, "jour": jour.date().isoformat(),
            "MAE_MW": float(np.mean(np.abs(err))),
            "RMSE_MW": float(np.sqrt(np.mean(err**2))),
            "biais_MW": float(np.mean(err)),
            "erreur_energie_MWh": float(np.sum(err)),
            "erreur_pointe_MW": float(np.max(reel) - np.max(predit)),
            "heure_pointe_reelle": h_reel,
            "heure_pointe_prevue": h_predit,
            "erreur_heure_pointe_h": abs(h_reel - h_predit),
            "temperature_moyenne_observee_C": float(g["temperature_moyenne"].mean()),
            "type_jour": g["type_jour"].iloc[0],
            "ferie": g["ferie"].iloc[0],
            "vacances": g["vacances"].iloc[0],
        })
    return pd.DataFrame(lignes)


def energie_pointes(quotidiens: pd.DataFrame) -> pd.DataFrame:
    lignes = []
    for modele, groupe in quotidiens.groupby("modele", sort=False):
        lignes.append({
            "modele": modele,
            "jours": len(groupe),
            "MAE_energie_MWh": float(groupe["erreur_energie_MWh"].abs().mean()),
            "MAE_pointe_MW": float(groupe["erreur_pointe_MW"].abs().mean()),
            "MAE_heure_pointe_h": float(groupe["erreur_heure_pointe_h"].mean()),
        })
    return pd.DataFrame(lignes).sort_values("MAE_energie_MWh")


def graphique_saisons(scores: pd.DataFrame, dossier: Path) -> None:
    pivot = scores.pivot(index="saison", columns="modele", values="RMSE_MW").reindex(SAISONS)
    fig, ax = plt.subplots(figsize=(10, 5))
    pivot.reindex(columns=COMPARAISONS).plot(kind="bar", ax=ax, width=0.83)
    ax.set(title="RMSE par saison — validation 2024", xlabel="", ylabel="RMSE (MW)")
    ax.tick_params(axis="x", rotation=0)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(dossier / "rmse_par_saison.png", dpi=160)
    plt.close(fig)


def graphique_heures(scores: pd.DataFrame, dossier: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    for modele in COMPARAISONS:
        g = scores[scores["modele"].eq(modele)].sort_values("heure")
        ax.plot(g["heure"], g["RMSE_MW"], label=modele, linewidth=1.8)
    ax.set(title="RMSE selon l'heure prévue — validation 2024", xlabel="Heure française", ylabel="RMSE (MW)",
           xticks=list(range(0, 24, 2)))
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(dossier / "rmse_par_heure.png", dpi=160)
    plt.close(fig)


def graphique_calendrier(analyses: dict[str, pd.DataFrame], dossier: Path) -> None:
    variables = [("type_jour", "Semaine / week-end"), ("ferie", "Jour férié"), ("vacances", "Vacances scolaires")]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, (variable, titre) in zip(axes, variables):
        pivot = analyses[variable].pivot(index=variable, columns="modele", values="RMSE_MW")
        pivot.reindex(columns=COMPARAISONS).plot.bar(ax=ax, rot=0, legend=False)
        ax.set(title=titre, xlabel="", ylabel="RMSE (MW)")
        ax.grid(axis="y", alpha=0.25)
        ax.tick_params(axis="x", labelsize=8)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=9)
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    fig.savefig(dossier / "rmse_par_type_jour.png", dpi=160)
    plt.close(fig)


def graphique_temperature(scores: pd.DataFrame, dossier: Path) -> None:
    ordre = ["Moins de 5 °C", "5 à moins de 15 °C", "15 °C et plus", "Météo manquante"]
    pivot = scores.pivot(index="classe_temperature", columns="modele", values="RMSE_MW")
    fig, ax = plt.subplots(figsize=(11, 5))
    pivot.reindex(index=ordre, columns=COMPARAISONS).plot.bar(ax=ax, rot=0)
    ax.set(title="RMSE selon la température observée du jour prévu (diagnostic a posteriori)",
           xlabel="", ylabel="RMSE (MW)")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(dossier / "rmse_par_temperature.png", dpi=160)
    plt.close(fig)


def graphique_echecs(df: pd.DataFrame, pire: pd.DataFrame, dossier: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(11, 10), sharex=True)
    for ax, row in zip(axes, pire.itertuples(index=False)):
        date = pd.Timestamp(row.jour)
        g = df[df["jour"].eq(date) & df["modele"].isin(
            [NOUVEAU, "Random Forest", "semaine_precedente"])]
        reel = g[g["modele"].eq(NOUVEAU)].sort_values("heure")
        ax.plot(reel["heure"], reel["reel_MW"], label="Observé", linewidth=2.2)
        for modele in (NOUVEAU, "Random Forest", "semaine_precedente"):
            serie = g[g["modele"].eq(modele)].sort_values("heure")
            ax.plot(serie["heure"], serie["prediction_MW"], label=modele, linewidth=1.5)
        ax.set(title=f"{row.jour} — RMSE du benchmark : {row.RMSE_MW:.0f} MW",
               ylabel="Consommation (MW)")
        ax.grid(alpha=0.25)
    axes[-1].set(xlabel="Heure française", xticks=list(range(0, 24, 2)))
    axes[0].legend(ncol=2, fontsize=8)
    fig.tight_layout()
    fig.savefig(dossier / "trois_jours_difficiles.png", dpi=160)
    plt.close(fig)


def rapport_markdown(
    df: pd.DataFrame,
    analyses: dict[str, pd.DataFrame],
    quotidien: pd.DataFrame,
    pointes: pd.DataFrame,
) -> str:
    """Construit une lecture critique à partir des métriques réellement calculées."""
    scores = regrouper(df.assign(ensemble="2024"), "ensemble").drop(columns="ensemble")
    scores = scores.set_index("modele")
    actuel = scores.loc[NOUVEAU]
    rf = scores.loc["Random Forest"]
    lr = scores.loc["Regression lineaire"]
    s = analyses["saison"]
    t = analyses["type_jour"]
    f = analyses["ferie"]
    h = analyses["heure"]
    jours = int(actuel.jours)
    reglage = pd.read_csv(DOSSIER_MODELE / "comparaison_2024.csv").iloc[0]

    def resultat(table: pd.DataFrame, modele: str, categorie: str, valeur: str) -> pd.Series:
        return table.loc[(table["modele"] == modele) & (table[categorie] == valeur)].iloc[0]

    saison = s[s["modele"] == NOUVEAU]
    faible = saison.loc[saison["RMSE_MW"].idxmin()]
    forte = saison.loc[saison["RMSE_MW"].idxmax()]
    heures = h[h["modele"] == NOUVEAU]
    pire_heure = heures.loc[heures["RMSE_MW"].idxmax()]
    semaine = resultat(t, NOUVEAU, "type_jour", "Semaine")
    weekend = resultat(t, NOUVEAU, "type_jour", "Week-end")
    ferie = resultat(f, NOUVEAU, "ferie", "Férié")
    non_ferie = resultat(f, NOUVEAU, "ferie", "Non férié")
    pointe = pointes.set_index("modele").loc[NOUVEAU]
    rf_pointe = pointes.set_index("modele").loc["Random Forest"]
    pires = quotidien[quotidien["modele"] == NOUVEAU].nlargest(3, "RMSE_MW")

    phrases = [
        "# Benchmark hebdomadaire adaptatif (V1) — analyse de validation 2024", "",
        "*Analyse régénérée à chaque exécution ; chiffres issus des prévisions enregistrées.*", "",
        "## Question et protocole", "",
        "- À J 14 h, prévoir les 24 consommations horaires de J+1.",
        f"- Profil pondéré sur {int(reglage.weeks)} semaines antérieures (poids géométriques, décroissance {reglage.decay:g}).",
        f"- Ajustement additif du niveau à partir des consommations de J entre 00 h et 08 h (coefficient {reglage.correction:g}).",
        f"- Comparaison sur les mêmes {jours} journées et {int(actuel.heures)} heures de 2024.",
        "- Les jours de changement d'heure sont masqués dans les historiques ; les données définitives RTE ne garantissent pas la disponibilité historique effective à 14 h.",
        "- Les températures du lendemain sont exploitées seulement pour les diagnostics a posteriori.", "",
        "## Comparaison globale", "",
        "| Méthode | MAE (MW) | RMSE (MW) | Biais (MW) |", "|---|---:|---:|---:|",
    ]
    for nom in (NOUVEAU, "Random Forest", "Regression lineaire", "Ridge", "semaine_precedente"):
        r = scores.loc[nom]
        phrases.append(f"| {nom} | {r.MAE_MW:,.2f} | {r.RMSE_MW:,.2f} | {r.biais_MW:+,.2f} |")
    phrases += [
        "",
        f"- La V1 a une MAE de {actuel.MAE_MW:,.0f} MW contre {lr.MAE_MW:,.0f} MW pour la régression linéaire, mais une RMSE de {actuel.RMSE_MW:,.0f} MW contre {lr.RMSE_MW:,.0f} MW : les classements dépendent de la métrique.",
        f"- Le Random Forest reste meilleur en RMSE ({rf.RMSE_MW:,.0f} MW).",
        f"- Un biais positif ({actuel.biais_MW:+,.0f} MW, défini comme réel moins prédit) correspond à une sous-estimation moyenne.", "",
        "## Où la méthode réussit-elle ou échoue-t-elle ?", "",
        f"- Meilleure saison : {faible.saison} (RMSE {faible.RMSE_MW:,.0f} MW sur {int(faible.jours)} jours) ; plus difficile : {forte.saison} (RMSE {forte.RMSE_MW:,.0f} MW sur {int(forte.jours)} jours).",
        f"- Semaine : RMSE {semaine.RMSE_MW:,.0f} MW ({int(semaine.jours)} jours) ; week-end : {weekend.RMSE_MW:,.0f} MW ({int(weekend.jours)} jours).",
        f"- Jours fériés : RMSE {ferie.RMSE_MW:,.0f} MW ({int(ferie.jours)} jours) ; autres jours : {non_ferie.RMSE_MW:,.0f} MW ({int(non_ferie.jours)} jours). Ces catégories peuvent se recouper avec le week-end.",
        f"- Heure de plus forte RMSE : {int(pire_heure.heure):02d} h ({pire_heure.RMSE_MW:,.0f} MW).",
        "- Les CSV détaillent également les mois, vacances et classes de température observée ; ces facteurs sont associés et n'autorisent pas une attribution causale des erreurs.", "",
        "## Énergie et pointes", "",
        f"- Erreur absolue moyenne d'énergie : {pointe.MAE_energie_MWh:,.0f} MWh/jour (somme des 24 MW horaires × 1 h).",
        f"- Erreur absolue moyenne de valeur de pointe : {pointe.MAE_pointe_MW:,.0f} MW.",
        f"- Erreur absolue moyenne d'heure de pointe : {pointe.MAE_heure_pointe_h:.2f} h, contre {rf_pointe.MAE_heure_pointe_h:.2f} h pour Random Forest. La distance entre heures est non circulaire.", "",
        "## Trois journées les plus difficiles", "",
    ]
    for r in pires.itertuples(index=False):
        sens = "sous-estimation" if r.biais_MW > 0 else "surestimation"
        phrases.append(f"- {r.jour} : RMSE {r.RMSE_MW:,.0f} MW ; {sens} moyenne de {abs(r.biais_MW):,.0f} MW.")
    phrases += [
        "", "## Discussion et limites", "",
        "- La forte saisonnalité résiduelle et les jours exceptionnels limitent la transposition brute d'un profil hebdomadaire.",
        "- Les scores de huit jours fériés ne représentent pas une estimation stable de toutes les situations calendaires.",
        "- La RMSE globale doit être recalculée sur toutes les heures : ce n'est pas la moyenne arithmétique des RMSE des saisons.",
        "- Il s'agit d'une simulation rétrospective utilisant les données définitives RTE, et non d'un essai de disponibilité réelle des données à J 14 h.",
        "- Le réglage de cette V1 et les corrections ultérieures ont été explorés avec connaissance de certains résultats 2024. Les comparaisons ultérieures sur 2024 sont donc exploratoires.",
        "- Aucune conclusion de significativité statistique n'est tirée de ces différences ; le test 2025 n'est pas utilisé.", "",
    ]
    return "\n".join(phrases)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=SORTIE_DEFAUT,
                        help="Dossier de sortie des diagnostics")
    args = parser.parse_args()
    sortie = (RACINE / args.output if not args.output.is_absolute() else args.output).resolve()
    sortie_permise = DOSSIER_MODELE.resolve()
    if sortie != sortie_permise and sortie_permise not in sortie.parents:
        parser.error("Les diagnostics doivent rester sous le dossier du benchmark adaptatif.")
    if sortie == sortie_permise:
        parser.error("Choisir un sous-dossier de diagnostics, pas la racine des prévisions.")

    df = charger()
    sortie.mkdir(parents=True, exist_ok=True)
    variables = ["saison", "heure", "type_jour", "ferie", "vacances", "mois", "classe_temperature"]
    analyses = {variable: regrouper(df, variable) for variable in variables}
    for variable, valeurs in analyses.items():
        valeurs.to_csv(sortie / f"scores_par_{variable}.csv", index=False)
    global_scores = regrouper(df.assign(ensemble="2024"), "ensemble").drop(columns="ensemble")
    global_scores.sort_values("RMSE_MW").to_csv(sortie / "comparaison_globale.csv", index=False)
    quotidien = calculer_quotidiens(df)
    quotidien.to_csv(sortie / "scores_quotidiens.csv", index=False)
    pointes = energie_pointes(quotidien)
    pointes.to_csv(sortie / "energie_et_pointes.csv", index=False)
    pire = quotidien[quotidien["modele"].eq(NOUVEAU)].nlargest(10, "RMSE_MW")
    pire.to_csv(sortie / "jours_difficiles_top10.csv", index=False)
    semaines = df[df["modele"].eq(NOUVEAU)].groupby("semaines_utilisees", dropna=False)
    pd.DataFrame([{"semaines_utilisees": int(k), **metriques(g)} for k, g in semaines]).to_csv(
        sortie / "scores_par_semaines_utilisees.csv", index=False
    )
    graphique_saisons(analyses["saison"], sortie)
    graphique_heures(analyses["heure"], sortie)
    graphique_calendrier(analyses, sortie)
    graphique_temperature(analyses["classe_temperature"], sortie)
    graphique_echecs(df, pire.head(3), sortie)
    (sortie / "analyse.md").write_text(
        rapport_markdown(df, analyses, quotidien, pointes), encoding="utf-8"
    )

    nom = NOUVEAU
    selection = global_scores[global_scores["modele"].eq(nom)].iloc[0]
    print("\n===== DIAGNOSTICS DU BENCHMARK HEBDOMADAIRE ADAPTATIF =====")
    print(f"2024 : {selection.jours} jours ; {selection.heures} heures (identiques entre modèles)")
    print(f"MAE = {selection.MAE_MW:,.2f} MW | RMSE = {selection.RMSE_MW:,.2f} MW")
    print("\nRMSE par saison :")
    print(analyses["saison"].query("modele == @nom")["saison RMSE_MW jours".split()].to_string(index=False))
    print("\nRMSE par type de jour :")
    print(analyses["type_jour"].query("modele == @nom")["type_jour RMSE_MW jours".split()].to_string(index=False))
    print("\nÉnergie et pointes :")
    print(pointes[pointes["modele"].eq(nom)].to_string(index=False))
    print("\nTrois journées aux plus fortes RMSE :")
    print(pire.head(3)[["jour", "RMSE_MW", "biais_MW"]].to_string(index=False))
    print(f"\nFichiers CSV, PNG et synthèse : {sortie}")
    print("Le jeu de test 2025 n'a pas été utilisé.")


if __name__ == "__main__":
    main()
