# Donnees meteorologiques

Depuis la racine du projet :

```bash
python data/temperature/extraction_meteo.py
python data/temperature/graphiques_mensuels.py
```

Les chemins et dates sont definis dans `chemins.py`. Les donnees brutes sont
conservees dans `raw`. Les CSV existants et valides sont
reutilises ; les fichiers manquants sont telecharges.

## Sorties conservees

Dans `processed` :

- `moyennes_reseau_horaires.csv` : temperature et precipitation horaires,
  moyennes et ecarts-types entre stations.
- `stations_selectionnees.csv` : stations retenues et couverture globale.
- `stations_metropole.csv` : noms et coordonnees, utilises par la carte.
- `bilan_selection_stations.csv` : couverture et decision pour chaque station.
- `couverture_stations_par_annee.csv` : controle de la couverture annuelle.
- `conflits_metropole.csv` : valeurs contradictoires remplacees par des manquants.
- `bilan_nettoyage.csv` : nombres de lignes, doublons et contradictions.

Les compteurs de doublons du bilan concernent toutes les stations importees ;
les compteurs contenant `metropole` concernent uniquement les stations 07xxx.
Une cellule contradictoire correspond a une variable pour un couple station/date.

Le journal de telechargement reste dans `data/temperature`.
Le script de graphiques produit le bilan mensuel et les trois PNG dans `graphiques`.

## Exports optionnels

Dans `extraction_meteo.py`, `EXPORT_DIAGNOSTICS = False` evite les exports
intermediaires. Les fonctions se transmettent directement les tableaux en memoire.
Mettre cette option a `True` ajoute les cinq gros tableaux SYNOP intermediaires,
l'inventaire, les doublons, le diagnostic des conflits, les versions repetees et
le tableau de couverture de temperature. Ces fichiers sont ecrits dans `processed`.
Cela facilite l'audit mais augmente l'espace disque et le temps d'execution.
Les tableaux restent necessaires en memoire, meme sans export.

Les anciens fichiers intermediaires deja presents ne sont pas supprimes
automatiquement. Avec l'option desactivee, ils ne sont ni lus ni actualises :
ils peuvent donc correspondre a une execution anterieure.

Les regles de selection (> 95 % pour temperature ET pluie), de nettoyage et
les calculs horaires restent les memes. La reconstruction horaire est
retrospective : une valeur interpolee peut utiliser une mesure ulterieure.

## Convention horaire

`date_utc` désigne l'instant de la température et le début de l'intervalle de pluie : à 10 h, la pluie couvre 10–11 h. Un cumul SYNOP enregistré à 12 h est divisé par trois et affecté aux heures 9 h, 10 h et 11 h. La date de la mesure source reste 12 h dans les diagnostics. Ni le merge ni les graphiques mensuels ne décalent à nouveau la pluie. La dernière heure de la grille reste sans pluie si aucune mesure ne couvre l'intervalle suivant.
