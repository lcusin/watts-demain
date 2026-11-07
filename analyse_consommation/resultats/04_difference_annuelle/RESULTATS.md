# Difference a 364 jours

Comparaison de la meme heure et des references decalees de -1 h et +1 h. Le decalage de 364 jours conserve le jour de semaine. Les residus STL sont retrospectifs : ce ne sont pas des erreurs de prevision. Voir ../../docs/04_difference_annuelle.md.

```text
                    index       n  moyenne_MW    MAE_MW   RMSE_MW  ecart_type_MW  ACF_1  ACF_24  ACF_168
          consommation_MW 96455.0   53262.648 53262.648 54547.527      11769.642  0.982   0.932    0.907
       reference_avant_1h 96455.0    -511.736  4758.138  6552.314       6532.335  0.945   0.874    0.472
               meme_heure 96455.0    -511.607  4262.324  6159.098       6137.845  0.996   0.864    0.403
       reference_apres_1h 96455.0    -511.488  4749.973  6553.842       6533.886  0.946   0.873    0.471
STL_hebdomadaire_standard 96455.0       0.285  1017.442  1493.753       1493.761  0.978   0.457   -0.406
 STL_hebdomadaire_robuste 96455.0      34.040  1496.475  2885.921       2885.735  0.967   0.659   -0.009
```
