

# Objectif :
# Étudier les propriétés statistiques de la consommation
# électrique pour identifier les modéles candidats 

# Analyses réalisées :
# 1. Consommation moyenne journalière
# 2. Statistiques descriptives
# 3. Moyenne mobile et écart-type mobile
# 4. Différenciation ordinaire et saisonnière
# 5. Analyse ACF et PACF

# Données utilisées : Train : 2012-2023




from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
# Fonctions d'autocorrélation et d'autocorrélation partielle.
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf



# Definition des chemins



BASE_DIR = Path(__file__).resolve().parent.parent

FICHIER_TRAIN = BASE_DIR / "data" / "processed" / "train.csv"

DOSSIER_GRAPHIQUES = (
    BASE_DIR / "data_temp" / "graphiques" / "modelisation"
)
# creer dossier qui n'existe pas : "modelisation"
DOSSIER_GRAPHIQUES.mkdir(parents=True, exist_ok=True)



# Charger train data


# Charger uniquement Train (2012-2023).
# parse_dates convertit les colonnes en dates pandas.
train = pd.read_csv(
    FICHIER_TRAIN,
    parse_dates=["date", "horodatage"]
)

# Trier les observations de la plus ancienne à la plus récente.
train = train.sort_values("horodatage")

# Afficher les dimensions du tableau.
print("Train :", train.shape)

# Afficher les dates de début et de fin.
print(
    "Période :",
    train["date"].min(),
    "à",
    train["date"].max()
)



# construire la serie journaliere


# Le dataset contient initialement une ligne par heure.


# Pour commencer l'analyse statistique, nous travaillons
# sur la consommation moyenne de chaque journée.
# groupby("date") regroupe les observations par journée.
# mean() calcule la moyenne des 24 consommations horaires.
# sort_index() classe les journées chronologiquement.

serie = (
    train.groupby("date")["consommation_MW"]
    .mean()
    .sort_index()
)

# Indiquer que la série possède une fréquence quotidienne.
# Les dates absentes deviennent des valeurs manquantes.
serie = serie.asfreq("D")

# Vérifier qu'aucune journée ou valeur ne manque.
if serie.isna().any():
    raise ValueError(
        "Des journées ou des consommations manquent dans Train."
    )

# Vérifier que toutes les consommations sont finies.
if not np.isfinite(serie.to_numpy()).all():
    raise ValueError(
        "La série contient des valeurs non finies."
    )

# Afficher le nombre de journées.
print("Nombre de jours :", len(serie))



#Statistiques descriptive globale


# Moyenne de la consommation sur toute la période.
moyenne = serie.mean()

# Écart-type : mesure la dispersion autour de la moyenne.
ecart_type = serie.std()

# Valeur minimale observée.
minimum = serie.min()

# Valeur maximale observée.
maximum = serie.max()

# Afficher les résultats.
print("\n===== STATISTIQUES DESCRIPTIVES =====")

print("Moyenne :", round(moyenne, 2), "MW")
print("Écart-type :", round(ecart_type, 2), "MW")
print("Minimum :", round(minimum, 2), "MW")
print("Maximum :", round(maximum, 2), "MW")



# Visualisation de la serie brute 

# Créer une figure et un axe.
fig, ax = plt.subplots(figsize=(13, 5))

# Tracer la consommation moyenne journalière.
ax.plot(
    serie.index,
    serie,
    linewidth=0.8
)

# Ajouter le titre et les noms des axes.
ax.set_title("Consommation moyenne journalière — Train")
ax.set_xlabel("Date")
ax.set_ylabel("Consommation (MW)")
# Ajouter une grille légère.
ax.grid(alpha=0.3)
# Ajuster les marges du graphique.
fig.tight_layout()

# Enregistrer le graphique.
fig.savefig(
    DOSSIER_GRAPHIQUES / "01_serie_brute.png",
    dpi=300
)
# Fermer la figure pour libérer la mémoire.
plt.close(fig)


