# Audit de disponibilité des variables

Pour chaque variable, préciser la règle exacte de disponibilité **à 14 h le jour J** et vérifier également ses délais de publication éventuels.

| Variable | Source | Heure/date réellement disponible | Observée ou prévue | Usage envisagé | Risque de fuite / vérification |
| --- | --- | --- | --- | --- | --- |
| Consommation passée | RTE éCO2mix | À vérifier selon horodatage et publication | Observée | Retards | Ne jamais inclure des heures futures ou publiées trop tard |
| Météo passée | SYNOP | À vérifier selon station, observation et publication | Observée | Variables météo passées | Vérifier le délai de publication |
| Météo de J+1 | Source à définir | À vérifier | Prévue, si disponible | Scénario opérationnel éventuel | Ne pas substituer les observations SYNOP futures |
| Météo observée de J+1 | SYNOP | Après l'origine | Observée | Comparaison « météo parfaite » uniquement | Fuite si utilisée pour le modèle opérationnel |
| Calendrier de J+1 | Calcul / source à préciser | À vérifier | Connue à l'avance | Jours et heures | Vérifier les événements ajoutés |
