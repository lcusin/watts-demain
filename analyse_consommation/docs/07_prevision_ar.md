# Correction autoregressive des residus de M09

## Objectif et variantes

Premiere etape de l'amelioration proposee : garder la regression M09 meteo/calendrier
et prevoir sa composante residuelle. Les essais d'inertie thermique, de calendrier
enrichi et de fenetres d'apprentissage courtes ne sont pas inclus dans cette etape.

On ecrit C(t) = m(t) + u(t). M09 estime m(t). Une regression par moindres carres des residus
sur leurs retards estime u(t), avec constante, sans penalisation.
Les coefficients sont ajustes uniquement sur le passe et le rang est verifie. L'estimation se fait en deux etapes ; ce n'est pas une
estimation conjointe par maximum de vraisemblance d'une regression-ARIMA.

Trois variantes principales sont comparees :

- M09 seul : correction residuelle nulle.
- M09 + AR court : retards 1, 2 et 3 heures.
- M09 + AR saisonnier : retards 1, 2, 3, 24, 25, 48 et 168 heures.

Trois benchmarks de consommation sont ajoutes : persistance, semaine precedente et moyenne des quatre semaines. Voir [les definitions et controles](10_benchmarks.md).

## Donnees et simulation

Le script `scripts/prevision_residus_ar.py` lit le train issu de la fusion canonique corrigee.
Le calendrier reste local et la meteo est alignee en UTC. Voir [les donnees](00_donnees.md).

Pour chaque jour cible de 2021, 2022 et 2023 :

1. L'origine est 14 h la veille, en heure francaise.
2. La derniere etiquette de consommation autorisee est **12 h la veille**.
   Cette valeur est la moyenne des puissances a 12:00 et 12:30. On suppose
   qu'elle est disponible a 14 h : cette hypothese de publication reste a verifier.
   Les fichiers definitifs ne permettent pas de reconstituer les revisions
   et delais reels de publication.
3. Le modele AR ne recoit que les 168 residus horaires consecutifs terminant
   a cette coupure. La fonction de prevision ne recoit aucun residu futur.
4. Il prevoit recursivement toutes les heures jusqu'a 23 h du lendemain.
   Des qu'un retard porte sur une heure apres la coupure, on reutilise sa
   prediction, jamais sa valeur observee.
5. Les corrections correspondant aux 24 heures du lendemain sont ajoutees
   aux predictions de M09. Ce sont des horizons 10 a 33 heures apres l'origine,
   ou 12 a 35 heures apres la derniere etiquette observee.

La regression et l'AR sont reajustes une fois par an, sur les observations
anterieures au **31 decembre a 00 h de l'annee precedente**. Cela exclut toute
observation future pour la premiere origine de chaque evaluation, le 31 decembre
a 14 h. Par exemple, pour les cibles 2021, l'ajustement s'arrete au 30 decembre
2020 a 23 h. Les informations nouvelles servent ensuite a initialiser l'AR,
mais les coefficients restent fixes pendant l'annee.

La meteo est **observee**, y compris celle du lendemain et celle utilisee pour
calculer les residus historiques. Sa reconstruction peut utiliser la mesure
SYNOP suivante. Il s'agit donc d'une simulation a **meteo parfaite**, avec une
coupure stricte sur la consommation, pas d'un systeme deployable a J,14 h.
La selection des stations sur un historique plus long reste une autre limite
du pretraitement, deja documentee dans l'audit meteo/calendrier.

## Support commun et exclusions

Sur 1095 journees candidates, 991 sont conservees pour les six methodes :

- 14 exclusions pour cible incomplete ou changement d'heure ;
- 72 pour historique commun de 168 heures incomplet ;
- 18 pour historique des benchmarks incomplet ou changement d'heure.

Les motifs sont attribues dans cet ordre. Les benchmarks ne demandent que la
consommation, sans filtre meteo sur leurs references. Les quatre semaines sont
obligatoires. Aucun trou n'est rempli et aucune exclusion ne depend des erreurs.

