# Plan du rapport actuel

Le rapport suit les modèles effectivement présentés dans les slides. Il ne présente ni Ridge ni la régression explicative à 215 variables comme une méthode explicitement enseignée.

1. **Introduction** : prévoir les 24 heures de J+1 à J14, et établir un gain par rapport aux références simples.
2. **Méthodes** : données et alignement horaire ; exploration et décompositions ; AR(1), AR(2), MA(1), ARMA(1,1) sur la double différence 24 h et 1 h ; trois benchmarks ; validation chronologique et disponibilité ; place des extensions météo/calendrier.
3. **Résultats** : stations et couverture géographique, profils et tendance ; diagnostics de décomposition ; comparaison prédictive interne et 2024 ; innovations ; résultats exploratoires météo clairement séparés.
4. **Discussion et audit** : tableau de disponibilité, trois journées d'échec, robustesse et métriques complémentaires, limites de déploiement et trois exemples d'usage critique de l'IA.

## Contraintes du rendu

- Moins de 10 pages pour le corps du rapport ; page de titre, bibliographie et annexes techniques raisonnables hors décompte.
- Consacrer environ 1 à 2 pages à l'audit critique.
- Documenter trois exemples d'usage de l'IA : proposition conservée après vérification, proposition modifiée ou rejetée, et erreur détectée. Préciser la décision et la vérification pour chacun.
- Terminer par une conclusion sur les résultats essentiels et les limites.

## Protocole réellement exécuté

- Exploration : 2012–2023.
- Comparaison interne des AR, MA et ARMA : 2021–2023, fenêtre de deux ans, estimation annuelle par maximum de vraisemblance. Cette fenêtre limite le coût de calcul et privilégie les observations récentes ; sa durée n'a pas été optimisée.
- Régressions météo/calendrier : apprentissage sur toutes les années antérieures disponibles depuis 2012, puis évaluation successive sur 2021, 2022 et 2023.
- Validation : 2024 ; modèle choisi sur la RMSE interne. Cette validation avait déjà été consultée dans d'autres expériences.
- Test final : 2025 réservé, non évalué.
- Comparaison des modèles du cours et des benchmarks : coupure J8 pour une prévision émise à J14 ; 1 053 journées internes et 352 en 2024, communes aux sept méthodes.
- Références : persistance, semaine précédente, moyenne des quatre semaines.
- Résultat : AR(2) est le meilleur des quatre candidats ARMA ; la semaine précédente reste meilleure globalement. Les innovations ne sont pas blanches.

## Reproduction et sources

Le script `analyse_consommation/scripts/modeles_cours.py` génère les prévisions, scores, diagnostics et le tableau LaTeX. La documentation méthodologique est dans `analyse_consommation/docs/12_modeles_cours.md`. Les expériences précédentes sont conservées comme extensions ; leurs scores ne sont pas directement comparables puisque les supports diffèrent.

Le rapport se compile depuis `rapport/main.tex`. Les figures sont incluses depuis les résultats, sans duplication. La couverture et la bibliographie sont hors du décompte du corps du mini-rapport. Le choix du modèle n'a pas utilisé le test final 2025.
