# Modèles du cours : protocole fixé avant le calcul

Les slides `02-modelisation-slides.pdf` présentent les candidats AR(1), AR(2), MA(1) et ARMA(1,1) (page PDF 33), l'estimation par maximum de vraisemblance (34), AIC/BIC (35) et les diagnostics des résidus (39–41). Les slides de prévision présentent les benchmarks (20) et la validation temporelle (40–41). Les numéros désignent les pages PDF, pas les compteurs imprimés.

La régression à 215 variables et sa correction AR restent des extensions exploratoires dans les étapes 6–8. Elles ne sont pas présentées comme un modèle explicitement enseigné. Le nouveau script `modeles_cours.py` constitue l'étape 9 du lanceur ; ses sorties sont dans `resultats/10_modeles_cours` (le dossier 09 contient la couverture géographique).

## Choix et justification

- Transformer la puissance horaire par `z = y.diff(24).diff()`, soit `(1-B)(1-B24)y`. La différence quotidienne vise le cycle de 24 heures ; la première différence vise la persistance lente restante. C'est une hypothèse simple issue de l'exploration, pas une preuve de stationnarité ni une transformation optimale. Les diagnostics peuvent révéler une surdifférenciation ou des cycles non traités.
- Aucun lissage centré, météo future ou ajustement sur 2025. La différence de 364 jours reste descriptive ; elle n'est pas cumulée avec les différences retenues pour cette expérience.
- Les quatre ARMA sont estimés sans constante sur cette même série, avec contraintes de stationnarité et d'inversibilité. La puissance est divisée par 1000 pour l'optimisation, puis reconvertie en MW. AIC et BIC ne sont comparables qu'entre modèles d'une même année, sur les mêmes observations et la même transformation.
- Fenêtre d'estimation fixée à deux ans, réestimation annuelle. Les observations nécessaires au calcul des premières différences peuvent précéder cette fenêtre de 25 heures, mais restent passées. Les années internes sont 2021, 2022 et 2023 ; le modèle est retenu par RMSE agrégée sur ces trois années. Aucun réglage selon 2024 ; cette année est une validation déjà consultée dans les expériences précédentes, pas un test final vierge.
- Chaque prévision est produite à J14, avec une coupure conservatrice à J8 identique pour tous. Les paramètres restent fixes dans l'année, mais l'état filtré est mis à jour avec les nouvelles observations autorisées. La dernière moyenne connue inclut J8:30, supposée publiée avant J14.
- Prévoir récursivement toutes les heures après J8 jusqu'à J+1 à 23 h, puis conserver les 24 heures cibles. L'inversion utilise `y[t] = z[t] + y[t-1] + y[t-24] - y[t-25]` ; tout terme postérieur à la coupure est une prévision, jamais une observation.
- Garder persistance, semaine précédente et moyenne des quatre semaines précédentes, à même heure locale. Exclure les journées de changement d'heure, les cibles incomplètes, les historiques de 25 heures incomplets et les quatre références hebdomadaires incomplètes. Tous les modèles sont évalués sur les mêmes dates. Les valeurs manquantes de la série transformée sont traitées par le filtre d'état, sans recoller les trous.

## Contrôles et livrables

Le calcul vérifie l'inversion sur une série synthétique, la convergence des 16 ajustements et l'égalité de prévisions obtenues à partir d'un filtre ne voyant que le passé et d'un filtre complet utilisé en mode dynamique. Ce dernier utilise seulement l'état prédit à l'origine, jamais les états lissés. Les observations après la coupure ne sont pas réinjectées dans l'horizon. Le fichier test 2025 est seulement haché avant/après ; il n'est pas chargé pour ajuster ou évaluer un modèle.

`ajustements.csv` fournit les paramètres et les AIC/BIC. `predictions.csv`, `scores.csv`, `scores_annuels.csv` et `scores_quotidiens.csv` permettent de recalculer les erreurs en MW, l'erreur d'énergie en MWh et les erreurs de pointe. Les ACF/PACF et Ljung–Box portent sur les innovations d'apprentissage à un pas, sur le plus long bloc valide après 168 heures d'amorçage : ce ne sont pas les erreurs J+1. Le test utilise les retards 24 et 168 et `model_df=p+q` ; avec autant d'observations, une petite dépendance peut être significative.

Les trois journées d'échec sont sélectionnées après évaluation parmi les plus fortes RMSE du modèle choisi, sans entraîner à nouveau le modèle. La persistance étant plate, son heure de pointe est conventionnellement la première heure. Aucune capacité de déploiement en temps réel n'est garantie : les consommations sont définitives et leur délai historique de publication n'est pas reconstitué.

Reproduction depuis la racine du dépôt :

```bash
python analyse_consommation/executer.py --depuis 9 --jusqua 9
```

## Résultats obtenus

Les 16 ajustements convergent. Sur 1 053 jours internes, AR(2) donne la meilleure RMSE parmi les quatre candidats (8 022 MW), mais la semaine précédente est meilleure (5 388 MW). Sur 352 jours de 2024, AR(2) atteint 8 210 MW contre 4 860 MW pour la semaine précédente. AIC/BIC favorisent AR(2) dans les quatre fenêtres, mais les innovations restent corrélées : Ljung–Box rejette aux deux retards dans tous les ajustements. Aucun de ces candidats n'améliore le meilleur benchmark global dans cette configuration.

Les erreurs sont aussi exportées par saison, type de jour et température observée en 2024 (`scores_par_contexte_2024.csv`) ; ces groupes servent à l'analyse rétrospective, pas au choix d'un nouveau modèle. La semaine précédente bat AR(2) dans chaque saison, mais pas sur le sous-groupe des jours fériés en RMSE ni sur les heures inférieures à 5 °C. Une météo manquante exclut seulement son groupe de diagnostic, pas l'évaluation globale.

Les trois fortes erreurs AR(2) sont les 2 mai, 26 décembre et 25 novembre 2024 : deux lendemains de jours fériés et un lundi. Les prévisions sous-estiment fortement la reprise. Cela suggère une limite du traitement du calendrier et de l'extrapolation des différences, sans attribution causale exhaustive. Le rapport ne présente pas AR(2) comme une amélioration : le benchmark reste préférable parmi les sept méthodes de cette expérience.
