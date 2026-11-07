# Comparaison STL

STL standard et robuste, compares aux moyennes mobiles sur les memes dates. Les trois echelles sont des experiences independantes. Le lissage utilise le futur : ces scores sont descriptifs. Voir ../../docs/03_stl.md.

```text
     echelle          methode      n   MAE_MW  RMSE_MW  biais_MW  ACF_1  ACF_periode
  journalier   classique_mean 105168 1702.054 2129.927    -0.045  0.861        0.626
  journalier classique_median 105168 1687.256 2151.591    -0.045  0.854        0.634
  journalier     STL_standard 105168  855.082 1209.320    -0.166  0.922       -0.168
  journalier      STL_robuste 105168 1572.953 2998.595 -1179.368  0.947        0.291
hebdomadaire   classique_mean 105024 1737.891 2359.623     0.396  0.915        0.463
hebdomadaire classique_median 105024 1719.523 2379.093     0.391  0.912        0.471
hebdomadaire     STL_standard 105024 1022.838 1505.347    -0.033  0.978       -0.400
hebdomadaire      STL_robuste 105024 1497.636 2892.898    38.327  0.966        0.003
      annuel   classique_mean    132 1641.034 2134.535   -21.136  0.193       -0.372
      annuel classique_median    132 1570.219 2221.798   -21.136  0.188       -0.281
      annuel     STL_standard    132 1386.177 1918.562    -1.842  0.124       -0.590
      annuel      STL_robuste    132 1355.265 2340.715    29.989  0.162       -0.223
```
