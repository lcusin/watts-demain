# Optimisation des hyperparamètres ML — analyse critique des résultats 2024

## Objectif et protocole

Cette étude complémentaire examine si un réglage ciblé des hyperparamètres améliore les prévisions horaires de consommation électrique du lendemain, produites au jour J à 14 h. Les modèles comparés sont Ridge, Random Forest et Gradient Boosting. Les configurations sont ajustées sur 2012–2022, départagées par leur RMSE sur 2023, puis réentraînées sur 2012–2023 avec les hyperparamètres retenus. La comparaison initial/optimisé porte sur exactement les mêmes **338 journées (8 112 heures) de 2024** et sur les mêmes observations réelles. Aucune donnée du test 2025 n'intervient dans cette expérience.

Les scores initiaux 2024 ayant été consultés avant la conception de cette recherche, il s'agit d'une **étude complémentaire exploratoire**. Le choix numérique des réglages sur 2023 réduit le risque d'optimisation directe sur 2024, sans faire de 2024 une validation totalement indépendante du processus de recherche.

## 1. Performances globales

| Modèle | RMSE initiale (MW) | RMSE optimisée (MW) | Gain de RMSE | MAE optimisée (MW) | Biais optimisé (MW) | Journées améliorées |
|---|---:|---:|---:|---:|---:|---:|
| Random Forest | 2 383,19 | **2 271,36** | **111,83 MW (4,69 %)** | **1 569,59** | −66,80 | 211/338 (62,4 %) |
| Gradient Boosting | 3 092,61 | **2 462,63** | **629,98 MW (20,37 %)** | 1 800,43 | −451,68 | 297/338 (87,9 %) |
| Ridge | 2 733,42 | **2 686,30** | **47,12 MW (1,72 %)** | 2 014,17 | −380,17 | 185/338 (54,7 %) |

La forêt aléatoire reste la meilleure méthode en MAE et en RMSE globale ; elle présente également le biais moyen le plus faible en valeur absolue. **Gradient Boosting est le modèle qui profite le plus du réglage**, avec une amélioration sur près de neuf journées sur dix. Les biais négatifs correspondent ici à une *surprévision moyenne* (convention : réel − prédit). Un biais proche de zéro ne suffit cependant pas à garantir de faibles erreurs ponctuelles.

Les paramètres retenus sont les meilleurs **parmi ceux effectivement testés**, et non un optimum global. Plusieurs paramètres des arbres ayant été modifiés conjointement, cette étude ne permet pas d'isoler l'effet causal de chacun.

## 2. La hiérarchie varie selon les situations

### Saisons

| Saison (jours évalués) | Random Forest optimisé | Gradient Boosting optimisé | Ridge optimisé | Meilleur des trois |
|---|---:|---:|---:|---|
| Hiver (91) | **3 378,9** | 3 572,9 | 3 520,5 | Random Forest |
| Printemps (78) | **2 214,0** | 2 509,3 | 2 450,0 | Random Forest |
| Été (92) | **992,3** | 1 404,3 | 2 013,4 | Random Forest |
| Automne (77) | 1 735,5 | **1 673,2** | 2 470,9 | Gradient Boosting |

Toutes les valeurs sont des RMSE en MW. L'hiver demeure la saison la plus difficile pour les trois modèles : optimiser les réglages ne fait pas disparaître ce problème. Random Forest s'améliore en hiver (+167,3 MW) et au printemps (+159,6 MW), mais se dégrade très légèrement en automne (−1,8 MW, soit environ −0,1 %). Ridge se dégrade aussi en automne (−40,6 MW). L'amélioration de Gradient Boosting est observée dans chacune des quatre saisons.

Il serait trompeur de conclure que Gradient Boosting devrait automatiquement être utilisé chaque automne : cette différence provient d'une seule année et le choix d'un modèle saisonnier devrait lui-même être validé sur des années antérieures.

### Jours fériés, week-ends et vacances scolaires

