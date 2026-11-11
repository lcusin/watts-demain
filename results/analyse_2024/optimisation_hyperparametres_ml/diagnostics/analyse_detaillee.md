# Étude détaillée des modèles ML optimisés — validation 2024

## Protocole et périmètre

Les modèles de référence et les modèles optimisés sont comparés **heure par heure, sur les mêmes 338 journées (8 112 heures)** de 2024. Les hyperparamètres ont été choisis sur 2023, après entraînement sur 2012–2022, puis réentraînés sur 2012–2023. Cette recherche est complémentaire et exploratoire, car les premiers scores 2024 avaient déjà été consultés. Le jeu 2025 n'est ni lu ni modifié.

La version *initiale* provient de `results/analyse_2024/ml/previsions_ml_2024.csv` ; la version *optimisée* de `optimisation_hyperparametres_ml/previsions_2024.csv`. L'égalité des observations réelles, des dates et des heures est contrôlée avant toute comparaison.

**Convention :** gain = RMSE initiale − RMSE optimisée ; un gain positif traduit une amélioration. Biais = consommation réelle − consommation prédite : positif signifie sous-prédiction.

## Résultats globaux

| Modèle | RMSE initiale | RMSE optimisée | Gain (%) | MAE optimisée | Biais optimisé | Jours améliorés (%) |
| --- | --- | --- | --- | --- | --- | --- |
| Random Forest | 2 383.2 | 2 271.4 | 4.7 | 1 569.6 | -66.8 | 62.4 |
| Gradient Boosting | 3 092.6 | 2 462.6 | 20.4 | 1 800.4 | -451.7 | 87.9 |
| Ridge | 2 733.4 | 2 686.3 | 1.7 | 2 014.2 | -380.2 | 54.7 |

- **Gradient Boosting** améliore la RMSE globale : gain de +630.0 MW (+20.4 %), avec 297 journées améliorées sur 338. Ce dernier indicateur évite de réduire la comparaison aux seules grosses erreurs.
- **Random Forest** améliore la RMSE globale : gain de +111.8 MW (+4.7 %), avec 211 journées améliorées sur 338. Ce dernier indicateur évite de réduire la comparaison aux seules grosses erreurs.
- **Ridge** améliore la RMSE globale : gain de +47.1 MW (+1.7 %), avec 185 journées améliorées sur 338. Ce dernier indicateur évite de réduire la comparaison aux seules grosses erreurs.

## Saisons

| Modèle | Saison | Jours | Avant | Après | Gain MW | Gain % |
| --- | --- | --- | --- | --- | --- | --- |
| Gradient Boosting | Automne | 77 | 2 309.1 | 1 673.2 | 635.8 | 27.5 |
| Gradient Boosting | Hiver | 91 | 4 282.9 | 3 572.9 | 710.0 | 16.6 |
| Gradient Boosting | Printemps | 78 | 3 147.5 | 2 509.3 | 638.2 | 20.3 |
| Gradient Boosting | Été | 92 | 2 033.0 | 1 404.3 | 628.7 | 30.9 |
| Random Forest | Automne | 77 | 1 733.7 | 1 735.5 | -1.8 | -0.1 |
| Random Forest | Hiver | 91 | 3 546.2 | 3 378.9 | 167.3 | 4.7 |
| Random Forest | Printemps | 78 | 2 373.6 | 2 214.0 | 159.6 | 6.7 |
| Random Forest | Été | 92 | 1 065.4 | 992.3 | 73.2 | 6.9 |
| Ridge | Automne | 77 | 2 430.3 | 2 470.9 | -40.6 | -1.7 |
| Ridge | Hiver | 91 | 3 643.3 | 3 520.5 | 122.9 | 3.4 |
| Ridge | Printemps | 78 | 2 479.5 | 2 450.0 | 29.5 | 1.2 |
| Ridge | Été | 92 | 2 040.8 | 2 013.4 | 27.4 | 1.3 |

