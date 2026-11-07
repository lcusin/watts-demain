
# ============================================================
# BENCHMARKS : PRÉVISION DE LA CONSOMMATION ÉLECTRIQUE
# ============================================================

# Objectif :
# Prédire les 24 consommations horaires du lendemain
# avec trois méthodes simples :
#
# 1. Même consommation que la semaine précédente
# 2. Moyenne des consommations des 4 semaines précédentes
# 3. Persistance de la dernière consommation connue à J8
#
# Validation : 2024
# Test final : 2025


# ============================================================
# 1. IMPORTER LES BIBLIOTHÈQUES
# ============================================================

import pandas as pd
import numpy as np
from pathlib import Path
from protocole import HEURE_COUPURE, masquer_transitions, jours_communs, enregistrer_execution
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ============================================================
# 2. CHARGER TRAIN ET VALIDATION
# ============================================================

# Récupérer le dossier racine du projet watts-demain.
BASE_DIR = Path(__file__).resolve().parent.parent

# Chemin du dossier contenant les données préparées.
DOSSIER_DATA = BASE_DIR / "data" / "merge"

# Charger les données d'entraînement (2012-2023).
train = pd.read_csv(
    DOSSIER_DATA / "train.csv",
    parse_dates=["horodatage", "date"]
)

# Charger les données de validation (2024).
validation = pd.read_csv(
    DOSSIER_DATA / "validation.csv",
    parse_dates=["horodatage", "date"]
)



# Vérifier les dimensions des deux ensembles.
print("Train :", train.shape)
print("Validation :", validation.shape)



# ============================================================
# 3. RÉUNIR TEMPORAIREMENT LES DONNÉES
# ============================================================

# Pourquoi réunir les datasets ?
#
# Pour prédire le 1er janvier 2024,
# on doit utiliser les consommations de décembre 2023.
#
# Si on applique shift(7) directement à validation,
# les 7 premiers jours de 2024 n'auront pas de prévisions.
#
# pd.concat() permet de réunir les deux tableaux
# en un seul tableau.
#
# ignore_index=True crée un nouvel index numérique.

df = pd.concat(
    [train, validation],
    ignore_index=True
)

# Trier les observations par horodatage.
df = df.sort_values("horodatage")
assert not df["horodatage"].duplicated().any()
assert df["horodatage"].diff().dropna().eq(pd.Timedelta(hours=1)).all()

# Masquer les changements d'heure sans retirer les lignes.
# Ainsi, shift(7) sur les profils journaliers reste un decalage de sept jours.
df = masquer_transitions(df)

print("\nDimensions des données réunies :", df.shape)


# ============================================================
# 4. TRANSFORMER LES DONNÉES EN PROFILS JOURNALIERS
# ============================================================

# Actuellement :
# Une ligne = une heure.
#
# Après pivot :
# Une ligne = une journée.
# Une colonne = une heure.
#
# Exemple :
#
# date        00:00    01:00    ...    23:00
# 2024-01-01  50000    48000    ...    53000
# 2024-01-02  51000    49000    ...    54000

conso = df.pivot(
    index="date",
    columns="heure",
    values="consommation_MW"
)

# Trier les heures dans l'ordre chronologique.
conso = conso.reindex(
    sorted(conso.columns),
    axis=1
)

# Trier les journées par ordre chronologique.
conso = conso.sort_index()

print("\nDimensions après pivot :", conso.shape)

# Vérifier le nombre de colonnes horaires.
print("Nombre d'heures :", len(conso.columns))

# Vérifier le nombre de valeurs manquantes.
print("Valeurs manquantes :", conso.isna().sum().sum())

# Vérifier que les dates sont consécutives.
dates_attendues = pd.date_range(
    conso.index.min(),
    conso.index.max(),
    freq="D"
)

jours_manquants = dates_attendues.difference(conso.index)

print("Journées manquantes :", len(jours_manquants))

# Arrêter le programme si les données ne permettent
# pas de calculer correctement les benchmarks.
if (
    len(conso.columns) != 24
    or len(jours_manquants) > 0
):
    raise ValueError(
        "Vérifier les heures, les valeurs manquantes "
        "et les journées absentes avant les benchmarks."
    )


# ============================================================
# 5. BENCHMARK 1 : SEMAINE PRÉCÉDENTE
# ============================================================

