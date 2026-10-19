# Conducteur de soutenance locale - 5 minutes puis 5 minutes de questions

Les durées sont un plan de répétition, pas une répétition déjà réalisée.

| Temps | Intervenant | Message et action |
| --- | --- | --- |
| 0:00-0:25 | Ethan | Paiements fictifs : la preuve de reprise est un nouveau paiement, pas un voyant vert. Montrer un paiement initial. |
| 0:25-0:55 | Josselin | WAF -> interface/API/auth -> PostgreSQL. Réseaux séparés ; Ansible sans socket Docker dans l'application. |
| 0:55-1:25 | Lucas | Trafic réel, fenêtres 3 s, OneClassSVM ; deux anomalies et autorisation de source. Petit jeu d'essai ; RAG indépendant sans outil d'action. |
| 1:25-2:25 | Maxime et écran | Clip continu <= 60 s s'il existe ; sinon ne pas le prétendre tourné. Identifier les deux PC et le réseau autorisé. |
| 2:25-3:45 | Maxime / Ethan | Démonstration sur les deux PC : transaction avant, attaque bornée, chronologie, quarantaine et paiement après. Aucune correction manuelle. |
| 3:45-4:35 | Jean-christophe | RTO cible 30 s / RPO 0 limités au scénario ; hypothèses de coût, EBIOS et écarts NIS2/DORA. Risque principal restant : hôte unique. |
| 4:35-5:00 | Ethan | Indiquer la preuve obtenue, les limites et la décision proposée : recette pédagogique acceptée ; pilote soumis à sauvegarde externe et nouveaux essais. |

En cas d'échec live : montrer `failed`, expliquer la limite et citer la recette
enregistrée comme un essai antérieur. Aucun redémarrage correctif dissimulé.

## Questions à préparer ensemble

- Pourquoi le quota 20 req/s n'est-il pas la détection ? C'est la ressource saturée ;
  le modèle apprend une frontière sur des fenêtres de trafic normal.
- Pourquoi RS256 ? Auth garde la clé privée ; les consommateurs vérifient avec la clé publique.
- Comment éviter un double débit fictif ? Clé d'idempotence et contrainte d'unicité en DB.
- Que peut faire Ansible ? Une quarantaine IP validée de 300 s ; pas de shell fourni par le client.
- Pourquoi 3,96 s ne suffit pas à prouver le RTO ? C'est détection -> preuve métier ;
  le début d'indisponibilité précède la détection.
- Les 12/12 fenêtres d'attaque prouvent-elles une efficacité générale ? Non, elles
  sont corrélées et incluent des requêtes bloquées ; publier également faux positifs et limites.
- Si la machine est perdue ? Le dump local est perdu aussi ; le PRA hors hôte reste à exercer.
- Le RAG peut-il modifier le SI ? Non ; il retrouve et cite les procédures locales.
- Êtes-vous conformes NIS2/DORA ? Cette maquette documente des mesures et des écarts ;
  l'applicabilité et une conformité de l'entreprise réelle ne sont pas démontrées.
- Qui a fait quoi ? Chaque membre présente uniquement ses contributions réelles et ses preuves.

## Si sélection nationale

Préparer séparément 1 minute de pitch avec introductions individuelles en anglais,
1 minute de Clip Chrono puis 3 minutes de démonstration. Ne pas confondre les deux formats.