Sur **8 journées fériées évaluées**, Gradient Boosting réduit sa RMSE de 4 788,5 à **3 265,3 MW** (−31,8 %) et améliore chacune de ces huit journées. Random Forest reste meilleur en niveau absolu (**3 064,9 MW**) mais n'améliore que **3 journées sur 8** après optimisation ; son gain de RMSE fériée est modeste (109,7 MW). Ridge reste pratiquement inchangé sur les fériés (3 663,8 à 3 663,6 MW). Il faut éviter toute conclusion générale à partir de seulement huit dates. Il serait utile de vérifier quelles dates fériées du calendrier 2024 ne figurent pas parmi les 338 journées évaluables et pour quelles raisons.

Random Forest est aussi le meilleur des trois en semaine (**2 435,3 MW**) et le week-end (**1 759,5 MW**). Gradient Boosting présente néanmoins des améliorations importantes dans les deux catégories. Les trois modèles s'améliorent globalement en période de vacances scolaires et hors vacances. Ces comparaisons décrivent des sous-groupes de 2024, sans isoler l'effet causal du calendrier : vacances, saison, température et type de jour se recoupent.

### Heures prévues

L'optimisation améliore la RMSE de **23 heures sur 24** pour Random Forest, **24 sur 24** pour Gradient Boosting et **23 sur 24** pour Ridge. Le gain horaire maximal de Random Forest apparaît à **18 h** (+246,3 MW), période intéressante pour la pointe de demande. Gradient Boosting progresse le plus à **04 h** (+1 328,5 MW), mais seulement de +45,2 MW à 13 h. Une amélioration à toutes les heures n'implique pas que l'amplitude du gain soit uniforme.

### Conditions de température

Les classes de température sont construites à partir des **observations réelles 2024 uniquement pour le diagnostic a posteriori** : elles ne doivent pas être interprétées comme des prévisions météorologiques connues à J 14 h. Pour Random Forest, la RMSE augmente après réglage de **53,9 MW** sur les **22 journées à 0–5 °C** et de **188,5 MW** sur les **2 journées à moins de 0 °C**. Ces dernières sont trop peu nombreuses pour une conclusion robuste. Dans les autres classes affichées, Random Forest progresse. Gradient Boosting progresse dans toutes les classes étudiées, tout en conservant des erreurs fortes dans le froid.

## 3. Les critères opérationnels ne désignent pas toujours le même modèle

| Indicateur après optimisation | Random Forest | Gradient Boosting | Ridge | Plus faible erreur |
|---|---:|---:|---:|---|
| Énergie quotidienne : MAE (MWh) | **32 689,4** | 34 984,0 | 33 300,2 | Random Forest |
| Valeur de la pointe : MAE (MW) | 1 754,8 | 1 920,5 | **1 635,6** | Ridge |
| Heure de la pointe : MAE (h) | **1,8** | 2,8 | 2,1 | Random Forest |

Random Forest est le meilleur compromis global parmi ces trois méthodes pour la consommation horaire, l'énergie quotidienne et la localisation de la pointe. **Ridge est toutefois le meilleur sur la hauteur de la pointe**. Le modèle à retenir dépend donc de la fonction de coût retenue : minimiser les écarts horaires ne revient pas nécessairement à prévoir le maximum quotidien le plus précisément possible. Les 24 valeurs d'une journée sont ici sommées en MWh selon la convention horaire actuelle du projet.

## 4. Trois journées à présenter pour une analyse des échecs

Ces cas illustrent des limites différentes. Les scores ne suffisent pas à expliquer les causes : l'analyse doit être complétée par les courbes horaire réel/prédit et, si disponibles, par les données de température et les indicateurs calendaires.