#moyenne mobile sur 30jours 
# La moyenne mobile permet d'étudier l'évolution du niveau moyen de consommation au cours du temps.

# Pour chaque journée, on calcule la moyenne des 30 dernières consommations journalières.

# Exemple :
# Moyenne mobile du 30 janvier =  moyenne des consommations du 1er au 30 janvier.

moyenne_mobile = serie.rolling(window=30).mean()

# Créer une figure.
fig, ax = plt.subplots(figsize=(13, 5))

# Tracer la consommation journalière.
ax.plot(
    serie.index,
    serie,
    label="Consommation journalière",
    linewidth=0.7,
    alpha=0.5
)

# Tracer la moyenne mobile.
ax.plot(
    moyenne_mobile.index,
    moyenne_mobile,
    label="Moyenne mobile (30 jours)",
    linewidth=2
)

# Ajouter les informations du graphique.
ax.set_title("Consommation et moyenne mobile sur 30 jours")
ax.set_xlabel("Date")
ax.set_ylabel("Consommation (MW)")

# Afficher la légende.
ax.legend()

# Ajouter la grille.
ax.grid(alpha=0.3)

# Ajuster les marges.
fig.tight_layout()

# Enregistrer le graphique.
fig.savefig(
    DOSSIER_GRAPHIQUES / "02_moyenne_mobile.png",
    dpi=300
)

# Fermer la figure.
plt.close(fig)



# ecart type mobile sur 30j 

# L'écart-type mesure la dispersion des valeurs.

# L'écart-type mobile permet de voir si cette dispersion évolue au cours du temps.
# window=30 : on considère les 30 derniers jours.

ecart_type_mobile = serie.rolling(window=30).std()

# Créer une figure.
fig, ax = plt.subplots(figsize=(13, 5))

# Tracer l'écart-type mobile.
ax.plot(
    ecart_type_mobile.index,
    ecart_type_mobile,
    linewidth=1
)

# Ajouter les informations.
ax.set_title("Écart-type mobile sur 30 jours")
ax.set_xlabel("Date")
ax.set_ylabel("Écart-type (MW)")

# Ajouter la grille.
ax.grid(alpha=0.3)

# Ajuster les marges.
fig.tight_layout()

# Enregistrer le graphique.
fig.savefig(
    DOSSIER_GRAPHIQUES / "03_ecart_type_mobile.png",
    dpi=300
)

# Fermer la figure.
plt.close(fig)



# statistiques annuelles


# serie.index.year récupère l'année de chaque observation.
# groupby(...) regroupe les consommations par année.

# agg(["mean", "std"]) calcule pour chaque année :
# - la moyenne des consommations journalières
# - leur écart-type

statistiques = serie.groupby(serie.index.year).agg(
    ["mean", "std"]
)

# Renommer les colonnes pour faciliter la lecture.
statistiques.columns = ["Moyenne", "Écart-type"]

# Afficher le tableau.
print("\n===== STATISTIQUES ANNUELLES =====")
print(statistiques.round(2))

# Enregistrer les statistiques dans un fichier CSV.
statistiques.to_csv(
    DOSSIER_GRAPHIQUES / "statistiques_annuelles.csv"
)



#Differenciation de la serie


# Objectif :
# Étudier différentes transformations de la série pour réduire certaines dépendances temporelles.





# Différence première

# Formule :
# Y_t = X_t - X_(t-1)

# On soustrait la consommation de la veille.

# diff() équivaut à diff(1).
# dropna() supprime la première valeur manquante.

serie_diff1 = serie.diff().dropna()



#Différence saisonnière de 7 jours


# Formule :
# Y_t = X_t - X_(t-7)

# On compare chaque journée à la même journée de la semaine précédente.

# Cette transformation permet d'étudier la saisonnalité hebdomadaire.

serie_diff7 = serie.diff(7).dropna()



#  Double différence


# On applique deux transformations successives :
# 1. Différence saisonnière de 7 jours.
# 2. Différence première sur le résultat.

