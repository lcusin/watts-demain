"""Variables communes aux comparaisons et a la decomposition retenue."""
import numpy as np
import pandas as pd
from sklearn.preprocessing import SplineTransformer

METHODES = {
    "sans_meteo": "Cycles seuls : reference pour mesurer l'apport meteo.",
    "lineaire": "Temperature lineaire : hypothese la plus simple.",
    "quadratique": "Temperature quadratique : methode precedente, relation courbe.",
    "seuils": "Froid sous 18 C et chaleur au-dessus de 22 C : deux pentes distinctes.",
    "splines": "Spline cubique de temperature : courbe souple avec cinq noeuds quantiles.",
    "splines_interactions": "Spline et sensibilite au froid selon l'heure : usages variables dans la journee.",
    "splines_annuel6": "Spline et six harmoniques annuelles : cycle annuel plus flexible.",
}


def matrices(apprentissage, evaluation, methode):
    # Tous les parametres de transformation viennent de l'apprentissage.
    colonnes = ["temperature_moyenne", "precipitation_moyenne"]
    medianes = apprentissage.groupby([apprentissage.index.month, apprentissage.index.hour])[colonnes].median()
    globales = apprentissage[colonnes].median()
    def meteo(x):
        cles = pd.MultiIndex.from_arrays([x.index.month, x.index.hour])
        remplacement = pd.DataFrame(medianes.reindex(cles).to_numpy(), index=x.index, columns=colonnes)
        return x[colonnes].fillna(remplacement).fillna(globales)
    temps_train = meteo(apprentissage)
    centre = temps_train.temperature_moyenne.mean()
    spline = SplineTransformer(n_knots=5, degree=3, include_bias=False, extrapolation="linear")
    if methode.startswith("splines"):
        spline.fit(temps_train[["temperature_moyenne"]])
    origine = apprentissage.index[0]
    duree = (apprentissage.index[-1] - origine).total_seconds() / (86400 * 365.2425)
    def construire(x):
        t = (x.index - origine).total_seconds() / (86400 * 365.2425)
        X = pd.DataFrame({"constante": 1., "tendance": t}, index=x.index)
        # Garder au moins un an apres le dernier changement de pente.
        for an in range(1, int(duree)):
            X[f"tendance_{an}"] = np.maximum(t - an, 0)
        for k in range(1, (6 if methode == "splines_annuel6" else 3) + 1):
            X[f"annuel_sin_{k}"] = np.sin(2 * np.pi * k * t)
            X[f"annuel_cos_{k}"] = np.cos(2 * np.pi * k * t)
        heures = pd.Series(pd.Categorical(x.index.dayofweek * 24 + x.index.hour, categories=range(168)), index=x.index)
        X = X.join(pd.get_dummies(heures, prefix="semaine", drop_first=True, dtype=float))
        if methode == "sans_meteo":
            return X
        m = meteo(x)
        temperature = m.temperature_moyenne
        if methode in ("lineaire", "quadratique"):
            X["temperature_1"] = temperature - centre
            if methode == "quadratique":
                X["temperature_2"] = (temperature - centre) ** 2
        elif methode == "seuils":
            X["temperature_froid"] = np.maximum(18 - temperature, 0)
            X["temperature_chaud"] = np.maximum(temperature - 22, 0)
        else:
            base = spline.transform(m[["temperature_moyenne"]])
            for j in range(base.shape[1]):
                X[f"temperature_spline_{j}"] = base[:, j]
            if methode == "splines_interactions":
                for h in range(1, 24):
                    X[f"temperature_heure_{h}"] = np.maximum(18 - temperature, 0) * (x.index.hour == h)
        X["pluie"] = np.log1p(m.precipitation_moyenne)
        for v in colonnes:
            X["imputation_" + v] = x[v].isna().astype(float)
        return X
    return construire(apprentissage), construire(evaluation)
