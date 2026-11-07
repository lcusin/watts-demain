# Analyse et prévision de la consommation électrique

Ce dossier rassemble le travail du 7 novembre 2026, dans l'ordre de raisonnement.
Commencer par [SYNTHESE.md](SYNTHESE.md) pour préparer le rapport et l'oral.
Les sources communes du projet restent dans `data/` : elles ne sont pas dupliquées ici.

## Comparaison principale du rapport

L’étape 9 compare AR(1), AR(2), MA(1), ARMA(1,1) et trois benchmarks. Lire [le protocole](docs/12_modeles_cours.md). Les étapes 6–8 restent des extensions exploratoires météo/calendrier ; elles ne sont pas présentées comme les modèles explicitement enseignés.

## Organisation

| Emplacement | Rôle |
|---|---|
| `executer.py` | Point d'entrée : préparation, analyses, contrôles et synthèse |
| `scripts/` | Code Python, avec chemins relatifs au projet |
| `docs/` | Protocole et interprétation de chaque étape |
| `resultats/01_…` à `10_…` | Figures PNG et tableaux CSV, regroupés par expérience |
| `sources/` | Huit réponses API RTE pour l'audit et scores de référence avant rangement |
| `resultats/CONTROLES.json` | Vérifications, versions et écarts numériques avant/après nettoyage |
| `resultats/INVENTAIRE.csv` | Liste des résultats avec taille et empreinte SHA-256 |

## Ordre des étapes

| N° | Script dans `scripts/` | Question étudiée | Documentation |
|---:|---|---|---|
| 0 | `aligner_meteo_calendrier.py` après les scripts de fusion | Les données représentent-elles les mêmes instants ? | [Données et horaires](docs/00_donnees.md) |
| 1 | `description.py` | Quels profils et quelles décompositions classiques ? | [Classique](docs/01_classique.md) |
| 2 | `tendance_moyenne_mobile.py` | Quelle évolution lente sur douze ans ? | [Méthode et résultats](resultats/02_tendance/RESULTATS.md) |
| 3 | `stl.py` | Quel apport du lissage LOESS et de la robustesse ? | [STL](docs/03_stl.md) |
| 4 | `differenciation_annuelle.py` | Soustraire la même heure 364 jours avant ? | [Différence annuelle](docs/04_difference_annuelle.md) |
| 5 | `comparer_methodes.py` | Quelles combinaisons réduisent les dépendances ? | [Comparaison](docs/05_comparaison.md) |
| 6 | `decomposition_meteo_calendrier.py` | Que peuvent expliquer météo et calendrier ? | [Régression conjointe](docs/06_meteo_calendrier.md) |
| 7 | `prevision_residus_ar.py` | Peut-on prévoir la dépendance résiduelle ? | [Correction AR](docs/07_prevision_ar.md) |
| 8 | `validation_meteo_2024.py` | Quel résultat avec une météo réellement issue du passé ? | [Validation 2024](docs/08_validation_2024.md) |
| 9 | `modeles_cours.py` | Les quatre modèles du cours battent-ils les benchmarks ? | [Protocole et contrôles](docs/12_modeles_cours.md) |

`chemins_analyse.py` centralise les chemins. `verifier_et_synthetiser.py` contrôle
les livrables et génère la synthèse. Leurs noms ne sont pas numérotés, pour garder
des imports Python simples ; l'ordre d'exécution est défini dans `executer.py`.

## Reproduction

Depuis la racine de `watts-demain` :

```bash
python -m pip install -r analyse_consommation/requirements.txt
python -B analyse_consommation/executer.py
```

Le programme utilise les sources déjà présentes dans `data/`. Il ne retélécharge
pas SYNOP ni éCO2mix. La STL robuste hebdomadaire est l'étape la plus coûteuse ;
la durée dépend de la machine. Les résultats existants sont remplacés.

Pour reprendre une étape, lorsque ses entrées existent déjà :

```bash
python -B analyse_consommation/executer.py --depuis 6 --jusqua 8
```

Les figures sont enregistrées, pas ouvertes dans des fenêtres. Les fichiers de
composantes sont conservés lorsqu'ils servent à comparer ou auditer les méthodes.
Les anciennes copies de tables alignées et la fusion temporaire 2012–2024 ont
été retirées ; les données canoniques sont désormais `data/merge/*.csv`.

## Conventions communes