# Formule :
# Y_t = (X_t - X_(t-7)) - (X_(t-1) - X_(t-8))

serie_diff1_7 = serie.diff(7).diff().dropna()



# REGROUPER LES SÉRIES À COMPARER


# Un dictionnaire permet d'associer :
# - un nom à chaque série
# - les observations correspondantes

series = {
    "Série brute": serie,
    "Différence première (d=1)": serie_diff1,
    "Différence saisonnière (7 jours)": serie_diff7,
    "Différences 7 jours puis 1 jour": serie_diff1_7
}



# VISUALISER LES TRANSFORMATIONS


# Parcourir les quatre séries.

# enumerate(..., start=1) attribue un numéro
# à chaque série pour nommer les fichiers.

for i, (nom, s) in enumerate(series.items(), start=1):

    # Créer une figure pour la série courante.
    fig, ax = plt.subplots(figsize=(13, 4))

    # Tracer son évolution temporelle.
    ax.plot(
        s.index,
        s,
        linewidth=0.8
    )

    # Ajouter le titre et les axes.
    ax.set_title(nom)
    ax.set_xlabel("Date")
    ax.set_ylabel("MW")

    # Ajouter la grille.
    ax.grid(alpha=0.3)

    # Ajuster les marges.
    fig.tight_layout()

    # Enregistrer le graphique.
    fig.savefig(
        DOSSIER_GRAPHIQUES / f"04_transformation_{i}.png",
        dpi=300
    )

    # Fermer la figure.
    plt.close(fig)



#  ANALYSE ACF ET PACF


# ACF = fonction d'autocorrélation. Elle mesure la corrélation entre une série et ses valeurs passées.

# PACF = fonction d'autocorrélation partielle. Elle mesure la corrélation directe entre deux observations séparées par un certain retard, en contrôlant les retards intermédiaires.
#
# Comme nous travaillons sur une série journalière :
# retard 1 = 1 jour
# retard 7 = 1 semaine
# retard 14 = 2 semaines
# retard 21 = 3 semaines


# Parcourir les quatre séries.
for i, (nom, s) in enumerate(series.items(), start=1):

    # Étudier jusqu'à 35 jours de retard.
    # La limite dépend aussi de la longueur de la série.
    n_lags = min(35, len(s) // 2 - 1)

    # Créer deux graphiques côte à côte.
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(14, 4)
    )

    # Tracer la fonction d'autocorrélation.
    # zero=False retire le retard 0,
    # dont l'autocorrélation vaut toujours 1.
    plot_acf(
        s,
        lags=n_lags,
        ax=axes[0],
        zero=False
    )

    # Tracer la fonction d'autocorrélation partielle.
    # method="ywm" choisit la méthode d'estimation.
    plot_pacf(
        s,
        lags=n_lags,
        ax=axes[1],
        zero=False,
        method="ywm"
    )

    # Ajouter les titres et noms des axes.
    axes[0].set_title(f"ACF — {nom}")
    axes[0].set_xlabel("Retard (jours)")

    axes[1].set_title(f"PACF — {nom}")
    axes[1].set_xlabel("Retard (jours)")

    # Ajuster la mise en page.
    fig.tight_layout()

    # Enregistrer les deux graphiques.
    fig.savefig(
        DOSSIER_GRAPHIQUES / f"05_acf_pacf_{i}.png",
        dpi=300
    )

    # Fermer la figure.
    plt.close(fig)


# verif le bon deroulement du programme

print("\n===== ANALYSE TERMINÉE =====")

print("Statistiques descriptives calculées.")
print("Moyenne mobile et écart-type mobile calculés.")
print("Différenciations réalisées.")
print("Graphiques ACF et PACF enregistrés.")

print("\nGraphiques enregistrés dans :")
print(DOSSIER_GRAPHIQUES)

print("\nProchaine étape :")
print("Identifier des modèles statistiques candidats.")
