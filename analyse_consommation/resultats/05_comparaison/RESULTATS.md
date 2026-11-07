# Comparaison des decompositions

36 variantes horaires et 7 mensuelles. Ci-dessous : cinq plus faibles moyennes des ACF au carre. Ce classement ne mesure pas la qualite predictive. Les lissages sont retrospectifs ; les differences peuvent amplifier le bruit. Les tests Ljung-Box sont indicatifs. Voir ../../docs/05_comparaison.md.

```text
                        methode     n               debut                 fin  moyenne  ecart_type  ACF_1  moyenne_ACF_carree  max_ACF_absolue  Ljung_Box_Q  Ljung_Box_p_indicatif
    STL_hebdomadaire_robuste_D1 87671 2013-07-01 13:00:00 2023-07-02 11:00:00    0.003     730.753  0.047               0.002            0.638    61392.185                    0.0
sans_tendance_365j_D8736_D24_D1 87671 2013-07-01 13:00:00 2023-07-02 11:00:00    0.009     610.347  0.657               0.003            0.657    96254.396                    0.0
             brute_D8736_D24_D1 87671 2013-07-01 13:00:00 2023-07-02 11:00:00    0.010     610.350  0.657               0.003            0.657    96254.831                    0.0
   STL_hebdomadaire_standard_D1 87671 2013-07-01 13:00:00 2023-07-02 11:00:00    0.003     310.193  0.551               0.004            0.551   132416.616                    0.0
    sans_tendance_365j_D8736_D1 87671 2013-07-01 13:00:00 2023-07-02 11:00:00    0.022     548.219  0.622               0.007            0.622   193067.155                    0.0
```
