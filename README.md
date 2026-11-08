# Watts Demain — prévision de la consommation électrique

Projet de données temporelles du Master 2 MALIA. À 14 h le jour J, nous prévoyons les 24 consommations horaires de J+1 en France métropolitaine (MW). Le scénario utilise le calendrier connu, la consommation supposée disponible jusqu'à J 8 h et la météo passée supposée publiée à temps. Les délais historiques de publication sont des hypothèses, non des faits vérifiés. Aucune observation de J+1 n'entre dans les prédicteurs.

L'apprentissage initial porte sur 2012–2023, la comparaison et la sélection sur 2024, et le test final indépendant sur 2025. Les journées de changement d'heure et celles sans historique requis complet sont exclues des évaluations, tout en conservant la grille horaire pour les retards.

## A. Consulter les résultats existants

**Aucune installation ni exécution n'est nécessaire pour consulter les résultats déjà présents.** Tous les chemins ci-dessous sont relatifs à la racine du dépôt.

| Question | Fichiers à consulter |
|---|---|
| Dix méthodes, validation 2024 (338 jours, 8 112 heures par méthode) | `results/analyse_2024/comparaison_globale.csv` (MAE, RMSE, biais), `previsions_communes.csv` (prévisions horaires), `SYNTHESE.md` et `CONTROLES.json` dans le même dossier. |
| Détail des familles | `results/analyse_2024/benchmarks/`, `statistiques/` et `ml/` : scores, journées, prévisions et traces `execution.json`. |
| Exploration, stations et ablation | `results/analyse_2024/exploration/` (cycles, météo, ACF/PACF), `couverture_geographique/` (carte et mesures), `ablation/comparaison_ablation.csv` et `ablation/comparaison_ablation.png`. |
| Erreurs 2024 | `results/analyse_2024/diagnostics/` (saisons, heures, calendrier, température, énergie, pointes, trois journées d'échec) ; `diagnostics_residus/` (ACF des erreurs AR/ARMA, Ljung-Box, AIC/BIC). |
| Test indépendant 2025 du seul Random Forest | `results/test_2025/comparaison_test_2025.csv`, `previsions_test_2025.csv`, `jours_evalues.csv`, `execution.json` et `figures/`. |
| Rapport | `rapport/main.pdf` ; sources LaTeX et bibliographie dans `rapport/`. |

Les trois références sont la persistance à J 8 h, la semaine précédente et la moyenne des quatre semaines précédentes. Les modèles statistiques sont AR(1), AR(2) et ARMA(1,1) sur la différence hebdomadaire ; les quatre modèles ML sont la régression linéaire, Ridge, Random Forest et Gradient Boosting. Les dix méthodes sont comparées sur les **mêmes journées de 2024**. Le Random Forest est retenu pour sa plus faible RMSE de validation (2 383,19 MW).

## B. Reproduire les analyses 2024

### Environnement et organisation

L'environnement de référence est **Python 3.11.7**. `requirements.txt` fixe NumPy, pandas, Matplotlib, SciPy, scikit-learn, statsmodels, seaborn, `threadpoolctl` et `requests` (utilisé par le téléchargeur RTE). Depuis la racine, avec Python 3.11.7, la commande d'installation vaut sous PowerShell comme sous un terminal Unix :

```sh
python -m pip install -r requirements.txt
```

| Chemin | Rôle |
|---|---|
| `data/conso/`, `data/temperature/`, `data/calendrier/` | Sources dans `raw/`, scripts de préparation et sorties dans `processed/`. Le fond de carte se trouve dans `data/temperature/fond_carte/france.geojson`. |
| `data/merge/` | Fusion des sources, puis `train.csv`, `validation.csv` et `test.csv`. |
| `src/` | Exploration, références, modèles et diagnostics ; `protocole.py` regroupe les règles communes de disponibilité et de sélection des jours. |
| `results/analyse_2024/`, `results/test_2025/` | Résultats et figures déjà produits et versionnés. |
| `rapport/` | Sources LaTeX, bibliographie et PDF ; `rapport/build/` contient les fichiers locaux de compilation, ignorés par Git. |
| `docs/` | Checklist issue du sujet ; `Archives/` contient d'anciens travaux locaux, ignorés par Git et inutiles au pipeline. |

### Sources et préparation

Les **14 archives annuelles RTE éCO2mix 2012–2025 sont déjà présentes** dans `data/conso/raw/`, nommées `eCO2mix_RTE_Annuel-Definitif_<année>.xls`. Malgré leur extension, ce sont des fichiers texte tabulés. Si une archive manque dans une autre copie du projet, le téléchargement facultatif demande un accès au site RTE et utilise `requests` ; par exemple :

```sh
python data/conso/telecharger_eco2mix.py --years 2025
```

Sans `--years`, le téléchargeur parcourt 2012–2025 et conserve les fichiers déjà présents et non vides. `main.py` **ne lance pas** ce téléchargeur. `data/conso/preparer_dataset_eco2mix.py` contrôle les doublons, moyenne les valeurs de :00 et :30 et produit `data/conso/processed/consommation_horaire_eco2mix_2012_2025.csv`.

Les sources calendaires fournies sont `data/calendrier/raw/om-referentiel-jours-feries (1).csv` et `data/calendrier/raw/data (3).csv` (vacances par zone). `data/calendrier/data_calendrier_prep.py` construit `data/calendrier/processed/calendrier_france_2012_2026.csv`, calendrier horaire en heure française.

Les **15 CSV SYNOP 2012–2026 sont déjà présents** dans `data/temperature/raw/`. `data/temperature/extraction_meteo.py` télécharge depuis Météo-France tout CSV absent ou invalide : l'étape peut donc requérir un accès réseau. Il traite les doublons et relevés contradictoires, sélectionne sur **2012–2023** les stations dont les couvertures en température et pluie sur trois heures dépassent chacune 95 %, puis produit `data/temperature/processed/moyennes_reseau_horaires.csv` et des tableaux de stations et de couverture dans `processed/`. La température est interpolée rétrospectivement entre mesures SYNOP ; le cumul de pluie de trois heures est réparti sur les trois heures précédentes.

`data/merge/merge.py` joint consommation et calendrier en heure française, convertit les horodatages vers UTC pour joindre la météo et produit `data/merge/donnees_combinees.csv`. `data/merge/train_valid_test_split.py` contrôle la grille et écrit dans `data/merge/` : `train.csv` (2012–2023), `validation.csv` (2024) et `test.csv` (2025). Ces fichiers sont déjà fournis ; préparer `test.csv` **ne constitue pas une évaluation du test 2025**.

### Chaîne principale et reprise

`main.py` lance ces scripts dans l'ordre avec l'interpréteur Python courant. **Il n'appelle ni `src/evaluation_test.py` ni la génération des figures 2025.** Toute étape relancée peut remplacer ses sorties existantes, y compris les analyses 2024.

| Étape | Scripts exécutés, dans l'ordre | Principales entrées → sorties |
|---|---|---|
| 0 | `data/conso/preparer_dataset_eco2mix.py` ; `data/calendrier/data_calendrier_prep.py` ; `data/temperature/extraction_meteo.py` ; `data/merge/merge.py` ; `data/merge/train_valid_test_split.py` | Sources `raw/` → données `processed/` → `data/merge/donnees_combinees.csv`, `train.csv`, `validation.csv`, `test.csv`. |
| 1 | `src/exploration.py` | `train.csv` → `results/analyse_2024/exploration/`. |
| 2 | `src/couverture_geographique.py` | Stations préparées, `france.geojson` → `results/analyse_2024/couverture_geographique/`. |
| 3 | `src/benchmarks.py` | Train, validation → `results/analyse_2024/benchmarks/`. |
| 4 | `src/modeles_statistiques.py` ; `src/diagnostics_residus.py` | Train, validation → `results/analyse_2024/statistiques/`, puis `diagnostics_residus/`. |
| 5 | `src/modeles_ml.py` ; `src/ablation_variables.py` | Train, validation → `results/analyse_2024/ml/`, puis `ablation/`. |
| 6 | `src/synthese.py` | Sorties et traces des étapes 3 à 5 → `results/analyse_2024/previsions_communes.csv`, `comparaison_globale.csv`, `CONTROLES.json`, `SYNTHESE.md`. |
| 7 | `src/diagnostics.py` | Sorties vérifiées de l'étape 6, validation → `results/analyse_2024/diagnostics/`. |

Pour reconstruire les analyses **2024** depuis les sources, avec les fichiers d'entrée en place :

```sh
python main.py
```

`--depuis N` reprend à l'étape N ; `--jusqua N` s'arrête après l'étape N. Les deux acceptent N de 0 à 7 inclus et peuvent être combinées si le début précède la fin. Sans option, les étapes 0 à 7 s'exécutent. Exemple de reprise lorsque les fichiers préparés, `train.csv` et `validation.csv` existent :

```sh
python main.py --depuis 3
```

L'étape 6 requiert également des sorties **cohérentes** des étapes 3 à 5. Pour préparer uniquement les données et les premières analyses : `python main.py --jusqua 2`. Les étapes météo (0), couverture géographique (2), AR/ARMA (4) et ML avec ablation (5) peuvent être longues. Les sorties déjà fournies évitent tout calcul pour leur consultation.

**Provenance et portabilité.** Les fichiers `execution.json` enregistrent des SHA-256 des octets locaux ; `src/synthese.py` compare les traces 2024 aux fichiers courants. Git peut convertir les fins de ligne LF/CRLF selon le système, et certaines clés enregistrées emploient les séparateurs Windows. Une reprise sur un autre poste à partir des sorties préexistantes peut donc échouer au contrôle de provenance malgré un contenu logique identique. Ne pas interpréter cette seule différence comme un changement du test 2025 : ses traces historiques sont conservées. La portabilité de ce contrôle demande une intervention technique distincte.

### Figures et rapport

Les figures 2024 et les quatre figures 2025 sont déjà présentes. **Facultatif**, le script suivant régénère uniquement les PNG 2025 à partir des prévisions et scores enregistrés. Il ne réentraîne aucun modèle, mais remplace les images dans `results/test_2025/figures/` :

```sh
python src/graphiques_test_2025.py
```

Pour compiler les sources de `rapport/`, il faut une distribution LaTeX fournissant `latexmk`, `biblatex` avec le style APA et **Biber**. Depuis la racine, sous PowerShell ou dans un terminal Unix avec `latexmk` dans le `PATH` :

```sh
cd rapport
latexmk -pdf -outdir=build main.tex
```

Cette commande produit `rapport/build/main.pdf` ; le PDF suivi par Git est `rapport/main.pdf`. La recette VS Code dans `.vscode/` utilise un chemin TeX Live propre à un ordinateur et n'est pas nécessaire ici. Les chemins des figures et de `biblio.bib` sont relatifs à `rapport/`.

## C. Comprendre le test final 2025 déjà réalisé

Le **Random Forest**, choisi d'après sa RMSE de validation 2024, a été le **seul modèle** réentraîné sur les exemples admissibles de 2012 jusqu'au 30 décembre 2024. Ses variables et hyperparamètres n'ont pas changé. Le test indépendant 2025 a **déjà été effectué** sur 337 journées admissibles (8 088 heures) ; ses résultats sont conservés dans `results/test_2025/`. Ils servent à l'évaluation finale et **ne doivent pas être utilisés pour réajuster le modèle**.

`src/evaluation_test.py` est indépendant de `main.py`. Il exige une confirmation explicite via `--confirmer-test` et s'arrête si le dossier `results/test_2025/` existe, afin de ne pas écraser le test enregistré. La consultation des résultats et la reproduction des analyses 2024 ne nécessitent pas son exécution. Les quatre figures 2025 montrent la comparaison des scores 2024/2025, les moyennes journalières sur l'année, quatre semaines saisonnières et la distribution des erreurs.
