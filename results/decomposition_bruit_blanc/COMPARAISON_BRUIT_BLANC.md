# Recherche d'une decomposition avec residus proches d'un bruit blanc

## Conclusion

**Meilleur compromis selon le critere fixe : regression conjointe a seuils de temperature, suivie d'une correction autoregressive regularisee utilisant les 336 heures precedentes.**

Les 24 combinaisons testees produisent des resultats tres differents. Les plus grandes ameliorations viennent de la correction autoregressive. Sur la confirmation 2024, le meilleur candidat ne produit cependant pas un bruit blanc convaincant : les tests d'autocorrelation rejettent encore cette hypothese, et la dependance des erreurs au carre suggere une variance conditionnelle variable.

Le choix est le meilleur parmi les candidats et selon le critere ci-dessous, pas un optimum sur tous les modeles possibles. Il n'est pas possible d'essayer exhaustivement toutes les familles et tous les parametres. Nous arretons les essais apres la confirmation independante pour ne pas ajuster indefiniment la methode aux memes donnees.

## Changement d'objectif

La comparaison precedente privilegiait la MAE et conservait la tendance. Ici, l'objectif est de retirer toutes les contributions estimees, y compris constante et tendance, puis de modeliser la dependance temporelle restante.

La decomposition prend la forme :

**Consommation = niveau/tendance + cycles annuel/journalier/hebdomadaire + interactions saisonnieres + temperature + pluie + calendrier + controles d'imputation + correction AR + innovation.**

Les interactions et le calendrier peuvent etre absents selon le candidat. Les coefficients de reference rendent le partage des constantes entre composantes conventionnel ; les composantes s'additionnent exactement. Une correction AR exploite la dependance au passe, mais ne fournit pas l'explication physique d'un motif.

## Protocole fixe avant evaluation

- Quatre structures explicatives croisees avec six corrections dynamiques : 24 candidats, 72 evaluations internes.
- Ajustements sur 2012-2020, puis 2012-2021, puis 2012-2022 ; evaluations respectives sur 2021, 2022 et 2023. Un ajustement par an.
- Pour la variante recente, seuls les trois ans precedant l'annee evaluee servent a l'ajustement.
- Les moyennes, medianes d'imputation, noeuds de spline, coefficients de regression et coefficients AR sont appris sur le passe uniquement.
- Choix fige apres les evaluations internes, puis confirmation unique sur validation.csv (2024). test.csv (2025) n'est pas lu.
- Les regenerations de figures de 2024 ne modifient ni le choix, ni les parametres.
- Les residus AR de validation a l'heure t utilisent les residus observes aux heures strictement anterieures. La valeur courante ou future n'est pas utilisee comme retard.
- La meteo observee simultanee et les consommations recentes sont disponibles dans ce diagnostic retrospectif. Ce n'est PAS une evaluation operationnelle des 24 heures de J+1 prevues a J, 14 h.

## Comment est defini le meilleur

Pour chaque annee : `score = moyenne(ACF(k)^2 + PACF(k)^2)` pour k de 1 a 336. On moyenne ensuite ce score sur les trois annees.

Une methode est admissible si sa RMSE moyenne ne depasse pas de plus de 10 % la meilleure RMSE moyenne des candidats. Parmi les admissibles, on choisit le plus petit score de dependance. Ce garde-fou evite de rechercher une ACF faible au prix d'erreurs beaucoup plus grandes. Le seuil de 10 % est un choix pratique, pas une loi statistique.

La MAE, le biais, les plus grands coefficients ACF/PACF et Ljung-Box servent aussi a la discussion. Le score principal ne garantit ni moyenne nulle, ni variance constante, ni independance. Les differences entre candidats voisins n'ont pas ete soumises a un test de superiorite.

## Les quatre structures explicatives

| Structure | Contenu et raison du test |
|---|---|
| seuils | Reference retenue auparavant : tendance lineaire par morceaux, trois harmoniques annuelles, profil de 168 heures, froid sous 18 C, chaleur au-dessus de 22 C, log(1 + pluie). |
| splines | Meme structure mais temperature sous forme de spline cubique a cinq noeuds quantiles : tester une relation plus souple. |
| enrichi | Reference a seuils + profil horaire modulable par la saison (deux harmoniques), modulation annuelle selon le jour, sensibilite au froid selon l'heure, jours feries selon l'heure, vacances A/B/C et changement d'heure. |
| enrichi_3ans | Structure enrichie ajustee sur les trois dernieres annees : tester l'adaptation aux changements de regime. |

