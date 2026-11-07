"""AR(1), AR(2), MA(1), ARMA(1,1) : estimation et prevision J+1 sans meteo future."""
import hashlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from threadpoolctl import threadpool_limits

from benchmarks import NOMS, prevoir_benchmarks
from chemins_analyse import PROJET, RESULTATS

SORTIE = RESULTATS / "10_modeles_cours"
ORDRES = {"AR1": (1, 0), "AR2": (2, 0), "MA1": (0, 1), "ARMA11": (1, 1)}


def transformer(y):
    return y.diff(24).diff()


def reconstruire(z, historique):
    """Inverser (1-B)(1-B24), sans utiliser les observations apres la coupure."""
    valeurs = list(np.asarray(historique, dtype=float))
    for ecart in z:
        valeurs.append(float(ecart) + valeurs[-1] + valeurs[-24] - valeurs[-25])
    return np.asarray(valeurs[-len(z):])


def modele(z, p, q):
    # Echelle GW pour une optimisation numerique mieux conditionnee.
    return SARIMAX(np.asarray(z, dtype=float) / 1000, order=(p, 0, q),
                   trend="n", enforce_stationarity=True, enforce_invertibility=True)


def scores(g):
    erreur = g.observe - g.prevision
    return {"n": len(g), "MAE_MW": float(erreur.abs().mean()),
            "RMSE_MW": float(np.sqrt((erreur**2).mean())), "biais_MW": float(erreur.mean())}


def contexte(pred, d):
    """Diagnostics descriptifs de validation ; aucune selection du modele ici."""
    val = pred[pred.annee == 2024].merge(
        d[["jour_ferie", "weekend", "temperature_moyenne"]],
        left_on="horodatage", right_index=True, validate="many_to_one")
    val["saison"] = val.horodatage.dt.month.map({12:"hiver", 1:"hiver", 2:"hiver",
        3:"printemps", 4:"printemps", 5:"printemps", 6:"ete", 7:"ete", 8:"ete",
        9:"automne", 10:"automne", 11:"automne"})
    val["type_jour"] = np.where(val.jour_ferie.eq(1), "ferie",
                                 np.where(val.weekend.eq(1), "weekend non ferie", "semaine non feriee"))
    val["temperature"] = pd.cut(val.temperature_moyenne, [-np.inf, 5, 20, np.inf],
                                labels=["moins de 5 C", "5 a 20 C", "plus de 20 C"])
    lignes = []
    for critere in ("saison", "type_jour", "temperature"):
        for (nom, valeur), g in val.groupby(["modele", critere], observed=True):
            lignes.append({"modele": nom, "critere": critere, "groupe": valeur, **scores(g)})
    pd.DataFrame(lignes).to_csv(SORTIE / "scores_par_contexte_2024.csv", index=False)


