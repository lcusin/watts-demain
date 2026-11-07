# Decompositions classiques

Comparaison sur le train uniquement, aux memes dates par echelle. Les scores mesurent un ajustement retrospectif, pas une prevision. Les echelles horaire et mensuelle ne sont pas directement comparables. Voir ../../docs/01_classique.md.

```text
     echelle         modele estimateur  n_valides  n_bords_non_estimes  MAE_descriptive_MW  RMSE_descriptive_MW  biais_MW  acf_erreur_lag1  acf_erreur_periode
  journalier       additive       mean     105168                   24            1702.054             2129.927    -0.045            0.861               0.626
  journalier       additive     median     105168                   24            1687.256             2151.591    -0.045            0.854               0.634
  journalier multiplicative       mean     105168                   24            1804.108             2242.522    -0.042            0.879               0.699
  journalier multiplicative     median     105168                   24            1775.145             2231.370    -0.042            0.872               0.699
hebdomadaire       additive       mean     105024                  168            1737.891             2359.623     0.396            0.915               0.463
hebdomadaire       additive     median     105024                  168            1719.523             2379.093     0.391            0.912               0.471
hebdomadaire multiplicative       mean     105024                  168            1919.648             2546.046     0.360            0.929               0.539
hebdomadaire multiplicative     median     105024                  168            1922.033             2616.708     0.336            0.928               0.563
      annuel       additive       mean        132                   12            1641.034             2134.535   -21.136            0.193              -0.372
      annuel       additive     median        132                   12            1570.219             2221.798   -21.136            0.188              -0.281
      annuel multiplicative       mean        132                   12            1570.220             2066.811   -15.772            0.151              -0.394
      annuel multiplicative     median        132                   12            1516.369             2142.871   -15.634            0.150              -0.313
```
