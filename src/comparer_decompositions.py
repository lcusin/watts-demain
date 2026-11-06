"""Comparaison chronologique interne ; ne lit ni validation.csv ni test.csv."""
from pathlib import Path
import numpy as np
import pandas as pd
from modele_decomposition import METHODES, matrices

racine = Path(__file__).resolve().parent.parent
sortie = racine / "results/decomposition/essais"
sortie.mkdir(parents=True, exist_ok=True)
x = pd.read_csv(racine / "data/merge/train.csv", parse_dates=["horodatage"]).set_index("horodatage").sort_index()
scores, erreurs = [], []
for annee in (2021, 2022, 2023):
    train = x[x.index.year < annee]
    valid = x[x.index.year == annee]
    for methode in METHODES:
        X, V = matrices(train, valid, methode)
        beta = np.linalg.lstsq(X, train.consommation_MW, rcond=None)[0]
        e = valid.consommation_MW - V.dot(beta)
        scores.append({"annee": annee, "methode": methode, "n": len(e),
                       "MAE_MW": e.abs().mean(), "RMSE_MW": np.sqrt((e ** 2).mean()),
                       "biais_MW": e.mean(), "ACF_24h": e.autocorr(24), "ACF_168h": e.autocorr(168)})
        erreurs.append(pd.DataFrame({"horodatage": valid.index, "methode": methode, "erreur_MW": e.to_numpy()}))
scores = pd.DataFrame(scores)
scores.to_csv(sortie / "scores_par_annee.csv", index=False)
pd.concat(erreurs).to_csv(sortie / "erreurs_validation_interne.csv", index=False)
classement = scores.groupby("methode").agg(MAE_MW=("MAE_MW", "mean"), RMSE_moyenne_MW=("RMSE_MW", "mean"), pire_MAE_annuelle_MW=("MAE_MW", "max"))
classement = classement.sort_values("MAE_MW")
classement.to_csv(sortie / "classement.csv")
(sortie / "methode_retenue.txt").write_text(classement.index[0], encoding="utf-8")