## Les six corrections dynamiques

| Correction | Retards | Pourquoi |
|---|---|---|
| sans_AR | Aucun | Mesurer ce que la decomposition explicative retire a elle seule. |
| AR1 | 1 h | Corriger une simple persistance. |
| AR24 | 1 a 24 h | Capturer la dynamique intrajournaliere. |
| AR_cible | 1-24 h, multiples de 24 jusqu'a 144 h, 168-191 h, 336 h | Tester un ensemble parcimonieux couvrant jours et semaines. |
| AR168 | 1 a 168 h | Laisser le modele exploiter toute la semaine precedente. |
| AR336 | 1 a 336 h | Ajouter une seconde semaine pour les dependances longues. |

Les regressions AR utilisent Ridge avec alpha=10, fixe pour tous les essais. Les retards et la cible sont divises par l'ecart-type des residus d'apprentissage. La correction est estimee en seconde etape sur les residus explicatifs d'apprentissage, puis appliquee sans reajustement a l'annee suivante. Elle n'est pas une estimation conjointe exacte de type ARMAX.

## Classement complet

Les maxima ACF/PACF ci-dessous sont les moyennes des maxima annuels. Les RMSE sont egalement moyennes par annee, pas calculees sur des erreurs concatenees.

| Methode | Score dependance | MAE MW | RMSE MW | Max ACF | Max PACF | Admissible |
|---|---:|---:|---:|---:|---:|---|
| seuils__AR336 | 0.000294 | 259.4 | 377.0 | 0.066 | 0.063 | oui |
| splines__AR336 | 0.000320 | 244.6 | 357.4 | 0.067 | 0.065 | oui |
| enrichi_3ans__AR336 | 0.000370 | 261.5 | 374.9 | 0.069 | 0.065 | oui |
| seuils__AR168 | 0.000418 | 261.8 | 380.8 | 0.099 | 0.093 | oui |
| splines__AR168 | 0.000454 | 247.8 | 361.3 | 0.107 | 0.101 | oui |
| enrichi_3ans__AR168 | 0.000460 | 263.0 | 378.6 | 0.122 | 0.120 | oui |
| enrichi__AR336 | 0.000342 | 270.4 | 394.2 | 0.082 | 0.080 | non |
| enrichi__AR168 | 0.000500 | 273.4 | 400.5 | 0.147 | 0.142 | non |
| enrichi_3ans__AR_cible | 0.004317 | 323.1 | 450.0 | 0.429 | 0.418 | non |
| splines__AR_cible | 0.004665 | 315.3 | 457.4 | 0.451 | 0.438 | non |
| enrichi__AR_cible | 0.004761 | 344.3 | 477.0 | 0.436 | 0.426 | non |
| seuils__AR_cible | 0.004896 | 337.5 | 482.9 | 0.466 | 0.452 | non |
| enrichi_3ans__AR24 | 0.011765 | 382.1 | 527.4 | 0.554 | 0.531 | non |
| enrichi__AR24 | 0.014144 | 429.8 | 582.7 | 0.582 | 0.560 | non |
| enrichi_3ans__AR1 | 0.018165 | 478.6 | 649.1 | 0.718 | 0.603 | non |
| enrichi__AR1 | 0.019873 | 534.3 | 709.4 | 0.731 | 0.621 | non |
| seuils__AR24 | 0.021838 | 468.8 | 641.4 | 0.647 | 0.563 | non |
| splines__AR24 | 0.022550 | 458.8 | 629.9 | 0.652 | 0.566 | non |
| seuils__AR1 | 0.040287 | 684.1 | 898.1 | 0.833 | 0.699 | non |
| splines__AR1 | 0.044424 | 666.5 | 882.9 | 0.837 | 0.709 | non |
| seuils__sans_AR | 0.177325 | 3267.1 | 4118.8 | 0.967 | 0.967 | non |
| splines__sans_AR | 0.194863 | 3281.6 | 4115.9 | 0.964 | 0.964 | non |
| enrichi__sans_AR | 0.212884 | 3045.2 | 3819.6 | 0.974 | 0.974 | non |
| enrichi_3ans__sans_AR | 0.243883 | 3045.5 | 3820.7 | 0.979 | 0.979 | non |

