# Saisonnalites et meteo : estimation conjointe

Execution : `python src/decomposition.py` depuis la racine du projet.
Dependances : pandas, numpy, matplotlib, statsmodels, scikit-learn.

## Un seul modele

Le script ajuste une regression sur la consommation brute de `data/processed/train.csv`
(2012-2023). Toutes les contributions sont estimees simultanement :

- tendance lineaire par morceaux, avec un changement de pente annuel ;
- cycle annuel : trois paires sinus/cosinus, periode de 365,2425 jours ;
- profil des 168 heures de la semaine ;
- temperature : max(18 - T, 0) et max(T - 22, 0) ;
- log(1 + precipitations) ;
- indicateurs de meteo manquante.

Le profil de semaine est separe en profil journalier moyen sur les sept jours
et ecarts a ce profil selon le jour : ces ecarts constituent le cycle hebdomadaire.
Cette convention evite de compter deux fois le cycle journalier dans celui de semaine.
Les profils saisonniers sont fixes sur l'apprentissage : MSTL n'est plus utilise.

Les contributions saisonnieres et meteo sont centrees sur zero. La tendance,
l'interception et les controles d'imputation ne sont jamais soustraits.
Les jours feries et vacances ne sont pas corriges.

## Series comparees

- `sans_saisonnalites` : consommation moins les trois cycles estimes conjointement ;
- `sans_temperature` : serie precedente moins la contribution temperature ;
- `sans_precipitations` : serie sans saisonnalites moins la contribution pluie ;
- `sans_meteo` : serie sans saisonnalites moins les deux contributions meteo.

L'identite est : consommation = trois cycles + effet temperature + effet pluie
+ sans_meteo. La serie finale conserve la tendance : ce n'est pas le residu strict
de la regression. Aucune seconde regression n'est ajustee apres la correction.

## Graphiques regeneres

1. `01_decomposition_annuelle.png` : consommation, cycle annuel et serie sans cycles,
   en moyennes quotidiennes.
2. `02_decomposition_saisonniere.png` : trois cycles et serie corrigee sur quatre semaines.
3. `03_acf_pacf.png` : retrait progressif des trois cycles.
4. `04_acf_pacf_composantes.png` : ACF/PACF des trois cycles.
5. `05_correction_meteo_annuelle.png` : comparaison meteo en moyennes quotidiennes.
6. `06_correction_meteo_horaire.png` : comparaison meteo sur quatre semaines.
7. `07_acf_pacf_meteo.png` : ACF/PACF avant/apres correction meteo.
8. `08_acf_pacf_effets_meteo.png` : ACF/PACF des contributions temperature et pluie.

Les correlogrammes couvrent 336 heures avec reperes a 24 et 168 h ; ils ne montrent
pas un pic a un an. PACF : Levinson-Durbin sur autocovariances biaisees par FFT.
Les bandes a 95 % sont ponctuelles et indicatives, surtout pour les cycles deterministes.

## Exports et limites

`composantes.csv` contient les series horaires. `coefficients_regression.csv`
contient tous les coefficients, `coefficients_meteo.csv` leur sous-ensemble meteo.
`comparaison_meteo.csv` fournit ecarts-types et autocorrelations a 1, 24 et 168 h.
La meteo absente est remplacee par la mediane du meme mois et de la meme heure
sur l'apprentissage ; `imputations_meteo.csv` identifie ces valeurs.
Le script suppose une consommation complete sur une grille horaire reguliere.

L'estimation conjointe tient compte du recouvrement entre saison et meteo, mais
leur attribution reste dependante du modele : les contributions ne sont pas causales.
Retirer uniquement les cycles laisse la saisonnalite portee par la meteo ; retirer
uniquement la meteo laisse les cycles. Meme apres les deux corrections, la tendance
conservee, les profils variables et les facteurs omis peuvent maintenir des structures.
Une baisse de dispersion ne demontre pas une amelioration de prevision.
L'analyse utilise tout l'apprentissage et la meteo observee simultanee : elle est
retrospective. Validation et test ne sont pas utilises. Pour prevoir a J, 14 h,
il faudra respecter la disponibilite des variables et reestimer sur le passe.

## Comparaison des methodes

Voir [COMPARAISON_METHODES.md](COMPARAISON_METHODES.md) pour les sept methodes,
le protocole temporel, les resultats et les limites. La methode a seuils est retenue.
Les variables communes sont construites dans src/modele_decomposition.py.
