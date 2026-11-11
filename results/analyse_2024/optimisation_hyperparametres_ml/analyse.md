# Optimisation des hyperparamètres — validation temporelle

## Protocole

- **2012–2022** : apprentissage des configurations candidates.
- **2023** : sélection de la configuration minimisant la RMSE horaire.
- **2012–2023** : réentraînement de la configuration retenue.
- **2024** : comparaison sur les mêmes journées que l'étude principale.
- **2025** : jeu de test non consulté.

L'ensemble des prédicteurs et les règles de disponibilité proviennent de `src/modeles_ml.py` et `src/protocole.py`.

Cette expérience de réglage a été engagée après consultation des résultats 2024 : les scores constituent donc une analyse complémentaire exploratoire. La sélection numérique des paramètres utilise toutefois seulement 2023.

## Résultats

### Random Forest

- Configurations testées sur 2023 : **4**.
- Meilleure RMSE interne 2023 : **2241.14 MW**.
- Paramètres retenus : `{"randomforestregressor__max_depth": 20, "randomforestregressor__max_features": 0.7, "randomforestregressor__min_samples_leaf": 5, "randomforestregressor__n_estimators": 120}`.
- Validation 2024 : MAE **1569.59 MW**, RMSE **2271.36 MW**, biais **-66.80 MW**.
- Écart à la configuration originale **enregistrée** : **-111.82 MW** de RMSE (amélioration).
- Écart à la référence **recalculée dans le même environnement** : **-111.82 MW** de RMSE (amélioration).


### Gradient Boosting

- Configurations testées sur 2023 : **4**.
- Meilleure RMSE interne 2023 : **2482.86 MW**.
- Paramètres retenus : `{"gradientboostingregressor__learning_rate": 0.08, "gradientboostingregressor__max_depth": 3, "gradientboostingregressor__n_estimators": 150}`.
- Validation 2024 : MAE **1800.43 MW**, RMSE **2462.63 MW**, biais **-451.68 MW**.
- Écart à la configuration originale **enregistrée** : **-629.99 MW** de RMSE (amélioration).
- Écart à la référence **recalculée dans le même environnement** : **-629.99 MW** de RMSE (amélioration).


### Ridge

- Configurations testées sur 2023 : **5**.
- Meilleure RMSE interne 2023 : **2594.97 MW**.
- Paramètres retenus : `{"ridge__alpha": 0.1}`.
- Validation 2024 : MAE **2014.17 MW**, RMSE **2686.30 MW**, biais **-380.17 MW**.
- Écart à la configuration originale **enregistrée** : **-47.12 MW** de RMSE (amélioration).
- Écart à la référence **recalculée dans le même environnement** : **-47.12 MW** de RMSE (amélioration).


## Interprétation et limites

Une réduction de RMSE sur 2023 ne garantit pas une amélioration sur 2024. Comparer les écarts de RMSE et les métriques complémentaires avant de conclure.
Les scores de référence historiques sont lus dans les résultats sauvegardés du projet. La référence recalculée est fournie uniquement lorsque l'option --recalculer-reference est utilisée.
Les écarts faibles ne démontrent pas de supériorité statistique ; l'incertitude et la dépendance entre journées restent à étudier.
Les données RTE définitives et le décalage de la convention d'agrégation horaire identifiés ensuite ne sont pas corrigés dans cette expérience : les scores concernent la cible horaire actuellement enregistrée dans les CSV.
Les limites du scénario rétrospectif à J 14 h (publication effective des observations historiques non reconstruite) restent applicables.

## Fichiers

- `reglages_2023.csv` : toutes les configurations évaluées en 2023.
- `comparaison_2024.csv` : scores des configurations retenues sur 2024.
- `previsions_2024.csv` : prévisions horaires des modèles optimisés.
- `execution.json` : versions et empreintes des scripts et données.