def tracer_echecs(val, pires, choix):
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.2), sharey=True)
    for ax, jour in zip(axes, pires.jour):
        g = val[val.jour==jour]
        ref = g[g.modele==choix]
        ax.plot(ref.horodatage.dt.hour, ref.observe, color="black", label="Observe")
        for nom in [choix, "benchmark_semaine", "benchmark_4_semaines"]:
            s = g[g.modele==nom]
            ax.plot(s.horodatage.dt.hour, s.prevision, label=NOMS.get(nom, nom))
        ax.set(title=jour, xlabel="Heure locale", xticks=[0, 6, 12, 18, 23])
    axes[0].set_ylabel("MW")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", fontsize=9, ncol=4)
    fig.tight_layout(rect=(0, 0, 1, .88))
    fig.savefig(SORTIE / "trois_echecs.png", dpi=180)
    plt.close(fig)


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    test = PROJET / "data/merge/test.csv"
    empreinte = hashlib.sha256(test.read_bytes()).hexdigest()
    d = pd.concat([pd.read_csv(PROJET / f"data/merge/{f}.csv", parse_dates=["horodatage"])
                   for f in ("train", "validation")]).set_index("horodatage").sort_index()
    assert d.index.is_unique and d.index.to_series().diff().dropna().eq(pd.Timedelta(hours=1)).all()
    assert d.index.max() < pd.Timestamp("2025-01-01")
    # Garder toutes les lignes : masquer les deux jours de transition avant les differences.
    y = d.consommation_MW.mask(d.jour_changement_heure)
    z = transformer(y)
    # Controle exact de l'inversion sur une serie synthetique non periodique.
    exemple = pd.Series(np.arange(120, dtype=float)**2 + np.sin(np.arange(120)))
    np.testing.assert_allclose(reconstruire(transformer(exemple).iloc[50:80], exemple.iloc[25:50]),
                               exemple.iloc[50:80], atol=1e-8)
    predictions, ajustements, exclusions, diagnostics = [], [], [], []
    innovations = {}
    for annee in (2021, 2022, 2023, 2024):
        # Premiere origine : 31 decembre precedent a 14 h, coupure a 8 h.
        premier = pd.Timestamp(annee, 1, 1)
        coupure_initiale = premier - pd.Timedelta(hours=16)
        debut = coupure_initiale - pd.DateOffset(years=2) + pd.Timedelta(hours=1)
        apprentissage = z.loc[debut:coupure_initiale]
        fin = pd.Timestamp(annee, 12, 31, 23)
        complet = z.loc[debut:fin]
        fits = {}
        for nom, (p, q) in ORDRES.items():
            m = modele(apprentissage, p, q)
            fit = m.fit(disp=False, maxiter=300)
            assert fit.mle_retvals["converged"], (annee, nom, fit.mle_retvals)
            # Filtrage causal, jamais lissage : un etat ne depend que de son passe.
            filtre = modele(complet, p, q).filter(fit.params)
            fits[nom] = filtre
            ajustements.append({"annee": annee, "modele": nom, "debut": str(debut),
                "fin": str(coupure_initiale), "n_valides": int(apprentissage.count()),
                "AIC": fit.aic, "BIC": fit.bic, "convergence": True,
                "parametres": json.dumps(dict(zip(fit.param_names, fit.params.tolist())))})
            # Verifier que les donnees posterieures ne changent pas la prevision.
            i = len(apprentissage)
            attendu = fit.forecast(39)
            obtenu = filtre.get_prediction(start=i, end=i+38, dynamic=True).predicted_mean
            np.testing.assert_allclose(obtenu, attendu, rtol=1e-8, atol=1e-8)
            milieu = len(apprentissage) + 1000
            passe = modele(complet.iloc[:milieu], p, q).filter(fit.params)
            dynamique = filtre.get_prediction(start=milieu, end=milieu+38, dynamic=True).predicted_mean
            np.testing.assert_allclose(dynamique, passe.forecast(39), rtol=1e-8, atol=1e-8)
            # Innovations d'apprentissage : plus long bloc sans trou, apres amorcage.
            e = pd.Series(np.asarray(fit.resid) * 1000, index=apprentissage.index)
            e[apprentissage.isna()] = np.nan
            e.iloc[:168] = np.nan
            blocs = [g.dropna() for _, g in e.groupby(e.isna().cumsum()) if g.notna().any()]
            bloc = max(blocs, key=len)
            lb = acorr_ljungbox(bloc, lags=[24, 168], model_df=p+q, return_df=True)
            for lag, row in lb.iterrows():
                diagnostics.append({"annee": annee, "modele": nom, "retard": lag,
                    "n_bloc": len(bloc), "debut_bloc": str(bloc.index.min()),
                    "fin_bloc": str(bloc.index.max()), "statistique": row.lb_stat,
                    "p_value": row.lb_pvalue})
            if annee == 2024:
                innovations[nom] = bloc
        for jour in pd.date_range(premier, pd.Timestamp(annee, 12, 31), freq="D"):
            cibles = pd.date_range(jour, periods=24, freq="h")
            coupure = jour - pd.Timedelta(hours=16)
            historique = y.loc[coupure-pd.Timedelta(hours=24):coupure]
            references = prevoir_benchmarks(y, cibles, coupure)
            raison = None
            if y.reindex(cibles).isna().any():
                raison = "cible manquante ou changement heure"
            elif historique.isna().any():
                raison = "25 heures historiques incompletes"
            elif references is None:
                raison = "benchmark incomplet"
            if raison:
                exclusions.append({"jour": str(jour.date()), "raison": raison})
                continue
            i = complet.index.get_loc(coupure) + 1
            horizon = int((cibles[-1] - coupure) / pd.Timedelta(hours=1))
            for nom, filtre in fits.items():
                futur = filtre.get_prediction(start=i, end=i+horizon-1, dynamic=True).predicted_mean
                references[nom] = reconstruire(np.asarray(futur)*1000, historique)[-24:]
            for nom, prevision in references.items():
                assert np.isfinite(prevision).all()
                predictions.append(pd.DataFrame({"horodatage": cibles, "annee": annee,
                    "jour": str(jour.date()), "coupure": coupure, "modele": nom,
                    "observe": y.reindex(cibles).to_numpy(), "prevision": prevision}))
    pred = pd.concat(predictions, ignore_index=True)
    pred["erreur_MW"] = pred.observe - pred.prevision
    assert pred.groupby(["modele", "jour"]).size().eq(24).all()
    assert pred.groupby("modele").size().nunique() == 1
    pred.to_csv(SORTIE / "predictions.csv", index=False)
    contexte(pred, d)
    pd.DataFrame(ajustements).to_csv(SORTIE / "ajustements.csv", index=False)
    pd.DataFrame(exclusions).to_csv(SORTIE / "exclusions.csv", index=False)
    pd.DataFrame(diagnostics).to_csv(SORTIE / "ljung_box.csv", index=False)
    lignes = []
    periodes = {"interne_2021_2023": pred[pred.annee < 2024],
                "validation_2024": pred[pred.annee == 2024]}
    for periode, sous in periodes.items():
        for nom, groupe in sous.groupby("modele"):
            ligne = {"periode": periode, "modele": nom}
            ligne.update(scores(groupe))
            lignes.append(ligne)
    resume = pd.DataFrame(lignes)
    resume.to_csv(SORTIE / "scores.csv", index=False)
    annuel = pd.DataFrame([{"annee": a, "modele": nom, **scores(g)} for (a, nom), g in pred.groupby(["annee", "modele"])])
    annuel.to_csv(SORTIE / "scores_annuels.csv", index=False)
    choix = resume[(resume.periode == "interne_2021_2023") & resume.modele.isin(ORDRES)].sort_values("RMSE_MW").iloc[0].modele
    # Tableau LaTeX produit depuis les scores, sans recopier les nombres a la main.
    lignes = [r"\begin{tabular}{lrrr}", r"\toprule",
              r"Modele & RMSE 2021--2023 & MAE 2024 & RMSE 2024 \\", r"\midrule"]
    for nom in [*NOMS, *ORDRES]:
        interne = resume[(resume.periode == "interne_2021_2023") & (resume.modele == nom)].iloc[0]
        val = resume[(resume.periode == "validation_2024") & (resume.modele == nom)].iloc[0]
        lignes.append(f"{NOMS.get(nom, nom)} & {interne.RMSE_MW:.0f} & {val.MAE_MW:.0f} & {val.RMSE_MW:.0f}" + r" \\")
    lignes += [r"\bottomrule", r"\end{tabular}"]
    (SORTIE / "tableau_scores.tex").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    quotidien = []
    for (nom, jour), g in pred.groupby(["modele", "jour"]):
        quotidien.append({"modele": nom, "jour": jour, **scores(g),
            "erreur_energie_MWh": g.erreur_MW.sum(),
            "erreur_pointe_MW": g.observe.max()-g.prevision.max(),
            "erreur_heure_pointe": int(g.horodatage.loc[g.observe.idxmax()].hour)-int(g.horodatage.loc[g.prevision.idxmax()].hour)})
    quotidien = pd.DataFrame(quotidien)
    quotidien.to_csv(SORTIE / "scores_quotidiens.csv", index=False)
    controles = {"choix_sur_2021_2023": choix, "test_2025_sha256": empreinte,
        "inversion_verifiee": True, "filtrage_causal_verifie_16_ajustements": True,
        "jours_internes": int(len(pred[(pred.annee<2024)&(pred.modele==choix)])/24),
        "jours_2024": int(len(pred[(pred.annee==2024)&(pred.modele==choix)])/24)}
    assert hashlib.sha256(test.read_bytes()).hexdigest() == empreinte
    (SORTIE / "controles.json").write_text(json.dumps(controles, indent=2), encoding="utf-8")
    fig, axes = plt.subplots(4, 2, figsize=(12, 11))
    for (nom, e), ax in zip(innovations.items(), axes):
        plot_acf(e, lags=168, zero=False, ax=ax[0], title=f"ACF innovations - {nom}")
        plot_pacf(e, lags=168, zero=False, method="ywm", ax=ax[1], title=f"PACF innovations - {nom}")
    fig.tight_layout()
    fig.savefig(SORTIE / "acf_pacf_innovations.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3))
    plot_acf(innovations[choix], lags=168, zero=False, ax=axes[0], title=f"ACF innovations - {choix}")
    plot_pacf(innovations[choix], lags=168, zero=False, method="ywm", ax=axes[1], title=f"PACF innovations - {choix}")
    fig.tight_layout()
    fig.savefig(SORTIE / "acf_pacf_retenu.png", dpi=160)
    plt.close(fig)
    val = pred[pred.annee==2024]
    fig, ax = plt.subplots(figsize=(10, 4))
    for nom, g in val.groupby("modele"):
        g.erreur_MW.abs().groupby(g.horodatage.dt.hour).mean().plot(ax=ax, label=NOMS.get(nom, nom))
    ax.set(xlabel="Heure locale cible", ylabel="MAE (MW)", title="Validation 2024 : memes dates et coupure J8")
    ax.legend(ncol=2, fontsize=8)
    fig.tight_layout()
    fig.savefig(SORTIE / "erreurs_par_heure.png", dpi=160)
    plt.close(fig)
    pires = quotidien[(quotidien.modele==choix)&quotidien.jour.str.startswith("2024")].nlargest(3, "RMSE_MW")
    pires.to_csv(SORTIE / "trois_echecs.csv", index=False)
    tracer_echecs(val, pires, choix)


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
