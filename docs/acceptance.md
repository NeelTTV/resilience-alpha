# Recette et preuves

## Socle

`scripts/check.ps1` vérifie lint, tests métier/auth, build/typage et syntaxe Compose.
`scripts/smoke.py` vérifie au travers du proxy l'API, l'authentification, la persistance
et l'idempotence d'une transaction sur la stack démarrée. Il ne teste ni attaque ni ML.

## Reprise autonome à démontrer

1. Créer une transaction avant incident, conserver son ID et son horodatage.
2. Déclencher le scénario validé depuis le PC Attaquant distinct.
3. Conserver événements et signaux bruts, score ML, version du modèle et heure de détection.
4. Observer la décision et les actions de remédiation sans correction humaine.
5. Exécuter automatiquement une nouvelle transaction avec une nouvelle clé d'idempotence.
6. Relire les transactions précédentes ; rechercher incohérences et doublons.
7. Enregistrer délais de détection et de reprise, limites, échecs et faux positifs.

Critères : nouvelle transaction réussie, anciennes données cohérentes, aucune action
corrective humaine, traçabilité complète. Un simple healthcheck ou redémarrage ne suffit pas.
Définir avant essai les RTO/RPO cibles ; ne pas les présenter comme mesurés avant recette.

## Contrôles complémentaires

- Secrets absents de Git et de l'archive ; clé SOPS/Vault hors livraison.
- Base, métriques, secrets et administration non accessibles depuis le PC Attaquant.
- Requêtes métier légitimes acceptées par le WAF ; scénario offensif observable.
- Rejeu et doublons d'incident sans multiplication des actions de reprise.
- Modèle ML évalué sur un jeu séparé ; indisponibilité du détecteur visible.
- Échec de reprise explicite avec nombre de tentatives limité.
- RAG capable de citer une procédure et de signaler une absence de source.