## Pourquoi les autres candidats ne sont pas retenus

- **Sans AR** : l'enrichissement calendrier/saison ameliore la reconstruction mais la dependance horaire reste tres forte. Retirer des motifs moyens n'elimine pas les ecarts persistants.
- **AR1 et AR24** : la correction couvre une duree trop courte pour faire disparaitre les motifs observes dans ce jeu de donnees ; les scores restent eleves.
- **AR cible** : plus parcimonieux, mais laisse ici davantage de dependance que l'ensemble dense des retards sur une ou deux semaines.
- **AR168** : net progres, mais les versions AR336 ont des scores de dependance inferieurs pour chacune des quatre structures.
- **splines + AR336** : meilleure MAE/RMSE moyenne que le candidat retenu, mais score ACF/PACF legerement moins bon. Ce serait un choix defensable si la precision redevenait prioritaire.
- **enrichi + AR336** : davantage de termes explicatifs, sans meilleur score de dependance ; depasse de peu le seuil admissible de RMSE. L'absence de gain ne prouve pas que les effets calendaires sont inutiles : l'AR peut en absorber une partie et les coefficients peuvent varier dans le temps.
- **enrichi_3ans + AR336** : comparable en RMSE, mais score de dependance superieur. La fenetre recente ne domine donc pas les annees d'historique supplementaires selon ce protocole.

Le candidat retenu n'est pas premier dans toutes les dimensions ; on ne doit pas presenter le resultat comme une victoire incontestable.

## Confirmation independante sur 2024

Coefficients ajustes sur 2012-2023 ; 8 784 heures evaluees. Aucune modification de modele apres lecture des scores 2024.

| Mesure | Residus explicatifs, sans AR | Innovations, avec AR336 |
|---|---:|---:|
| MAE_MW | 2588.5 | 248.84 |
| RMSE_MW | 3355.5 | 360.57 |
| biais_MW | -1196.1 | -11.634 |
| max_ACF | 0.96341 | 0.09819 |
| max_PACF | 0.96341 | 0.087026 |
| ACF_24h | 0.71413 | -0.032377 |
| ACF_168h | 0.38251 | 0.018912 |
| fraction_ACF_hors95 | 0.87202 | 0.098214 |
| LB_24_p | 0 (sous-flux numerique possible) | 4.8371e-13 |
| LB_168_p | 0 (sous-flux numerique possible) | 4.1486e-09 |
| LB_336_p | 0 (sous-flux numerique possible) | 1.3521e-14 |
| LB_carres_24_p | 0 (sous-flux numerique possible) | 0 (sous-flux numerique possible) |

Les erreurs moyennes absolues sont nettement plus faibles, mais l'AR beneficie des observations recentes : ce gain ne se transpose pas tel quel a une prevision de toute une journee sans mise a jour.

### Verdict bruit blanc

**Non : le bruit blanc n'est pas atteint sur la confirmation.** Ljung-Box rejette l'absence d'autocorrelation aux trois horizons 24/168/336 h, meme avec un seuil de 0,05/3 pour ces trois tests. Les autocorrelations sont faibles en comparaison de la serie brute, mais pas toutes negligeables. La PACF est aussi inspectee, sans constituer un second test independant.

Les tests sont calcules sur des erreurs hors ajustement : nous utilisons les degres de liberte egaux au nombre de retards, sans soustraire 336 parametres AR ajustes sur une autre periode. Les p-valeurs restent des diagnostics asymptotiques, pas une preuve exacte sous heteroscedasticite et estimation en deux etapes. Les bandes des graphiques sont ponctuelles, pas simultanees.

L'ecart-type mensuel des innovations varie de 330.6 a 406.2 MW. Le test sur leurs carres rejette lui aussi l'absence de dependance. Une variance constante n'est donc pas convaincante. La normalite n'est pas une condition necessaire a un bruit blanc faible, et elle n'a pas ete utilisee comme critere de selection.

