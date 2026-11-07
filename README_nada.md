# Prévision horaire de la consommation électrique en France

Projet de données temporelles — Master MALIA. Groupe de trois personnes.

## Objectif
À 14 h le jour J, prévoir la consommation électrique de France métropolitaine pour chacune des 24 heures du jour J+1. Le protocole opérationnel ne doit utiliser que les informations disponibles à cette origine de prévision.

## Démarrage du groupe
1. Remplacer « membre-1 », « membre-2 », « membre-3 » par vos prénoms dans `docs/notes/`.
2. Lire `docs/sujet-et-checklist.md` et remplir `docs/protocole.md` ensemble.
3. Consigner chaque séance dans `docs/journal-de-bord.md` et les choix durables dans `docs/decisions.md`.
4. Documenter toute variable dans `docs/disponibilite-donnees.md` **avant** de l'utiliser dans un modèle opérationnel.

## Organisation
- `docs/` : protocole, décisions, notes individuelles et audit critique.
- `data/raw/` : fichiers sources locaux ; `data/processed/` : données horaires dérivées.
- `notebooks/` : exploration et analyse, numérotées dans l'ordre logique.
- `src/` : code réutilisable pour collecte, préparation, variables, modèles et évaluation.
- `results/` : figures et tableaux produits ; `rapport/` et `presentation/` : rendus finaux.

## Installation et exécution
Créer un environnement Python, puis installer les dépendances avec `pip install -r requirements.txt`. Le groupe complétera ici les commandes exactes de téléchargement et d'exécution au fur et à mesure de leur implémentation. Chaque opération de nettoyage et chaque résultat du rapport doivent pouvoir être reproduits à partir du code versionné et des sources documentées.

## Sources prévues
Consommation : RTE éCO2mix. Observations météo : réseau SYNOP de Météo-France. Variables calendaires : construites par le groupe. Noter URL, période, date de récupération, licence et méthode d'agrégation dans `docs/sources.md`.

## Attention au protocole
Une valeur observée après 14 h le jour J ne peut pas servir à prévoir J+1 dans le scénario opérationnel. La météo observée pendant J+1 peut servir à un scénario rétrospectif « météo parfaite », clairement séparé. Apprentissage, validation et test final suivent l'ordre chronologique ; le test ne sert pas à choisir les variables ni les hyperparamètres.

## Travail en groupe
Créer une issue GitHub par tâche, travailler sur une branche par tâche, puis faire relire chaque pull request par une autre personne. Les notes individuelles ne remplacent pas le journal commun ni la compréhension collective du code.
