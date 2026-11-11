# Benchmark hebdomadaire adaptatif (V1) — analyse de validation 2024

*Analyse régénérée à chaque exécution ; chiffres issus des prévisions enregistrées.*

## Question et protocole

- À J 14 h, prévoir les 24 consommations horaires de J+1.
- Profil pondéré sur 8 semaines antérieures (poids géométriques, décroissance 0.7).
- Ajustement additif du niveau à partir des consommations de J entre 00 h et 08 h (coefficient 1).
- Comparaison sur les mêmes 338 journées et 8112 heures de 2024.
- Les jours de changement d'heure sont masqués dans les historiques ; les données définitives RTE ne garantissent pas la disponibilité historique effective à 14 h.
- Les températures du lendemain sont exploitées seulement pour les diagnostics a posteriori.

## Comparaison globale

| Méthode | MAE (MW) | RMSE (MW) | Biais (MW) |
|---|---:|---:|---:|
| Moyenne hebdomadaire adaptative | 1,816.50 | 2,710.28 | +118.89 |
| Random Forest | 1,644.14 | 2,383.19 | -145.94 |
| Regression lineaire | 2,014.92 | 2,686.24 | -390.01 |
| Ridge | 2,041.19 | 2,733.42 | -296.66 |
| semaine_precedente | 3,213.81 | 4,887.64 | +256.75 |

- La V1 a une MAE de 1,817 MW contre 2,015 MW pour la régression linéaire, mais une RMSE de 2,710 MW contre 2,686 MW : les classements dépendent de la métrique.
- Le Random Forest reste meilleur en RMSE (2,383 MW).
- Un biais positif (+119 MW, défini comme réel moins prédit) correspond à une sous-estimation moyenne.

## Où la méthode réussit-elle ou échoue-t-elle ?

- Meilleure saison : Été (RMSE 1,306 MW sur 92 jours) ; plus difficile : Hiver (RMSE 4,011 MW sur 91 jours).
- Semaine : RMSE 2,926 MW (246 jours) ; week-end : 2,023 MW (92 jours).
- Jours fériés : RMSE 6,167 MW (8 jours) ; autres jours : 2,569 MW (330 jours). Ces catégories peuvent se recouper avec le week-end.
- Heure de plus forte RMSE : 18 h (3,221 MW).
- Les CSV détaillent également les mois, vacances et classes de température observée ; ces facteurs sont associés et n'autorisent pas une attribution causale des erreurs.

## Énergie et pointes

- Erreur absolue moyenne d'énergie : 39,285 MWh/jour (somme des 24 MW horaires × 1 h).
- Erreur absolue moyenne de valeur de pointe : 1,949 MW.
- Erreur absolue moyenne d'heure de pointe : 1.65 h, contre 2.07 h pour Random Forest. La distance entre heures est non circulaire.

## Trois journées les plus difficiles

- 2024-01-08 : RMSE 12,991 MW ; sous-estimation moyenne de 12,019 MW.
- 2024-12-25 : RMSE 10,644 MW ; surestimation moyenne de 9,651 MW.
- 2024-01-22 : RMSE 9,131 MW ; surestimation moyenne de 8,968 MW.

## Discussion et limites

- La forte saisonnalité résiduelle et les jours exceptionnels limitent la transposition brute d'un profil hebdomadaire.
- Les scores de huit jours fériés ne représentent pas une estimation stable de toutes les situations calendaires.
- La RMSE globale doit être recalculée sur toutes les heures : ce n'est pas la moyenne arithmétique des RMSE des saisons.
- Il s'agit d'une simulation rétrospective utilisant les données définitives RTE, et non d'un essai de disponibilité réelle des données à J 14 h.
- Le réglage de cette V1 et les corrections ultérieures ont été explorés avec connaissance de certains résultats 2024. Les comparaisons ultérieures sur 2024 sont donc exploratoires.
- Aucune conclusion de significativité statistique n'est tirée de ces différences ; le test 2025 n'est pas utilisé.
