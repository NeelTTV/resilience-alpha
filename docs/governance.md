# Gouvernance : périmètre, analyse de risques et preuves

## Périmètre et responsabilités

Groupe 3 : responsabilités dans `team.md`.
Actif métier principal : disponibilité et cohérence des paiements fictifs.
Flux et accès : `architecture.md`, `compose.yaml` et README. Les signatures sont
RS256 ; seul auth possède la clé privée. L'exécuteur Ansible est opérationnel,
authentifié par une clé dédiée et limité à une quarantaine de 300 secondes.

## Impact métier et objectifs proposés

Hypothèses pédagogiques à faire approuver, sans revenu réel ni mesure de clientèle :
30 tentatives de paiement/minute, panier moyen de 25 EUR, commission de 0,20 EUR
par paiement, 50 % d'abandon définitif lors d'une indisponibilité. Le flux interrompu
est de 750 EUR/minute ; ce volume n'est pas un chiffre d'affaires perdu. La perte de
commissions estimée est 30 x 50 % x 0,20 = 3 EUR/minute. Une intervention manuelle
de deux personnes pendant 20 minutes à 45 EUR/h ajoute 30 EUR par incident.
Une coupure de cinq minutes coûterait ainsi 45 EUR dans ce modèle, hors atteinte
à la confiance, rapprochement comptable et pénalités non chiffrées.

La cible RTO <= 30 s borne à environ 15 les tentatives affectées à cette charge ;
la perte de commissions hypothétique serait de 1,50 EUR. L'automatisation évite
l'intervention de routine, sous réserve de sa réussite. Le RPO = 0 protège les
paiements confirmés du scénario de saturation : aucune restauration n'est lancée.
Ces objectifs sont des choix du laboratoire, pas des seuils imposés par NIS2/DORA.
Pour une perte complète du poste, aucune cible n'est déclarée tenue avant exercice.

Le délai détection -> reprise mesuré est dans `output/evidence/recovery.json`.
Les sondes externes espacées d'environ 0,5 s bornent l'indisponibilité observée ;
elles ne donnent ni l'instant exact du début d'attaque ni une garantie de RTO.

## Décisions proposées à la direction fictive

| Décision | Motif et coût | Critère d'acceptation | Responsable |
| --- | --- | --- | --- |
| Accepter uniquement le démonstrateur sur réseau isolé | Un hôte existant, pas de haute disponibilité | Deux PC physiques et paiement autonome prouvés | Ethan / Maxime |
| Consacrer une demi-journée à la recette réseau | Budget de planification, non réalisé | IP attaquante distincte, TLS et ports contrôlés | Josselin |
| Avant tout pilote, financer une sauvegarde externe chiffrée et un second hôte | Coût matériel à deviser ; risque de perte totale du poste | Restauration hors hôte avec RTO/RPO mesurés | Josselin / direction |
| Réserver une journée à l'évaluation ML indépendante | Charge humaine proposée ; couverture actuelle limitée | Charges variées, faux positifs et échecs publiés | Lucas |
| Refuser une déclaration de conformité fondée sur cette seule maquette | Statut et périmètre de l'entreprise à examiner | Analyse réglementaire et gouvernance réelles | Jean-christophe |

Le coût du laboratoire suppose le matériel déjà disponible ; aucune facture ni
validation collective n'est inventée. Le coach et l'équipe doivent acter les décisions.

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
| Perte du PC Hôte | 4 | 2 | Restauration locale testée, copie externe absente | 2 (risque non réduit) |
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

### Exécution et gestion d'échec

Prévention : vérifier Docker, l'espace libre, le modèle chargé, les cibles Prometheus
et un paiement de référence avant l'exercice. Pendant la saturation, l'automate seul
isole la source puis vérifie un paiement et les précédents. Le RAG ne décide aucune
action. Si l'état devient `failed`, conserver la chronologie ; aucune intervention
corrective n'est cachée au jury. Le diagnostic humain commence après la démonstration.

Pour une corruption de données, arrêter les écritures hors démo, conserver la base
endommagée et restaurer un dump dans une base distincte. Comparer lignes et empreintes
avant tout basculement explicitement décidé par l'équipe. Ne jamais présenter le dump
local comme protection contre une perte du disque. Politique proposée pour un futur
pilote : copie externe chiffrée toutes les 15 minutes, rétention de sept jours,
vérification quotidienne et exercice mensuel. Le RPO hypothétique serait au mieux
15 minutes ; le stockage externe et ces exercices ne sont pas encore mis en place.

## Matrice NIS2/DORA du prototype

NIS2 traite notamment les risques cyber et le signalement d'incidents pour les
entités concernées. [Commission européenne](https://digital-strategy.ec.europa.eu/en/policies/nis2-directive).
DORA porte sur la résilience numérique du secteur financier, dont les risques TIC
et les essais. [EIOPA](https://www.eiopa.europa.eu/digital-operational-resilience-act-dora_en).
L'applicabilité réelle et les textes nationaux/sectoriels demandent une analyse
distincte ; aucun statut réglementé n'est attribué au labo.

| Thème | Preuve technique | Écart |
| --- | --- | --- |
| Pilotage des risques (NIS2 art. 20-21 ; DORA art. 5-6) | Rôles, scénarios et cotations proposées | Validation par l'équipe/direction à obtenir |
| Incidents (NIS2 art. 23 ; DORA art. 17-19) | Score ML, chronologie, logs WAF/API/Loki | Qualification et notification réglementaires non mises en œuvre |
| Continuité et essais (NIS2 art. 21 ; DORA art. 11-12 et 24-25) | Paiement après reprise et restauration isolée | Pas de multi-site ni campagne représentative |
| Accès et secrets (NIS2 art. 21 ; DORA art. 9) | RS256, SOPS/age, privilèges bornés | MFA, révocation et rotation complète non démontrés |
| Dépendances et tiers (NIS2 art. 21 ; DORA art. 28-30) | Verrous et digest du WAF | SBOM, contrats et audit des images à compléter |

Références primaires consultées le 19 octobre 2026 :
[directive NIS2](https://eur-lex.europa.eu/eli/dir/2022/2555/oj) et
[règlement DORA](https://eur-lex.europa.eu/eli/reg/2022/2554/oj).
Les rapprochements désignent des thèmes à étudier. Le statut de la société fictive
ne permet pas de conclure à l'applicabilité simultanée des deux textes : DORA comporte
des dispositions sectorielles spécifiques à examiner avant de déduire les obligations.

Cette matrice n'est ni une certification ni une déclaration de conformité.
