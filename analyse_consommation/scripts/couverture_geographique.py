"""Proximité des stations retenues : surface métropolitaine, sans pondération démographique."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as Contour
import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[2]
METEO = RACINE / "data/temperature"
SORTIE = RACINE / "analyse_consommation/resultats/09_couverture_geographique"
RAYON = 6371.0088  # Terre sphérique, kilomètres.


def calculer(pas, polygones, stations):
    # Centres des cellules : une même grille couvre continent et Corse.
    lon = np.arange(-5.5 + pas / 2, 10, pas)
    lat = np.arange(41 + pas / 2, 51.5, pas)
    xx, yy = np.meshgrid(lon, lat)
    points = np.column_stack([xx.ravel(), yy.ravel()])
    dedans = np.zeros(len(points), dtype=bool)
    for polygone in polygones:
        masque = Contour(polygone[0]).contains_points(points)
        for trou in polygone[1:]:
            masque &= ~Contour(trou).contains_points(points)
        dedans |= masque
    x, y = np.radians(points[dedans]).T
    distance = np.full(len(x), np.inf)
    for station in stations.itertuples():
        a, b = np.radians([station.lon, station.lat])
        h = np.sin((y - b) / 2)**2 + np.cos(y) * np.cos(b) * np.sin((x - a) / 2)**2
        distance = np.minimum(distance, 2 * RAYON * np.arcsin(np.sqrt(np.clip(h, 0, 1))))
    # Aire sphérique exacte de chaque cellule ; frontière approchée par son centre.
    demi = np.radians(pas / 2)
    poids = RAYON**2 * np.radians(pas) * (np.sin(y + demi) - np.sin(y - demi))
    ordre = np.argsort(distance)
    cumul = np.cumsum(poids[ordre]) / poids.sum()
    bilan = {"pas_degres": pas, "nb_stations": len(stations), "surface_km2": poids.sum(),
             "distance_moyenne_km": np.average(distance, weights=poids),
             "distance_mediane_km": np.interp(.5, cumul, distance[ordre]),
             "distance_p90_km": np.interp(.9, cumul, distance[ordre]),
             "distance_max_grille_km": distance.max()}
    for seuil in (25, 50, 75, 100):
        bilan[f"surface_moins_{seuil}km_pct"] = 100 * poids[distance <= seuil].sum() / poids.sum()
    image = np.full(xx.size, np.nan)
    image[dedans] = distance
    return bilan, lon, lat, image.reshape(xx.shape)


def main():
    selection = pd.read_csv(METEO / "processed/stations_selectionnees.csv", dtype={"geo_id_wmo": str})
    positions = pd.read_csv(METEO / "processed/stations_metropole.csv", dtype={"geo_id_wmo": str})
    positions = positions.drop_duplicates("geo_id_wmo")
    stations = selection[["geo_id_wmo"]].merge(positions[["geo_id_wmo", "lat", "lon"]],
                                               on="geo_id_wmo", how="left", validate="one_to_one")
    assert len(stations) > 0 and stations[["lat", "lon"]].notna().all().all()
    fond = json.loads((METEO / "fond_carte/france.geojson").read_text(encoding="utf-8"))
    polygones = fond["geometry"]["coordinates"]
    bilans = []
    for pas in (.02, .01, .005):
        bilan, lon, lat, distances = calculer(pas, polygones, stations)
        bilans.append(bilan)
    SORTIE.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(bilans).to_csv(SORTIE / "couverture.csv", index=False)
    # Contrôle de convergence du maillage, pas de l'exactitude du fond géographique.
    for seuil in (50, 100):
        cle = f"surface_moins_{seuil}km_pct"
        assert abs(bilans[-1][cle] - bilans[-2][cle]) < .1
    fig, ax = plt.subplots(figsize=(7, 6))
    carte = ax.pcolormesh(lon, lat, distances, shading="nearest", cmap="YlGnBu", vmin=0, vmax=150)
    for polygone in polygones:
        contour = np.asarray(polygone[0])
        ax.plot(contour[:, 0], contour[:, 1], color=".3", lw=.6)
    ax.scatter(stations.lon, stations.lat, s=16, c="black", edgecolors="white", linewidths=.4,
               label=f"{len(stations)} stations retenues")
    ax.set(xlim=(-5.5, 10), ylim=(41, 51.5), xlabel="Longitude (°)", ylabel="Latitude (°)",
           title="Distance à la station SYNOP la plus proche")
    ax.set_aspect(1 / np.cos(np.radians(46)))
    ax.legend(loc="upper left", fontsize=8)
    fig.colorbar(carte, ax=ax, label="Distance (km)", shrink=.8)
    fig.tight_layout()
    fig.savefig(SORTIE / "couverture_geographique.png", dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    main()
