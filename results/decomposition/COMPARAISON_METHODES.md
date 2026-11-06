# Comparaison des methodes de decomposition saisonniere et meteo

## Conclusion

**Choix retenu : regression additive conjointe avec temperature a deux seuils (18 et 22 degres C), precipitation transformee et trois saisonnalites.**

Il s'agit de la meilleure des sept variantes testees selon la MAE moyenne de validation interne, pas d'une meilleure methode universelle. Les splines a six harmoniques sont pratiquement ex aequo et meilleures selon la RMSE. Aucune superiorite statistiquement significative n'est revendiquee.

## Ce que mesure cet essai

On compare la capacite du modele complet a reconstruire la consommation sur une annee suivante, avec sa meteo observee. La cible de cette comparaison est la consommation brute. Il ne s'agit ni de minimiser artificiellement la variance apres correction, ni d'un protocole operationnel J+1 a 14 h.

La decomposition finale conserve toujours la tendance. Pour mesurer les erreurs hors echantillon, la prediction complete comprend cependant la tendance extrapolee. Le classement depend donc aussi de cette extrapolation, et ne mesure pas une pure qualite de separation des composantes.

## Protocole commun

| Ajustement | Evaluation interne |
|---|---|
| 2012-2020 | 2021 |
| 2012-2021 | 2022 |
| 2012-2022 | 2023 |

- Sept methodes, trois decoupages : 21 ajustements valides, 26 280 heures evaluees par methode.
- Un ajustement au debut de chaque annee ; pas de reestimation pendant cette annee.
- Seulement train.csv est lu. validation.csv (2024) et test.csv (2025) ne sont pas utilises.
- Mediane meteo par mois/heure, centrage et noeuds des splines appris uniquement sur le passe. Repli sur mediane globale d'apprentissage si un groupe est vide.
- Memes dates, consommation et controles de tendance pour toutes les variantes ; aucune correction jours feries/vacances.
- Critere principal : moyenne des trois MAE annuelles (les trois annees ont chacune 8 760 heures). Criteres secondaires : moyenne des RMSE annuelles, pire MAE annuelle, biais et autocorrelations.
- La RMSE du tableau est la moyenne des RMSE annuelles, pas une RMSE globale calculee sur les trois annees concatenees.
- Les hyperparametres des sept candidats ont ete fixes avant leur comparaison ; aucun balayage des seuils 18/22 ou des noeuds n'a ete realise.

## Classement

| Methode | MAE moyenne (MW) | Moyenne RMSE (MW) | Pire MAE annuelle (MW) |
|---|---:|---:|---:|
| seuils | 3267.1 | 4118.8 | 3690.7 |
| splines_annuel6 | 3269.3 | 4068.0 | 3883.4 |
| splines | 3281.6 | 4115.9 | 3873.9 |
| splines_interactions | 3323.8 | 4143.3 | 4052.3 |
| quadratique | 3349.6 | 4198.2 | 3980.2 |
| lineaire | 3618.8 | 4649.6 | 3876.5 |
| sans_meteo | 4682.8 | 5953.1 | 5432.2 |

## Stabilite par annee

| Methode | MAE 2021 | MAE 2022 | MAE 2023 |
|---|---:|---:|---:|
| seuils | 2777.6 | 3333.1 | 3690.7 |
| splines_annuel6 | 2561.0 | 3363.7 | 3883.4 |
| splines | 2634.6 | 3336.2 | 3873.9 |
| splines_interactions | 2576.3 | 3342.8 | 4052.3 |
| quadratique | 2655.3 | 3413.3 | 3980.2 |
| lineaire | 3116.2 | 3876.5 | 3863.8 |
| sans_meteo | 3665.6 | 4950.5 | 5432.2 |

## Pourquoi chaque methode a ete testee et retenue ou ecartee

### sans_meteo

Reference : mesurer ce que les cycles seuls expliquent.

MAE la plus elevee ; les variations meteorologiques ne sont pas expliquees.

### lineaire

Tester une relation temperature-consommation simple.

La relation lineaire donne une MAE superieure aux variantes non lineaires. Cela ne prouve pas a lui seul la cause physique de l'ecart.

### quadratique

Reevaluer la methode du script precedent : temperature centree et son carre.

Moins bonne MAE moyenne que les seuils, malgre une meilleure annee 2021. Une seule parabole impose une forme globale.

### seuils

Distinguer une sensibilite au froid et a la chaleur avec deux termes simples.

Retenue pour la MAE moyenne minimale et la plus faible pire MAE annuelle. Pas premiere en 2021 ni en RMSE moyenne.

### splines

Autoriser une relation souple : spline cubique, cinq noeuds quantiles appris sur le passe.

Tres proche, mais MAE moyenne et pire annee moins bonnes que les seuils. La flexibilite supplementaire ne donne pas ici de gain moyen.

### splines_interactions

Ajouter 23 interactions froid-heure pour des sensibilites variables dans la journee.