- **Random Forest** : le gain est le plus élevé en hiver (+167.3 MW) et le plus faible en automne (-1.8 MW). Ces contrastes décrivent 2024 ; ils ne prouvent pas une cause saisonnière.
- **Gradient Boosting** : le gain est le plus élevé en hiver (+710.0 MW) et le plus faible en été (+628.7 MW). Ces contrastes décrivent 2024 ; ils ne prouvent pas une cause saisonnière.
- **Ridge** : le gain est le plus élevé en hiver (+122.9 MW) et le plus faible en automne (-40.6 MW). Ces contrastes décrivent 2024 ; ils ne prouvent pas une cause saisonnière.

## Jours fériés, week-ends et vacances

### Jours fériés

| Modèle | Catégorie | Jours | Avant | Après | Gain MW | Jours améliorés % |
| --- | --- | --- | --- | --- | --- | --- |
| Gradient Boosting | Férié | 8 | 4 788.5 | 3 265.3 | 1 523.2 | 100.0 |
| Gradient Boosting | Non férié | 330 | 3 039.8 | 2 439.9 | 599.9 | 87.6 |
| Random Forest | Férié | 8 | 3 174.6 | 3 064.9 | 109.7 | 37.5 |
| Random Forest | Non férié | 330 | 2 360.7 | 2 248.7 | 112.1 | 63.0 |
| Ridge | Férié | 8 | 3 663.8 | 3 663.6 | 0.2 | 75.0 |
| Ridge | Non férié | 330 | 2 706.9 | 2 658.2 | 48.7 | 54.2 |

### Semaine et week-end

| Modèle | Catégorie | Jours | Avant | Après | Gain MW | Jours améliorés % |
| --- | --- | --- | --- | --- | --- | --- |
| Gradient Boosting | Semaine | 246 | 3 222.6 | 2 604.3 | 618.4 | 87.0 |
| Gradient Boosting | Week-end | 92 | 2 714.6 | 2 036.1 | 678.5 | 90.2 |
| Random Forest | Semaine | 246 | 2 564.5 | 2 435.3 | 129.2 | 64.6 |
| Random Forest | Week-end | 92 | 1 811.5 | 1 759.5 | 52.0 | 56.5 |
| Ridge | Semaine | 246 | 2 803.0 | 2 749.7 | 53.3 | 52.8 |
| Ridge | Week-end | 92 | 2 538.0 | 2 509.0 | 29.0 | 59.8 |

### Vacances scolaires

| Modèle | Catégorie | Jours | Avant | Après | Gain MW | Jours améliorés % |
| --- | --- | --- | --- | --- | --- | --- |
| Gradient Boosting | Hors vacances | 202 | 3 192.3 | 2 480.1 | 712.2 | 88.6 |
| Gradient Boosting | Vacances scolaires | 136 | 2 938.4 | 2 436.5 | 501.9 | 86.8 |
| Random Forest | Hors vacances | 202 | 2 394.9 | 2 307.6 | 87.3 | 60.9 |
| Random Forest | Vacances scolaires | 136 | 2 365.6 | 2 216.5 | 149.2 | 64.7 |
| Ridge | Hors vacances | 202 | 2 812.8 | 2 755.9 | 56.9 | 50.5 |
| Ridge | Vacances scolaires | 136 | 2 611.1 | 2 579.5 | 31.6 | 61.0 |

**Prudence : 8 journée(s) fériée(s) seulement** sont évaluables dans cet échantillon. Une erreur exceptionnelle peut faire varier fortement la RMSE de ce groupe. Il ne faut pas généraliser à tous les jours fériés.

## Heures de la journée

Le fichier `comparaison_par_heure.csv` détaille les 24 heures pour chaque modèle ; le graphique `rmse_par_heure.png` compare les deux versions.