# Pour prédire une journée,
# on reprend les 24 consommations du même jour
# de la semaine précédente.
#
# Exemple :
# Pour prédire le mardi 14 janvier,
# on utilise le mardi 7 janvier.
#
# shift(7) décale les valeurs de 7 lignes.
#
# Ici, une ligne = une journée.
# Donc shift(7) correspond à 7 jours.

prediction_semaine = conso.shift(7)


# ============================================================
# 6. BENCHMARK 2 : MOYENNE DES 4 SEMAINES
# ============================================================

# On utilise les consommations :
#
# - 7 jours avant
# - 14 jours avant
# - 21 jours avant
# - 28 jours avant
#
# On calcule leur moyenne heure par heure.

prediction_moyenne = (
    conso.shift(7)
    + conso.shift(14)
    + conso.shift(21)
    + conso.shift(28)
) / 4


# ============================================================
# 7. SÉLECTIONNER LA VALIDATION : 2024
# ============================================================

# Récupérer les consommations réellement observées
# pendant l'année 2024.
reel = conso.loc[
    "2024-01-01":"2024-12-31"
]

# Récupérer les prévisions du premier benchmark.
pred1 = prediction_semaine.loc[
    "2024-01-01":"2024-12-31"
]

# Récupérer les prévisions du deuxième benchmark.
pred2 = prediction_moyenne.loc[
    "2024-01-01":"2024-12-31"
]

# Garder les memes journees completes pour les deux benchmarks.
# Une valeur masquee dans une des quatre semaines exclut la cible commune.
jours_valides = reel.index.isin(jours_communs(df, "2024-01-01", "2024-12-31"))
reel = reel.loc[jours_valides]
pred1 = pred1.loc[jours_valides]
pred2 = pred2.loc[jours_valides]

# Vérifier que les tableaux ont les mêmes dimensions.
print("\nDimensions validation :")

print("Réel :", reel.shape)
print("Benchmark 1 :", pred1.shape)
print("Benchmark 2 :", pred2.shape)


# ============================================================
# 8. FONCTION D'ÉVALUATION
# ============================================================

# MAE = moyenne des erreurs absolues.
#
# RMSE = racine de la moyenne des erreurs au carré.
#
# Plus ces métriques sont faibles,
# meilleures sont les prévisions.

def evaluer(y_reel, y_pred):

    # Transformer les DataFrames en tableaux NumPy.
    valeurs_reelles = y_reel.to_numpy()
    valeurs_predites = y_pred.to_numpy()

    # Vérifier qu'aucune valeur ne manque.
    if (
        not np.isfinite(valeurs_reelles).all()
        or not np.isfinite(valeurs_predites).all()
    ):
        raise ValueError("Valeurs manquantes dans l'évaluation.")

    # Calculer l'erreur :
    # consommation réelle - consommation prédite.
    erreur = valeurs_reelles - valeurs_predites

    # MAE : moyenne des valeurs absolues des erreurs.
    mae = np.mean(np.abs(erreur))

    # RMSE : racine carrée de la moyenne
    # des erreurs élevées au carré.
    rmse = np.sqrt(np.mean(erreur ** 2))

    # Retourner les deux résultats.
    return mae, rmse


# ============================================================
# 9. ÉVALUER LES BENCHMARKS SUR 2024
# ============================================================

# Calculer les métriques du premier benchmark.
mae1, rmse1 = evaluer(reel, pred1)

# Calculer les métriques du deuxième benchmark.
mae2, rmse2 = evaluer(reel, pred2)


# ============================================================
# 10. AFFICHER LES RÉSULTATS
# ============================================================

print("\n===== RÉSULTATS VALIDATION 2024 =====")

print("\nBenchmark 1 : semaine précédente")
print("MAE :", round(mae1, 2), "MW")
print("RMSE :", round(rmse1, 2), "MW")

print("\nBenchmark 2 : moyenne des 4 semaines")
print("MAE :", round(mae2, 2), "MW")
print("RMSE :", round(rmse2, 2), "MW")


# ============================================================
# 11. COMPARER LES DEUX REFERENCES HEBDOMADAIRES
# ============================================================

# Le meilleur benchmark selon la MAE
# est celui qui a la plus petite erreur moyenne.

if mae1 < mae2:
    print("\nMeilleur benchmark selon la MAE :")
    print("Semaine précédente")

elif mae2 < mae1:
    print("\nMeilleur benchmark selon la MAE :")
    print("Moyenne des 4 semaines")

else:
    print("\nLes deux benchmarks ont la même MAE.")

