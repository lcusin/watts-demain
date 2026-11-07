# Données : une seule préparation horaire

## Responsabilités des scripts data

1. `data/conso/preparer_dataset_eco2mix.py` : lecture RTE, moyenne des puissances
   :00/:30, conservation des étiquettes locales et signalement des changements d'heure.
2. `data/calendrier/data_calendrier_prep.py` : calendrier civil français, avec jours
   de semaine, jours fériés et vacances A/B/C ; aucune conversion UTC ici.
3. `data/temperature/extraction_meteo.py` : observations SYNOP UTC, sélection des
   stations, reconstruction horaire et moyenne de réseau. Les heures intermédiaires
   peuvent utiliser la mesure suivante ; la pluie est datée en début d'intervalle.
4. `data/merge/merge.py` : interprétation Europe/Paris des étiquettes RTE, conversion
   UTC, jointure météo et conservation du calendrier local. C'est l'unique fusion.
5. `data/merge/train_valid_test_split.py` : séparation 2012–2023 / 2024 / 2025.

L'étape 0 du point d'entrée relance les étapes 4–5, puis l'audit. Les extractions
ne sont pas relancées inutilement : leurs fichiers préparés sont déjà présents.

## Colonnes et intervalles

| Colonne | Signification |
|---|---|
| `horodatage` | Étiquette locale française de début d'heure ; sans suffixe de fuseau |
| `date_utc` | Instant correspondant en UTC (le nom de colonne précise le fuseau) ; vide si ambigu/inexistant |
| `consommation_MW` | Moyenne des puissances RTE à :00 et :30 |
| `temperature_moyenne` | Température moyenne du réseau à l'instant initial |
| `temperature_ecart_type` | Dispersion spatiale des températures au même instant |
| `precipitation_moyenne` | Moyenne de réseau du cumul sur [h,h+1], déjà daté à h par l’extraction |
| `precipitation_ecart_type` | Dispersion spatiale de ce cumul |
| `jour_changement_heure` | Indicateur déjà fourni par la préparation de consommation ; utilisé pour filtrer les analyses |

Les analyses utilisent directement `temperature_moyenne`, sans moyenne supplémentaire
aux instants :00/:30. La pluie n'est plus décalée après l'extraction. Les écarts-types
restent des dispersions spatiales, pas des intervalles de confiance nationaux.
Le masque de disponibilité est calculé dans les scripts d'analyse à partir des
valeurs présentes et de `jour_changement_heure`, sans ajouter de colonnes au merge.

## Changements d'heure

Les fichiers RTE utilisés contiennent 24 étiquettes par jour, même aux transitions.
Une grille régulière d'étiquettes n'est donc pas une preuve de chronologie UTC.
Le merge laisse sans météo les seules heures ambiguës/inexistantes et conserve
les autres lignes. Les modèles météo/AR maintiennent leur exclusion des journées
de changement d'heure à partir de l'indicateur de consommation, puis excluent les
origines qui n'ont plus l'historique continu nécessaire. Ce choix appartient à
l'analyse, pas à la préparation du fichier fusionné.

Les explorations classiques et différenciations des étapes 1–5 restent sur la
grille d'étiquettes RTE : « 24 h » y désigne 24 créneaux enregistrés. Cette limite
historique est conservée et annoncée ; leurs résultats ne décrivent pas exactement
les intervalles physiques aux changements d'heure. Pour conserver ces journées
en prévision, il faudrait une source documentee qui distingue les deux passages
d'octobre et traite les etiquettes inexistantes de mars. Un champ UTC dans l'API
ne suffit pas, a lui seul, a recuperer les observations absentes.

## Audit et provenance

Les huit points vérifiés contre l'API RTE correspondent exactement aux valeurs
brutes locales : janvier/juillet 2012, 2018, 2023 et deux transitions de 2020.
Ils confirment UTC+1 en hiver et UTC+2 en été sur les exemples vérifiés.
Les réponses et leurs URLs sont dans `sources/verification_rte_api.json`.

L'audit contrôle également l'agrégation de consommation, les indicateurs calendaires
contre leurs sources, la conversion UTC et les valeurs météo de la fusion.
Les effectifs utilisables seront recalculés lors de la prochaine exécution de
l'audit ; les effectifs et scores actuellement enregistrés précèdent cette
adaptation. Il n'y a pas d'imputation.

L'ancienne fusion associait les étiquettes locales à des heures UTC identiques,
donc à des instants différents. Elle est remplacée dans les exports canoniques.
Le test 2025 a été corrigé par le même traitement déterministe, sans calculer ses
performances ni ajuster de modèle. Son empreinte est contrôlée avant/après validation.

Source officielle : https://reseaux-energies-rte.opendatasoft.com/explore/dataset/eco2mix-national-cons-def/api/


## Regle retenue pour les previsions et les benchmarks

Les donnees utilisees proviennent des fichiers annuels telecharges directement
sur le site eco2mix. L'API sert uniquement de verification externe, pas d'extraction.

1. La preparation conserve toutes les consommations et signale les deux derniers
   dimanches de mars et d'octobre avec `jour_changement_heure`.
2. Le calendrier reste en heure francaise. Le merge ajoute UTC pour joindre la meteo ;
   les heures ambigues ou inexistantes ont une date UTC manquante.
3. Dans les previsions, la consommation de ces deux journees devient `NaN` en memoire.
   On ne supprime pas les lignes avant les differences ou les retards.
4. Si la cible ou l'historique necessaire est incomplet, le jour est exclu pour
   toutes les methodes de la meme comparaison. Aucun remplissage n'est effectue.
5. Les benchmarks des quatre semaines exigent les quatre valeurs : une moyenne
   de seulement trois semaines ne remplace pas une reference manquante.

Cette regle est aussi appliquee au script separe `src/benchmark.py`.
Les comparaisons de plusieurs experiences peuvent garder des jours differents
si leurs besoins d'historique different. Il faut utiliser l'intersection des
jours pour comparer directement leurs scores.

Les figures descriptives des etapes 1-5 restent sur la grille RTE complete ;
elles ne constituent pas une evaluation predictive sur les jours de transition.
Aucune donnee brute n'est modifiee. Les resultats et le rapport doivent etre
actualises apres la prochaine execution par l'utilisatrice.
