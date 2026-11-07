"""Description et decomposition classique de la consommation, sur train uniquement."""


import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import acf

from resume import ecrire_resume
from chemins_analyse import PROJET, CLASSIQUE
FIGURES = CLASSIQUE / "graphiques"
TABLEAUX = CLASSIQUE / "tableaux"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def sauver_figure(fig, nom):
    fig.tight_layout()
    fig.savefig(FIGURES / nom, dpi=180, bbox_inches="tight")
    plt.close(fig)


def moyenne_mobile(y, periode):
    # Pour une periode paire : moyenne centree 2 x periode, demi-poids aux extremites.
    if periode % 2:
        return y.rolling(periode, center=True).mean()
    k = periode // 2
    return (y.rolling(periode + 1, center=True).sum()
            - (y.shift(k) + y.shift(-k)) / 2) / periode


def decomposer(y, groupes, periode, modele, estimateur):
    tendance = moyenne_mobile(y, periode)
    if modele == "additive":
        sans_tendance = y - tendance
    else:
        assert y.gt(0).all()
        sans_tendance = y / tendance
    # Comparer les memes heures, heures de semaine ou mois du calendrier.
    coefficients = sans_tendance.groupby(groupes).agg(estimateur)
    if modele == "additive":
        coefficients -= coefficients.mean()
    else:
        coefficients /= coefficients.mean()
    saison = pd.Series(groupes.map(coefficients), index=y.index, dtype=float)
    if modele == "additive":
        ajuste = y - saison
        residu = sans_tendance - saison
        explique = tendance + saison
    else:
        ajuste = y / saison
        residu = sans_tendance / saison
        explique = tendance * saison
    resultat = pd.DataFrame({"consommation_MW": y, "tendance_cycle_MW": tendance,
        "sans_tendance": sans_tendance, "saisonnalite": saison,
        "desaisonnalisee_MW": ajuste, "residu": residu,
        "ajustement_MW": explique, "erreur_MW": y - explique})
    # Verifier les identites de reconstruction et le centrage des coefficients.
    reconstruit = tendance + saison + residu if modele == "additive" else tendance * saison * residu
    valides = tendance.notna()
    np.testing.assert_allclose(reconstruit[valides], y[valides], rtol=1e-12)
    np.testing.assert_allclose(coefficients.mean(), 0 if modele == "additive" else 1, atol=1e-10)
    assert resultat.erreur_MW.notna().equals(valides)
    return resultat, coefficients


