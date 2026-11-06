"""Decomposition explicative puis dynamique causale ; validation chronologique.
python src/comparer_bruit_blanc.py
python src/comparer_bruit_blanc.py --confirmation
"""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd
from scipy.stats import chi2
from sklearn.linear_model import Ridge
from statsmodels.tsa.stattools import acf, acovf, levinson_durbin
from modele_decomposition import matrices

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "results/decomposition_bruit_blanc"
SORTIE.mkdir(parents=True, exist_ok=True)
STRUCTURES = ["seuils", "splines", "enrichi", "enrichi_3ans"]
RETARDS = {
    "sans_AR": [], "AR1": [1], "AR24": list(range(1, 25)),
    "AR_cible": sorted(set(list(range(1, 25)) + [48, 72, 96, 120, 144] + list(range(168, 192)) + [336])),
    "AR168": list(range(1, 169)), "AR336": list(range(1, 337)),
}


def charger(nom):
    return pd.read_csv(RACINE / f"data/merge/{nom}.csv", parse_dates=["horodatage"]).set_index("horodatage").sort_index()


def enrichir(X, x):
    # Profil horaire et hebdomadaire variable avec la saison, calendrier et meteo.
    ajouts = {}
    for h in range(24):
        indicatrice = (x.index.hour == h).astype(float)
        ajouts[f"calendrier_ferie_{h}"] = x.jour_ferie * indicatrice
        if h > 0:
            ajouts[f"temperature_heure_{h}"] = X.temperature_froid * indicatrice
            for k in (1, 2):
                for onde in ("sin", "cos"):
                    ajouts[f"interaction_heure_{h}_{onde}_{k}"] = indicatrice * X[f"annuel_{onde}_{k}"]
    for jour in range(1, 7):
        for onde in ("sin", "cos"):
            ajouts[f"interaction_jour_{jour}_{onde}"] = (x.index.dayofweek == jour) * X[f"annuel_{onde}_1"]
    for v in ["vacances_A", "vacances_B", "vacances_C", "jour_changement_heure"]:
        ajouts["calendrier_" + v] = x[v].astype(float)
    return pd.concat([X, pd.DataFrame(ajouts, index=x.index)], axis=1)


def structure(train, valid, nom):
    if nom == "enrichi_3ans":
        train = train[train.index >= valid.index[0] - pd.DateOffset(years=3)]
    methode = "splines" if nom == "splines" else "seuils"
    X, V = matrices(train, valid, methode)
    if nom.startswith("enrichi"):
        X, V = enrichir(X, train), enrichir(V, valid)
    beta = np.linalg.lstsq(X, train.consommation_MW, rcond=None)[0]
    return train, X, V, beta


def corriger_ar(res_train, res_valid, retards):
    if not retards:
        return np.zeros(len(res_valid)), None
    r = pd.concat([res_train, res_valid])
    decalages = pd.DataFrame({k: r.shift(k) for k in retards})
    debut, fin = max(retards), len(res_train)
    echelle = res_train.std()
    modele = Ridge(alpha=10).fit(decalages.iloc[debut:fin] / echelle, res_train.iloc[debut:] / echelle)
    correction = modele.predict(decalages.iloc[fin:] / echelle) * echelle
    return correction, modele


def diagnostic(erreur):
    e = np.asarray(erreur)
    n = len(e)
    a = acf(e, nlags=336, fft=True)[1:]
    p = levinson_durbin(acovf(e, fft=True, nlag=336), nlags=336, isacov=True)[2][1:]
    q = n * (n + 2) * np.cumsum(a ** 2 / (n - np.arange(1, 337)))
    carre = acf(e ** 2, nlags=24, fft=True)[1:]
    q2 = n * (n + 2) * np.sum(carre ** 2 / (n - np.arange(1, 25)))
    d = {"n": n, "MAE_MW": np.mean(abs(e)), "RMSE_MW": np.sqrt(np.mean(e ** 2)),
         "biais_MW": np.mean(e), "score_dependance": np.mean(a ** 2 + p ** 2),
         "max_ACF": np.max(abs(a)), "max_PACF": np.max(abs(p)),
         "fraction_ACF_hors95": np.mean(abs(a) > 1.96 / np.sqrt(n)),
         "ACF_24h": a[23], "ACF_168h": a[167], "LB_carres_24_p": chi2.sf(q2, 24)}
    for k in (24, 168, 336):
        d[f"LB_{k}_p"] = chi2.sf(q[k - 1], k)
    return d