- **Cible :** puissance moyenne horaire en MW, issue des valeurs RTE à :00/:30.
- **Dates :** calendrier civil français ; colonne UTC explicite pour la jointure météo.
- **Découpage :** apprentissage 2012–2023, validation 2024, test 2025.
- **Test 2025 :** réaligné par la même préparation, mais jamais évalué ni utilisé pour ajuster les modèles.
- **Changements d'heure :** journées signalées et exclues des analyses avec météo ; voir les limites de l'exploration en étiquettes locales.
- **Erreurs :** observé moins prévu. MAE/RMSE en MW ; énergie quotidienne en MWh.
- **Supports :** identiques entre variantes d'une même expérience, pas entre toutes les expériences.

Les étapes 1–5 sont descriptives, avec des lissages rétrospectifs. L'étape 6
utilise la météo observée. L'étape 7 simule J,14 h avec météo parfaite et coupure
de consommation à J,12 h. L'étape 8 compare trois scénarios avec une coupure
commune à J,8 h pour contrôler aussi les sources météo interpolées.

Les délais de publication supposés, les révisions des données RTE et la sélection
des stations sur une période plus longue que le train empêchent encore de
qualifier l'ensemble de simulation opérationnelle stricte. Ces limites sont
expliquées dans les documents, pas masquées par les scores.

## Utilisation dans le rendu

Les régressions et corrections AR utilisent les **moindres carrés ordinaires**.
Le [journal du changement d'estimateur](docs/11_moindres_carres.md) décrit les
contrôles et l'effet sur les scores ; les anciens résultats Ridge sont historiques.

Le complément [couverture géographique](docs/09_couverture_geographique.md) mesure
la proximité aux 37 stations. Exécuter séparément
`python -B analyse_consommation/scripts/couverture_geographique.py` pour reproduire
la carte et les contrôles de convergence dans `resultats/09_couverture_geographique/`.
Ce calcul spatial ne réentraîne aucun modèle.

Ne pas placer toutes les figures dans le rapport. La synthèse sélectionne les
principales ; les autres servent de preuves et de diagnostics reproductibles.
Les ACF/PACF des erreurs à plusieurs pas ne doivent pas être présentées comme
des tests exigeant un bruit blanc. Les effets météo/calendaires sont associatifs,
pas causaux. Le meilleur score interne n'est pas une performance de test final.

Le [journal de nettoyage](docs/NETTOYAGE.md) précise les déplacements, suppressions
et vérifications. Les anciens travaux du projet hors de cette analyse gardent
leur propre périmètre ; ils ne font pas partie de ce point d'entrée.

## Recalcul après simplification du merge

Les scripts sont adaptés à la température instantanée et à la pluie déjà datée
en début d'intervalle. Le filtre des jours de changement d'heure reste propre aux
analyses. Les modèles et leurs paramètres de réglage ne sont pas modifiés.

Aucun recalcul n'a été lancé lors de cette adaptation : les résultats existants
et les nombres du rapport correspondent encore à l'ancienne préparation.
Le CSV météo est déjà actualisé ; pour reconstruire la fusion, refaire le découpage
puis relancer toutes les analyses depuis la racine du dépôt :

```bash
python analyse_consommation/executer.py
```

Le lanceur ne télécharge pas les données météo. Pour le faire, exécuter auparavant
`python data/temperature/extraction_meteo.py`. Les contrôles globaux et la synthèse
s'exécutent après la dernière étape (9) ; une exécution partielle s'arrête aux
étapes demandées. Les textes LaTeX ne sont pas réécrits par cette commande.


## Lecture du code

Les scripts actifs se trouvent dans `scripts/`, et leurs sorties dans `resultats/`.
Le dossier `results/` à la racine contient d'anciennes sorties.

- Les étapes suivent le même schéma : lecture, calculs, tableaux, graphiques.
- Les options des régressions sont nommées dans `MODELES`. Par défaut, elles incluent
  le calendrier complet, sans météo ni interactions ; chaque entrée indique les changements.
- `resume.py` écrit les courts bilans `RESULTATS.md`. Les détails méthodologiques restent dans `docs/`.
- Les contrôles de dates, de disponibilité et de reconstruction sont conservés : ils évitent des résultats trompeurs.

La simplification du code ne relance pas les analyses. Les CSV, PNG et le rapport
restent ceux de la dernière exécution jusqu'à ce que les scripts soient relancés.
