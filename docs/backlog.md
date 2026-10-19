# Backlog du workshop

Le setup initialise le dépôt et le parcours métier. Les responsables et le numéro du
groupe sont à renseigner avec l'équipe, sans attribution inventée.

| Pilier | Livré dans le setup | Prochaine preuve attendue | Responsable |
| --- | --- | --- | --- |
| DEV | Auth, paiement fictif idempotent, dashboard, tests | États et chronologie incident/reprise dans le dashboard | À désigner |
| INFRA | Compose, volumes, healthchecks, profil métriques/Loki/Grafana, playbook déploiement | Collecteur de logs, restauration testée, exécuteur limité | À désigner |
| IA/DATA | Contrats détecteur/RAG, serveur Ollama optionnel | Données, modèle ML évalué, alerte vers remédiation, RAG LangChain sourcé | À désigner |
| CYBER | Secrets locaux ignorés, durcissement des conteneurs applicatifs, routes filtrées | WAF, SOC/SIEM, SOPS/Vault, attaque depuis le deuxième PC | À désigner |
| TRANSFORMATION | Trames risques, PCA/PRA et recette | Analyse liée à l'architecture, arbitrages et preuves | À désigner |

## Ordre de travail proposé

1. Valider avec le coach l'architecture, l'incident principal et les objectifs métier.
2. Exécuter le parcours métier sur le PC Hôte et collecter un jeu de mesures normal.
3. Déployer WAF, collecte Loki/SOC et SOPS/Vault ; préparer le scénario du PC Attaquant.
4. Entraîner/évaluer le détecteur avec observations normales et perturbées distinctes.
5. Relier la détection à une remédiation bornée, puis vérifier une nouvelle transaction.
6. Intégrer le RAG, la chronologie dashboard et les preuves dans le dossier.
7. Répéter le scénario complet sans correction humaine et préparer les rendus.

## Livrables à préparer

Dossier `Workshop2026-M2-G<n>` : remplacer `<n>` par le numéro réel du groupe.
Dossier PDF (ordre de grandeur 8 à 12 pages hors annexes), présentation PPTX,
clip continu de 60 secondes maximum, archive du code et déploiement sans secrets.
Les documents sources sont le sujet PDF (sections 3 à 8) et la présentation workshop
(diapositives 3 à 7), fournis par l'utilisateur. Confirmer le calendrier avec le campus.
