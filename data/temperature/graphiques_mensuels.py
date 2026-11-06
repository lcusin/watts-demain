"""Exporter le bilan mensuel en CSV et afficher les deux graphiques."""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import json
from matplotlib.patches import Polygon
from chemins import RACINE, PREPARE, GRAPHIQUES, lire
from chemins import PREPARE, GRAPHIQUES, lire, sauver

x = lire(PREPARE / "moyennes_reseau_horaires.csv").sort_values("date_utc")
assert not x.empty and x.date_utc.notna().all() and not x.date_utc.duplicated().any()
assert x.date_utc.diff().dropna().eq(pd.Timedelta(hours=1)).all()
bilans = []
for v in ["temperature_c", "precipitation_1h_mm"]:
    dates = x.date_utc if v == "temperature_c" else x.date_utc - pd.Timedelta(hours=1)
    valeurs = x[v + "_moyenne"]
    for mois, s in valeurs.groupby(dates.dt.strftime("%Y-%m-01")):
        debut = pd.Timestamp(mois)
        attendues = debut.days_in_month * 24
        n = s.count()
        valeur = s.mean() if v == "temperature_c" else s.sum(min_count=1)
        bilans.append({"variable": v, "mois_debut": mois, "nb_heures": len(s),
            "nb_heures_valides": n, "heures_attendues": attendues, "valeur": valeur,
            "annee": debut.year, "mois": debut.month, "couverture_horaire_pct": 100 * n / attendues,
            "mois_entier": len(s) == attendues,
            "completude": "Toutes les heures" if n == attendues else "Heures manquantes"})
mensuel = pd.DataFrame(bilans).sort_values(["variable", "mois_debut"])
mensuel["affiche"] = mensuel.mois_entier & mensuel.couverture_horaire_pct.ge(95) & mensuel.annee.ge(2012)
sauver(mensuel, GRAPHIQUES / "resume_mensuel.csv")
annees = sorted(mensuel.loc[mensuel.annee.ge(2012), "annee"].unique())
couleurs = dict(zip(annees, plt.get_cmap("tab20")(np.linspace(0, 1, len(annees)))))
for v, titre, unite in [("temperature_c", "Temperature moyenne mensuelle", "Temperature (°C)"),
                         ("precipitation_1h_mm", "Precipitations mensuelles", "Cumul disponible (mm)")]:
    fig, ax = plt.subplots(figsize=(12, 7))
    for annee in annees:
        s = mensuel.loc[mensuel.variable.eq(v) & mensuel.annee.eq(annee)].sort_values("mois")
        ax.plot(s.mois, s.valeur.where(s.affiche), color=couleurs[annee], label=str(annee))
        for complet in (True, False):
            points = s.loc[s.affiche & s.completude.eq("Toutes les heures").eq(complet)]
            ax.scatter(points.mois, points.valeur, edgecolors=couleurs[annee],
                       facecolors=couleurs[annee] if complet else "none")
    ax.set(title=titre, ylabel=unite, xticks=range(1, 13),
           xticklabels=["Jan", "Fev", "Mar", "Avr", "Mai", "Juin", "Juil", "Aout", "Sep", "Oct", "Nov", "Dec"])
    ax.legend(title="Annee", ncol=3)
    ax.grid(alpha=.2)
    fig.text(.1, .02, "Poids egaux ; calendrier UTC. Mois tronques ou couverture < 95 % exclus.\n"
             "Point creux : heures manquantes ; cumul de pluie partiel, non corrige.")
    fig.tight_layout(rect=(0, .07, 1, 1))
# Pas d'export PNG : seules les donnees CSV sont ecrites.
plt.show()

"""Carte fixe des stations retenues pour les moyennes meteorologiques."""
selection = lire(PREPARE / "stations_selectionnees.csv")
positions = lire(PREPARE / "stations_metropole.csv")
# Une position de reference par station, comme dans l'inventaire.
positions = positions.drop_duplicates("geo_id_wmo")
stations = selection.merge(positions, on="geo_id_wmo", validate="one_to_one")
assert len(stations) == len(selection)
assert stations[["lat", "lon"]].notna().all().all()

# Fond Natural Earth conserve localement : aucune connexion necessaire.
fond = json.loads((RACINE / "fond_carte/france.geojson").read_text(encoding="utf-8"))
fig, ax = plt.subplots(figsize=(8, 8))
for polygone in fond["geometry"]["coordinates"]:
    ax.add_patch(Polygon(polygone[0], facecolor="#f0f0f0",
                         edgecolor="#666666", linewidth=0.6))

ax.scatter(stations.lon, stations.lat, s=38, color="#007f99",
           edgecolors="white", linewidths=0.6, zorder=3,
           label=f"{len(stations)} stations sélectionnées")
ax.set(xlim=(-5.5, 10), ylim=(41, 51.5), xlabel="Longitude (°)",
       ylabel="Latitude (°)", title="Stations SYNOP retenues — France métropolitaine")
ax.set_aspect(1 / 0.694)  # Correction de l'echelle des longitudes vers 46° N.
ax.legend(loc="upper left", frameon=False)
ax.grid(alpha=0.15)
fig.text(0.5, 0.02, "Couverture > 95 % en température et précipitations\n"
         "Stations : Météo-France SYNOP · Fond : Natural Earth (domaine public)",
         ha="center", fontsize=9)
fig.tight_layout(rect=(0, 0.06, 1, 1))
GRAPHIQUES.mkdir(parents=True, exist_ok=True)
fig.savefig(GRAPHIQUES / "carte_stations.png", dpi=300)
plt.close(fig)