def main():
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLEAUX.mkdir(parents=True, exist_ok=True)
    # 1. Lire et verifier les heures sans remplir ni supprimer de valeurs.
    x = pd.read_csv(PROJET / "data/merge/train.csv", parse_dates=["horodatage"])
    assert not x.horodatage.duplicated().any() and x.horodatage.notna().all()
    x = x.set_index("horodatage").sort_index()
    y = x.consommation_MW.astype(float)
    assert y.index.equals(pd.date_range(y.index.min(), y.index.max(), freq="h"))
    assert np.isfinite(y).all() and y.gt(0).all()
    quotidien = y.resample("D").mean()
    mensuel = y.resample("MS").mean()
    annuel = y.groupby(y.index.year).agg(["count", "mean", "median", "min", "max", "std"])
    annuel.to_csv(TABLEAUX / "bilan_annuel.csv", index_label="annee")

    # 2. Graphiques simples : niveau, profils, distribution et amplitude.
    fig, axes = plt.subplots(2, 1, figsize=(12, 7))
    axes[0].plot(quotidien.index, quotidien, lw=.6, alpha=.5, label="Moyenne quotidienne")
    axes[0].plot(mensuel.index, mensuel, lw=1.4, label="Moyenne mensuelle")
    axes[0].set(title="Consommation électrique — apprentissage 2012–2023", ylabel="MW")
    axes[0].legend()
    axes[1].plot(annuel.index, annuel["mean"], "o-")
    axes[1].set(title="Moyenne annuelle (niveau observé, sans correction météo)", xlabel="Année", ylabel="MW")
    sauver_figure(fig, "01_evolution.png")

    jours = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for ouvrable, nom in [(True, "Lundi à vendredi"), (False, "Samedi et dimanche")]:
        s = y[(y.index.dayofweek < 5) == ouvrable]
        axes[0].plot(s.groupby(s.index.hour).mean(), label=nom)
    axes[0].set(title="Profil horaire moyen", xlabel="Heure enregistrée", ylabel="MW")
    axes[0].legend(fontsize=8)
    axes[1].bar(jours, y.groupby(y.index.dayofweek).mean())
    axes[1].set(title="Profil hebdomadaire moyen", ylabel="MW")
    couleurs = plt.get_cmap("tab20")(np.linspace(0, 1, mensuel.index.year.nunique()))
    for couleur, (annee, s) in zip(couleurs, mensuel.groupby(mensuel.index.year)):
        axes[2].plot(s.index.month, s, label=str(annee), color=couleur, lw=1)
    axes[2].set(title="Profil annuel par année", xlabel="Mois", ylabel="MW", xticks=[1, 3, 6, 9, 12])
    axes[2].legend(ncol=3, fontsize=7)
    sauver_figure(fig, "02_profils_saisonniers.png")

    profils = y.groupby([y.index.dayofweek, y.index.hour]).mean().unstack()
    fig, ax = plt.subplots(figsize=(11, 4))
    im = ax.imshow(profils, aspect="auto", cmap="viridis")
    ax.set(title="Consommation moyenne selon le jour et l’heure", xlabel="Heure enregistrée",
           yticks=range(7), yticklabels=jours, xticks=range(0, 24, 2))
    fig.colorbar(im, ax=ax, label="MW")
    sauver_figure(fig, "03_jour_heure.png")

    amplitudes = y.resample("D").agg(["mean", "min", "max"])
    amplitudes["amplitude"] = amplitudes["max"] - amplitudes["min"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].hist(y, bins=60, color="#007f99")
    axes[0].set(title="Distribution des consommations horaires", xlabel="MW", ylabel="Nombre d’heures")
    axes[1].scatter(amplitudes["mean"], amplitudes.amplitude, s=5, alpha=.2)
    axes[1].set(title="Amplitude quotidienne et niveau", xlabel="Moyenne quotidienne (MW)", ylabel="Maximum − minimum (MW)")
    sauver_figure(fig, "04_distribution_amplitude.png")

    # 3. Trois echelles independantes, et quatre variantes par echelle.
    echelles = {"journalier": (y, y.index.hour, 24, "Heure"),
                "hebdomadaire": (y, y.index.dayofweek * 24 + y.index.hour, 168, "Heure de semaine (0 = lundi 00 h)"),
                "annuel": (mensuel, mensuel.index.month, 12, "Mois")}
    scores = []
    for echelle, (serie, groupes, periode, unite) in echelles.items():
        fig_coef, axes_coef = plt.subplots(2, 1, figsize=(12, 6))
        fig_acf, ax_acf = plt.subplots(figsize=(12, 4))
        for modele, ax_coef in zip(["additive", "multiplicative"], axes_coef):
            fig, axes = plt.subplots(5, 1, figsize=(13, 11), sharex=True)
            # Zoom identique sur les deux echelles horaires, serie entiere pour l'annuel.
            debut = serie.index.min() if echelle == "annuel" else pd.Timestamp("2019-01-07")
            fin = serie.index.max() if echelle == "annuel" else pd.Timestamp("2019-01-28")
            for estimateur in ["mean", "median"]:
                nom = f"{echelle}_{modele}_{estimateur}"
                d, coef = decomposer(serie, groupes, periode, modele, estimateur)
                d.to_csv(TABLEAUX / f"{nom}.csv", index_label="horodatage")
                coef.to_csv(TABLEAUX / f"coefficients_{nom}.csv", index_label="saison", header=["coefficient"])
                z = d.loc[debut:fin]
                if estimateur == "mean":
                    axes[0].plot(z.index, z.consommation_MW, label="Observée", lw=.8)
                    axes[0].plot(z.index, z.tendance_cycle_MW, label="Tendance-cycle", lw=1.5)
                    axes[1].plot(z.index, z.sans_tendance, lw=.8)
                for ax, colonne in zip(axes[2:], ["saisonnalite", "desaisonnalisee_MW", "residu"]):
                    ax.plot(z.index, z[colonne], label=estimateur, lw=1)
                ax_coef.plot(coef.index, coef, label=estimateur)
                erreur = d.erreur_MW.dropna()
                # Comparer les variantes dans la meme unite, pas MW contre ratios.
                scores.append({"echelle": echelle, "modele": modele, "estimateur": estimateur,
                    "n_valides": len(erreur), "n_bords_non_estimes": int(d.erreur_MW.isna().sum()),
                    "MAE_descriptive_MW": erreur.abs().mean(), "RMSE_descriptive_MW": np.sqrt((erreur**2).mean()),
                    "biais_MW": erreur.mean(), "acf_erreur_lag1": erreur.autocorr(1),
                    "acf_erreur_periode": erreur.autocorr(periode)})
                correlations = acf(erreur, nlags=36 if echelle == "annuel" else 336, fft=True)
                ax_acf.plot(range(1, len(correlations)), correlations[1:], label=f"{modele}, {estimateur}", lw=1)
            ratio = modele == "multiplicative"
            axes[0].set_title(f"Décomposition {modele} — {echelle} (moyenne et médiane)")
            for ax, label in zip(axes, ["Observée et\ntendance-cycle (MW)", "Sans tendance\n" + ("(ratio)" if ratio else "(MW)"),
                                      "Saisonnalité\n" + ("(facteur)" if ratio else "(MW)"), "Désaisonnalisée\n(MW)",
                                      "Résidu\n" + ("(ratio)" if ratio else "(MW)")]):
                ax.set_ylabel(label)
                ax.grid(alpha=.15)
            for ax in [axes[1], axes[2], axes[4]]:
                ax.axhline(1 if ratio else 0, color="gray", ls="--", lw=.7)
            for ax in [axes[0], axes[2], axes[3], axes[4]]:
                ax.legend(fontsize=8, loc="upper right")
            sauver_figure(fig, f"05_decomposition_{echelle}_{modele}.png")
            ax_coef.set(title=f"Coefficients saisonniers — {modele}", ylabel="Facteur" if ratio else "MW", xlabel=unite)
            ax_coef.axhline(1 if ratio else 0, color="gray", ls="--", lw=.7)
            ax_coef.legend()
        sauver_figure(fig_coef, f"06_coefficients_{echelle}.png")
        ax_acf.axhline(0, color="gray", lw=.7)
        ax_acf.set(title=f"Autocorrélation de l’erreur en MW — {echelle}", xlabel="Retard (mois)" if echelle == "annuel" else "Retard (heures)", ylabel="ACF")
        ax_acf.legend(fontsize=8)
        sauver_figure(fig_acf, f"07_acf_{echelle}.png")
    scores = pd.DataFrame(scores)
    scores.to_csv(TABLEAUX / "comparaison_descriptive.csv", index=False)

    ecrire_resume(CLASSIQUE, "Decompositions classiques",
                  "Comparaison sur le train uniquement, aux memes dates par echelle. "
                  "Les scores mesurent un ajustement retrospectif, pas une prevision. "
                  "Les echelles horaire et mensuelle ne sont pas directement comparables. "
                  "Voir ../../docs/01_classique.md.", scores)


if __name__ == "__main__":
    main()
