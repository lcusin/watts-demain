# Fusion canonique des données

```bash
python data/merge/merge.py
python data/merge/train_valid_test_split.py
```

`donnees_combinees.csv` est l'unique fusion complète. Les fichiers `train.csv`,
`validation.csv` et `test.csv` sont ses sous-ensembles chronologiques, nécessaires
pour séparer apprentissage 2012–2023, validation 2024 et test 2025. Ils ne sont
pas des versions alternatives des mêmes données.

La consommation et le calendrier utilisent les étiquettes civiles françaises.
La météo utilise UTC. `merge.py` effectue la conversion avant la jointure,
conserve `horodatage` local et ajoute `date_utc` explicite. La météo est déjà
préparée par l'extraction : température à h, pluie sur [h,h+1] datée à h.
Le merge ne décale plus la pluie et n'effectue pas de nouvelle interpolation.
Les heures locales ambiguës ou inexistantes restent sans correspondance météo ;
les lignes sont conservées et les journées entières ne sont pas exclues.

Les anciennes colonnes `temperature_moyenne_00_30`, `exclu_changement_heure`
et `utilisable_meteo` ne sont plus produites par ce merge simplifié.
Le découpage train/validation/test utilise uniquement les dates. Les scripts
d'analyse utilisent directement `temperature_moyenne` et `precipitation_moyenne`,
et calculent leur filtre de disponibilité avec `jour_changement_heure`.
Les CSV fusionnés et les résultats existants restent à recalculer avec ces scripts.

Ne pas transformer les dates civiles du calendrier en UTC indépendamment de
la consommation. Ne pas interpréter `horodatage` comme une date UTC. Ne pas
interpoler ou supprimer les lignes manquantes avant de construire des retards :
elles doivent préserver les distances temporelles.

Le réalignement du test 2025 applique le même traitement déterministe ; ce n'est
pas une évaluation. Les analyses et leurs limitations sont centralisées dans
[analyse_consommation](../../analyse_consommation/README.md), notamment
[le contrat de données](../../analyse_consommation/docs/00_donnees.md).


Pour les previsions, les scripts masquent la consommation des jours marques
`jour_changement_heure`, sans supprimer de lignes. Les retards sont calcules
sur cette grille complete. L'evaluation conserve uniquement les journees pour
lesquelles toutes les methodes comparees disposent des valeurs necessaires.
Les fichiers fusionnes conservent les valeurs d'origine et le calendrier francais.
