import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import matplotlib.dates as mdates
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

sns.set_theme(style="whitegrid")

# Racine du projet
BASE_DIR = Path(__file__).resolve().parent.parent

# Chemin du dataset
FICHIER = BASE_DIR / "data" / "merge" / "train.csv"

# Charger le dataset
df = pd.read_csv(FICHIER)
assert pd.to_datetime(df["horodatage"]).between("2012-01-01", "2023-12-31 23:00:00").all()

# Conversion des dates
df["horodatage"] = pd.to_datetime(df["horodatage"])
df["date"] = pd.to_datetime(df["date"])


print(df.head())
print("Dimensions :", df.shape)
print(df["horodatage"].is_monotonic_increasing)
print("Période :", df["date"].min(), "à", df["date"].max())

df.info()
print(df.isna().sum())


 #Identifier les journées atypiques
#Les cinq journées avec les pointes les plus élevées
# Consommation maximale pour chaque journée
conso_max = df.groupby("date")["consommation_MW"].max()

# Afficher les cinq plus grandes pointes
print("Les 5 journées avec les pointes les plus élevées :")
print(conso_max.nlargest(5))





#Évolution de la consommation électrique
# par moyenne journaliere
conso_jour = df.groupby("date")["consommation_MW"].mean()

plt.figure(figsize=(14, 5))
plt.plot(conso_jour.index, conso_jour.values)

plt.title("Évolution de la consommation électrique journaliere en France")
plt.xlabel("Année")
plt.ylabel("Consommation moyenne (MW)")

# Afficher chaque année sur l'axe X
plt.gca().xaxis.set_major_locator(mdates.YearLocator())
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

plt.xticks(rotation=45)
plt.grid(True)
plt.tight_layout()

# Créer le dossier pour les graphiques
DOSSIER_GRAPHIQUES = BASE_DIR / "results" / "analyse_2024" / "exploration"
DOSSIER_GRAPHIQUES.mkdir(parents=True, exist_ok=True)

# Sauvegarder le graphique
plt.savefig(
    DOSSIER_GRAPHIQUES / "evolution_consommation_journaliere.png",
    dpi=300,
    bbox_inches="tight"
)
plt.close()

# ACF et PACF avant et apr�s diff�renciation hebdomadaire.
serie_horaire = df.set_index("horodatage")["consommation_MW"].sort_index().asfreq("h")
assert serie_horaire.notna().all()

for nom, serie in [
    ("brute", serie_horaire),
    ("difference_168h", serie_horaire.diff(168).dropna()),
]:
    fig, axes = plt.subplots(1, 2, figsize=(14, 4))
    plot_acf(serie, lags=336, zero=False, ax=axes[0])
    plot_pacf(serie, lags=48, zero=False, method="ywm", ax=axes[1])
    axes[0].set_title(f"ACF - {nom}")
    axes[1].set_title(f"PACF - {nom}")
    fig.tight_layout()
    fig.savefig(DOSSIER_GRAPHIQUES / f"acf_pacf_{nom}.png", dpi=180)
    plt.close(fig)

#Consommation moyenne par année
df["annee"] = df["date"].dt.year

conso_annee = df.groupby("annee")["consommation_MW"].mean()

plt.figure(figsize=(12, 5))
conso_annee.plot(kind="bar")

plt.title("Consommation moyenne annuelle en France")
plt.xlabel("Année")
plt.ylabel("Consommation moyenne (MW)")

# Améliorer la lisibilité
plt.xticks(rotation=45)
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()

