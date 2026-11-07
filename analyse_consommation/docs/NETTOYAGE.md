# Réorganisation du 7 novembre 2026

## Ce qui a été fait

- Déplacement du travail de `results/description` vers `analyse_consommation`.
- Séparation des scripts, documents, sources d'audit et résultats par étape.
- Centralisation des chemins et création d'un point d'entrée reproductible.
- Remplacement des notes cumulatives devenues contradictoires par des documents
  décrivant l'état final, avec une synthèse spécifique au rendu.
- Conservation des expériences moins bonnes lorsqu'elles justifient les choix :
  un résultat négatif documenté n'est pas un fichier inutile.

## Suppressions justifiées

- `data/merge/combiner_donnees.R` : ancienne fusion non appelée, dépendant des archives R.
- `data/merge/donnees_combinees_2012_2024.csv` : export temporaire remplacé par la fusion canonique.
- Copie `donnees_alignees_train.csv` propre aux analyses : les modèles lisent maintenant
  directement le train canonique ; aucune deuxième implémentation de fusion.
- Ancien document généré de tendance, remplacé par l'unique `RESULTATS.md` de l'étape 2.
- Notes historiques répétées ou périmées, dont le contenu utile est intégré aux
  protocoles actuels ; caches Python et dossiers devenus vides.

Les fichiers bruts des fournisseurs et les travaux antérieurs hors de cette
analyse ne sont pas supprimés. Les CSV de composantes ont un rôle précis :
comparaison des méthodes, vérification des reconstructions ou diagnostic des erreurs.

## Données corrigées

`merge.py` est la seule fusion. Les scripts d'analyse n'en reproduisent plus la
logique. Les fichiers fusionnés et les trois splits sont régénérés ensemble.
La cible de consommation ne change pas ; les covariables météo sont réalignées.
Les étiquettes civiles et les instants UTC sont explicitement distingués.

Le test 2025 a été **réaligné**, pas laissé avec l'ancien décalage. Il n'a pas été
évalué ni utilisé pour sélectionner les modèles. Sa nouvelle empreinte est figée
pendant la validation 2024. Les anciennes affirmations « fusion encore à corriger »
ne décrivent donc plus l'état courant.

## Vérification

La chaîne entière est relancée après déplacement. Les contrôles vérifient :

1. La syntaxe des scripts et leurs chemins dans la nouvelle structure.
2. L'identité des consommations entre fusion et concaténation des splits.
3. La cohérence des météo, calendriers, horaires et bornes train/validation/test.
4. La stabilité des scores des trois dernières expériences par rapport à ceux
   enregistrés avant rangement, avec une tolérance numérique explicitée dans le code.
5. La lisibilité et le caractère non vide des résultats, et l'absence de fichiers
   de résultats strictement identiques par leur empreinte.
6. L'intégrité du test réaligné pendant l'évaluation 2024.

Les résultats effectifs des contrôles sont dans `resultats/CONTROLES.json` et
les durées d'exécution dans `resultats/execution.json`. Le petit fichier
`sources/scores_reference.json` est une référence de non-régression du nettoyage,
pas un deuxième jeu de résultats à présenter. Si la méthode ou les données
changent intentionnellement, cette référence devra être revue explicitement.