def comparer():
    x = charger("train")
    scores, erreurs = [], []
    for annee in (2021, 2022, 2023):
        passe, valid = x[x.index.year < annee], x[x.index.year == annee]
        for nom in STRUCTURES:
            train, X, V, beta = structure(passe, valid, nom)
            r_train = train.consommation_MW - X.dot(beta)
            r_valid = valid.consommation_MW - V.dot(beta)
            for ar, retards in RETARDS.items():
                correction, _ = corriger_ar(r_train, r_valid, retards)
                e = r_valid - correction
                methode = nom + "__" + ar
                scores.append({"annee": annee, "methode": methode, **diagnostic(e)})
                erreurs.append(pd.DataFrame({"horodatage": valid.index, "methode": methode, "erreur_MW": e.to_numpy()}))
    scores = pd.DataFrame(scores)
    scores.to_csv(SORTIE / "scores_par_annee.csv", index=False)
    pd.concat(erreurs).to_csv(SORTIE / "erreurs_internes.csv", index=False)
    classement = scores.groupby("methode")[["score_dependance", "MAE_MW", "RMSE_MW", "max_ACF", "max_PACF"]].mean()
    # Ne pas choisir une serie decorrelee au prix d'une forte degradation de precision.
    classement["admissible"] = classement.RMSE_MW <= 1.10 * classement.RMSE_MW.min()
    classement = classement.sort_values(["admissible", "score_dependance", "RMSE_MW"], ascending=[False, True, True])
    classement.to_csv(SORTIE / "classement.csv")
    (SORTIE / "choix.json").write_text(json.dumps({"methode": classement.index[0], "critere": "dependance ACF/PACF sous contrainte RMSE +10%"}, indent=2), encoding="utf-8")


def confirmer():
    choix = json.loads((SORTIE / "choix.json").read_text(encoding="utf-8"))["methode"]
    nom, ar = choix.split("__")
    passe, valid = charger("train"), charger("validation")
    train, X, V, beta = structure(passe, valid, nom)
    r_train = train.consommation_MW - X.dot(beta)
    r_valid = valid.consommation_MW - V.dot(beta)
    correction, modele = corriger_ar(r_train, r_valid, RETARDS[ar])
    e = r_valid - correction
    resultat = pd.DataFrame({"consommation_MW": valid.consommation_MW})
    groupes = {
        "niveau_tendance": [v for v in V if v == "constante" or v.startswith("tendance")],
        "cycle_annuel": [v for v in V if v.startswith("annuel_")],
        "profil_semaine": [v for v in V if v.startswith("semaine_")],
        "interactions_saisonnieres": [v for v in V if v.startswith("interaction_")],
        "effet_temperature": [v for v in V if v.startswith("temperature_")],
        "effet_pluie": ["pluie"],
        "effet_calendrier": [v for v in V if v.startswith("calendrier_")],
        "controle_imputation": [v for v in V if v.startswith("imputation_")],
    }
    coefficients = pd.Series(beta, index=V.columns)
    for composante, colonnes in groupes.items():
        resultat[composante] = V[colonnes].dot(coefficients[colonnes])
    profil = np.r_[0, coefficients[[f"semaine_{h}" for h in range(1, 168)]]].reshape(7, 24)
    resultat["cycle_journalier"] = profil.mean(axis=0)[valid.index.hour]
    resultat["cycle_hebdomadaire"] = resultat.pop("profil_semaine") - resultat["cycle_journalier"]
    resultat["residu_explicatif"] = r_valid
    resultat["correction_AR"] = correction
    resultat["innovation"] = e
    resultat.to_csv(SORTIE / "decomposition_validation_2024.csv", index_label="horodatage")
    pd.DataFrame([{"methode": nom + "__sans_AR", **diagnostic(r_valid)},
                  {"methode": choix, **diagnostic(e)}]).to_csv(SORTIE / "confirmation_2024.csv", index=False)
    coefficients.to_csv(SORTIE / "coefficients_structure.csv", index_label="variable")
    if modele is not None:
        pd.Series(modele.coef_, index=RETARDS[ar]).to_csv(SORTIE / "coefficients_AR.csv", index_label="retard")
    tracer(resultat, choix)


