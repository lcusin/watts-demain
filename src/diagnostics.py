"""Énergie quotidienne, pointes, saisons et trois journées d'échec sur la validation."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from synthese import verifier, scores

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "results/analyse_2024/diagnostics"
CLASSES = ["moins de 5 C", "5 a moins de 15 C", "15 C et plus", "meteo manquante"]


def bilan_jour(g):
    g = g.sort_values("horodatage").reset_index(drop=True)
    heure_reelle = g.loc[g.reel_MW.idxmax(), "horodatage"].hour
    heure_prevue = g.loc[g.prediction_MW.idxmax(), "horodatage"].hour
    return {**scores(g), "energie_reelle_MWh": g.reel_MW.sum(),
            "energie_prevue_MWh": g.prediction_MW.sum(),
            "erreur_energie_MWh": g.reel_MW.sum() - g.prediction_MW.sum(),
            "erreur_pointe_MW": g.reel_MW.max() - g.prediction_MW.max(),
            "heure_pointe_reelle": heure_reelle, "heure_pointe_prevue": heure_prevue,
            "erreur_heure_pointe_h": abs(heure_reelle - heure_prevue)}


def tracer_temperature(p, classement):
    meilleur = classement.loc[classement.famille.ne("benchmarks")].iloc[0].modele
    temperature = pd.DataFrame([
        {"modele": nom, "classe_temperature": classe, **scores(g)}
        for (nom, classe), g in p[p.modele.isin(
            [meilleur, "semaine_precedente"]
        )].groupby(["modele", "classe_temperature"], observed=True)
    ])
    tableau = temperature.pivot(
        index="classe_temperature", columns="modele", values="RMSE_MW"
    ).reindex(CLASSES)
    effectifs = temperature.loc[temperature.modele.eq(meilleur)].set_index("classe_temperature")
    fig, ax = plt.subplots(figsize=(10, 5))
    tableau.plot.bar(ax=ax, rot=0)
    ax.set(title="RMSE selon la température - validation 2024",
           xlabel="Température moyenne horaire observée", ylabel="RMSE (MW)")
    ax.set_xticklabels([f"{nom}\n(n = {int(effectifs.heures.get(nom, 0))})" for nom in CLASSES])
    ax.grid(axis="y", alpha=.2)
    fig.text(.5, .01, "Températures observées utilisées uniquement pour le diagnostic a posteriori.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .06, 1, 1))
    fig.savefig(SORTIE / "rmse_par_temperature.png", dpi=180)
    plt.close(fig)


def tracer_echecs(p, echecs, meilleur):
    fig, axes = plt.subplots(len(echecs), 1, figsize=(11, 3.5*len(echecs)), squeeze=False)
    for ax, ligne in zip(axes[:, 0], echecs.itertuples()):
        g = p.loc[p.jour.eq(ligne.jour) & p.modele.eq(meilleur)].sort_values("horodatage")
        reference = p.loc[p.jour.eq(ligne.jour) & p.modele.eq("semaine_precedente")].sort_values("horodatage")
        ax.plot(g.heure, g.reel_MW, label="Observé")
        ax.plot(g.heure, g.prediction_MW, label=meilleur)
        ax.plot(reference.heure, reference.prediction_MW, label="Semaine précédente", linestyle="--")
        ax.set(title=str(ligne.jour.date()), xlabel="Heure française", ylabel="MW", xticks=range(0,24,3))
        ax.legend(); ax.grid(alpha=.2)
    fig.suptitle(f"Trois plus fortes RMSE quotidiennes en validation 2024 - {meilleur}")
    fig.tight_layout()
    fig.savefig(SORTIE / "trois_echecs.png", dpi=180)
    plt.close(fig)


def graphiques(p, quotidien, classement):
    """Comparer les diagnostics sur les mêmes journées de validation."""
    ordre = classement.modele.tolist()

    # Erreurs horaires et critères quotidiens ; une barre par méthode.
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    for ax, colonne, titre, unite in [
        (axes[0], "RMSE_MW", "RMSE horaire", "MW"),
        (axes[1], "erreur_energie_MWh", "Erreur absolue d'énergie quotidienne", "MWh"),
        (axes[2], "erreur_pointe_MW", "Erreur absolue sur la pointe", "MW")]:
        if colonne == "RMSE_MW":
            valeurs = classement.set_index("modele")[colonne].reindex(ordre)
        else:
            valeurs = quotidien.groupby("modele")[colonne].apply(lambda x: x.abs().mean()).reindex(ordre)
        ax.barh(valeurs.index, valeurs.values, color="steelblue")
        ax.invert_yaxis()
        ax.set(title=titre, xlabel=unite)
        ax.grid(axis="x", alpha=.2)
    fig.suptitle("Comparaison des prévisions — validation 2024")
    fig.tight_layout()
    fig.savefig(SORTIE / "comparaison_erreurs.png", dpi=180)
    plt.close(fig)

    # Profils horaires de trois methodes sur trois journees de l'annee.
    modeles = ["semaine_precedente", "ARMA(1,1)", "Random Forest"]
    dates = ["2024-01-15", "2024-06-20", "2024-12-15"]
    fig, axes = plt.subplots(3, 1, figsize=(12, 11), sharex=True)
    for ax, date in zip(axes, dates):
        jour = pd.Timestamp(date)
        reel = p.loc[p.jour.eq(jour) & p.modele.eq(modeles[0])].sort_values("heure")
        ax.plot(reel.heure, reel.reel_MW, label="Observe", linewidth=2, color="black")
        for modele in modeles:
            g = p.loc[p.jour.eq(jour) & p.modele.eq(modele)].sort_values("heure")
            ax.plot(g.heure, g.prediction_MW, label=modele)
        ax.set(title=date, ylabel="MW")
        ax.grid(alpha=.2)
    axes[-1].set(xlabel="Heure", xticks=range(0, 24, 2))
    axes[0].legend(ncol=2)
    fig.tight_layout()
    fig.savefig(SORTIE / "comparaison_previsions.png", dpi=180)
    plt.close(fig)

    # Les 24 heures d'une même journée restent regroupées dans chaque saison.
    saisons = ["hiver", "printemps", "été", "automne"]
    saison = pd.DataFrame([{"modele": nom, "saison": s, **scores(g)}
                           for (nom, s), g in p.groupby(["modele", "saison"])])
    tableau = saison.pivot(index="saison", columns="modele", values="RMSE_MW").reindex(saisons)
    fig, ax = plt.subplots(figsize=(13, 6))
    tableau[ordre].plot.bar(ax=ax, width=.85)
    ax.set(title="RMSE selon la saison — validation 2024", xlabel="Saison", ylabel="RMSE (MW)")
    ax.tick_params(axis="x", rotation=0)
    ax.legend(title="Modèle", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(axis="y", alpha=.2)
    fig.tight_layout()
    fig.savefig(SORTIE / "rmse_par_saison.png", dpi=180)
    plt.close(fig)

    # Comparer le meilleur modele et le benchmark selon la temperature observee.
    tracer_temperature(p, classement)

    fig, ax = plt.subplots(figsize=(12, 6))
    for nom in ordre:
        g = p[p.modele.eq(nom)]
        rmse = g.groupby("heure").apply(lambda x: scores(x)["RMSE_MW"])
        ax.plot(rmse.index, rmse.values, label=nom)
    ax.set(title="RMSE selon l'heure — validation 2024", xlabel="Heure française", ylabel="RMSE (MW)", xticks=range(0, 24, 2))
    ax.legend(title="Modèle", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(SORTIE / "rmse_par_heure.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 6))
    # La persistance est constante : son heure de pointe ne représente pas une prévision de pointe.
    heures = quotidien[quotidien.modele.ne("persistance")].groupby("modele").erreur_heure_pointe_h.mean()
    heures = heures.reindex([nom for nom in ordre if nom != "persistance"])
    ax.barh(heures.index, heures.values, color="steelblue")
    ax.invert_yaxis()
    ax.set(title="Erreur moyenne sur l'heure de pointe", xlabel="Heures (écart absolu non circulaire)")
    ax.grid(axis="x", alpha=.2)
    fig.text(.12, .02, "Persistance exclue : sa prévision est constante sur les 24 heures.", fontsize=9)
    fig.tight_layout(rect=(0, .05, 1, 1))
    fig.savefig(SORTIE / "erreur_heure_pointe.png", dpi=180)
    plt.close(fig)

    # Comparer les catégories calendaires pour le meilleur modèle et la semaine précédente.
    meilleur = classement.loc[classement.famille.ne("benchmarks")].iloc[0].modele
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    for ax, variable, titre in zip(axes, ["weekend", "jour_ferie", "vacances_scolaires"],
                                   ["Week-end", "Jour férié", "Vacances scolaires"]):
        lignes = [{"modele": nom, "categorie": valeur, **scores(g)}
                  for (nom, valeur), g in p[p.modele.isin([meilleur, "semaine_precedente"])].groupby(["modele", variable])]
        tableau = pd.DataFrame(lignes).pivot(index="categorie", columns="modele", values="RMSE_MW")
        tableau.plot.bar(ax=ax, rot=0)
        ax.set(title=titre, xlabel="0 : non ; 1 : oui", ylabel="RMSE (MW)")
        ax.grid(axis="y", alpha=.2)
    fig.suptitle("Performances selon le calendrier — validation 2024")
    fig.tight_layout()
    fig.savefig(SORTIE / "rmse_calendrier.png", dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--graphiques-seuls", action="store_true")
    args = parser.parse_args()
    if args.graphiques_seuls:
        p = pd.read_csv(RACINE / "results/analyse_2024/previsions_communes.csv", parse_dates=["horodatage"])
        classement = pd.read_csv(RACINE / "results/analyse_2024/comparaison_globale.csv")
        validation = pd.read_csv(RACINE / "data/merge/validation.csv", parse_dates=["horodatage"])
        p = p.merge(validation[["horodatage", "temperature_moyenne"]], on="horodatage", validate="many_to_one")
        p["jour"] = p.horodatage.dt.normalize()
        p["heure"] = p.horodatage.dt.hour
        p["classe_temperature"] = pd.cut(
            p.temperature_moyenne, [-np.inf, 5, 15, np.inf], right=False,
            labels=CLASSES[:3],
        ).cat.add_categories(CLASSES[3]).fillna(CLASSES[3])
        echecs = pd.read_csv(SORTIE / "trois_echecs.csv", parse_dates=["jour"])
        meilleur = classement.loc[classement.famille.ne("benchmarks")].iloc[0].modele
        tracer_temperature(p, classement)
        tracer_echecs(p, echecs, meilleur)
        return
    # Refaire les contrôles évite d'utiliser une ancienne synthèse.
    p, classement, jours = verifier()
    SORTIE.mkdir(parents=True, exist_ok=True)
    validation = pd.read_csv(RACINE / "data/merge/validation.csv", parse_dates=["horodatage"])
    train = pd.read_csv(RACINE / "data/merge/train.csv", parse_dates=["horodatage"])
    historique = pd.concat([train, validation], ignore_index=True)
    colonnes = ["horodatage", "jour_ferie", "weekend", "vacances_scolaires", "temperature_moyenne"]
    p = p.merge(validation[colonnes], on="horodatage", validate="many_to_one")
    p["jour"] = p.horodatage.dt.normalize()
    p["heure"] = p.horodatage.dt.hour
    p["saison"] = p.horodatage.dt.month.map({12:"hiver", 1:"hiver", 2:"hiver",
        3:"printemps", 4:"printemps", 5:"printemps", 6:"été", 7:"été", 8:"été",
        9:"automne", 10:"automne", 11:"automne"})
    p["classe_temperature"] = pd.cut(
        p.temperature_moyenne, [-np.inf, 5, 15, np.inf],
        right=False, labels=["moins de 5 C", "5 a moins de 15 C", "15 C et plus"],
    ).cat.add_categories("meteo manquante").fillna("meteo manquante")
    # Moyennes des erreurs horaires ; mêmes dates pour chaque modèle.
    for variable in ["saison", "heure", "weekend", "jour_ferie",
                     "vacances_scolaires", "classe_temperature"]:
        lignes = [{"modele": nom, variable: valeur, **scores(g)}
                  for (nom, valeur), g in p.groupby(["modele", variable], observed=True)]
        pd.DataFrame(lignes).to_csv(SORTIE / f"scores_par_{variable}.csv", index=False)
    quotidien = pd.DataFrame([{"modele": nom, "jour": jour, **bilan_jour(g)}
                              for (nom, jour), g in p.groupby(["modele", "jour"])])
    quotidien.to_csv(SORTIE / "scores_quotidiens.csv", index=False)
    resumes = []
    for nom, g in quotidien.groupby("modele"):
        resumes.append({"modele": nom, "jours": len(g),
            "MAE_energie_MWh": g.erreur_energie_MWh.abs().mean(),
            "biais_energie_MWh": g.erreur_energie_MWh.mean(),
            "MAE_pointe_MW": g.erreur_pointe_MW.abs().mean(),
            "MAE_heure_pointe_h": g.erreur_heure_pointe_h.mean()})
    pd.DataFrame(resumes).to_csv(SORTIE / "energie_et_pointes.csv", index=False)
    graphiques(p, quotidien, classement)
    # Trois pires journées du meilleur modèle hors benchmarks, selon la RMSE horaire.
    meilleur = classement.loc[classement.famille.ne("benchmarks")].iloc[0].modele
    echecs = quotidien.loc[quotidien.modele.eq(meilleur)].nlargest(3, "RMSE_MW").copy()
    contexte = historique.assign(jour=historique.horodatage.dt.normalize()).groupby("jour").agg(
        temperature_moyenne=("temperature_moyenne", "mean"),
        consommation_moyenne=("consommation_MW", "mean"),
        jour_ferie=("jour_ferie", "max"), weekend=("weekend", "max"),
        vacances_scolaires=("vacances_scolaires", "max"))
    reference_7j = contexte[["temperature_moyenne", "consommation_moyenne"]].copy()
    reference_7j.index = reference_7j.index + pd.Timedelta(days=7)
    reference_7j = reference_7j.rename(columns={
        "temperature_moyenne": "temperature_7j_avant",
        "consommation_moyenne": "consommation_7j_avant",
    })
    contexte = contexte.join(reference_7j)
    echecs = echecs.merge(contexte, on="jour", validate="one_to_one")
    echecs.to_csv(SORTIE / "trois_echecs.csv", index=False)
    texte = f"# Trois journées d'échec — {meilleur}\n\nSélection : trois plus fortes RMSE quotidiennes sur 2024.\n"
    for ligne in echecs.itertuples():
        reference = p.loc[p.jour.eq(ligne.jour) & p.modele.eq("semaine_precedente")].sort_values("horodatage")
        rmse_reference = scores(reference)["RMSE_MW"]
        sens = "sous-estimation" if ligne.biais_MW > 0 else "surestimation"
        texte += (f"\n## {ligne.jour.date()}\n\nRMSE : {ligne.RMSE_MW:.0f} MW ; {sens} moyenne "
                  f"de {abs(ligne.biais_MW):.0f} MW. Erreur absolue d'énergie : {abs(ligne.erreur_energie_MWh):.0f} MWh ; "
                  f"de pointe : {abs(ligne.erreur_pointe_MW):.0f} MW ; d'heure de pointe : {ligne.erreur_heure_pointe_h} h. "
                  f"Température moyenne observée : {ligne.temperature_moyenne:.1f} °C ; "
                  f"jour férié : {ligne.jour_ferie} ; vacances : {ligne.vacances_scolaires}.\n\n"
                  "À interpréter : vérifier l'historique utilisé, les variations météorologiques et les effets calendaires. "
                  "Ces constats ne permettent pas, seuls, d'attribuer une cause à l'erreur.\n")
        texte += (f"Sept jours avant : temperature moyenne "
                  f"{ligne.temperature_7j_avant:.1f} C et consommation moyenne "
                  f"{ligne.consommation_7j_avant:.0f} MW. "
                  f"RMSE du benchmark hebdomadaire : {rmse_reference:.0f} MW.\n")
    texte += ("\nLes températures du jour cible servent uniquement au diagnostic rétrospectif. "
              "Énergie = somme des 24 puissances moyennes multipliées par 1 h. "
              "Heure de pointe : première occurrence du maximum ; distance absolue entre les heures (non circulaire).\n")
    tracer_echecs(p, echecs, meilleur)
    (SORTIE / "ANALYSE_ECHECS.md").write_text(texte, encoding="utf-8")


if __name__ == "__main__":
    main()
