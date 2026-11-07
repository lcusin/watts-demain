# Watts Demain — prévision de consommation électrique

Projet de données temporelles, Master MALIA. À 14 h le jour J en heure française,
prévoir les 24 puissances moyennes horaires de J+1. La cible est en MW, pas en MWh.
La chaine principale applique les memes regles horaires a tous les modeles.

## Organisation

- `main.py` : lanceur principal.
- `data/conso/`, `data/calendrier/`, `data/temperature/` : scripts de préparation,
  données sources dans `raw/` et données préparées dans `processed/`.
- `data/merge/` : fusion et trois sous-ensembles chronologiques.
- `src/` : exploration, benchmarks, AR/ARMA, ML, contrôles et diagnostics.
- `results/analyse_2024/` : sorties de la chaîne principale.
- `docs/sujet-et-checklist.md` : consignes du projet.
- `rapport/`, `presentation/` : livrables, distincts des calculs.
- `Archives/` : anciennes chaînes, sorties, notes et documents remplacés ; ignoré par Git.
  Les fichiers archivés sont des témoins historiques, pas des points d'entrée exécutables.

Ce README est la documentation générale unique. Les comptes rendus calculés
(`SYNTHESE.md`, `ANALYSE_ECHECS.md`) restent des résultats, pas des modes d'emploi.

## Environnement de référence

Environnement de Lola : Anaconda, Python 3.11.7. Les versions effectivement installées
ont été relevées dans `requirements.txt`. Aucun changement d'environnement n'a été effectué.
Pour reproduire cet environnement dans un environnement Python séparé :

```powershell
python -m pip install -r requirements.txt
```

Aucun notebook n'est nécessaire. Les dépendances sont NumPy, pandas, Matplotlib,
SciPy, scikit-learn, statsmodels, seaborn et threadpoolctl.

## Ordre d'exécution

Depuis la racine du dépôt, avec l'interpréteur Anaconda de Lola :

```powershell
python main.py
```

| Étape | Contenu |
|---:|---|
| 0 | Préparation consommation, calendrier, météo ; fusion ; découpage |
| 1 | Exploration du train et ACF/PACF horaires |
| 2 | Couverture geographique des stations |
| 3 | Trois benchmarks |
| 4 | AR(1), AR(2), ARMA(1,1) sur différence hebdomadaire |
| 5 | Régression linéaire, Ridge, Random Forest, Gradient Boosting |
| 6 | Contrôles communs, comparaison globale et synthèse |
| 7 | Énergie quotidienne, pointes, saisons et journées d'échec |

Pour conserver les données déjà préparées et ne reprendre que les prévisions :

```powershell
python main.py --depuis 3
```

`--jusqua` permet de s'arrêter après une étape. Les sorties correspondantes sont
remplacées. L'extraction météo réutilise les CSV bruts valides ; elle peut télécharger
les fichiers manquants. La couverture géographique et les ajustements statistiques/ML
peuvent être coûteux. Aucune de ces opérations n'a été relancée lors du rangement.
Les scripts restent lançables séparément avec `python src/nom_du_script.py`.

## Données et préparation

- RTE : fichiers annuels éCO2mix téléchargés directement sur le site, au format texte
  tabulé malgré l'extension `.xls`. Moyenne des valeurs à :00 et :30, datée en début d'heure.
- Calendrier : jours de semaine, week-ends, jours fériés et vacances scolaires par zone.
  Les étiquettes horaires sont en heure civile française.
- SYNOP : observations à 3 h ; stations métropolitaines avec couverture strictement
  supérieure à 95 % pour température ET précipitations. Moyenne spatiale à poids égaux.
  L'écart-type entre stations n'est pas un intervalle de confiance national.
- Température : interpolation entre mesures valides espacées de trois heures.
  Pluie : cumul réparti également sur les trois heures précédentes, datées au début
  de l'intervalle. À 10 h, la pluie couvre 10–11 h. Aucun second décalage dans la fusion.
- `date_utc` sert à joindre la météo ; `horodatage` garde l'heure française.
  Les heures ambiguës ou inexistantes restent sans correspondance UTC. La fusion
  conserve les lignes ; les scripts de prévision masquent les journées de transition.
- Apprentissage : 2012–2023 ; validation : 2024 ; test réservé : 2025 uniquement.
  Les graphiques exploratoires de consommation et météo utilisent seulement 2012–2023.
  Les graphiques de prévision portent sur la validation 2024, jamais sur le test 2025.

La fusion de référence est `data/merge/donnees_combinees.csv`. `train.csv`,
`validation.csv`, `test.csv` sont ses sous-ensembles et ne sont pas des doublons à supprimer.
Le test est préparé par les mêmes règles déterministes, mais n'est ni exploré ni évalué.

### Sorties météo utiles