def tracer(r, choix):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from statsmodels.graphics.tsaplots import plot_acf
    noms = ["consommation_MW", "residu_explicatif", "innovation"]
    fig, axes = plt.subplots(3, 2, figsize=(14, 10))
    for ligne, v in enumerate(noms):
        plot_acf(r[v], lags=336, fft=True, zero=False, ax=axes[ligne, 0], title="ACF - " + v)
        p = levinson_durbin(acovf(r[v], fft=True, nlag=336), nlags=336, isacov=True)[2][1:]
        ax = axes[ligne, 1]
        ax.vlines(np.arange(1, 337), 0, p)
        ax.axhline(0, color="black", linewidth=.5)
        seuil = 1.96 / np.sqrt(len(r))
        ax.axhspan(-seuil, seuil, alpha=.2)
        ax.set_title("PACF - " + v)
        if ligne == 2:
            limite = max(.1, 1.1 * max(abs(p)))
            ax.set_ylim(-limite, limite)
            limite_acf = max(.1, 1.1 * max(abs(acf(r[v], nlags=336, fft=True)[1:])))
            axes[ligne, 0].set_ylim(-limite_acf, limite_acf)
        for ax in axes[ligne]:
            ax.set_xlabel("Retard (heures)")
            for k in (24, 168):
                ax.axvline(k, color="grey", linestyle=":")
    fig.suptitle("Confirmation 2024 - " + choix)
    fig.tight_layout()
    fig.savefig(SORTIE / "01_acf_pacf_confirmation.png", dpi=160)
    plt.close(fig)
    colonnes = ["consommation_MW", "niveau_tendance", "cycle_annuel", "effet_temperature", "effet_pluie", "effet_calendrier", "correction_AR", "innovation"]
    axes = r[colonnes].resample("D").mean().plot(subplots=True, figsize=(14, 16), legend=False)
    for ax, v in zip(axes, colonnes):
        ax.set_title(v)
        ax.set_ylabel("MW")
    plt.tight_layout()
    plt.savefig(SORTIE / "02_composantes_2024.png", dpi=160)
    plt.close()
    fig, axes = plt.subplots(2, 1, figsize=(13, 7))
    r.innovation.plot(ax=axes[0], linewidth=.5, title="Innovations horaires 2024")
    r.innovation.resample("MS").std().plot(ax=axes[1], marker="o", title="Ecart-type mensuel des innovations")
    for ax in axes:
        ax.set_ylabel("MW")
    fig.tight_layout()
    fig.savefig(SORTIE / "03_stabilite_innovations.png", dpi=160)
    plt.close(fig)
    colonnes = ["consommation_MW", "niveau_tendance", "cycle_annuel", "cycle_journalier",
                "cycle_hebdomadaire", "effet_temperature", "effet_pluie", "correction_AR", "innovation"]
    axes = r[colonnes].iloc[24 * 31:24 * 59].plot(subplots=True, figsize=(14, 18), legend=False)
    for ax, v in zip(axes, colonnes):
        ax.set_title(v)
        ax.set_ylabel("MW")
    plt.tight_layout()
    plt.savefig(SORTIE / "04_decomposition_horaire.png", dpi=160)
    plt.close()


if __name__ == "__main__":
    if "--confirmation" in sys.argv:
        confirmer()
    else:
        comparer()
