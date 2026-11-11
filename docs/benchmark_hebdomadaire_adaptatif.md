# Prévision hebdomadaire adaptative : méthode, variantes et audit

## Objectif et positionnement

À 14 h le jour **J** (heure française), produire 24 prévisions de puissance moyenne (MW) pour le lendemain **D = J+1**. Le benchmark utilise la saisonnalité hebdomadaire et un ajustement de niveau mesuré le matin de J, sans apprentissage supervisé. Il apporte une référence simple, explicable et peu coûteuse face aux méthodes ML.

L'expérience suit le découpage du projet : **2012–2023 : apprentissage**, **2024 : validation**, **2025 : test final de l'étude principale**. La méthode complémentaire n'accède pas à 2025. La comparaison 2024 porte sur les **338 mêmes jours (8 112 heures)** que les dix méthodes de référence, grâce à `results/analyse_2024/benchmarks/jours_evalues.csv`.

## 1. V1 : moyenne hebdomadaire pondérée, ajustée par le matin

Pour une date cible D, une heure h et une semaine passée k allant de 1 à K :

\[
 w_k = \frac{\alpha^{k-1}}{\sum_{j\in\mathcal K_D}\alpha^{j-1}},
 \qquad
 P_{D,h} = \sum_{k\in\mathcal K_D}w_k C_{D-7k,h},
\]

\[
 \Delta_J = \frac{1}{9}\sum_{r=0}^{8}
  \left(C_{J,r}-\sum_{k\in\mathcal K_D}w_kC_{J-7k,r}\right),
 \qquad
 \widehat C_{D,h} = P_{D,h}+\lambda\Delta_J.
\]

Les paramètres de référence sont **K = 8**, **α = 0,7**, **λ = 1** et au moins **quatre semaines complètes**. Les poids sont renormalisés si une semaine est indisponible. On peut interpréter `Δ_J` comme la différence entre le niveau de ce matin et celui des matins comparables. L'ajustement est identique pour les 24 heures de la cible : c'est à la fois la simplicité et la limite de cette approche.

**Contrôle temporel :** seules les consommations de J entre 00 h et 08 h, et celles des semaines antérieures, interviennent dans une prévision. Les données de D sont utilisées *uniquement pour évaluer l'erreur*. Les journées ambiguës aux changements d'heure sont masquées dans les historiques. Sur la validation jointe, **320 jours** utilisent huit semaines et **18 jours** n'en utilisent que sept.

**Pourquoi hebdomadaire plutôt qu'annuel ?** Le profil de même jour de semaine conserve la structure travail/week-end, alors qu'une date anniversaire peut changer de jour de semaine d'une année à l'autre. Les poids favorisant les semaines récentes s'adaptent plus rapidement au niveau local qu'une moyenne pluriannuelle brute.

## 2. V2 : modifications et hypothèses testées

| Variante | Modification | Raison et risque |
|---|---|---|
| Filtre calendaire | Écarte les fêtes passées pour une cible ordinaire, si suffisamment de semaines restent. Neutralise l'ajustement du matin quand J est férié et D ordinaire. | Éviter des analogues mal assortis ; risque de réduire l'historique disponible. |
| Proportionnelle | Multiplie le profil selon le rapport du niveau réel du matin au niveau historique (rapport borné entre 0,75 et 1,25). | Réagir à des changements relatifs de charge ; peut amplifier le bruit. |
| Hybride | Moyenne des corrections additive et proportionnelle. | Arbitrage empirique ; pas nécessairement meilleur que chacune séparément. |
| Fêtes annuelles | Ratio de la charge d'une fête *à date fixe* avec celle de semaines précédentes non fériées, estimé uniquement sur les années antérieures ; facteur borné puis appliqué à intensité 0,5. | Capturer les événements non hebdomadaires ; peu d'exemples et risque de surajustement. |

La correction spécifique ne concerne que les huit fêtes françaises à date fixe codées dans le script. Les fêtes mobiles restent inchangées ; les analogues sont calculés uniquement à partir d'années antérieures à l'origine.

### Calibration : pourquoi 2023 ?

La V2 teste **36 configurations** sur les journées admissibles de 2023, **à l'intérieur du train 2012–2023**, et retient la RMSE minimale. Elle réévalue ensuite sans ajustement cette configuration sur 2024. Ainsi **2023 n'est pas le test final** ; c'est une calibration interne chronologique. Sur les fichiers fournis, 361 journées de 2023 sont admissibles, et la configuration retenue est : **sans filtre calendaire, correction hybride, intensité 0,75, analogues annuels activés**.

**Important pour l'interprétation :** la V1 et la conception de la V2 ont été élaborées après avoir consulté certains résultats 2024. La sélection interne sur 2023 ne supprime donc pas complètement ce biais de développement. La comparaison actuelle est **exploratoire**, sans nouvel examen du test 2025. De plus, la calibration sur 2023 n'a pas été appliquée de manière identique aux autres méthodes de référence.

## 3. Principaux résultats observés sur les fichiers fournis (validation 2024)

