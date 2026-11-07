"""Recalculer AIC et BIC des ARMA a partir des coefficients deja estimes."""
import json

import numpy as np
import pandas as pd

from chemins_analyse import PROJET, RESULTATS
from modeles_cours import ORDRES, modele, transformer

SORTIE = RESULTATS / "10_modeles_cours"


def main():
    d = pd.read_csv(PROJET / "data/merge/train.csv", parse_dates=["horodatage"])
    d = d.set_index("horodatage").sort_index()
    assert d.index.is_unique
    assert d.index.to_series().diff().dropna().eq(pd.Timedelta(hours=1)).all()
    y = d.consommation_MW.mask(d.jour_changement_heure)
    z = transformer(y)
    ajustements = pd.read_csv(SORTIE / "ajustements.csv")
    lignes = []

    for ligne in ajustements.itertuples():
        serie = z.loc[ligne.debut:ligne.fin]
        assert len(serie) == len(pd.date_range(ligne.debut, ligne.fin, freq="h"))
        assert serie.count() == ligne.n_valides
        p, q = ORDRES[ligne.modele]
        m = modele(serie, p, q)  # Meme transformation et meme echelle en GW.
        coefficients = json.loads(ligne.parametres)
        parametres = [coefficients[nom] for nom in m.param_names]
        resultat = m.filter(parametres)  # Pas de nouvel ajustement.
        log_vraisemblance = resultat.llf
        k = len(parametres)  # Coefficients AR/MA et variance, sans constante.
        n = int(serie.count())  # Observations disponibles, sans compter les NaN.
        aic = -2 * log_vraisemblance + 2 * k
        bic = -2 * log_vraisemblance + k * np.log(n)
        assert np.isclose(aic, ligne.AIC, rtol=0, atol=0.01)
        lignes.append({"annee_prevue": ligne.annee, "modele": ligne.modele,
                       "debut": ligne.debut, "fin": ligne.fin,
                       "n": n, "k": k, "log_vraisemblance": log_vraisemblance,
                       "AIC": aic, "BIC": bic})

    scores = pd.DataFrame(lignes)
    scores.to_csv(SORTIE / "criteres_information.csv", index=False)
    tableau = [r"\begin{tabular}{llrrr}", r"\toprule",
               r"Année prévue & Modèle & $k$ & AIC & BIC \\", r"\midrule"]
    noms = {"AR1": "AR(1)", "AR2": "AR(2)", "MA1": "MA(1)", "ARMA11": "ARMA(1,1)"}
    for annee, groupe in scores.groupby("annee_prevue"):
        assert groupe.n.nunique() == 1
        assert groupe.debut.nunique() == 1 and groupe.fin.nunique() == 1
        for r in groupe.itertuples():
            aic = f"{r.AIC:.1f}".replace(".", ",")
            bic = f"{r.BIC:.1f}".replace(".", ",")
            if r.AIC == groupe.AIC.min():
                aic = r"\textbf{" + aic + "}"
            if r.BIC == groupe.BIC.min():
                bic = r"\textbf{" + bic + "}"
            tableau.append(f"{annee} & {noms[r.modele]} & {r.k} & {aic} & {bic}" + r" \\")
    tableau += [r"\bottomrule", r"\end{tabular}"]
    (SORTIE / "tableau_aic_bic.tex").write_text("\n".join(tableau) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
