# Trois benchmarks de consommation

Les trois références correspondent aux familles des notes de cours : naïf par
persistance, naïf saisonnier, moyenne historique sur le passé.

Pour chaque heure cible du lendemain :

| Identifiant | Définition |
|---|---|
| `benchmark_persistance` | Répéter la dernière consommation autorisée pour les 24 heures. |
| `benchmark_semaine` | Reprendre le même jour de semaine, à la même heure locale, 7 jours auparavant. |
| `benchmark_4_semaines` | Moyenne arithmétique des valeurs à la même heure locale 7, 14, 21 et 28 jours auparavant. |

La dernière consommation autorisée est J12 h pour l'évaluation interne 2021--2023,
J8 h pour la validation 2024, comme pour les modèles de chaque expérience.
Ce sont des puissances moyennes horaires : leur disponibilité à 14 h reste une
hypothèse du protocole, et non une preuve de publication historique.

Les dates sont recherchées explicitement dans l'index local, sans décaler les
lignes d'un tableau après suppression de trous. Les consommations des journées
de changement d'heure sont masquées. Si une référence manque, la journée cible
est exclue pour **toutes** les méthodes de l'expérience. La moyenne exige les
quatre semaines ; aucune moyenne partielle ni imputation n'est utilisée. Les
benchmarks ne nécessitent aucune donnée météo.

La persistance de **consommation** ne doit pas être confondue avec la persistance
**météo à 48 h**, qui est un scénario de covariables pour la régression + AR.
Les jours fériés ne sont pas corrigés dans ces références simples.

## Mise à jour des comparaisons

Les trois benchmarks remplacent les anciennes références à 7 et 364 jours.
La différenciation descriptive à 364 jours reste étudiée séparément.
Les dates communes sont recalculées : 991 journées internes et 333 journées
de validation. Les variations des scores des modèles proviennent de ce changement
de support, pas d'un nouveau réglage. Les anciens scores de nettoyage conservés
dans `sources/scores_reference.json` ne sont donc plus des attentes numériques
pour les étapes 07/08 ; celles-ci sont contrôlées à partir des prévisions actuelles.

Les fichiers `comparaison.csv`, `previsions.csv` et les graphiques des étapes
07/08 incluent les nouvelles références. Le biais est **observation moins prévision**.
Pour la persistance constante, toutes les heures sont ex aequo pour la pointe :
la convention existante choisit la première heure, donc cette erreur d'heure de
pointe doit être interprétée avec prudence.

## Contrôles

- Formules vérifiées sur une série synthétique, y compris une semaine traversant
  le changement d'heure : la même heure locale est conservée.
- Modifier toutes les consommations après la coupure ne change aucun benchmark.
- Une valeur manquante dans la quatrième semaine empêche la prévision commune.
- Le vérificateur recalcule les trois benchmarks depuis les observations, contrôle
  les dates communes, les 24 prévisions par jour, le signe des erreurs et les scores.
- Le test 2025 n'est pas évalué.

```powershell
python -B analyse_consommation/scripts/prevision_residus_ar.py
python -B analyse_consommation/scripts/validation_meteo_2024.py
python -B analyse_consommation/scripts/verifier_et_synthetiser.py
```
