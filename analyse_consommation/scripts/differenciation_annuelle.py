"""Comparer 364 jours de decalage, avec une reference une heure avant/apres."""


import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import acf, levinson_durbin

from resume import ecrire_resume
from chemins_analyse import RESULTATS as DOSSIER, PROJET
SORTIE = DOSSIER / "04_difference_annuelle"
DECALAGES = {"reference_avant_1h": 8737, "meme_heure": 8736,
             "reference_apres_1h": 8735}


def sauver(fig, nom):
    fig.tight_layout()
    fig.savefig(SORTIE / f"{nom}.png", dpi=180)
    plt.close(fig)


def scores(s):
    correlations = acf(s, nlags=168, fft=True)
    return {"n": len(s), "moyenne_MW": s.mean(), "MAE_MW": s.abs().mean(),
            "RMSE_MW": np.sqrt(s.pow(2).mean()), "ecart_type_MW": s.std(),
            "ACF_1": correlations[1], "ACF_24": correlations[24],
            "ACF_168": correlations[168]}


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    x = pd.read_csv(PROJET / "data/merge/train.csv",
                    parse_dates=["horodatage"])
    y = x.set_index("horodatage").consommation_MW.sort_index()
    assert y.index.is_unique and np.isfinite(y).all()
    assert y.index.equals(pd.date_range(y.index.min(), y.index.max(), freq="h"))

    # Rechercher des dates, et non supposer qu'une ligne vaut toujours une heure.
    references = pd.DataFrame(index=y.index)
    for nom, retard in DECALAGES.items():
        references[nom] = y.reindex(y.index - pd.Timedelta(hours=retard)).to_numpy()
    references = references.dropna()  # Support commun aux trois essais.
    differences = references.rsub(y.loc[references.index], axis=0)
    series = pd.DataFrame({"consommation_MW": y.loc[references.index]})
    series = series.join(differences)
    for methode in ["standard", "robuste"]:
        fichier = DOSSIER / "03_stl" / f"composantes_hebdomadaire_{methode}.csv"
        stl = pd.read_csv(fichier, index_col="horodatage", parse_dates=True)
        series[f"STL_hebdomadaire_{methode}"] = stl.residu_MW.reindex(series.index)
    assert series.notna().all().all()
    for nom in DECALAGES:
        assert np.allclose(differences[nom] + references[nom], series.consommation_MW)
    series.to_csv(SORTIE / "series.csv", index_label="horodatage")
    bilan = pd.DataFrame({nom: scores(s) for nom, s in series.items()}).T
    bilan.to_csv(SORTIE / "comparaison.csv", index_label="methode")

    # Stabilite du classement : chaque sous-groupe garde exactement les memes dates.
    lignes = []
    for groupe, valeurs in [("annee", differences.index.year),
                             ("mois", differences.index.month),
                             ("heure", differences.index.hour)]:
        for valeur, bloc in differences.groupby(valeurs):
            for nom, s in bloc.items():
                lignes.append({"groupe": groupe, "valeur": valeur, "methode": nom,
                               "n": len(s), "MAE_MW": s.abs().mean(),
                               "RMSE_MW": np.sqrt(s.pow(2).mean())})
    details = pd.DataFrame(lignes)
    details.to_csv(SORTIE / "scores_par_groupe.csv", index=False)

    # Controle des etiquettes locales problematiques, sans convertir les donnees.
    local = y.index.tz_localize("Europe/Paris", ambiguous="NaT", nonexistent="NaT")
    audit = pd.DataFrame({"horodatage": y.index[local.isna()],
                          "motif": "Heure locale ambigue ou inexistante"})
    audit.to_csv(SORTIE / "audit_heures_changement.csv", index=False)
    dates_reference = series.index - pd.Timedelta(days=364)
    assert (dates_reference.hour == series.index.hour).all()
    assert (dates_reference.dayofweek == series.index.dayofweek).all()

    fig, axes = plt.subplots(len(series.columns), 2, figsize=(15, 18))
    for ligne, (nom, s) in enumerate(series.items()):
        a = acf(s, nlags=336, fft=True)
        p = levinson_durbin(a, nlags=336, isacov=True)[2]
        for ax, valeurs, titre in zip(axes[ligne], [a, p], ["ACF", "PACF"]):
            ax.vlines(np.arange(1, 337), 0, valeurs[1:], linewidth=.8)
            ax.axhline(0, color="black", linewidth=.5)
            for retard in [24, 168]:
                ax.axvline(retard, color="grey", linestyle=":")
            ax.set(title=f"{titre} — {nom}", xlabel="Retard (heures)", ylim=(-1, 1))
    sauver(fig, "acf_pacf")

    fig, axes = plt.subplots(3, 1, figsize=(13, 10))
    for nom, s in differences.items():
        axes[0].plot(s.resample("MS").mean(), label=nom)
        axes[1].plot(s.groupby(s.index.hour).mean(), label=nom)
        a = acf(s, nlags=9000, fft=True)
        axes[2].plot(np.arange(8500, 9001), a[8500:], label=nom)
    axes[0].set(title="Moyenne mensuelle des differences", ylabel="MW")
    axes[1].set(title="Profil horaire moyen des differences", xlabel="Heure enregistree", ylabel="MW")
    axes[2].axvline(8736, color="grey", linestyle=":")
    axes[2].set(title="ACF autour de 364 jours", xlabel="Retard (heures)")
    for ax in axes:
        ax.legend()
        ax.grid(alpha=.2)
    sauver(fig, "profils_et_retard_annuel")

    fig, ax = plt.subplots(figsize=(11, 5))
    for nom in DECALAGES:
        s = details.loc[details.groupe.eq("annee") & details.methode.eq(nom)]
        ax.plot(s.valeur, s.RMSE_MW, marker="o", label=nom)
    ax.set(xlabel="Annee", ylabel="RMSE (MW)", title="Stabilite annuelle du decalage")
    ax.legend()
    sauver(fig, "comparaison_annuelle")

    ecrire_resume(SORTIE, "Difference a 364 jours",
                  "Comparaison de la meme heure et des references decalees de -1 h et +1 h. "
                  "Le decalage de 364 jours conserve le jour de semaine. "
                  "Les residus STL sont retrospectifs : ce ne sont pas des erreurs de prevision. "
                  "Voir ../../docs/04_difference_annuelle.md.", bilan.reset_index())


if __name__ == "__main__":
    main()