### Retards les plus marques en 2024

| Retard h | ACF |
|---:|---:|
| 336 | 0.0982 |
| 1 | 0.0813 |
| 264 | -0.0329 |
| 142 | 0.0325 |
| 24 | -0.0324 |
| 144 | 0.0324 |
| 167 | -0.0317 |
| 38 | -0.0306 |
| 291 | -0.0300 |
| 121 | -0.0289 |

## Pourquoi une structure peut rester

- Les profils et coefficients restent essentiellement fixes pendant l'annee evaluee ; la consommation et sa sensibilite a la temperature peuvent evoluer.
- Le calendrier et la meteo disponibles ne decrivent pas tous les usages, evenements, fermetures, effets de pont ou variations economiques. Ces causes sont plausibles, pas attribuees automatiquement a chaque pic.
- L'agregation spatiale de la meteo et l'interpolation horaire perdent de l'information. L'alignement des fuseaux et les conventions d'horodatage restent a auditer.
- L'AR lineaire capture beaucoup de dependance, mais pas necessairement la non-linearite, les changements de regime ou la variance variable.
- Avec pres de 9 000 heures par an, meme des dependances modestes peuvent etre detectees.

Ne pas ajouter du bruit, supprimer les jours difficiles, lisser les innovations ou multiplier les essais sur 2024 pour obtenir artificiellement des bandes rassurantes. Obtenir un p > 0,05 ne prouverait de toute facon ni independance ni absence de toute saisonnalite a tous les horizons.

Les 336 retards ne permettent pas de conclure a l'absence de dependance annuelle. La confirmation ne contient qu'une annee : il faudrait une periode independante plus longue pour cet aspect.

## Utilisation et prochaine etape raisonnable

Le modele retenu sert de diagnostic et de decomposition dynamique retrospective. Pour le sujet J+1 a 14 h, il faudra figer l'information a cette heure, utiliser une meteo disponible alors et propager les residus futurs recursivement ou construire des modeles directs. Les erreurs seront plus grandes qu'a un pas avec observations recentes.

Avant de nouvelles recherches de modeles, les priorites sont l'audit temporel et l'analyse des jours en echec. Un reajustement plus frequent ou une variance conditionnelle peuvent faire l'objet d'un futur protocole, mais n'ont pas ete testes ici. Le test 2025 doit rester reserve a l'evaluation finale ; 2024 est desormais une periode consultee.

## Fichiers et reproduction

```bash
python src/comparer_bruit_blanc.py
python src/comparer_bruit_blanc.py --confirmation
```

- `classement.csv`, `scores_par_annee.csv`, `erreurs_internes.csv` : les 72 evaluations et leurs erreurs.
- `choix.json` : candidat selectionne avant confirmation.
- `confirmation_2024.csv` : diagnostic independant du candidat fige.
- `decomposition_validation_2024.csv` : contributions, correction AR et innovations horaires.
- `coefficients_structure.csv`, `coefficients_AR.csv` : coefficients pour inspection. Le script reconstruit les transformations et l'interception AR a l'execution.
- `01_acf_pacf_confirmation.png` : serie brute, residus explicatifs, innovations ; zoom vertical sur les innovations pour ne pas masquer les pics.
- `02_composantes_2024.png`, `04_decomposition_horaire.png` : composantes a echelles annuelle et horaire.
- `03_stabilite_innovations.png`, `stabilite_mensuelle.csv`, `principaux_retards_restants.csv` : variance et dependances restantes.

Verifications : formule de Ljung-Box comparee a statsmodels ; modification des observations futures sans changement des corrections AR presentes ou passees ; reconstruction additive des contributions ; grille horaire et valeurs finies.

## References methodologiques

- Statsmodels, Ljung-Box : https://www.statsmodels.org/stable/generated/statsmodels.stats.diagnostic.acorr_ljungbox.html
- Hyndman et Athanasopoulos, diagnostics des residus : https://otexts.com/fpp3/diagnostics.html

Les resultats chiffres de ce document proviennent des scripts locaux et non de ces references.
