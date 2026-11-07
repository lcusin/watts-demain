# Validation 2024 : information disponible et scenarios meteo

## Protocole fixe avant lecture des scores

Trois scenarios : sans covariables meteo, meteo prevue par persistance a 48 h,
et meteo parfaite. Les trois utilisent calendrier, saisonnalites, tendance lineaire
et correction AR aux retards 1,2,3,24,25,48,168. Les deux avec meteo partagent
la meme regression M09 ajustee sur meteo observee historique ; seul son futur
meteorologique change. Le modele sans meteo est reajuste sans temperature ni pluie,
mais conserve les effets feries par heure et les vacances.

Les parametres sont ajustes une seule fois, sur 2012 au 30 decembre 2023 inclus.
La regression et la correction AR sont ajustees par moindres carres ordinaires
avec constante, sans penalisation, uniquement sur cette periode. Le rang des
predicteurs est controle. Les variables et les retards restent fixes ; aucun
reglage n'est effectue sur 2024 lors de ce remplacement d'estimateur.
Les observations nouvelles de 2024 servent a initialiser l'AR chaque jour,
pas a reestimer les coefficients. Les scores 2024 sont une validation pour les
choix suivants ; ce n'est pas le test final, qui reste 2025.

## Fusion corrigee

La preparation canonique est expliquee dans [00_donnees.md](00_donnees.md).
Le script lit `data/merge/donnees_combinees.csv` puis limite immediatement l'analyse
aux dates anterieures a 2025. Le modele utilise `temperature_moyenne_00_30` et
la pluie alignee sur l'intervalle de consommation. Les anciens exports temporaires
ont ete supprimes ; train, validation et test ont tous ete regeneres par la meme
preparation. Le test 2025 est realigne, mais jamais evalue.

## Disponibilite a J,14 h

Une temperature horaire SYNOP peut utiliser la mesure de l'heure synoptique suivante.
Il ne suffit donc pas que son etiquette precede 14 h. Pour une ligne initiale UTC u,
la derniere source necessaire a nos covariables est majoree par ceil_3h(u+1 h).
On lui ajoute **trois heures de delai suppose de publication**.

Les trois scenarios utilisent le meme dernier creneau de consommation : **J,8 h**.
La puissance de ce creneau est la moyenne des valeurs a 8:00 et 8:30. On suppose
qu'elle est publiee a 14 h ; les fichiers definitifs ne donnent pas son instant
de publication reel. Le choix 8 h permet aussi aux covariables meteo de ce creneau
de respecter la borne de disponibilite ci-dessus, en hiver comme en ete.
Les 168 residus horaires precedents doivent etre disponibles sans trou.

L'AR prevoit recursivement les heures suivantes jusqu'a 23 h du lendemain, sans
acceder a aucune consommation ulterieure a la coupure. Les 24 cibles du lendemain
sont a 10–33 heures de l'origine, ou 16–39 heures de la derniere etiquette observee.

Pour la persistance, chaque temperature/pluie cible est remplacee par celle du
meme instant UTC **48 heures auparavant**. Aucune observation future n'entre
dans cette prevision. Ce decalage assure que meme la source de la derniere heure
du lendemain est anterieure a l'origine, en tenant compte de la reconstruction.
Il conserve approximativement le cycle journalier ; ce n'est pas une prevision
numerique de l'atmosphere et il peut echouer lors des changements rapides de temps.

Le scenario parfait est volontairement idealise. Son historique AR est toutefois
soumis aux memes coupures que les deux autres, pour isoler l'effet de la meteo future.
Les valeurs maximales de disponibilite sont exportees pour chaque origine dans
`audit_disponibilite.csv` et verifiees par assertions.

## Limites du realisme

Les delais de publication sont des hypotheses, pas des disponibilites historiques
observees. Les donnees RTE definitives peuvent differer de celles publiees en temps
reel. Le reseau meteorologique a ete selectionne sur une periode allant au-dela
du train : cette selection doit encore etre refaite sur le passe pour une simulation
entierement operationnelle. Les scripts ne pretendent donc pas certifier un systeme
deployable, meme pour les scenarios sans meteo future.

