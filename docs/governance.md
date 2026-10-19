# Gouvernance : périmètre, analyse de risques et preuves

## Périmètre et responsabilités

Équipe DIVET : responsabilités dans `team.md`. Numéro de groupe non attribué.
Actif métier principal : disponibilité et cohérence des paiements fictifs.
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

## Analyse EBIOS RM proposée pour l'architecture livrée

Les cinq ateliers structurent le cadrage, les sources, les scénarios et le traitement.
Référence : [ANSSI](https://cyber.gouv.fr/securisation/analyse-des-risques/methode-ebios-rm/).
L'analyse ci-dessous est une proposition à valider par l'équipe et le coach.
Aucun atelier collectif n'est présenté comme déjà réalisé.

### 1. Cadrage et socle

Valeurs : disponibilité du paiement, cohérence de l'historique, preuve de reprise.
Biens supports : PC Hôte, hotspot, WAF, frontend, auth, API, PostgreSQL, superviseur,
exécuteur, procédures et secrets. Hors périmètre : banques réelles et réseaux tiers.
Événements redoutés : paiement impossible, doublon/altération, abus de remédiation,
perte de preuves. Socle livré : RS256, SOPS/age, WAF, conteneurs non privilégiés,
journaux et exécuteur isolé sans socket Docker.

### 2. Sources et objectifs

Client malveillant sur le hotspot : empêcher les paiements. Compte opérateur compromis :
créer/lire des opérations fictives ou perturber le service. Composant interne compromis :
abuser des droits de quarantaine. Fournisseur de dépendances compromis : introduire du
code malveillant. Les accès réseau locaux et la chaîne logicielle restent des dépendances.

### 3. Scénario stratégique

Client du hotspot -> point d'entrée WAF -> consommation du quota partagé de l'API ->
refus des paiements légitimes. La chaîne ML/Ansible doit isoler la source et rétablir
le métier alors que le flux offensif continue. La même adresse NAT peut représenter
plusieurs clients, ce qui impose d'évaluer le dommage collatéral d'une quarantaine.

### 4. Scénarios opérationnels et cotations proposées

Échelle pédagogique G/V de 1 à 4. G = impact métier, V = facilité/reproductibilité
dans ce laboratoire. Ces cotations sont des hypothèses, pas des statistiques réelles.

| Risque | G | V initiale | Traitement livré | V résiduelle proposée |
| --- | --- | --- | --- | --- |
| Saturation d'une source | 3 | 4 | Modèle de nouveauté, quarantaine 300 s, preuve métier | 2 |
| Doublon de paiement | 3 | 3 | Idempotence et contrainte unique | 1 |
| Abus des droits de reprise | 4 | 3 | Clé dédiée, CIDR/action bornés, réseau control interne | 2 |
| Perte du PC Hôte | 4 | 2 | Dump et restauration dans une base neuve | 2 |
| Compromission du compte | 3 | 3 | Mot de passe aléatoire et JWT RS256 de 15 min | 2 |

### 5. Traitement et risques résiduels

Priorité 1 : recette sur deux PC physiques. Priorité 2 : confiance TLS et contrôle
du pare-feu sur le réseau du groupe. Priorité 3 : sauvegarde hors machine, comptes
individuels/MFA, rotation, SBOM et audit des images. Jean-christophe tient le registre
des écarts ; les responsables techniques apportent les preuves. Réexaminer les risques
après tout changement du modèle, du réseau ou des privilèges.

## PCA/PRA concret

Objectifs proposés : RTO <= 30 s depuis l'apparition de la saturation ; RPO = 0 pour
les paiements déjà confirmés dans ce scénario, qui ne restaure ni n'efface la base.
Ce RPO ne couvre pas la perte du PC Hôte. Le délai détecté -> recovered de la
chronologie est distinct du RTO complet depuis l'indisponibilité.

| Situation | Procédure | Responsable | Sortie attendue |
| --- | --- | --- | --- |
| Saturation | Quarantaine automatique et 5 vérifications max | Automate | Nouvelle transaction et données préservées |
| Détecteur indisponible | Healthcheck en échec, aucune reprise inventée | Lucas | Boucle fraîche, modèle chargé |
| Reprise échouée | Conserver failed et preuves, corriger hors démo | Josselin/Ethan | Nouvelle recette distincte |
| Données perdues | Restaurer un dump dans une nouvelle base | Josselin | Empreintes et comptages identiques |
| Hôte perdu | Redéployer, déchiffrer secrets, restaurer copie externe | Équipe | Essai physique encore à réaliser |

`scripts/backup_check.py` crée un dump, restaure dans `restorecheck_<uuid>`, compare
les lignes puis supprime uniquement cette base d'essai. Il n'écrase pas la base métier.
Une copie locale n'est pas une sauvegarde contre la perte du poste ; définir une
copie externe et sa fréquence avant tout usage réel.

## Matrice NIS2/DORA du prototype

NIS2 traite notamment les risques cyber et le signalement d'incidents pour les
entités concernées. [Commission européenne](https://digital-strategy.ec.europa.eu/en/policies/nis2-directive).
DORA porte sur la résilience numérique du secteur financier, dont les risques TIC
et les essais. [EIOPA](https://www.eiopa.europa.eu/digital-operational-resilience-act-dora_en).
L'applicabilité réelle et les textes nationaux/sectoriels demandent une analyse
distincte ; aucun statut réglementé n'est attribué au labo.

| Thème | Preuve technique | Écart |
| --- | --- | --- |
| Pilotage des risques | Rôles, scénarios et cotations proposées | Validation par l'équipe/direction à obtenir |
| Traçabilité des incidents | Score ML, chronologie, logs WAF/API/Loki | Qualification et notification réglementaires non mises en œuvre |
| Continuité et essais | Paiement après reprise et restauration isolée | Pas de multi-site ni campagne représentative |
| Accès et secrets | RS256, SOPS/age, privilèges bornés | MFA, révocation et rotation complète non démontrés |
| Dépendances et tiers | Verrous et digest du WAF | SBOM, contrats et audit des images à compléter |

Cette matrice n'est ni une certification ni une déclaration de conformité.
