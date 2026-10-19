# Architecture initiale

## Chemin métier livré

Navigateur -> proxy Nginx/dashboard -> auth ou API -> PostgreSQL.
Le proxy publie uniquement health, token et transactions. Les services et la base
n'ont pas de ports hôte. Les données métier persistent dans le volume PostgreSQL.
Chaque transaction a une référence UUID, un propriétaire et une clé d'idempotence unique.
Les requêtes SQL passent par SQLAlchemy ; aucun SQL provenant des entrées utilisateur.

Prometheus interroge `/metrics` sur auth/API toutes les cinq secondes. Grafana présente
disponibilité, débit et latence. Loki est configuré comme source, sans collecteur pour
l'instant. Les services émettent des messages JSON sans corps de requête ni jeton.
Les logs d'accès Uvicorn sont désactivés ; les métriques distinguent routes, codes et durées.

## Chaîne de résilience à raccorder

Signaux Prometheus/Loki -> détecteur ML -> événement d'incident authentifié ->
automate de remédiation -> exécuteur Ansible limité -> vérification métier -> état final.
Les contrats prévus sont dans `services/detector` et `services/remediation`.
Ollama + futur RAG LangChain consultent les procédures, sans droit d'action sur les conteneurs.

## Décisions et limites

- Python commun aux API et à la future détection pour limiter les interfaces en quatre jours.
- React/TypeScript/Tailwind pour le dashboard conformément au sujet.
- Deux services auth/API distincts, une base métier. Pas de système de paiement existant.
- Compte opérateur unique de laboratoire. Aucun registre d'utilisateurs, révocation ou RBAC.
- HS256 partagé auth/API à remplacer par clés asymétriques si isolation renforcée.
- `create_all` initialise le schéma ; ajouter Alembic avant toute évolution du modèle livré.
- Volumes locaux : pas de haute disponibilité, réplication, sauvegarde ou PRA démontré.
- Réseau Compose partagé : absence de ports hôte ne remplace pas une segmentation complète.
- Pas de socket Docker exposé aux applications et pas d'exécuteur privilégié dans ce setup.
- HTTP sur localhost pour développer ; TLS, WAF et contrôle de débit requis avant exposition LAN.
- Secrets locaux ignorés, montés par fichiers ; Vault/SOPS reste un chantier explicite.

## Références techniques

- [FastAPI dans Docker](https://fastapi.tiangolo.com/deployment/docker/)
- [Vite 6 : installation](https://v6.vite.dev/guide/)
- [Secrets Docker Compose](https://docs.docker.com/compose/how-tos/use-secrets/)

Les documents fournis servent de cahier des charges ; ils n'autorisent aucune action
sur le campus, un service tiers ou la publication des livrables.