| Journée | Modèle | RMSE avant → après (MW) | Observation vérifiée | Analyse complémentaire nécessaire |
|---|---|---:|---|---|
| **08/01/2024** | Random Forest | 6 757,4 → **7 390,6** | La configuration optimisée dégrade fortement une journée déjà difficile | Vérifier signe du biais, profil des heures de pointe, données du matin et conditions météorologiques |
| **25/12/2024** | Gradient Boosting | 10 214,8 → **7 404,9** | Gain important sur ce jour férié, mais erreur finale toujours très élevée | Comparer le profil réel aux jours fériés historiques, sans prétendre que la fête explique seule l'erreur |
| **25/02/2024** | Gradient Boosting | 2 612,8 → **5 227,7** | Une des plus fortes dégradations individuelles malgré le gain global | Examiner la répartition horaire de l'erreur et les variables retardées ; rechercher un éventuel changement de régime sans l'affirmer a priori |

Autres cas à signaler si nécessaire : **21/11/2024** pour la forte erreur persistante de Random Forest (7 671,9 MW après optimisation), **22/01/2024** pour Ridge (8 089,1 MW), et **16/12/2024** pour la plus forte dégradation de Random Forest (−1 118,3 MW de gain quotidien).

Cette sélection permet de distinguer trois situations : erreur persistante, amélioration réelle mais insuffisante, et détérioration après réglage. Pour le rapport universitaire, afficher les **trois courbes horaires** serait plus convaincant qu'une liste de RMSE.

## 5. Stabilité et incertitude

Une estimation indicative de l'incertitude du gain de RMSE a été réalisée par rééchantillonnage en blocs de semaines (51 blocs). Les intervalles à 95 % fournis sont : **Random Forest [52,2 ; 167,6] MW**, **Gradient Boosting [496,0 ; 792,9] MW**, **Ridge [7,8 ; 86,4] MW**. Ces intervalles sont positifs pour les trois modèles dans l'échantillon étudié, mais ne constituent ni un nouveau test hors échantillon, ni une garantie de performance future. Le choix des blocs, la dépendance temporelle et le fait qu'une seule année soit évaluée limitent l'interprétation.

## 6. Limites méthodologiques et conclusion

1. **Recherche exploratoire :** 2024 avait déjà été consultée avant le lancement de l'étude ; la comparaison reste informative mais pas complètement indépendante de la démarche de recherche. Le test 2025 n'a pas été utilisé.
2. **Données de consommation :** ces résultats utilisent la convention d'agrégation horaire actuelle. La réponse de RTE sur les horodatages de fin de période appelle une correction et une analyse de sensibilité séparée ; les métriques actuelles ne doivent pas être présentées comme celles de la cible horaire corrigée.
3. **Disponibilité à J 14 h :** les archives définitives RTE ne permettent pas de reconstruire exactement les données effectivement publiées à chaque origine historique de prévision. Le scénario est rétrospectif sous hypothèses explicites de disponibilité.
4. **Groupes réduits ou confondus :** huit jours fériés et deux jours à température négative ne permettent pas de généraliser ; les groupes saisons/vacances/météo se chevauchent.
5. **Explication des mécanismes :** plusieurs hyperparamètres ont varié ensemble. Une attribution à `max_depth`, `max_features` ou `learning_rate` exigerait une expérience contrôlée à un seul facteur.

**Conclusion.** La recherche de paramètres sur 2023 améliore les trois modèles en validation 2024. Random Forest conserve la meilleure RMSE globale (**2 271,36 MW**) et les meilleurs scores d'énergie et de localisation de la pointe parmi les trois modèles étudiés. Gradient Boosting réalise le gain relatif le plus important (**−20,37 %**) et améliore une large majorité des journées, mais reste moins précis globalement. Ridge, presque équivalent à la régression linéaire en RMSE, se distingue par la prévision de la valeur maximale quotidienne. Le choix du modèle doit donc reposer sur la métrique pertinente et sur les conditions de prévision, pas uniquement sur un classement global.

**Traçabilité.** Synthèse rédigée à partir de `results/analyse_2024/optimisation_hyperparametres_ml/diagnostics/analyse_detaillee.md` et des sorties d'optimisation fournies. Les explications causales concernant les journées atypiques restent des hypothèses à investiguer, non des faits établis.