`processed/` conserve les moyennes horaires, stations sélectionnées, positions,
bilan de sélection, couverture annuelle, conflits et bilan de nettoyage.
`EXPORT_DIAGNOSTICS = False` dans `extraction_meteo.py` évite les gros exports
Le journal de telechargement est conserve dans `data/temperature/processed/`.
La couverture géographique mesure la distance à une station, pas la représentativité
climatique ni une couverture pondérée par la population.

## Règles communes

- Prévision émise à J14, consommation disponible jusqu'à J8 inclus, en heure française.
  Ce délai est une hypothèse conservatrice, pas une disponibilité historique vérifiée.
- Grille horaire conservée. Mesures des deux journées de changement d'heure masquées.
- La fonction `jours_communs` de `protocole.py` sélectionne les journées complètes :
  cible D=J+1, matin de J, journées historiques du ML (J-1, J-7, J-14, J-28),
  références des benchmarks (D-7, D-14, D-21, D-28) et 169 heures jusqu'à J8
  pour disposer d'une semaine d'historique et de la différence hebdomadaire à la coupure.
  Cette règle conservatrice est commune, même si un modèle utilise moins d'historique.
- Les valeurs météo de la cible ne servent ni aux prédicteurs ni à la sélection des dates.
- Météo passée : borne de disponibilité `ceil_3h(date_utc + 1 h) + 3 h`, tenant compte
  de la pluie datée en début d'intervalle, de l'interpolation et d'un délai SYNOP supposé.
  Les valeurs du matin non disponibles à J14 sont masquées ; les historiques journaliers
  sont contrôlés. Les valeurs manquantes sont imputées dans le pipeline ajusté sur le train.
- Modèles ML entraînés sur des cibles depuis 2012 jusqu'au 30 décembre 2023 inclus :
  le 31 décembre entier ne serait pas connu à la première origine de prévision.
- AR/ARMA entraînés depuis 2012 jusqu'au 31 décembre 2023 à J8 ; coefficients ensuite
  fixes, états actualisés seulement jusqu'à la coupure. Les trous restent dans la série
  différenciée, traités par le modèle ; les avertissements sont visibles et la convergence contrôlée.
- Validation 2024 ; test 2025 non chargé. Le classement sur 2024 reste une validation,
  pas un résultat sur un test indépendant.

Les familles et hyperparametres compares sont : difference de 168 h,
AR(1), AR(2), ARMA(1,1), régression linéaire, Ridge, Random Forest et Gradient Boosting.
Les trois benchmarks sont persistance à J8, semaine précédente et moyenne de quatre semaines.
Les retards du ML sont relatifs à J, et restent différents des retards des benchmarks relatifs à D.


## Contrôles et résultats

Chaque famille écrit ses prévisions horaires, ses scores, `jours_evalues.csv` et
`execution.json` (empreintes du train, de la validation, des scripts et versions Python).
Les contrôles refusent des sorties périmées, des modèles manquants, des dates différentes,
des doublons ou des valeurs non finies. Ils recalculent MAE/RMSE et vérifient les trois
formules de benchmark. Aucun fichier du test 2025 n'est chargé par les analyses.

`synthese.py` produit `comparaison_globale.csv`, `previsions_communes.csv`,
`CONTROLES.json` et `SYNTHESE.md`. Une erreur bloque la chaîne avant les diagnostics.

`diagnostics.py` produit, pour chaque modèle :
- MAE, RMSE et biais par saison, heure, week-end, jour férié et vacances ;
- énergie quotidienne en MWh : somme des 24 puissances moyennes multipliées par 1 h ;
- erreur de valeur et d'heure de pointe (premier maximum en cas d'égalité ; distance absolue non circulaire) ;
- trois pires journées du meilleur modèle hors benchmarks selon la RMSE, avec courbes,
  contexte météo/calendaire observé et constats chiffrés. L'interprétation des causes
  reste à rédiger après vérification : le programme n'invente pas d'événement explicatif.

Les erreurs signées sont observé moins prévu : un biais négatif indique une surestimation.
La météo de la cible utilisée dans ces diagnostics est rétrospective, jamais un prédicteur.
Les contrôles numériques ne remplacent pas l'audit de disponibilité historique.

## Limites et état du travail

Les resultats harmonises sont produits dans `results/analyse_2024/`.
reste une validation, pas une évaluation finale indépendante. Le choix des stations
sur une période dépassant le train, les données RTE révisées et les délais de publication
supposés limitent l'interprétation opérationnelle. La différence hebdomadaire ne garantit
pas à elle seule la stationnarité ; les diagnostics doivent être interprétés.

Les anciens documents et notes sont conservés dans `Archives/ancienne_chaine_et_documentation/`.
Le rapport utilise les figures de la chaine active.