- **Random Forest** : RMSE améliorée à 23/24 heures ; gain maximal à 18 h (+246.3 MW), minimal à 01 h (-1.1 MW).
- **Gradient Boosting** : RMSE améliorée à 24/24 heures ; gain maximal à 04 h (+1328.5 MW), minimal à 13 h (+45.2 MW).
- **Ridge** : RMSE améliorée à 23/24 heures ; gain maximal à 00 h (+86.7 MW), minimal à 08 h (-9.0 MW).

## Température et mois

Les groupes de température utilisent la **température effectivement observée en 2024**, uniquement pour analyser les erreurs *après coup*. Ce n'est pas une météo prévisionnelle accessible à J 14 h. Les données manquantes restent identifiées et les moyennes sont calculées par journée.

| Modèle | Température journalière | Jours | Avant | Après | Gain MW |
| --- | --- | --- | --- | --- | --- |
| Gradient Boosting | 0–5 °C | 22 | 4 304.2 | 3 213.3 | 1 090.9 |
| Gradient Boosting | 10–15 °C | 78 | 3 061.3 | 2 456.4 | 604.9 |
| Gradient Boosting | 15–20 °C | 86 | 2 272.6 | 1 456.1 | 816.5 |
| Gradient Boosting | 5–10 °C | 97 | 3 634.5 | 3 156.9 | 477.7 |
| Gradient Boosting | < 0 °C | 2 | 8 805.2 | 6 568.7 | 2 236.5 |
| Gradient Boosting | >= 20 °C | 53 | 2 007.3 | 1 483.8 | 523.5 |
| Random Forest | 0–5 °C | 22 | 3 369.7 | 3 423.7 | -53.9 |
| Random Forest | 10–15 °C | 78 | 2 340.0 | 2 138.2 | 201.9 |
| Random Forest | 15–20 °C | 86 | 1 213.1 | 1 183.2 | 29.9 |
| Random Forest | 5–10 °C | 97 | 3 157.8 | 2 982.9 | 174.9 |
| Random Forest | < 0 °C | 2 | 6 086.3 | 6 274.8 | -188.5 |
| Random Forest | >= 20 °C | 53 | 1 188.7 | 1 125.1 | 63.6 |
| Ridge | 0–5 °C | 22 | 3 646.4 | 3 467.5 | 178.9 |
| Ridge | 10–15 °C | 78 | 2 556.4 | 2 563.6 | -7.3 |
| Ridge | 15–20 °C | 86 | 2 271.0 | 2 273.8 | -2.7 |
| Ridge | 5–10 °C | 97 | 3 216.4 | 3 156.7 | 59.7 |
| Ridge | < 0 °C | 2 | 5 828.8 | 5 179.9 | 648.9 |
| Ridge | >= 20 °C | 53 | 1 981.7 | 1 928.2 | 53.4 |

Consulter aussi `comparaison_par_mois.csv`, `comparaison_par_jour_semaine.csv` et les cartes `gain_saison_heure_*.png`.

## Énergie quotidienne et pointes

Somme des 24 valeurs horaires : énergie en MWh ; les indicateurs de pointe comparent la valeur maximale et son heure, sans hypothèse de continuité entre 23 h et 0 h. Seules les 24 heures retenues par le protocole sont évaluées.

| Modèle | Énergie avant (MWh) | Énergie après (MWh) | Erreur de pointe après (MW) | Erreur heure pointe après (h) |
| --- | --- | --- | --- | --- |
| Gradient Boosting | 43 895.8 | 34 984.0 | 1 920.5 | 2.8 |
| Random Forest | 33 478.2 | 32 689.4 | 1 754.8 | 1.8 |
| Ridge | 34 284.7 | 33 300.2 | 1 635.6 | 2.1 |

## Journées difficiles

### Random Forest

Trois plus fortes erreurs après optimisation :

| Jour | Férié ? | Avant | Après | Gain MW |
| --- | --- | --- | --- | --- |
| 2024-11-21 | Non férié | 7 312.4 | 7 671.9 | -359.5 |
| 2024-01-08 | Non férié | 6 757.4 | 7 390.6 | -633.1 |
| 2024-12-27 | Non férié | 6 922.4 | 7 112.0 | -189.6 |

