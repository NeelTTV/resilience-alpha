# Trame de gouvernance à compléter avec les preuves

## Périmètre et responsabilités

Groupe, membres, responsables des cinq piliers, coach, machines autorisées et réseau :
à renseigner. Actif métier principal : disponibilité et cohérence des paiements fictifs.
Inventorier les flux, identités, données, volumes et accès d'administration réels.

## Analyse de risques EBIOS RM

Décrire le cadrage et les événements redoutés, les sources de risque, les scénarios
stratégiques puis opérationnels. Relier chaque scénario aux composants réellement livrés.
Les lignes suivantes sont des pistes à évaluer, sans gravité ni vraisemblance inventée.

| Événement redouté | Surface | Mesures à valider | Preuves à joindre |
| --- | --- | --- | --- |
| Indisponibilité des paiements | Proxy/API/DB | Filtrage, détection ML et reprise bornée | Chronologie et nouvelle transaction |
| Doublons ou incohérence | API et base | Idempotence, contraintes DB, sauvegarde | Tests et restauration |
| Abus des droits de reprise | Futur exécuteur | Actions autorisées et authentification | Tests d'accès/refus et journal d'audit |
| Compromission d'identifiants | Auth/secrets | SOPS/Vault, moindre privilège, rotation | Configuration et exercice de rotation |

## PCA / PRA

Fixer RTO et RPO cibles avec justification métier, sans les confondre avec des mesures.
Décrire scénarios couverts/non couverts, déclencheurs, responsables, sauvegardes,
restauration et vérification de cohérence. La base sur volume persistant ne constitue
pas une sauvegarde. Inclure les procédures d'échec et risques résiduels après reprise.
Renseigner après recette les délais observés et les pertes de données éventuelles.

## NIS2 / DORA

Préparer une matrice entre exigences pertinentes pour l'entreprise financière fictive,
mesures du prototype, preuves et écarts. Vérifier les textes officiels à jour avant
analyse : cette trame ne formule aucune conclusion juridique ou de conformité.
Éviter de présenter le prototype comme une certification ou une conformité démontrée.

## Arbitrages à présenter

Budget matériel, séparation IA facultative, simplicité du socle, limites du compte
unique/HS256, privilèges de remédiation, coût d'une indisponibilité et travaux prioritaires
avant un usage industriel. Consigner les contributions réelles de chaque membre.
