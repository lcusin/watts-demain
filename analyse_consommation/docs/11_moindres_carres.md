# Remplacement de Ridge par les moindres carrés

À la demande du groupe, les régressions explicatives et les corrections AR sont
désormais estimées par **moindres carrés ordinaires avec constante**. La
pénalisation de Ridge, fixée précédemment à 100, est supprimée. Le choix vise
une méthode plus facile à rattacher au cours et à expliquer, et non un gain
de performance annoncé à l'avance.

## Ce qui est estimé

Les coefficients minimisent la somme des carrés des écarts entre consommation
observée et valeur ajustée, sur l'apprentissage uniquement. `LinearRegression`
résout ce problème sans pénalisation et sans standardisation explicite.
La régression des résidus sur leurs retards est également ajustée ainsi.
Il s'agit d'une régression suivie d'un AR, pas d'une estimation ARMA conjointe.

Les variables, les interactions et les retards sont conservés pour isoler le
changement d'estimateur. Une fonction de température par morceaux reste linéaire
dans ses coefficients : ses transformations sont des colonnes du tableau de
régression. M09 possède 215 colonnes explicatives, hors constante ; les variantes
plus simples restent comparées. Ce changement ne constitue donc pas, à lui seul,
une réduction du nombre de variables.

## Réestimation et contrôles

Les étapes 06, 07 et 08 ont été entièrement réexécutées : coefficients, résidus,
prévisions, scores et graphiques. Le rang des prédicteurs centrés est égal à leur
nombre de colonnes pour chaque ajustement. Les audits sont exportés dans chaque
dossier sous `audit_moindres_carres.csv`. Ce contrôle garantit l'absence de
redondance exacte détectée, pas l'absence de corrélations fortes ni la stabilité
des coefficients entre périodes.

Un exemple synthétique vérifie la récupération de coefficients et d'une constante
connus. Modifier les cibles après la fin d'apprentissage ne modifie pas ces
coefficients ; ajouter une colonne exactement redondante provoque un échec du
contrôle de rang. Le vérificateur recalcule les métriques depuis les erreurs
exportées et les benchmarks depuis les observations.

Les trois benchmarks et les dates communes sont inchangés : 991 journées
internes et 333 journées en 2024. Les observations 2025 ne sont pas évaluées.
2024 reste une validation déjà consultée, pas un nouveau test indépendant.

## Effet sur les scores

| Comparaison (mêmes dates) | RMSE Ridge, historique (MW) | RMSE moindres carrés (MW) |
|---|---:|---:|
| M09 explicatif, 2021--2023 | 2 952,9 | 2 957,2 |
| M09 + AR saisonnier, 2021--2023 | 1 736,9 | 1 760,5 |
| Sans météo + AR, 2024 | 2 415,6 | 2 545,8 |
| Persistance météo + AR, 2024 | 3 289,4 | 3 359,1 |
| Météo parfaite + AR, 2024 | 1 981,3 | 2 030,5 |

Les scores se dégradent légèrement à modérément, sans inverser le classement des
trois scénarios météo sur les scores globaux. Le classement horaire varie : la
persistance météo fait légèrement mieux que le modèle sans météo à 20 et 21 h,
mais moins bien aux autres heures. Le rapport présente les scores des moindres carrés.
Les scores historiques sont conservés dans `sources/scores_avant_moindres_carres.json`
pour documenter le changement ; ils ne servent pas de résultats actuels.

Reproduction : étapes 6 à 8 de `executer.py`, puis le vérificateur de synthèse
(appelé automatiquement par l'orchestrateur). Aucun nouveau réglage sur 2024
n'a été recherché pour compenser la suppression de la pénalisation.
