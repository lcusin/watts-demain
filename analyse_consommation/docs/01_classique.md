# Exploration et décompositions classiques

Source : `data/merge/train.csv`, 2012–2023. La cible est une puissance en MW.
Les graphiques montrent l'évolution quotidienne/mensuelle, les profils par heure,
jour de semaine et mois, les distributions et les amplitudes.

Trois expériences **séparées** : période 24 sur données horaires, période 168
sur données horaires, période 12 sur moyennes mensuelles. Ce ne sont pas trois
saisonnalités retirées successivement de la même série.

Pour chaque expérience, la tendance-cycle est estimée par moyenne mobile centrée.
Pour une période paire p, on utilise une moyenne 2 × p : poids 1/p à l'intérieur,
1/(2p) aux extrémités. Les bords sans fenêtre complète restent manquants.

- Additif : retirer la tendance, agréger les écarts d'une même saison par moyenne
  ou médiane, centrer les coefficients pour une moyenne nulle, puis soustraire.
- Multiplicatif : diviser par la tendance, agréger les ratios, normaliser les
  coefficients pour une moyenne égale à 1, puis diviser.

La reconstruction est contrôlée pour les 12 variantes. Les moyennes ont également
été vérifiées contre `statsmodels.seasonal_decompose` sur un exemple synthétique.
Les résidus multiplicatifs sont des ratios ; les erreurs de reconstruction en MW
sont utilisées pour comparer l'amplitude des écarts. Les ACF restent descriptives.

Une tendance courte absorbe aussi les variations plus lentes que sa fenêtre.
Ces méthodes rétrospectives ne séparent pas un cycle économique identifiable et
ne constituent pas des prévisions hors échantillon. Le calendrier horaire est
celui des étiquettes RTE : voir [les limites horaires](00_donnees.md).

Sorties : `resultats/01_classique/` ; les CSV de composantes sont ensuite lus par
la comparaison globale. [Scores](../resultats/01_classique/RESULTATS.md).
