# Watts Demain — Prévision de la consommation électrique

Ce projet vise à prévoir, à **14 h le jour J**, les 24 consommations électriques horaires du lendemain (J+1) en France métropolitaine, exprimées en MW.

Les prédictions utilisent les données historiques de consommation RTE éCO2mix, les observations météorologiques SYNOP de Météo-France et les informations calendaires. Seules les informations supposées disponibles au moment de la prévision sont utilisées.

## 1. Méthodologie

Les données sont réparties chronologiquement :

- **2012–2023** : apprentissage.
- **2024** : validation et comparaison des modèles.
- **2025** : test final indépendant.

Dix méthodes sont comparées sur les mêmes 338 journées admissibles de 2024 : trois benchmarks, trois modèles statistiques (AR/ARMA) et quatre modèles de machine learning.

Le **Random Forest**, sélectionné pour sa meilleure RMSE en validation (2 383,19 MW), obtient une RMSE de **2 306,95 MW** sur les 337 journées évaluées en 2025.

## 2. Installation

Environnement de référence : **Python 3.11.7**.

Installer les dépendances depuis la racine du dépôt :

```bash
python -m pip install -r requirements.txt
```

Les données nécessaires et les résultats des analyses sont déjà présents dans le dépôt.

## 3. Exécution

La chaîne principale est orchestrée par `main.py` :

| Étape | Traitement |
|---|---|
| 0 | Préparation et fusion des données |
| 1 | Exploration temporelle |
| 2 | Couverture géographique des stations |
| 3 | Benchmarks |
| 4 | Modèles statistiques AR/ARMA |
| 5 | Modèles ML et ablation |
| 6 | Synthèse et comparaison |
| 7 | Diagnostics des erreurs |

Pour reproduire les analyses 2024 :

```bash
python main.py
```

Pour reprendre à une étape précise :

```bash
python main.py --depuis 3
```

Il est également possible de limiter l'exécution avec `--jusqua N`.

**Attention :** l'exécution peut remplacer les résultats 2024 déjà présents et certaines étapes sont coûteuses. Une reprise nécessite les données et sorties des étapes précédentes.

## 4. Résultats

Les principaux fichiers sont disponibles dans :

- `results/analyse_2024/comparaison_globale.csv` : scores des dix méthodes.
- `results/analyse_2024/exploration/` : analyses temporelles et météorologiques.
- `results/analyse_2024/ablation/` : contribution des groupes de variables.
- `results/analyse_2024/diagnostics/` : analyse des erreurs.
- `results/test_2025/` : résultats du test final indépendant et figures.

**Le test 2025 est déjà terminé.** Seul le Random Forest a été réentraîné, avec ses hyperparamètres conservés. Il n'est pas nécessaire de relancer `src/evaluation_test.py`.
