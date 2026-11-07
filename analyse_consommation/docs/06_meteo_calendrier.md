# Décomposition conjointe : météo et calendrier

## Données et estimation

La fusion canonique a été corrigée selon [l'audit](00_donnees.md). Les modèles
utilisent les mêmes 104 477 heures valides de 2012–2023. Aucun remplissage de
météo manquante. Les indicateurs calendaires sont ceux de la date locale.

Les composantes sont estimées **ensemble** par régression linéaire multiple,
ajustée par moindres carrés ordinaires avec constante, sans pénalisation.
Le rang de la matrice des prédicteurs est vérifié à chaque ajustement. Cela évite de retirer une
saison puis d'attribuer mécaniquement à la météo ce qui reste. Les effets restent
corrélés et associatifs, pas causaux. Leurs contributions en MW sont centrées,
leur niveau moyen reporté dans la constante, et la reconstruction vérifiée.

| Modèle | Ajout ou modification |
|---|---|
| M00 | Tendance linéaire, 3 harmoniques annuelles, profil horaire |
| M01 | Profil spécifique à chaque jour de semaine et heure |
| M02 | Jours fériés |
| M03 | Vacances A/B/C |
| M04 | Température linéaire |
| M05 | Température : max(18−T,0) et max(T−22,0) |
| M06 | Pluie seule, log(1+pluie), ajoutée à M03 |
| M07 | Température à seuils + pluie |
| M08 | Température linéaire par morceaux, nœuds 0,5,10,15,20,25 °C + pluie |
| M09 | Effets fériés par heure, sensibilités chaud/froid par plages de 6 h |
| M10 | M09 avec changements de pente de tendance en 2015,2018,2020 |
| M11–M13 | M10 sans pluie, sans vacances, sans fériés |
| M14–M17 | M09 sans pluie, sans vacances, sans fériés, sans température |

Les nœuds et seuils sont des choix de modèle, pas des seuils universels établis.
M14–M17 ont été ajoutés après la comparaison des 14 premières variantes : c'est
une sélection exploratoire sur les mêmes années internes, pas une confirmation indépendante.

## Évaluation interne

Ajustement sur les années antérieures à chaque année 2021, 2022, 2023, avec une
réestimation annuelle. MAE/RMSE/biais sur 26 076 heures communes. La météo de
l'heure expliquée est observée : cette expérience n'est pas une prévision à J,14 h.
Aucun score de validation 2024 ou de test 2025 n'entre dans cet ajustement.

M09 obtient la meilleure RMSE globale : 2957,2 MW, contre 4882,5 MW pour M03.
L'ablation de la température porte la RMSE à 4857,4 MW ; sans fériés, 3077,3 MW ;
sans vacances, 2995,5 MW ; sans pluie, 2964,8 MW. La pluie a donc un apport
marginal dans cette comparaison. L'absence de vacances donne une MAE légèrement
meilleure : le classement dépend de la métrique.

La température non linéaire est plus utile que sa version linéaire (M04 :
4180,0 MW ; M05 : 3275,9 MW). La tendance plus flexible n'est pas meilleure
globalement : M10 atteint 3307,0 MW, avec un classement variable selon l'année.

## Résidus et interprétation

Pour M09, les ACF d'évaluation par blocs restent proches de 0,947 à 1 h,
0,802 à 24 h et 0,502 à 168 h. Réduire l'amplitude des erreurs n'implique pas
une baisse de toutes leurs corrélations normalisées. D'où l'étape AR suivante.

Les ACF/PACF sont calculées dans les blocs horaires continus, coupés aux trous
et aux changements d'année. On somme les autocovariances biaisées des blocs,
puis on normalise par l'énergie totale ; les nombres de paires sont exportés.
La PACF est descriptive et ne fournit pas un test d'indépendance sur ces données lacunaires.

Les effets fériés, vacances et semaine sont tracés à contexte fixé ; les zones
scolaires corrélées ne permettent pas d'identifier précisément des effets régionaux.
La courbe météo représente une contribution relative, non un effet causal.

Les fichiers de `resultats/06_meteo_calendrier/` distinguent les résidus réajustés
sur 2012–2023 et les erreurs des trois évaluations internes. La sélection des
stations sur un historique plus long et la météo rétrospective restent des limites
pour une future simulation opérationnelle stricte.
