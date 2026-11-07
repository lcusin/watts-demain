"""STL standard et robuste, aux trois echelles de l'exploration classique."""

import json
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import acf

from description import decomposer

from resume import ecrire_resume
from chemins_analyse import RESULTATS as DOSSIER, PROJET
SORTIE = DOSSIER / "03_stl"
SAISON = 7  # Nombre de cycles voisins pour lisser une meme position saisonniere.


def enregistrer(fig, nom):
    fig.tight_layout()
    fig.savefig(SORTIE / f"{nom}.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def indicateurs(erreur, echelle, methode, periode):
    return {"echelle": echelle, "methode": methode, "n": len(erreur),
            "MAE_MW": erreur.abs().mean(), "RMSE_MW": np.sqrt((erreur**2).mean()),
            "biais_MW": erreur.mean(), "ACF_1": erreur.autocorr(1),
            "ACF_periode": erreur.autocorr(periode)}


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    x = pd.read_csv(PROJET / "data/merge/train.csv", parse_dates=["horodatage"])
    assert x.horodatage.notna().all() and not x.horodatage.duplicated().any()
    y = x.set_index("horodatage").consommation_MW.sort_index()
    assert y.index.equals(pd.date_range(y.index.min(), y.index.max(), freq="h"))
    assert np.isfinite(y).all()
    mensuel = y.resample("MS").mean()
    echelles = {"journalier": (y, y.index.hour, 24),
                "hebdomadaire": (y, y.index.dayofweek * 24 + y.index.hour, 168),
                "annuel": (mensuel, mensuel.index.month, 12)}
    scores, parametres = [], []
    for echelle, (serie, groupes, periode) in echelles.items():
        # Meme support que la decomposition classique, qui perd les bords.
        dates = serie.index[periode // 2:-periode // 2]
        erreurs = {}
        for estimateur in ["mean", "median"]:
            classique, _ = decomposer(serie, groupes, periode, "additive", estimateur)
            erreur = classique.loc[dates, "erreur_MW"]
            scores.append(indicateurs(erreur, echelle, f"classique_{estimateur}", periode))
            if estimateur == "mean":
                erreurs["Classique (moyenne)"] = erreur
        for robuste in [False, True]:
            nom = "robuste" if robuste else "standard"
            debut_calcul = time.perf_counter()
            modele = STL(serie, period=periode, seasonal=SAISON, robust=robuste,
                         seasonal_deg=1, trend_deg=1, low_pass_deg=1,
                         seasonal_jump=1, trend_jump=1, low_pass_jump=1)
            # Iterations explicites : meme nombre interne pour isoler la robustesse.
            resultat = modele.fit(inner_iter=2, outer_iter=15 if robuste else 0)
            d = pd.DataFrame({"consommation_MW": serie, "tendance_cycle_MW": resultat.trend,
                "saisonnalite_MW": resultat.seasonal, "residu_MW": resultat.resid,
                "sans_tendance_MW": serie - resultat.trend,
                "desaisonnalisee_MW": serie - resultat.seasonal,
                "poids_robuste": resultat.weights})
            np.testing.assert_allclose(d.tendance_cycle_MW + d.saisonnalite_MW + d.residu_MW,
                                       serie, rtol=1e-12)
            assert np.isfinite(d).all().all()
            assert d.poids_robuste.between(0, 1).all()
            d.to_csv(SORTIE / f"composantes_{echelle}_{nom}.csv", index_label="horodatage")
            erreur = d.loc[dates, "residu_MW"]
            erreurs[f"STL {nom}"] = erreur
            scores.append(indicateurs(erreur, echelle, f"STL_{nom}", periode))
            parametres.append({"echelle": echelle, "variante": nom, **modele.config,
                "inner_iter": 2, "outer_iter": 15 if robuste else 0,
                "secondes": time.perf_counter() - debut_calcul,
                "fraction_poids_inferieur_05": float(d.poids_robuste.lt(.5).mean())})

            z = d if echelle == "annuel" else d.loc["2019-01-07":"2019-01-27"]
            fig, axes = plt.subplots(5, 1, figsize=(13, 10), sharex=True)
            axes[0].plot(z.index, z.consommation_MW, label="Observée", lw=.8)
            axes[0].plot(z.index, z.tendance_cycle_MW, label="Tendance-cycle", lw=1.3)
            axes[0].legend()
            for ax, colonne, titre in zip(axes[1:],
                    ["sans_tendance_MW", "saisonnalite_MW", "desaisonnalisee_MW", "residu_MW"],
                    ["Sans tendance", "Saisonnalité", "Désaisonnalisée", "Résidu"]):
                ax.plot(z.index, z[colonne], lw=.9)
                ax.set_ylabel(titre + "\n(MW)")
                if colonne != "desaisonnalisee_MW":
                    ax.axhline(0, color="gray", ls="--", lw=.6)
            axes[0].set(title=f"STL {nom} — {echelle}", ylabel="Consommation\n(MW)")
            for ax in axes:
                ax.grid(alpha=.15)
            enregistrer(fig, f"decomposition_{echelle}_{nom}")

            # Montrer que le profil saisonnier peut changer au fil des annees.
            profils = d.saisonnalite_MW.groupby([serie.index.year, groupes]).mean().unstack(0)
            fig, ax = plt.subplots(figsize=(12, 4))
            couleurs = plt.get_cmap("tab20")(np.linspace(0, 1, profils.shape[1]))
            for couleur, annee in zip(couleurs, profils.columns):
                ax.plot(profils.index, profils[annee], label=str(annee), color=couleur, lw=.9)
            ax.set(title=f"Saisonnalité STL {nom} par année — {echelle}", ylabel="MW",
                   xlabel="Mois" if echelle == "annuel" else "Heure" if echelle == "journalier" else "Heure de semaine (lundi = 0)")
            ax.legend(ncol=4, fontsize=8)
            enregistrer(fig, f"profils_{echelle}_{nom}")

        fig, ax = plt.subplots(figsize=(12, 4))
        for nom, erreur in erreurs.items():
            valeurs = acf(erreur, nlags=36 if echelle == "annuel" else 336, fft=True)
            ax.plot(range(1, len(valeurs)), valeurs[1:], label=nom)
        ax.axhline(0, color="gray", lw=.7)
        ax.set(title=f"ACF des résidus — {echelle}, mêmes dates", ylabel="ACF",
               xlabel="Retard (mois)" if echelle == "annuel" else "Retard (heures)")
        ax.legend()
        enregistrer(fig, f"acf_{echelle}")
        # Sauvegarde progressive pour pouvoir suivre les essais longs.
        pd.DataFrame(scores).to_csv(SORTIE / "comparaison.csv", index=False)
        (SORTIE / "parametres.json").write_text(json.dumps(parametres, indent=2), encoding="utf-8")

    ecrire_resume(SORTIE, "Comparaison STL",
                  "STL standard et robuste, compares aux moyennes mobiles sur les memes dates. "
                  "Les trois echelles sont des experiences independantes. "
                  "Le lissage utilise le futur : ces scores sont descriptifs. "
                  "Voir ../../docs/03_stl.md.", pd.DataFrame(scores))


if __name__ == "__main__":
    main()
