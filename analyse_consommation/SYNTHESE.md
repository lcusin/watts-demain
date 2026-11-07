# Synthese des resultats

Les tableaux ci-dessous ont des supports differents : comparer les modeles au sein de chaque experience.
Le test 2025 n'est pas evalue. La meteo parfaite n'est pas disponible en conditions reelles.
Voir [le guide](README.md) pour les methodes, figures et limites.

## Modeles du cours et benchmarks

```text
          periode                modele     n   MAE_MW   RMSE_MW  biais_MW
interne_2021_2023                   AR1 25272 8303.052 11618.640  -333.763
interne_2021_2023                   AR2 25272 5993.946  8022.487  -196.448
interne_2021_2023                ARMA11 25272 6997.671  9540.103  -252.764
interne_2021_2023                   MA1 25272 6637.790  8968.518  -249.215
interne_2021_2023  benchmark_4_semaines 25272 4294.219  5978.543   -55.140
interne_2021_2023 benchmark_persistance 25272 6066.371  7585.287 -1613.954
interne_2021_2023     benchmark_semaine 25272 3592.765  5388.438   -55.908
  validation_2024                   AR1  8448 8519.189 11860.672  -401.408
  validation_2024                   AR2  8448 6151.605  8210.493  -244.366
  validation_2024                ARMA11  8448 7194.068  9784.315  -309.936
  validation_2024                   MA1  8448 6606.299  8838.585  -278.868
  validation_2024  benchmark_4_semaines  8448 3689.888  5362.063   231.706
  validation_2024 benchmark_persistance  8448 5716.338  7119.106  -697.560
  validation_2024     benchmark_semaine  8448 3225.532  4860.412   159.524
```

## Regression meteo et calendrier

```text
                  modele   MAE_MW  RMSE_MW  biais_MW     n
        M09_interactions 2268.875 2954.622  -767.482 26076
      M14_M09_sans_pluie 2266.988 2962.413  -765.756 26076
   M15_M09_sans_vacances 2257.204 2993.154  -748.579 26076
       M08_splines_pluie 2369.141 3053.397  -742.921 26076
     M16_M09_sans_feries 2348.892 3074.923  -776.574 26076
        M07_seuils_pluie 2547.914 3273.406  -629.954 26076
  M05_temperature_seuils 2544.894 3273.860  -631.657 26076
   M10_tendance_flexible 2578.257 3304.294  -252.578 26076
          M11_sans_pluie 2577.034 3305.347  -251.718 26076
       M12_sans_vacances 2570.357 3338.850  -203.127 26076
         M13_sans_feries 2651.059 3407.258  -278.692 26076
M04_temperature_lineaire 3251.598 4179.503  -603.958 26076
M17_M09_sans_temperature 3610.341 4857.401  -516.950 26076
         M06_pluie_seule 3633.053 4874.265  -517.107 26076
            M03_vacances 3641.125 4882.452  -516.442 26076
              M02_feries 3687.229 5017.312  -484.153 26076
             M01_semaine 3740.845 5124.992  -488.700 26076
             M00_saisons 4469.027 5839.658  -498.091 26076
```

## Correction AR, meteo parfaite

```text
               modele  jours   MAE_MW  RMSE_MW  biais_MW  MAE_energie_MWh  MAE_pointe_MW  MAE_heure_pointe
    M09_AR_saisonnier    991 1200.070 1750.963  -119.230        23665.348       1048.380             1.631
         M09_AR_court    991 1938.466 2561.541  -597.905        39959.884       1744.492             2.420
             M09_seul    991 2193.137 2876.918  -703.875        46892.553       1975.025             2.461
    benchmark_semaine    991 3520.291 5336.330   -84.709        81558.144       3736.861             2.083
 benchmark_4_semaines    991 4249.452 5967.564   -97.190        99093.692       4419.834             1.882
benchmark_persistance    991 6687.026 8047.700 -5513.423       143775.168       3163.112            13.375
```

## Validation des scenarios meteo

```text
             scenario    n   MAE_MW  RMSE_MW  biais_MW
 benchmark_4_semaines 7992 3583.736 5296.269   504.912
benchmark_persistance 7992 5661.014 7054.957  -671.340
    benchmark_semaine 7992 3251.024 4931.780   246.323
       meteo_parfaite 7992 1444.261 2020.497   -98.922
meteo_persistance_48h 7992 2306.501 3350.474     6.630
           sans_meteo 7992 1783.537 2545.757    13.521
```
