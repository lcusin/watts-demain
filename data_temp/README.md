# Données météo SYNOP

Ce dossier rassemble les neuf scripts, les archives téléchargées, les données préparées et les graphiques.

- `meteo_synop_2012_2026/brut/` : archives annuelles originales.
- `meteo_synop_2012_2026/prepare/` : données nettoyées, sélection et moyennes.
- `graphiques/` : deux graphiques mensuels et leur tableau CSV.
- `00_chemins.R` : chemins communs, chargé automatiquement par chaque script.

Exécuter les scripts 01 à 09 dans l'ordre pour reconstruire tous les résultats.
Les fichiers existants ont été déplacés : il n'est pas nécessaire de tout relancer.

Depuis la racine du projet :

```r
source("data_temp/09_graphiques_mensuels.R", encoding = "UTF-8")
```

Depuis le dossier `data_temp` :

```r
source("09_graphiques_mensuels.R", encoding = "UTF-8")
```

Les mêmes chemins fonctionnent avec `Rscript`. Le dossier de travail doit être
la racine du projet ou `data_temp`. Les dépendances sont `data.table`, `R.utils`
et `ggplot2`.