# Si la RMSE du benchmark 1 est plus petite,
# alors le benchmark 1 est meilleur selon la RMSE.
if rmse1 < rmse2:
    print("Meilleur benchmark selon la RMSE : semaine précédente")
    print("RMSE :", round(rmse1, 2), "MW")

# Si la RMSE du benchmark 2 est plus petite,
# alors le benchmark 2 est meilleur selon la RMSE.
elif rmse2 < rmse1:
    print("Meilleur benchmark selon la RMSE : moyenne des 4 semaines")
  

# Si les deux RMSE sont égales,
# les benchmarks ont les mêmes performances selon la RMSE.
else:
    print("Les deux benchmarks ont la même RMSE.")





# 14. VISUALISATION DES PRÉDICTIONS de validation SUR PLUSIEURS JOURNÉES


import matplotlib.pyplot as plt

# Dossier où enregistrer les graphiques
DOSSIER_GRAPHIQUES = BASE_DIR / "results" / "analyse_2024" / "benchmarks"

# Créer le dossier s'il n'existe pas
DOSSIER_GRAPHIQUES.mkdir(parents=True, exist_ok=True)
pd.Series(reel.index, name="jour").to_csv(DOSSIER_GRAPHIQUES / "jours_evalues.csv", index=False)
# Troisième référence du rapport : dernière consommation connue à J8.
y = df.set_index("horodatage").consommation_MW
coupures = reel.index - pd.Timedelta(days=1) + pd.Timedelta(hours=HEURE_COUPURE)
pred3 = pd.DataFrame(np.repeat(y.reindex(coupures).to_numpy()[:, None], 24, axis=1),
                     index=reel.index, columns=reel.columns)
mae3, rmse3 = evaluer(reel, pred3)
print("Persistance à J8 : MAE =", round(mae3, 2), "; RMSE =", round(rmse3, 2), "MW")
pd.DataFrame([
    {"modele": "persistance", "MAE_MW": mae3, "RMSE_MW": rmse3},
    {"modele": "semaine_precedente", "MAE_MW": mae1, "RMSE_MW": rmse1},
    {"modele": "moyenne_4_semaines", "MAE_MW": mae2, "RMSE_MW": rmse2},
]).to_csv(DOSSIER_GRAPHIQUES / "comparaison_2024.csv", index=False)

# Exporter les prévisions horaires pour les contrôles et diagnostics communs.
lignes = []
for nom, prediction in [("persistance", pred3), ("semaine_precedente", pred1),
                         ("moyenne_4_semaines", pred2)]:
    heures = pd.DatetimeIndex([jour + pd.Timedelta(hours=h) for jour in reel.index for h in range(24)])
    lignes.append(pd.DataFrame({"horodatage": heures, "modele": nom,
                               "reel_MW": reel.to_numpy().ravel(),
                               "prediction_MW": prediction.to_numpy().ravel()}))
pd.concat(lignes, ignore_index=True).to_csv(DOSSIER_GRAPHIQUES / "previsions_horaires_2024.csv", index=False)
enregistrer_execution(DOSSIER_GRAPHIQUES, __file__)

# Comparer les trois benchmarks sur trois journ�es repr�sentatives.
dates_exemples = ["2024-01-15", "2024-06-20", "2024-12-15"]
dates_exemples = [d for d in dates_exemples if pd.Timestamp(d) in reel.index]
fig, axes = plt.subplots(len(dates_exemples), 1, figsize=(12, 4 * len(dates_exemples)), sharex=True)
axes = np.atleast_1d(axes)
for ax, date_exemple in zip(axes, dates_exemples):
    ax.plot(range(24), reel.loc[date_exemple], label="Consommation r�elle", linewidth=2)
    ax.plot(range(24), pred1.loc[date_exemple], label="Semaine pr�c�dente", linestyle="--")
    ax.plot(range(24), pred2.loc[date_exemple], label="Moyenne des 4 semaines", linestyle=":")
    ax.plot(range(24), pred3.loc[date_exemple], label="Persistance � J8", linestyle="-.")
    ax.set(title=date_exemple, ylabel="Consommation (MW)")
    ax.grid(alpha=0.3)
axes[-1].set(xlabel="Heure", xticks=range(24))
axes[0].legend(ncol=2)
fig.tight_layout()
fig.savefig(DOSSIER_GRAPHIQUES / "benchmarks_exemples.png", dpi=200)
plt.close(fig)