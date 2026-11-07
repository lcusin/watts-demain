# Correction autoregressive

Previsions J+1 emises a J14, consommation disponible jusqu'a J12, meteo parfaite. Les methodes sont comparees sur les memes jours de 2021-2023. Les erreurs J+1 sont distinctes des innovations a un pas. Voir ../../docs/07_prevision_ar.md.

```text
               modele  jours   MAE_MW  RMSE_MW  biais_MW  MAE_energie_MWh  MAE_pointe_MW  MAE_heure_pointe
    M09_AR_saisonnier    991 1200.070 1750.963  -119.230        23665.348       1048.380             1.631
         M09_AR_court    991 1938.466 2561.541  -597.905        39959.884       1744.492             2.420
             M09_seul    991 2193.137 2876.918  -703.875        46892.553       1975.025             2.461
    benchmark_semaine    991 3520.291 5336.330   -84.709        81558.144       3736.861             2.083
 benchmark_4_semaines    991 4249.452 5967.564   -97.190        99093.692       4419.834             1.882
benchmark_persistance    991 6687.026 8047.700 -5513.423       143775.168       3163.112            13.375
```
