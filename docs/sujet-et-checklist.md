# Sujet et checklist de rendu

Synthèse de travail de l'énoncé « Données temporelles — Projet de prévision : Consommation électrique en France métropolitaine ». Se reporter au PDF original du cours pour les formulations exactes.

## 1. Problème
- [ ] Définir cible, période, exclusions, origine à 14 h du jour J et horizon de 24 heures pour J+1.
- [ ] Lister les informations effectivement disponibles à 14 h.

## 2. Données
- [ ] Récupérer la consommation éCO2mix (RTE) et les observations SYNOP (Météo-France).
- [ ] Construire les variables calendaires utiles et justifier les événements retenus.
- [ ] Ramener les données à l'heure ; expliquer stations, agrégation spatiale, valeurs manquantes, changements d'heure et valeurs atypiques.
- [ ] Séparer scénario opérationnel et scénario rétrospectif à météo parfaite, si celui-ci est étudié.

## 3. Analyse et modèles
- [ ] Explorer cycles journaliers et hebdomadaires, saisonnalité annuelle, météo, calendrier, ruptures et anomalies.
- [ ] Comparer au moins deux benchmarks simples sur les mêmes journées et avec la même information.
- [ ] Choisir des modèles de complexité différente ; justifier chaque ajout.

## 4. Validation et évaluation
- [ ] Définir apprentissage, validation, test final, fréquence de réestimation et sélection des variables/hyperparamètres.
- [ ] Rejouer chaque origine de prévision à 14 h sans fuite d'information.
- [ ] Évaluer MAE, RMSE et des erreurs quotidiennes / pointe pertinentes ; examiner saisons, types de jours et conditions météo.

## 5. Audit critique (environ 1 à 2 pages du rapport)
- [ ] Tableau de disponibilité des variables et risques de fuite.
- [ ] Benchmark vs modèle simple vs modèle élaboré ; ablation ou sensibilité.
- [ ] Étudier au moins trois journées de forte erreur.
- [ ] Discuter stabilité des classements et conditions où le système serait déconseillé.

## 6. IA et livrables
- [ ] Documenter trois cas : proposition conservée après vérification, proposition modifiée/rejetée, erreur ou réponse trompeuse détectée.
- [ ] Mini-rapport de moins de 10 pages (hors titre, bibliographie et annexes techniques raisonnables).
- [ ] Code reproductible et README avec dépendances, organisation, ordre d'exécution et étapes coûteuses.
- [ ] Oral avec diapositives de 10 minutes maximum ; chacun doit pouvoir expliquer le travail.
