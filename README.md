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

## 5. Expérience complémentaire : benchmark hebdomadaire adaptatif

Cette expérience est **indépendante de la chaîne principale** (`main.py`). Elle
ne modifie pas les modèles historiques ni le test final 2025. Elle nécessite
les données `data/merge/train.csv`, `validation.csv`, les dates communes
`results/analyse_2024/benchmarks/jours_evalues.csv` et les prévisions
`results/analyse_2024/previsions_communes.csv` déjà présentes dans le dépôt.

Depuis la racine du projet :

```bash
python src/benchmark_hebdomadaire_adaptatif.py
python src/analyser_benchmark_hebdomadaire_adaptatif.py
python src/experimenter_benchmark_hebdomadaire_v2.py
```

- **V1** : moyenne pondérée des huit profils des mêmes jours de semaine
  précédents, ajustée sur la consommation du matin de J (00–08 h).
- **V2** : ablation des corrections calendaire, proportionnelle, hybride et
  par fêtes annuelles. Le réglage est choisi sur l'année **2023**, appartenant
  au train 2012–2023, et ensuite évalué sur **2024**.
- **Analyse automatique** : les CSV, figures et fichiers `analyse.md` sont
  régénérés par les scripts à chaque exécution. Les sorties restent dans
  `results/analyse_2024/benchmark_hebdomadaire_adaptatif/` et
  `results/analyse_2024/benchmark_hebdomadaire_adaptatif_v2/`.

**Limite méthodologique :** les résultats 2024 ont été consultés durant le
développement de l'expérience. Même avec un choix de paramètres sur 2023, les
comparaisons de cette méthode sur 2024 sont donc **exploratoires**. Les
paramètres des autres méthodes n'ont pas tous été optimisés sur 2023.

Voir `docs/benchmark_hebdomadaire_adaptatif.md` pour les formules, les
justifications, les contrôles et l'interprétation des résultats.

Pour vérifier le calcul sur des données synthétiques :

```bash
python -m unittest discover -s tests -p "test_benchmark_hebdomadaire.py"
```
