# Données météo SYNOP

Ce dossier rassemble les neuf scripts, les archives téléchargées, les données préparées et les graphiques.

Les fichiers `moyennes_reseau_horaires.csv` et `.rds` contiennent une ligne par
heure UTC et cinq colonnes : `date_utc`, `temperature_c_moyenne`,
`temperature_c_ecart_type`, `precipitation_1h_mm_moyenne` et
`precipitation_1h_mm_ecart_type`. Les écarts-types décrivent la dispersion entre stations.
Le script 09 lit directement ce format.

- `meteo_synop_2012_2026/brut/` : archives annuelles originales.
- `meteo_synop_2012_2026/prepare/` : données nettoyées, sélection et moyennes.
- `graphiques/` : deux graphiques mensuels et leur tableau CSV.
- `00_chemins.R` : chemins communs, chargé automatiquement par chaque script.
- `fonctions_moyennes.R` : calcul des moyennes, quantiles et effectifs du script 07.

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
la racine du projet ou `data_temp`. Seul `ggplot2` est nécessaire pour les graphiques.
Les autres traitements utilisent le R de base : `data.frame`, `read.csv`,
`write.csv`, filtres avec `$`, boucles `for`, `aggregate`, `split` et `merge`.
Les fichiers RDS générés sont des tableaux classiques (`data.frame`).