# Sauvegarder le graphique
plt.savefig(
    DOSSIER_GRAPHIQUES / "consommation_moyenne_annuelle.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()
#Étudier la saisonnalité

#Cycle journalier

#Objectif : observer comment la consommation électrique varie au cours d'une journée moyenne.
#On cherche à identifier les heures de faible consommation, 
# les heures de pointe et les variations entre le jour et la nuit.
df["heure_num"] = df["horodatage"].dt.hour
conso_heure = df.groupby("heure_num")["consommation_MW"].mean()

plt.figure(figsize=(10, 5))

plt.plot(
    conso_heure.index,
    conso_heure.values,
    marker="o"
)

plt.title("Profil moyen de consommation sur 24 heures")
plt.xlabel("Heure")
plt.ylabel("Consommation moyenne (MW)")

plt.xticks(range(24))
plt.grid(True)
plt.tight_layout()

# Sauvegarde
plt.savefig(
    DOSSIER_GRAPHIQUES / "cycle_journalier.png",
    dpi=300
)

plt.close()


#Cycle hebdomadaire
#Objectif : comparer la consommation moyenne entre lundi, mardi, mercredi… et dimanche.
#On veut vérifier si les jours ouvrés présentent une consommation différente de celle des weekends.
# Consommation moyenne par jour de semaine
# Extraire le jour de la semaine (0 = lundi, 6 = dimanche)
df["jour_semaine"] = df["date"].dt.dayofweek

# Noms des jours
jours = [
    "Lundi", "Mardi", "Mercredi", "Jeudi",
    "Vendredi", "Samedi", "Dimanche"
]
conso_semaine = df.groupby("jour_semaine")["consommation_MW"].mean()

plt.figure(figsize=(10, 5))

plt.bar(jours, conso_semaine.values)

plt.title("Consommation moyenne selon le jour de la semaine")
plt.xlabel("Jour")
plt.ylabel("Consommation moyenne (MW)")

plt.xticks(rotation=30)
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()

# Sauvegarde
plt.savefig(
    DOSSIER_GRAPHIQUES / "cycle_hebdomadaire.png",
    dpi=300
)

plt.close()
# cycle hebdo : moyenne du jour par an 
# Cycle hebdomadaire : une courbe par année

# Extraire l'année et le jour de la semaine
df["annee"] = df["date"].dt.year
df["jour_semaine"] = df["date"].dt.dayofweek

# Noms des jours
jours = [
    "Lundi", "Mardi", "Mercredi", "Jeudi",
    "Vendredi", "Samedi", "Dimanche"
]

# Consommation moyenne par jour de semaine et par année
conso_semaine_annee = df.groupby(
    ["annee", "jour_semaine"]
)["consommation_MW"].mean().unstack(level=0)

plt.figure(figsize=(13, 6))

# Une courbe pour chaque année
for annee in conso_semaine_annee.columns:
    plt.plot(
        conso_semaine_annee.index,
        conso_semaine_annee[annee],
        marker="o",
        markersize=4,
        label=str(annee)
    )

plt.title("Profil hebdomadaire de consommation par année")
plt.xlabel("Jour de la semaine")
plt.ylabel("Consommation moyenne (MW)")

plt.xticks(range(7), jours)

plt.legend(
    title="Année",
    bbox_to_anchor=(1.02, 1),
    loc="upper left"
)

plt.grid(True, alpha=0.3)
plt.tight_layout()

# Sauvegarde
plt.savefig(
    DOSSIER_GRAPHIQUES / "cycle_hebdomadaire_par_annee.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()
#Saisonnalité annuelle
#On cherche à déterminer si la consommation est plus élevée en hiver et plus faible en été, 
# ainsi que l'amplitude des variations saisonnières.
# Extraire le mois (1 = janvier, 12 = décembre)
df["mois"] = df["date"].dt.month

# Consommation moyenne par mois
conso_mois = df.groupby("mois")["consommation_MW"].mean()

plt.figure(figsize=(10, 5))
plt.plot(conso_mois.index, conso_mois.values, marker="o")

plt.title("Consommation moyenne selon le mois")
plt.xlabel("Mois")
plt.ylabel("Consommation moyenne (MW)")

plt.xticks(range(1, 13))
plt.grid(True)
plt.tight_layout()

# Sauvegarde
plt.savefig(
    DOSSIER_GRAPHIQUES / "saisonnalite_annuelle.png",
    dpi=300
)

plt.close()

#Évolution mensuelle de la consommation électrique par année
# Saisonnalité annuelle : une courbe par année

# Extraire l'année et le mois
df["annee"] = df["date"].dt.year
df["mois"] = df["date"].dt.month

# Consommation moyenne pour chaque mois de chaque année
conso_mois_annee = df.groupby(
    ["annee", "mois"]
)["consommation_MW"].mean().unstack(level=0)

plt.figure(figsize=(13, 6))

# Une courbe pour chaque année
for annee in conso_mois_annee.columns:
    plt.plot(
        conso_mois_annee.index,
        conso_mois_annee[annee],
        marker="o",
        markersize=3,
        label=str(annee)
    )

plt.title("Évolution mensuelle de la consommation électrique par année")
plt.xlabel("Mois")
plt.ylabel("Consommation moyenne (MW)")

plt.xticks(
    range(1, 13),
    ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin",
     "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]
)

plt.legend(
    title="Année",
    bbox_to_anchor=(1.02, 1),
    loc="upper left"
)

plt.grid(True, alpha=0.3)
plt.tight_layout()

# Sauvegarde
plt.savefig(
    DOSSIER_GRAPHIQUES / "saisonnalite_par_annee.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()
#Comparer les profils de consommation
#Profil horaire : semaine vs weekend
#Objectif : vérifier si la forme de la courbe journalière dépend du type de journée.
# Consommation moyenne selon l'heure et le weekend
profil = df.groupby(
    ["heure_num", "weekend"]
)["consommation_MW"].mean().unstack()

plt.figure(figsize=(11, 5))

plt.plot(
    profil.index,
    profil[0],
    label="Semaine"
)

plt.plot(
    profil.index,
    profil[1],
    label="Weekend"
)

plt.title("Profil horaire : semaine vs weekend")
plt.xlabel("Heure")
plt.ylabel("Consommation moyenne (MW)")

plt.xticks(range(24))
plt.legend()
plt.grid(True)
plt.tight_layout()

# Sauvegarde
plt.savefig(
    DOSSIER_GRAPHIQUES / "profil_semaine_weekend.png",
    dpi=300
)

plt.close()

#Heatmap : jour de semaine × heure
#Objectif : visualiser simultanément les cycles journaliers et hebdomadaires
# Tableau des consommations moyennes
tableau = df.pivot_table(
    values="consommation_MW",
    index="jour_semaine",
    columns="heure_num",
    aggfunc="mean"
)

plt.figure(figsize=(13, 5))

sns.heatmap(
    tableau,
    cmap="YlOrRd",
    yticklabels=jours
)

plt.title("Consommation moyenne selon le jour et l'heure")
plt.xlabel("Heure")
plt.ylabel("Jour de la semaine")

plt.tight_layout()

# Sauvegarde
plt.savefig(
    DOSSIER_GRAPHIQUES / "heatmap_jour_heure.png",
    dpi=300
)

plt.close()

#Relation entre météo et consommation
#Température et consommation
plt.figure(figsize=(10, 5))

sns.scatterplot(
    data=df,
    x="temperature_moyenne",
    y="consommation_MW",
    alpha=0.2,
    s=10
)

plt.title("Relation entre température et consommation")
plt.xlabel("Température moyenne (°C)")
plt.ylabel("Consommation (MW)")

plt.grid(True)
plt.tight_layout()

# Sauvegarde
plt.savefig(
    DOSSIER_GRAPHIQUES / "temperature_consommation.png",
    dpi=300
)

plt.close()

#Température et consommation selon le mois
# Moyennes mensuelles
moyennes = df.groupby("mois")[
    ["temperature_moyenne", "consommation_MW"]
].mean()

fig, ax1 = plt.subplots(figsize=(10, 5))

# Courbe de consommation
ax1.plot(
    moyennes.index,
    moyennes["consommation_MW"],
    color="blue",
    marker="o"
)

ax1.set_xlabel("Mois")
ax1.set_ylabel("Consommation (MW)", color="blue")
ax1.set_xticks(range(1, 13))

# Deuxième axe pour la température
ax2 = ax1.twinx()

ax2.plot(
    moyennes.index,
    moyennes["temperature_moyenne"],
    color="red",
    marker="o"
)

ax2.set_ylabel("Température (°C)", color="red")

plt.title("Consommation et température selon le mois")
plt.tight_layout()

# Sauvegarde
plt.savefig(
    DOSSIER_GRAPHIQUES / "temperature_consommation_mensuelle.png",
    dpi=300
)

plt.close()
plt.figure(figsize=(9, 5))

sns.boxplot(
    data=df,
    x="jour_ferie",
    y="consommation_MW"
)
#Effet des jours fériés et des vacances
#Jours fériés
#Objectif : comparer la distribution de la consommation entre jours fériés et jours non fériés.
plt.title("Consommation selon les jours fériés")
plt.xlabel("Jour férié (0 = Non, 1 = Oui)")
plt.ylabel("Consommation (MW)")

plt.tight_layout()

# Sauvegarde
plt.savefig(
    DOSSIER_GRAPHIQUES / "consommation_jours_feries.png",
    dpi=300
)

plt.close()

#Vacances scolaires
#Objectif : étudier si les périodes de vacances scolaires présentent un comportement différent.
plt.figure(figsize=(9, 5))

sns.boxplot(
    data=df,
    x="vacances_scolaires",
    y="consommation_MW"
)

plt.title("Consommation et vacances scolaires")
plt.xlabel("Vacances scolaires (0 = Non, 1 = Oui)")
plt.ylabel("Consommation (MW)")

plt.tight_layout()

# Sauvegarde
plt.savefig(
    DOSSIER_GRAPHIQUES / "consommation_vacances.png",
    dpi=300
)

plt.close()