Bonne en 2021, mais moins stable ensuite ; pire MAE annuelle la plus forte parmi les variantes non lineaires. Surajustement ou changement de regime possibles, non demontres.

### splines_annuel6

Combiner la courbe souple avec six harmoniques annuelles au lieu de trois.

Quasi ex aequo en MAE et meilleure RMSE moyenne. Non retenue comme choix principal car plus complexe et moins bonne sur la pire annee ; reste une alternative valable.

## Methode retenue en detail

Une seule regression par moindres carres estime simultanement :

1. Une constante et une tendance lineaire par morceaux, avec des changements de pente annuels. Le dernier changement doit avoir au moins un an de donnees apres lui.
2. Trois paires sinus/cosinus annuelles, de periode 365,2425 jours.
3. Un profil de 168 heures, separe ensuite en profil journalier moyen et ecarts selon le jour de la semaine.
4. Deux termes temperature : `max(18 - T, 0)` et `max(T - 22, 0)`. Les seuils sont des hypotheses fixes ; les coefficients ne sont pas contraints en signe.
5. `log(1 + precipitation)` et deux indicateurs de valeurs meteo imputees.

Les cycles et contributions meteo sont centres sur zero. On les soustrait a la consommation selon le graphique souhaite. La constante, la tendance et les indicateurs d'imputation restent dans la serie corrigee. Les jours feries restent egalement non corriges.

Gain moyen de MAE : 30.2 % par rapport aux cycles sans meteo, et 2.5 % par rapport a la temperature quadratique. Ces pourcentages concernent ce protocole uniquement.

## Structure restante et limites

| Annee | Biais observe - reconstruit (MW) | Autocorrelation erreur 24 h | Autocorrelation erreur 168 h |
|---|---:|---:|---:|
| 2021 | 1462.8 | 0.784 | 0.377 |
| 2022 | -2312.2 | 0.875 | 0.569 |
| 2023 | 2418.2 | 0.826 | 0.561 |

Les erreurs gardent donc une structure importante. La methode ne produit pas un bruit blanc. Les biais changent de signe selon les annees : les changements de niveau de consommation et l'extrapolation de tendance limitent la reconstruction.

La meteo et la saison sont correlees : leur partage depend du modele, sans interpretation causale. Les cycles sont fixes et peuvent manquer des variations de profil selon les saisons. Les valeurs observees de meteo sur l'annee evaluee ne seraient pas connues a une origine de prevision annuelle ou a J, 14 h : les scores ne sont pas ceux d'un systeme deployable.

Le classement a servi a choisir la methode ; il ne constitue donc pas une evaluation finale independante. La validation 2024 et le test 2025 restent disponibles pour les etapes ulterieures du projet. Les profils des residus pourront guider ces etapes, sans multiplier indefiniment les essais pour obtenir une ACF plate.

## Essai invalide detecte et corrige

Le premier passage placait un noeud de tendance presque a la fin de certaines annees, car une annee de 365,2425 jours ne coincide pas exactement avec les annees civiles. La derniere pente etait alors estimee sur quelques heures et extrapolee sur un an. Les MAE atteignaient des millions de MW : ces scores etaient inutilisables.

Correction appliquee a toutes les variantes : au moins un an de donnees apres le dernier noeud. Les 21 ajustements ont ete relances avec cette regle commune. Les premiers scores sont conserves uniquement pour audit dans `essais/essai_invalide_tendance.csv` et sont exclus du classement. Cet incident illustre pourquoi les anciens graphiques en ajustement complet ne suffisaient pas a valider la tendance hors echantillon.

## Reproduction et fichiers

```bash
python src/comparer_decompositions.py
python src/decomposition.py
```

- `src/modele_decomposition.py` : transformations partagees, identiques entre comparaison et decomposition.
- `src/comparer_decompositions.py` : sept variantes et validation chronologique interne.
- `src/decomposition.py` : methode a seuils retenue, reajustee sur tout train.csv, et huit graphiques regeneres.
- `essais/classement.csv`, `scores_par_annee.csv` et `erreurs_validation_interne.csv` : resultats numeriques auditables.
- `essais/methode_retenue.txt` : premier candidat selon la MAE. Le choix dans decomposition.py est explicite pour ne pas changer silencieusement lors d'un futur essai.

Verifications : modifier la meteo de validation ne modifie pas la matrice d'apprentissage ; colonnes identiques entre apprentissage et evaluation ; les composantes finales doivent reconstruire la consommation sans soustraction de la tendance.

## Suite : recherche de residus proches du bruit blanc

L'objectif a ensuite change : retrait de la tendance et correction dynamique.
Voir [COMPARAISON_BRUIT_BLANC.md](../decomposition_bruit_blanc/COMPARAISON_BRUIT_BLANC.md).
Cette nouvelle etude compare 24 candidats, consulte 2024 une fois le choix fige
et conserve 2025 pour le test final. Le classement ci-dessus reste celui de l'ancien objectif.
