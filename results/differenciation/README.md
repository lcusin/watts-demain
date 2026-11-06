# Differences a 52 semaines, 24 heures et 1 heure

Depuis la racine :

```bash
python src/differenciation.py
python src/diagnostic_pics_acf.py
```

Le script utilise uniquement train.csv (2012-2023). Il compare la consommation
brute, la consommation sans tendance lineaire, la difference a 364 jours,
cette difference apres retrait de la tendance et la difference a 364 jours
suivie de celle a 24 heures, puis cette derniere suivie de celle a 1 heure.

## Calcul final

z(t) = C(t) - C(t - 8736 heures)

w(t) = z(t) - z(t - 24 heures)

Enfin v(t) = w(t) - w(t - 1 heure).

Soit (1 - B)(1 - B^24)(1 - B^8736) C(t). On retire a la difference annuelle sa valeur
au meme horaire la veille. Les six series utilisent les memes dates, apres
365 jours et une heure d'historique. Le decalage de 364 jours conserve le jour de la semaine,
y compris autour du 29 fevrier. Les heures sont celles du fichier, supposees UTC ;
les jours feries et changements d'heure civile ne sont pas automatiquement alignes.

La tendance est une droite estimee sur toutes les observations de 2012-2023.
La soustraire avant la difference annuelle ne change cette derniere que d'une
constante, donc pas ses ACF/PACF centrees. La double difference annuelle et
journaliere annule deja une tendance parfaitement lineaire.

## Sorties

- 01_series.png : six series sur quatre semaines.
- 02_acf_pacf.png : ACF/PACF jusqu'a 336 heures, sur toute la periode commune.
- 03_tendance_12_ans.png : consommation, droite et consommation sans tendance.
- 04_pics_acf.png : comparaison des differences annuelle, annuelle/journaliere et triple,
  aux retards courts et longs (jusqu'a 9000 heures).
- series_differenciees.csv : les six series horaires communes.
- tendance.csv et coefficients_tendance.csv : tendance sur toute la periode.
- pics_acf.csv et reperes_acf.csv : extrema locaux et valeurs aux retards choisis.

Les pics locaux sont detectes avec une proeminence minimale de 0,02, critere
visuel et non test statistique. Les bandes a 95 % sont ponctuelles, pas simultanees.
La differenciation peut laisser des motifs et introduire une correlation negative
aux retards soustraits ; elle ne garantit pas un bruit blanc.

Les donnees actuelles sont completes et regulieres a l'heure. Le script conserve
les trous eventuels : si les donnees changent, il faudra verifier leur completude.
L'analyse est descriptive ; validation 2024 et test 2025 ne sont pas utilises ici.

Les differences a retards fixes commutent : appliquer 24 h puis 1 h donne
le meme resultat que 1 h puis 24 h, sur les memes dates completes.
La derniere serie est donc identique a la triple difference testee auparavant,
a l'arrondi numerique pres. Les etapes intermediaires restent affichees.
