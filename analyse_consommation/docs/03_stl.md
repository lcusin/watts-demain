# STL : saisonnalité et tendance par LOESS

Trois expériences séparées, identiques aux échelles classiques : 24 heures,
168 heures, et 12 mois sur moyennes mensuelles. Pour chacune, STL standard et
robuste sont comparées aux méthodes classiques additives. Pas de STL logarithmique.

Réglages communs : fenêtre saisonnière 7 cycles, degrés LOESS 1, pas de calcul 1 ;
fenêtres de tendance et passe-bas par défaut de statsmodels. Deux itérations
internes ; 0 externe pour standard, 15 pour robuste. Les réglages et durées exacts
sont exportés dans `resultats/03_stl/parametres.json`.

Les scores sont calculés sur les mêmes dates que la décomposition classique,
sans les bords non estimables de celle-ci. Les composantes STL exportées couvrent
la période entière ; le lissage utilise le futur, surtout près des extrémités.

STL standard réduit l'erreur de reconstruction aux trois échelles, mais cela ne
prouve pas un meilleur pouvoir prédictif : une tendance flexible peut absorber
beaucoup de variation. Les résidus restent autocorrélés.

La STL journalière robuste sous-pondère fortement les week-ends : un cycle
hebdomadaire absent du modèle peut être traité comme atypique. Les poids <0,5
concernent environ 64 % des heures du samedi et 76 % du dimanche. La robustesse
n'est donc pas automatiquement préférable et ces poids ne prouvent pas une erreur
sur les données.

Les séries ont été reconstruites numériquement à partir de leurs composantes ;
les poids sont finis et compris entre 0 et 1. [Scores](../resultats/03_stl/RESULTATS.md).
Les CSV sont réutilisés dans les expériences de différence annuelle et de comparaison.