| Configuration | MAE (MW) | RMSE (MW) | Interprétation |
|---|---:|---:|---|
| Random Forest du projet | 1 644,14 | 2 383,19 | Meilleure RMSE de cette comparaison |
| V2 : fêtes annuelles | 1 782,92 | 2 624,95 | Meilleure variante *observée* sur 2024, descriptive |
| **V2 : réglage choisi sur 2023** | **1 813,28** | **2 659,47** | Configuration principale de l'expérience V2 |
| Régression linéaire du projet | 2 014,92 | 2 686,24 | RMSE proche de la V2 |
| V1 | 1 816,50 | 2 710,28 | Référence avant corrections |
| Ridge | 2 041,19 | 2 733,42 | Configuration fixée dans le projet |
| Gradient Boosting | 2 324,04 | 3 092,61 | Configuration fixée dans le projet |

La RMSE de la **V2 choisie sur 2023** baisse de **50,81 MW (1,87 %)** face à la V1, sans démontrer une supériorité générale sur les modèles ML. La **variante « fêtes annuelles »** réduit de **85,33 MW (3,15 %)** la RMSE 2024 face à la V1, mais elle a été explorée en connaissant les échecs de 2024 : la présenter comme une variante expérimentale, non comme le modèle retenu indépendamment.

### D'où vient l'amélioration ?

- **Jours fériés (8 journées)** : RMSE V1 **6 166,99 MW** ; V2 fêtes annuelles **4 335,47 MW**. Gain concentré sur un petit groupe, donc estimation incertaine.
- **Jours non fériés (330 journées)** : V1 et V2 fêtes annuelles ont **exactement les mêmes prévisions** (RMSE **2 569,38 MW**). Ce mécanisme ne corrige donc pas un défaut général des jours ordinaires.
- La **V2 choisie sur 2023** améliore la RMSE globale, mais passe de **2 569,38 MW** (V1) à **2 593,54 MW** sur les jours non fériés : l'amélioration n'est pas homogène.
- Les corrections proportionnelle seule et combinée se dégradent en 2024 (RMSE respectives **2 857,93 MW** et **2 923,70 MW**) : complexifier une méthode n'implique pas améliorer sa performance.

### Saisons, énergie et pointe

| Saison | V1 : RMSE (MW) | V2 choisie sur 2023 : RMSE (MW) |
|---|---:|---:|
| Hiver | 4 010,90 | 3 971,48 |
| Printemps | 2 810,50 | 2 499,63 |
| Été | 1 306,15 | 1 214,27 |
| Automne | 1 786,71 | 2 077,33 |

La V2 retenue améliore notamment le printemps et l'été, mais **dégrade l'automne**. Elle reste fragile lors des fortes consommations hivernales. Les erreurs d'énergie quotidienne et de pointe sont calculées dans `energie_et_pointes.csv` ; l'erreur sur l'heure de pointe est une distance **non circulaire** entre heures (de 0 à 23 h).

## 4. Limites et précautions de rédaction

1. **Temporalité :** à chaque origine J 14 h, le code évite la cible et la météo observée de D. Mais l'heure réelle de publication historique des consommations RTE *définitives* n'est pas établie : il s'agit d'une simulation rétrospective.
2. **Calendrier :** seules les dates communes admissibles 2024 sont évaluées. Autour des changements d'heure, des historiques sont masqués ; les 338 jours ne sont pas toute l'année.
3. **Sélection :** les choix de la V2 sont calibrés sur 2023 ; la conception de l'expérience a cependant été influencée par 2024. On ne peut donc pas parler d'une nouvelle validation 2024 aveugle.
4. **Comparaison :** les autres modèles du projet utilisent des hyperparamètres essentiellement fixés, pas la même procédure de recherche sur 2023. Les résultats mesurent donc des *implémentations*, pas l'avantage intrinsèque d'une famille.
5. **Sous-groupes :** les huit jours fériés sont trop peu nombreux pour une inférence statistique robuste. Semaine/week-end, saison et température ne sont pas causalement isolés. Une RMSE agrégée n'est pas la moyenne des RMSE par saison.
6. **Portée opérationnelle :** les fortes variations de météo et les jours atypiques restent difficiles. Les prévisions météo réellement disponibles pour le lendemain ne sont pas utilisées.
7. **Test 2025 :** il est déjà publié pour le modèle principal. Nous ne l'utilisons pas ici pour choisir des corrections ou revendiquer une généralisation supplémentaire.

## 5. Reproduction et fichiers

Exécuter dans cet ordre à la racine du dépôt :

```bash
python src/benchmark_hebdomadaire_adaptatif.py
python src/analyser_benchmark_hebdomadaire_adaptatif.py
python src/experimenter_benchmark_hebdomadaire_v2.py
python -m unittest discover -s tests -p "test_benchmark_hebdomadaire.py"
```

Les scripts régénèrent automatiquement :

- `results/analyse_2024/benchmark_hebdomadaire_adaptatif/` : prévisions et métriques V1 ; dans `diagnostics/`, saison, heure, calendrier, énergie/pointe, figures et **`analyse.md`** ;
- `results/analyse_2024/benchmark_hebdomadaire_adaptatif_v2/` : résultats V2, grille de 2023, ablation, diagnostics, graphiques, **`analyse.md`** et `execution.json` de traçabilité.

Les versions actuelles de l'environnement sont enregistrées dans les manifestes d'exécution. Pour une reproduction au plus proche de l'environnement de référence du projet, utiliser **Python 3.11.7** et les versions listées dans `requirements.txt`. Les résultats détaillés générés par les scripts prévalent sur les valeurs arrondies de ce document.
