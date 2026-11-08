# Watts Demain — prévision de la consommation électrique

Projet de données temporelles du Master MALIA. L'objectif est de prévoir, à 14 h le jour J, les 24 consommations horaires de la journée J+1 en France métropolitaine. La consommation est exprimée en MW.

## Données et protocole

Les données combinent la consommation éCO2mix de RTE, les observations SYNOP de Météo-France et un calendrier des jours fériés, week-ends et vacances scolaires. Les stations SYNOP sont retenues si leur couverture dépasse 95 % pour la température et les précipitations sur 2012–2023. La température est interpolée à l'heure et le cumul de pluie sur trois heures est réparti sur les trois heures correspondantes.

Les modèles utilisent le calendrier connu et les observations passées disponibles à l'origine de prévision. La consommation est supposée connue jusqu'à 8 h le jour J. La météo du lendemain n'est pas utilisée comme prédicteur. Les horaires de consommation sont en heure française et la météo est jointe en UTC. Les journées de changement d'heure sont masquées.

L'apprentissage utilise 2012–2023, la validation 2024 et le test final est réservé à 2025. Pour comparer les méthodes sur les mêmes observations, les journées sans historique complet sont exclues. La validation porte ainsi sur 338 jours. Les délais de disponibilité des observations sont des hypothèses du protocole.

## Exécution

Depuis la racine du projet, avec Python 3.11.7 :

```bash
python -m pip install -r requirements.txt
python main.py
```

Les fichiers éCO2mix annuels `.xls` sont attendus dans `data/conso/raw/`. Les fichiers des jours fériés et des vacances scolaires sont attendus dans `data/calendrier/raw/` sous les noms `om-referentiel-jours-feries (1).csv` et `data (3).csv`. Les CSV SYNOP sont lus dans `data/temperature/raw/` et les fichiers manquants sont téléchargés automatiquement. La carte de fond est dans `data/temperature/fond_carte/`.

La chaîne complète peut prendre du temps, notamment pour la météo, la couverture géographique et l'entraînement des modèles. Les sorties des étapes lancées sont remplacées. Pour reprendre avec les données déjà préparées :

```bash
python main.py --depuis 3
```

Les étapes sont numérotées de 0 à 7 dans le tableau ci-dessous. `--jusqua N` permet de s'arrêter après l'étape N. Les scripts peuvent aussi être lancés individuellement depuis la racine, en respectant cet ordre.

## Scripts et sorties

| Étape | Script | Rôle et principales sorties |
|---|---|---|
| 0 | `data/conso/preparer_dataset_eco2mix.py` | Prépare la consommation horaire dans `data/conso/processed/`. |
| 0 | `data/calendrier/data_calendrier_prep.py` | Construit les variables calendaires dans `data/calendrier/processed/`. |
| 0 | `data/temperature/extraction_meteo.py` | Télécharge et prépare SYNOP, sélectionne les stations et calcule les moyennes horaires dans `data/temperature/processed/`. Il utilise `chemins.py` pour les chemins et les fonctions de lecture et d'écriture. |
| 0 | `data/merge/merge.py` | Fusionne les trois sources dans `data/merge/donnees_combinees.csv`. |
| 0 | `data/merge/train_valid_test_split.py` | Crée `train.csv`, `validation.csv` et `test.csv` dans `data/merge/`. |
| 1 | `src/exploration.py` | Produit les graphiques descriptifs et ACF/PACF du train dans `results/analyse_2024/exploration/`. |
| 2 | `src/couverture_geographique.py` | Calcule la couverture géographique des stations et produit une carte dans `couverture_geographique/`. |
| 3 | `src/benchmarks.py` | Évalue la persistance à J8, la semaine précédente et la moyenne des quatre semaines précédentes dans `benchmarks/`. |
| 4 | `src/modeles_statistiques.py` | Ajuste AR(1), AR(2) et ARMA(1,1) sur la différence hebdomadaire dans `statistiques/`. |
| 4 | `src/diagnostics_residus.py` | Produit les ACF des erreurs, les tests de Ljung–Box et les AIC/BIC dans `diagnostics_residus/`. |
| 5 | `src/modeles_ml.py` | Ajuste les régressions linéaire et Ridge, le Random Forest et le Gradient Boosting dans `ml/`. |
| 5 | `src/ablation_variables.py` | Compare trois groupes de variables pour le Random Forest dans `ablation/`. |
| 6 | `src/synthese.py` | Vérifie les prévisions et produit la comparaison globale et la synthèse dans `results/analyse_2024/`. |
| 7 | `src/diagnostics.py` | Analyse les erreurs par heure, saison, calendrier et température, l'énergie quotidienne, les pointes et trois journées d'échec dans `diagnostics/`. |

Les dossiers de résultats indiqués sans chemin complet se trouvent dans `results/analyse_2024/`. Les modèles et benchmarks produisent des prévisions horaires et des scores au format CSV. Les principales sorties communes sont `comparaison_globale.csv`, `previsions_communes.csv`, `CONTROLES.json` et `SYNTHESE.md`. Les graphiques sont au format PNG.

`src/protocole.py` contient les règles communes de sélection des jours, de disponibilité des données et de contrôle des sorties. Il est importé par les autres scripts. `main.py` lance les étapes 0 à 7 dans l'ordre.

## Test final

Après avoir fixé les modèles et le protocole à partir de la validation, l'évaluation sur 2025 se lance séparément :

```bash
python src/evaluation_test.py --confirmer-test
```

`src/evaluation_test.py` réentraîne les modèles avec les données disponibles avant le test, puis enregistre les prévisions, les scores et les jours évalués dans `results/test_2025/`. Il vérifie les sorties de validation et refuse d'écraser un dossier de test existant. Les scores de 2025 sont destinés à l'évaluation finale, après sélection des modèles.