Les trois scenarios et les trois benchmarks partagent les memes 333 jours de 2024, soit 7992 heures :
24 jours exclus pour historique incomplet et trois pour cible ou meteo parfaite
incomplete (dont les changements d'heure), ainsi que six pour references de benchmarks indisponibles ou journees de changement d'heure. Aucune exclusion ne depend de la taille
de l'erreur. Exiger la meteo observee de la cible sert a comparer les scenarios
sur le meme support, mais limite la portee des scores a ces journees admissibles.

Les [trois benchmarks de consommation](10_benchmarks.md) utilisent eux aussi la coupure J8 h. Ils sont calcules sans meteo et ne doivent pas etre confondus avec la persistance meteo.

## Resultats et decision

| Methode | MAE (MW) | RMSE (MW) | Biais observation - prevision (MW) |
|---|---:|---:|---:|
| Moyenne des quatre semaines | 3583.7 | 5296.3 | 504.9 |
| Persistance consommation | 5661.0 | 7055.0 | -671.3 |
| Semaine précédente | 3251.0 | 4931.8 | 246.3 |
| Météo parfaite (comparaison idéale) | 1450.7 | 2030.5 | -100.1 |
| Persistance météo à 48 h | 2311.2 | 3359.1 | 5.4 |
| Sans météo | 1783.5 | 2545.8 | 13.5 |

La meteo parfaite reduit la RMSE d'environ 20,2 % par rapport a l'absence de meteo.
En revanche, la persistance l'augmente d'environ 31,9 %. Elle fait mieux que le
modele sans meteo seulement 132 jours sur 333, selon l'erreur quadratique quotidienne.
Son erreur absolue moyenne de temperature est d'environ 2,25 degres C.
Le modele a ete ajuste avec la meteo observee : il n'a pas appris a attenuer
automatiquement les erreurs de cette prevision de temperature rudimentaire.

Pour la suite, le modele **sans meteo + AR saisonnier** est donc le candidat
pratique le plus convaincant parmi les deux scenarios sans meteo future observee
testes ici. L'apport potentiel d'une meilleure prevision meteo reste visible,
mais il n'est pas obtenu avec la persistance a 48 h.

Ces scores ne sont pas directement comparables aux scores 2021–2023 : autre annee,
autre support et coupure d'observation plus ancienne. Le test 2025 n'est pas evalue
et son fichier realigne reste identique pendant la validation (empreinte SHA-256 verifiee).

## Trois echecs de la persistance

Les trois jours ci-dessous sont selectionnes apres evaluation uniquement pour
interpreter les erreurs, sans ajuster de nouveau modele.

| Jour | Temperature observee - persistance, moyenne (C) | RMSE consommation (MW) |
|---|---:|---:|
| 2024-11-25 | +7,07 | 14309,3 |
| 2024-01-22 | +8,91 | 15021,6 |
| 2024-01-20 | -6,59 | 10978,1 |

Les deux premiers jours sont beaucoup plus chauds que la reference repetee :
le modele avec persistance surestime fortement la consommation. Le troisieme
est plus froid et la consommation est sous-estimee. Cela concorde avec la
thermosensibilite apprise. La meteo parfaite reduit fortement ces erreurs,
mais ne les annule pas toutes, notamment le 25 novembre. Une limite du modele
ou d'autres facteurs non observes subsistent ; aucun evenement externe precis
n'a ete verifie pour expliquer cet ecart. Aucun de ces trois jours n'est ferie.

## Controles et fichiers

- Concordance de la fusion corrigee avec la table auditee sur le train.
- Controle hiver/ete et borne de disponibilite de toutes les sources meteo utilisees.
- Test de non-fuite : modifier les observations meteo futures ne change pas la
  persistance ; une demande necessitant une source future est rejetee.
- Modeles ajustes avant la premiere origine ; parametres inchanges pendant 2024.
- Meme nombre de jours et exactement 24 previsions finies par origine/scenario.
- Aucun test ou reglage sur les consommations 2025 ; empreinte du test inchangee.
- Inspection visuelle des trois journees d'echec.

Les sorties comprennent scores globaux, mensuels et journaliers, predictions,
erreurs meteo, audit de disponibilite, parametres, ACF/PACF et graphiques d'echecs.
Les ACF/PACF portent sur des erreurs de prevision a plusieurs pas, qui ne sont
pas necessairement blanches meme pour un modele correctement specifie.

Reproduction depuis la racine :

```bash
python data/merge/merge.py
python data/merge/train_valid_test_split.py
python analyse_consommation/scripts/validation_meteo_2024.py
```
