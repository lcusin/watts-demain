# Couverture géographique des stations SYNOP

## Définition

La couverture temporelle (> 95 % de mesures pour la température et la pluie) ne mesure pas la couverture du territoire. Pour les 37 stations sélectionnées, on calcule ici la part de la **surface métropolitaine** située à moins d'une distance donnée de la station la plus proche, continent et Corse inclus. Les seuils sont descriptifs : ils ne définissent pas un rayon de représentativité climatique.

## Sources et calcul

- Positions de référence : `data/temperature/processed/stations_metropole.csv`, première position par identifiant, comme pour la carte existante.
- Sélection : `data/temperature/processed/stations_selectionnees.csv`.
- Contour : `data/temperature/fond_carte/france.geojson`, fond Natural Earth déjà utilisé pour la carte. Frontières et côtes simplifiées ; ce n'est pas un calcul cadastral.
- Maillage régulier longitude/latitude, cellules retenues si leur centre appartient au territoire. Les trous éventuels des polygones sont exclus.
- Distance par la formule de haversine, rayon terrestre moyen 6 371,0088 km ; aire sphérique des cellules utilisée comme poids, plutôt qu'un comptage non pondéré des points.
- Médiane et quantile à 90 % pondérés par la surface. Aucune pondération par la population, l'altitude ou la consommation.

## Résultats

Au pas de 0,005 degré (environ 0,56 km nord-sud), le contour représente environ 546 424 km² :

| Indicateur | Valeur approximative |
|---|---:|
| Surface à moins de 25 km | 12,1 % |
| Surface à moins de 50 km | 45,1 % |
| Surface à moins de 75 km | 81,8 % |
| Surface à moins de 100 km | 97,3 % |
| Distance moyenne surfacique | 53,5 km |
| Distance médiane surfacique | 53,0 km |
| Quantile à 90 % de la distance | 83,5 km |
| Distance maximale sur la grille | 151,9 km |

La surface estimée est celle du fond utilisé, pas une nouvelle estimation officielle de la superficie française. La distance maximale dépend du maillage.

## Vérification et limites

Calcul répété aux pas 0,02, 0,01 et 0,005 degré. Entre les deux derniers, les proportions à 50 et 100 km varient de moins de 0,01 point de pourcentage. Cette convergence contrôle la discrétisation, pas les erreurs du contour, des coordonnées ou de l'approximation sphérique. Les résultats sont donc arrondis au dixième.

Cette carte décrit la proximité au réseau sélectionné, et non sa disponibilité à chaque heure. Elle ne prouve pas que la moyenne à poids égaux des stations représente la météo moyenne du territoire ou celle des lieux de consommation. Le relief, les microclimats et les déplacements historiques des stations ne sont pas modélisés.

## Reproduction

Depuis la racine du dépôt :

```powershell
python -B analyse_consommation/scripts/couverture_geographique.py
```

Sorties dans `analyse_consommation/resultats/09_couverture_geographique/` : `couverture.csv` (trois résolutions) et `couverture_geographique.png`. Les données et les scores des modèles restent inchangés. Le calcul est indépendant de la chaîne de prévision et n'examine pas les consommations du test 2025.
