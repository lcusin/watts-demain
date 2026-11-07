# Synthèse de validation 2024

338 journées communes, 10 modèles et benchmarks.

Plus faible RMSE : **Random Forest**, 2383.2 MW.

| Modèle | MAE (MW) | RMSE (MW) | Biais (MW) |
|---|---:|---:|---:|
| Random Forest | 1644.1 | 2383.2 | -145.9 |
| Regression lineaire | 2014.9 | 2686.2 | -390.0 |
| Ridge | 2041.2 | 2733.4 | -296.7 |
| Gradient Boosting | 2324.0 | 3092.6 | -646.8 |
| ARMA(1,1) | 2147.4 | 3290.7 | 88.8 |
| AR(2) | 2177.3 | 3298.0 | 113.7 |
| AR(1) | 2230.2 | 3408.0 | 80.1 |
| semaine_precedente | 3213.8 | 4887.6 | 256.8 |
| moyenne_4_semaines | 3704.8 | 5413.3 | 291.3 |
| persistance | 5658.6 | 7055.6 | -778.1 |

Classement sur la validation, pas sur un test indépendant. Test 2025 non évalué. Les délais de publication restent des hypothèses ; les contrôles numériques ne prouvent pas la disponibilité historique des données. Les diagnostics complètent ces scores.
