# Meteo et calendrier

Meilleure RMSE interne : M09_interactions. Estimation par moindres carres. Evaluation 2021-2023 avec apprentissage sur les annees precedentes. La meteo observee est un scenario a meteo parfaite. La decomposition descriptive est reajustee sur 2012-2023. Les contributions ne sont pas des effets causaux. Voir ../../docs/06_meteo_calendrier.md.

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
