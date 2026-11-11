# Étude de corrections du benchmark hebdomadaire — validation 2024

*Rapport recalculé automatiquement à partir des prévisions et de leurs diagnostics.*

## 1. Définition de l'expérience

- Origine : jour J à 14 h ; cible : les 24 heures de J+1.
- Profil hebdomadaire de 8 semaines, poids décroissants 0,7^(k−1), normalisés après exclusion des historiques incomplets.
- V1 : correction additive basée sur la moyenne de l'écart des consommations du matin de J (00–08 h) par rapport aux matins historiques.
- Calendrier : filtrage des fêtes historiques pour une cible non fériée ; neutralisation de l'ajustement du matin lorsque J est férié et J+1 ordinaire.
- Proportionnelle : facteur issu du rapport des consommations matinales, borné dans [0,75 ; 1,25] avant correction ; hybride : moyenne des versions additive et proportionnelle.
- Analogues annuels : sur les seules fêtes légales à date fixe, ratio entre la charge d'une fête historique et celle de semaines précédentes non fériées. Le ratio est borné dans [0,70 ; 1,10], puis appliqué avec une intensité de 0,5. Fêtes mobiles inchangées.
- Sélection du réglage sur 361 journées de 2023, dans l'ensemble d'apprentissage, par RMSE minimale parmi 36 configurations ; évaluation séparée sur 338 journées de 2024.
- Les seules observations disponibles avant l'origine entrent dans les prévisions ; les températures du lendemain ne servent qu'à la description rétrospective.
- Le test 2025 est réservé à l'étude principale et n'est pas consulté.

## 2. Réglage retenu sur l'année interne 2023

- Filtrage des fêtes historiques : non ; mode : **hybride** ; intensité : **0.75** ; analogues de fêtes annuelles : oui.
- RMSE interne 2023 : **2,609.47 MW**.
- 2023 fait partie de l'apprentissage initial 2012–2023 ; il sert ici à calibrer, pas à tester l'algorithme en finale.

## 3. Résultats de validation 2024

| Méthode | MAE (MW) | RMSE (MW) | Biais (MW) |
|---|---:|---:|---:|
| Random Forest | 1,644.14 | 2,383.19 | -145.94 |
| V2 - Feries annuels | 1,782.92 | 2,624.95 | +187.07 |
| V2 - Choix 2023 | 1,813.28 | 2,659.47 | +231.65 |
| V2 - Filtre et feries | 1,784.78 | 2,662.58 | -57.48 |
| Regression lineaire | 2,014.92 | 2,686.24 | -390.01 |
| V1 - Adaptative | 1,816.50 | 2,710.28 | +118.89 |
| Ridge | 2,041.19 | 2,733.42 | -296.66 |
| V2 - Calendrier | 1,818.36 | 2,746.74 | -125.66 |
| V2 - Proportionnelle | 1,948.77 | 2,857.93 | +131.23 |
| V2 - Combinee | 1,953.67 | 2,923.70 | -119.75 |
| semaine_precedente | 3,213.81 | 4,887.64 | +256.75 |

- Le réglage retenu sur 2023 **diminue** la RMSE 2024 de **50.81 MW** par rapport à la V1.
- La variante 'fêtes annuelles' obtient une RMSE de 2,624.95 MW (V1 : 2,710.28 MW). Son score 2024 ne doit pas être utilisé rétrospectivement pour sélectionner les paramètres.
- Le Random Forest obtient 2,383.19 MW ; il reste devant la configuration choisie sur 2023.

## 4. D'où viennent les gains et les échecs ?

- **Saisons (configuration retenue)** : Automne : RMSE 2,077 MW (n=77 jours) ; Hiver : RMSE 3,971 MW (n=91 jours) ; Printemps : RMSE 2,500 MW (n=78 jours) ; Été : RMSE 1,214 MW (n=92 jours).
- **Semaine et week-end (configuration retenue)** : Semaine : RMSE 2,839 MW (n=246 jours) ; Week-end : RMSE 2,107 MW (n=92 jours).
- **Jours fériés (configuration retenue)** : Férié : RMSE 4,621 MW (n=8 jours) ; Non férié : RMSE 2,594 MW (n=330 jours).
- **Vacances scolaires (configuration retenue)** : Hors vacances : RMSE 2,918 MW (n=202 jours) ; Vacances : RMSE 2,220 MW (n=136 jours).

- **Effet des fêtes annuelles** : sur les 8 jours fériés évalués, la RMSE passe de 6,167 MW (V1) à 4,335 MW (variante fêtes annuelles).
- Les 330 jours non fériés sont **inchangés par cette variante** : RMSE V1 2,569.38 MW ; variante fêtes 2,569.38 MW.
- La configuration choisie sur 2023 a une RMSE de 2,593.54 MW les jours non fériés, contre 2,569.38 MW pour la V1 : le gain global ne signifie donc pas un gain sur tous les sous-groupes.
- Heure la plus difficile (configuration retenue) : 08 h, RMSE 3,122 MW.
- Énergie quotidienne : MAE 38,545 MWh ; valeur de la pointe : MAE 1,887 MW ; heure de pointe : MAE 1.65 h (distance non circulaire).

### Trois journées les plus difficiles du réglage retenu

- 2024-01-08 : RMSE 13,823 MW ; sous-estimation moyenne 12,945 MW.
- 2024-01-09 : RMSE 10,522 MW ; sous-estimation moyenne 10,486 MW.
- 2024-01-19 : RMSE 9,032 MW ; sous-estimation moyenne 8,867 MW.

## 5. Interprétation scientifique

- Une correction n'est pas nécessairement bénéfique : les variantes proportionnelles et combinées doivent être jugées d'après leurs résultats, pas d'après leur complexité.
- La réduction d'erreur sur un petit nombre de journées atypiques peut améliorer la RMSE globale sans améliorer les journées ordinaires.
- Les huit jours fériés sont peu nombreux ; les sous-groupes ne sont pas indépendants et le diagnostic est descriptif, non causal.
- La RMSE globale n'est pas une moyenne simple des RMSE des saisons ou des catégories.
- Les réglages de la V1 et la conception des variantes ont bénéficié de l'examen de résultats 2024 antérieurs. Le réglage 2023 réduit le choix direct sur 2024, mais ne rend pas cette expérience entièrement indépendante de 2024.
- Les hyperparamètres des autres modèles ML du dépôt sont pour la plupart fixés, sans recherche équivalente sur 2023 : la comparaison mesure des configurations concrètes, non une supériorité intrinsèque des familles de modèles.
- La disponibilité effective des données RTE définitives et des observations météo à J 14 h n'est pas historiquement démontrée. Les jours de changement d'heure sont masqués.
- Aucune significativité statistique n'est revendiquée et le test final 2025 n'est pas consulté.
