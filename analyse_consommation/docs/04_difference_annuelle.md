# Différence à 364 jours et alignement horaire

On calcule C(t) − C(t − 8736), où 8736 = 364 × 24 heures enregistrées.
Ce décalage de 52 semaines conserve le jour de semaine et l'heure de l'étiquette.
Il est proche de l'anniversaire, sans lui être identique. Le 29 février ne demande
pas de traitement particulier pour une durée fixe ; les jours fériés ne sont pas
nécessairement alignés. Voir [les conventions horaires](00_donnees.md).

Trois références fixes sont testées :

| Référence | Retard en créneaux horaires | RMSE de la référence (MW) |
|---|---:|---:|
| Une heure avant | 8737 | 6552,3 |
| Même heure | 8736 | 6159,1 |
| Une heure après | 8735 | 6553,8 |

Support commun : 96 455 heures du 30 décembre 2012 à 01 h au 31 décembre 2023
à 23 h. La même heure est meilleure pour chaque année complète 2013–2023.
Les décalages ±1 h réintroduisent un motif quotidien et augmentent la RMSE
approximativement de 6,4 %. Aucun décalage n'est choisi après observation de chaque cible.

La différence reste très autocorrélée : ACF1 ≈ 0,996, ACF24 ≈ 0,864 et ACF168
≈ 0,403. Elle ne retire pas une tendance explicitement estimée. Le pic négatif
vers 8736 peut être créé par la soustraction elle-même : deux différences partagent
une observation avec des signes opposés.

Les résidus STL sont tracés sur les mêmes dates, mais leur erreur de reconstruction
rétrospective ne doit pas être comparée au benchmark comme une erreur de prévision.
Les références sont retrouvées par date et la reconstruction est vérifiée.

Sorties et graphiques : `resultats/04_difference_annuelle/`.
