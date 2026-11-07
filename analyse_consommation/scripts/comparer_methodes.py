"""Comparer les decompositions et combinaisons sur un support commun (train)."""
from itertools import combinations


import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import chi2
from statsmodels.tsa.stattools import acf, levinson_durbin

from description import moyenne_mobile
from resume import ecrire_resume
from chemins_analyse import RESULTATS as DOSSIER, PROJET, CLASSIQUE
SORTIE = DOSSIER / "05_comparaison"


def lire(fichier, colonne):
    x = pd.read_csv(fichier, index_col=0, parse_dates=True)
    return x[colonne]


def comparer(series, nom, retards, unite):
    # Aucun trou interne supprime : les bords seuls definissent le support commun.
    x = pd.DataFrame(series).dropna()
    frequence = "h" if unite == "heures" else "MS"
    assert x.index.equals(pd.date_range(x.index.min(), x.index.max(), freq=frequence))
    assert np.isfinite(x).all().all()
    mesures, correlations = [], []
    courbes = {}
    for methode, s in x.items():
        a = acf(s, nlags=retards, fft=True)
        p = levinson_durbin(a, nlags=retards, isacov=True)[2]
        courbes[methode] = (a, p)
        n = len(s)
        q = n * (n + 2) * np.sum(a[1:]**2 / (n - np.arange(1, retards + 1)))
        mesures.append({"methode": methode, "n": n, "debut": x.index.min(),
                        "fin": x.index.max(), "moyenne": s.mean(), "ecart_type": s.std(),
                        "ACF_1": a[1], "moyenne_ACF_carree": np.mean(a[1:]**2),
                        "max_ACF_absolue": np.max(np.abs(a[1:])),
                        "Ljung_Box_Q": q, "Ljung_Box_p_indicatif": chi2.sf(q, retards)})
        correlations.extend({"methode": methode, "retard": k, "ACF": a[k], "PACF": p[k]}
                            for k in range(retards + 1))
    bilan = pd.DataFrame(mesures).sort_values("moyenne_ACF_carree")
    bilan.to_csv(SORTIE / f"indicateurs_{nom}.csv", index=False)
    pd.DataFrame(correlations).to_csv(SORTIE / f"correlations_{nom}.csv", index=False)
    # Un nombre limite de lignes par image, pour garder les graphes lisibles.
    noms = list(x.columns)
    for debut in range(0, len(noms), 4):
        page = noms[debut:debut + 4]
        fig, axes = plt.subplots(len(page), 2, figsize=(15, 3 * len(page)), squeeze=False)
        for ligne, methode in enumerate(page):
            for ax, v, titre in zip(axes[ligne], courbes[methode], ["ACF", "PACF"]):
                ax.vlines(range(1, retards + 1), 0, v[1:], linewidth=.8)
                ax.axhline(0, color="black", linewidth=.5)
                for k in ([24, 168] if unite == "heures" else [12, 24]):
                    ax.axvline(k, color="grey", linestyle=":")
                ax.set(title=f"{titre} : {methode}", ylim=(-1, 1), xlabel=f"Retard ({unite})")
        fig.suptitle(f"{nom} — memes dates : {x.index.min():%Y-%m-%d} / {x.index.max():%Y-%m-%d}")
        fig.tight_layout(rect=(0, 0, 1, .97))
        fig.savefig(SORTIE / f"acf_pacf_{nom}_{debut // 4 + 1:02}.png", dpi=160)
        plt.close(fig)
    return bilan


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    y = lire(PROJET / "data/merge/train.csv", "consommation_MW")
    assert y.index.is_unique and np.isfinite(y).all()
    assert y.index.equals(pd.date_range(y.index.min(), y.index.max(), freq="h"))
    # Version horaire centree 2 x 8760 : demi-poids aux deux extremites.
    tendance = moyenne_mobile(y, 365 * 24)
    bases = {"brute": y, "sans_tendance_365j": y - tendance}
    horaires = dict(bases)
    registre = [{"methode": nom, "famille": "base", "definition": nom} for nom in bases]
    # Chaque sous-ensemble est unique : les differences a retards fixes commutent.
    for base, serie in bases.items():
        for nombre in [1, 2, 3]:
            for retards in combinations([8736, 24, 1], nombre):
                s = serie.copy()
                for retard in retards:
                    s = s.diff(retard)
                nom = base + "_D" + "_D".join(map(str, retards))
                horaires[nom] = s
                registre.append({"methode": nom, "famille": "differences",
                                 "definition": f"Base {base} ; differences {retards} heures"})
    for echelle in ["journalier", "hebdomadaire"]:
        for modele in ["additive", "multiplicative"]:
            for estimateur in ["mean", "median"]:
                nom = f"classique_{echelle}_{modele}_{estimateur}"
                # Residus natifs : MW en additif, ratios en multiplicatif.
                horaires[nom] = lire(CLASSIQUE / "tableaux" / f"{echelle}_{modele}_{estimateur}.csv", "residu")
                registre.append({"methode": nom, "famille": "classique", "definition": "Residu natif"})
        for methode in ["standard", "robuste"]:
            nom = f"STL_{echelle}_{methode}"
            fichier = DOSSIER / "03_stl" / f"composantes_{echelle}_{methode}.csv"
            horaires[nom] = lire(fichier, "residu_MW")
            horaires[nom + "_D1"] = horaires[nom].diff()
            registre.extend([{"methode": nom, "famille": "STL", "definition": "Residu STL"},
                             {"methode": nom + "_D1", "famille": "STL", "definition": "Difference 1 h du residu STL"}])
            # Remplacer la tendance courte STL par la tendance longue ; ne pas les cumuler.
            nom_long = f"MM365j_saison_STL_{echelle}_{methode}"
            horaires[nom_long] = y - tendance - lire(fichier, "saisonnalite_MW")
            registre.append({"methode": nom_long, "famille": "combinaison",
                             "definition": "Consommation - MM365j - saisonnalite STL (tendance STL non retiree)"})
    bilan = comparer(horaires, "horaire", 336, "heures")

    # Les decompositions annuelles sur moyennes mensuelles restent a part.
    mensuels = {"brute_mensuelle": y.resample("MS").mean()}
    for modele in ["additive", "multiplicative"]:
        for estimateur in ["mean", "median"]:
            nom = f"classique_annuel_{modele}_{estimateur}"
            mensuels[nom] = lire(CLASSIQUE / "tableaux" / f"annuel_{modele}_{estimateur}.csv", "residu")
    for methode in ["standard", "robuste"]:
        mensuels[f"STL_annuel_{methode}"] = lire(DOSSIER / "03_stl" / f"composantes_annuel_{methode}.csv", "residu_MW")
    comparer(mensuels, "mensuel", 36, "mois")
    pd.DataFrame(registre).to_csv(SORTIE / "methodes_horaires.csv", index=False)
    ecrire_resume(SORTIE, "Comparaison des decompositions",
                  f"{len(horaires)} variantes horaires et {len(mensuels)} mensuelles. "
                  "Ci-dessous : cinq plus faibles moyennes des ACF au carre. "
                  "Ce classement ne mesure pas la qualite predictive. "
                  "Les lissages sont retrospectifs ; les differences peuvent amplifier le bruit. "
                  "Les tests Ljung-Box sont indicatifs. Voir ../../docs/05_comparaison.md.", bilan.head())


if __name__ == "__main__":
    main()
