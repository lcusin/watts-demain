# Validation 2024

Parametres fixes avant 2024 ; previsions J+1 emises a J14, coupure commune J8. La meteo parfaite n'est pas deployable. Les delais de publication sont supposes. Le test 2025 n'est pas evalue. Voir ../../docs/08_validation_2024.md.

```text
             scenario    n   MAE_MW  RMSE_MW  biais_MW
 benchmark_4_semaines 7992 3583.736 5296.269   504.912
benchmark_persistance 7992 5661.014 7054.957  -671.340
    benchmark_semaine 7992 3251.024 4931.780   246.323
       meteo_parfaite 7992 1444.261 2020.497   -98.922
meteo_persistance_48h 7992 2306.501 3350.474     6.630
           sans_meteo 7992 1783.537 2545.757    13.521
```
