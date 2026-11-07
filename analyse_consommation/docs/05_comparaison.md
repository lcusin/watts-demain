# Comparaison des méthodes et combinaisons

36 variantes horaires :

- série brute et sans tendance longue ;
- sur chacune, sept combinaisons non vides des différences à 8736, 24 et 1 h ;
- huit décompositions classiques (24/168 h, additive/multiplicative, moyenne/médiane) ;
- quatre STL (24/168 h, standard/robuste), et leurs quatre variantes différenciées à 1 h ;
- quatre combinaisons de tendance longue et de la seule saisonnalité STL.

La tendance longue est ici une moyenne horaire centrée 2 × 8760 : adaptation
horaire de la fenêtre quotidienne de 365 jours, sans effet d'escalier à minuit.
Les différences à retards fixes commutent : leurs permutations ne sont pas répétées.
Retirer la tendance puis différencier signifie D(y−T)=Dy−DT. On ne soustrait pas
la tendance en niveau d'une série déjà différenciée.

Le support commun horaire contient 87 671 heures du 1er juillet 2013 à 13 h au
2 juillet 2023 à 11 h. Les sept variantes mensuelles sont comparées séparément
sur 132 mois de juillet 2012 à juin 2023. Aucune lacune interne n'est recollée.

Les ACF/PACF couvrent 1–336 heures ou 1–36 mois. La PACF utilise Levinson–Durbin.
La moyenne des ACF au carré fournit un classement de décorrélation, **pas un
classement prédictif**. Les p-values Ljung–Box sont indicatives, sans correction
des composantes estimées ni des comparaisons multiples. Les ratios multiplicatifs
et les résidus MW ont des ACF comparables, mais pas des écarts-types comparables.

STL hebdomadaire robuste + D1 a la plus faible moyenne ACF² (0,00208), mais
conserve un pic de 0,638 à 168 h. D8736+D24+D1 vient ensuite (0,00327) et conserve
une ACF1 de 0,657. Le retrait préalable de tendance longue change très peu ce
second résultat. Ces variantes ne donnent pas un bruit blanc.

Les retards annuels sont hors des 336 h affichées : consulter également
l'ACF longue de l'étape 4. Les sous-ensembles de variantes et les scores exacts
sont exportés dans `resultats/05_comparaison/`.