Trois journées où l'optimisation dégrade le plus la RMSE :

| Jour | Saison | Avant | Après | Gain MW |
| --- | --- | --- | --- | --- |
| 2024-12-16 | Hiver | 2 325.8 | 3 444.1 | -1 118.3 |
| 2024-01-08 | Hiver | 6 757.4 | 7 390.6 | -633.1 |
| 2024-02-26 | Hiver | 3 339.4 | 3 967.8 | -628.4 |

### Gradient Boosting

Trois plus fortes erreurs après optimisation :

| Jour | Férié ? | Avant | Après | Gain MW |
| --- | --- | --- | --- | --- |
| 2024-01-09 | Non férié | 11 458.6 | 8 652.8 | 2 805.8 |
| 2024-12-25 | Férié | 10 214.8 | 7 404.9 | 2 809.9 |
| 2024-01-19 | Non férié | 7 535.3 | 7 279.6 | 255.7 |

Trois journées où l'optimisation dégrade le plus la RMSE :

| Jour | Saison | Avant | Après | Gain MW |
| --- | --- | --- | --- | --- |
| 2024-02-25 | Hiver | 2 612.8 | 5 227.7 | -2 614.9 |
| 2024-04-30 | Printemps | 3 366.6 | 5 147.4 | -1 780.7 |
| 2024-02-26 | Hiver | 3 698.4 | 5 428.4 | -1 730.0 |

### Ridge

Trois plus fortes erreurs après optimisation :

| Jour | Férié ? | Avant | Après | Gain MW |
| --- | --- | --- | --- | --- |
| 2024-01-22 | Non férié | 9 357.0 | 8 089.1 | 1 268.0 |
| 2024-12-24 | Non férié | 7 589.3 | 8 029.2 | -439.9 |
| 2024-01-08 | Non férié | 7 974.9 | 7 823.1 | 151.8 |

Trois journées où l'optimisation dégrade le plus la RMSE :

| Jour | Saison | Avant | Après | Gain MW |
| --- | --- | --- | --- | --- |
| 2024-02-06 | Hiver | 1 084.9 | 2 556.5 | -1 471.6 |
| 2024-11-27 | Automne | 2 672.5 | 3 449.4 | -776.9 |
| 2024-11-20 | Automne | 2 071.8 | 2 831.9 | -760.2 |

Ces dates sont des **cas à examiner** : la métrique ne permet pas à elle seule d'attribuer l'erreur à un événement externe, à la météo ou au modèle.

## Incertitude des gains

Intervalle indicatif à 95 % obtenu en rééchantillonnant des blocs de semaines, pour conserver une part de la dépendance temporelle. Il ne s'agit ni d'un nouveau test hors échantillon ni d'une preuve de causalité ; une seule année 2024 est étudiée.

| Modèle | Blocs semaines | IC bas (MW) | IC haut (MW) |
| --- | --- | --- | --- |
| Random Forest | 51 | 52.2 | 167.6 |
| Gradient Boosting | 51 | 496.0 | 792.9 |
| Ridge | 51 | 7.8 | 86.4 |

## Limites et conclusion

- Le choix numérique des réglages a été fait en 2023, mais l'expérience a été imaginée après examen de 2024 : elle reste exploratoire.
- Les résultats utilisent les fichiers horaires **actuels** ; la convention d'agrégation des demi-heures RTE identifiée ensuite n'est pas corrigée dans cette expérience.
- Les fichiers définitifs RTE ne reconstituent pas exactement ce qui était publié à J 14 h lors de chaque date historique.
- Les températures observées du lendemain servent seulement à segmenter *a posteriori* les erreurs, jamais à générer les prévisions.
- Des moyennes par saison, vacances et fériés ne suffisent pas pour affirmer la robustesse hors de 2024.

Les tableaux détaillés et graphiques sont rangés dans ce dossier. La lecture des cas d'échec doit accompagner la comparaison des scores.