## Evaluation et resultats

| Methode | MAE (MW) | RMSE (MW) | Biais observation - prevision (MW) |
|---|---:|---:|---:|
| M09 + AR journalier/hebdomadaire | 1205.5 | 1760.5 | -120.6 |
| M09 + AR court | 1925.5 | 2545.3 | -586.1 |
| M09 seul | 2194.8 | 2880.1 | -703.3 |
| Semaine précédente | 3520.3 | 5336.3 | -84.7 |
| Moyenne des quatre semaines | 4249.5 | 5967.6 | -97.2 |
| Persistance consommation | 6687.0 | 8047.7 | -5513.4 |

L'AR saisonnier reduit la RMSE d'environ 38,9 % par rapport a M09 seul sur ce
support. Il est meilleur que les cinq autres variantes pour chaque annee
2021, 2022 et 2023. L'erreur absolue moyenne sur la pointe passe de 1963 a 1054 MW,
et celle sur l'heure de pointe d'environ 2,37 a 1,61 h. En cas d'egalite de maxima,
la premiere heure est retenue. L'ecart d'heure est absolu sur la journee, non circulaire.
L'erreur d'energie quotidienne est la valeur absolue de la somme des erreurs
horaires en MW multipliees par une heure, donc exprimee en MWh.

Ces chiffres ne sont pas directement comparables aux 2957,2 MW obtenus precedemment
pour M09 : les dates admissibles et la fin de l'apprentissage different.
M09 ayant deja ete selectionne sur 2021-2023, il s'agit toujours d'une evaluation
interne exploratoire, pas d'un test independant. Validation 2024 et test 2025
ne sont pas utilises.

## ACF/PACF : deux diagnostics differents

- `acf_pacf_erreurs_J_plus_1.png` : erreurs sur les 24 previsions faites a la meme
  origine. Meme avec un bon modele, ces erreurs a plusieurs pas peuvent etre
  correlees parce qu'elles partagent des innovations futures inconnues a l'origine.
- `acf_pacf_innovations_conditionnelles_1h.png` : prediction de chaque residu avec
  ses retards effectivement observes jusqu'a l'heure precedente. Ce diagnostic
  a un pas **n'entre pas dans les scores J+1**, car il utilise de nouvelles
  observations qui n'etaient pas disponibles a l'origine de ces previsions.

Les trois diagnostics a un pas ont un support commun. Les autocovariances sont
calculees par blocs horaires continus, coupes aux exclusions et aux changements
d'annee, puis normalisees. La methode et ses limites sont expliquees dans
`06_meteo_calendrier.md`.

L'AR court laisse une ACF a 24 h d'environ 0,829 dans les innovations. L'AR
saisonnier la ramene a environ -0,191, mais conserve des correlations d'environ
0,260 a 1 h et 0,227 a 168 h. Il n'a donc pas tout explique. L'amelioration des
previsions est nette sur cette comparaison, sans affirmer que les innovations
sont devenues un bruit blanc.

## Controles et reproduction

- Grilles et references datees, sans decalage de lignes a travers des trous.
- Origines strictement posterieures aux observations utilisees pour l'ajustement.
- Historique de consommation coupe avant l'origine ; fonction recursive sans
  acces aux valeurs cibles.
- Verification numerique d'un AR(1) contre sa formule fermee.
- Verification du retard 24 : apres 24 pas, la recursion reutilise les predictions.
- Historique fourni non modifie par la fonction.
- 24 predictions finies par jour et meme nombre de jours pour toutes les variantes.
- Inspection du graphique des erreurs par heure.

Executer depuis la racine :

```bash
python analyse_consommation/scripts/prevision_residus_ar.py
```

Sorties : predictions datees, jours exclus, coefficients AR, scores globaux et
annuels, erreurs quotidiennes, innovations a un pas, deux planches ACF/PACF
avec les valeurs CSV, et un graphique de MAE par heure cible.
