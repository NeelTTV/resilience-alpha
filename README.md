# Resilience Alpha

Socle du démonstrateur de cyber-résilience pour le workshop EPSI M2 2026.
Données et paiements entièrement fictifs. Le socle fournit un parcours métier testable ;
les cinq piliers du sujet restent suivis dans [le backlog](docs/backlog.md).

## Démarrage sur Windows

Prérequis : Docker Desktop en mode conteneurs Linux avec WSL2, Python 3.10+ accessible
avec `py`, Node.js 20.17+ et npm. Node 22 est utilisé dans Docker et la CI.
Prévoir au moins 16 Go de RAM et 50 Go libres pour le laboratoire complet.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1
docker compose up --build -d --wait
```

Ouvrir **http://localhost:8080**. Compte fictif : `operator`.
Lire son mot de passe local avec `Get-Content .secrets/demo_password`.
Le setup ne réécrit pas les secrets existants et ne publie aucun secret dans Git.
Ne pas utiliser les identifiants d'un compte personnel ou de données bancaires réelles.

```powershell
# Vérifier le parcours complet à travers le proxy
./.venv/Scripts/python.exe scripts/smoke.py
# Lint, tests, typage/build frontend et validation de Compose
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1
# État, logs et arrêt (sans supprimer les données)
docker compose ps
docker compose logs --tail=100 api auth
docker compose down
```

Le smoke test crée une transaction fictive persistante. Une nouvelle exécution utilise une
nouvelle référence. Le test unitaire utilise SQLite temporaire ; le smoke Docker utilise PostgreSQL.

## Services

| Composant | Technologie | Accès |
| --- | --- | --- |
| Dashboard et proxy | React, TypeScript, Vite, Tailwind, Nginx | localhost:8080 |
| API de paiement | Python / FastAPI / SQLAlchemy | Interne, routes métier via `/api/` |
| Authentification | FastAPI, JWT de 15 minutes | Interne, `/auth/token` via le proxy |
| Base de données | PostgreSQL 17, volume persistant | Interne uniquement |
| Métriques | Prometheus | localhost:9090, profil `observability` |
| Supervision | Grafana | localhost:3000, profil `observability` |
| Journaux | Loki | Interne, profil `observability` |
| Modèle local | Ollama | localhost:11434, profil `ai` |

```powershell
docker compose --profile observability up -d
docker compose --profile ai up -d
# Facultatif : téléchargement explicite d'un modèle de 4B paramètres
docker compose exec ollama ollama pull qwen3:4b
```

Grafana : utilisateur `admin`, mot de passe dans `.secrets/grafana_password`.
Les sources Prometheus/Loki et un dashboard métriques sont provisionnés.
La collecte de journaux vers Loki, les règles SOC et le service LangChain restent à intégrer.
Le profil IA ne télécharge aucun modèle automatiquement.

## Contrats d'API

- `POST /auth/token` : `{ "username": "operator", "password": "..." }`.
- `GET /api/health` : disponibilité de l'API et connexion à la base.
- `POST /api/transactions` : `{ "amount_cents": 1250, "currency": "EUR" }` avec
  `Authorization: Bearer <token>` et `Idempotency-Key: <référence unique>`.
- `GET /api/transactions` : 100 dernières transactions du compte authentifié.

Montants en centimes entiers positifs, maximum 1 000 000 EUR par opération fictive.
Une clé rejouée avec les mêmes données retourne la même transaction ; des données
différentes avec la même clé donnent HTTP 409. En cas de réponse réseau ambiguë,
réutiliser la même clé pour éviter un doublon. Les paiements sont des enregistrements
simulés, sans banque, débit réel, solde ni prestataire de paiement.

Les schémas OpenAPI et `/metrics` sont disponibles à l'intérieur des conteneurs :
ils ne sont pas publiés par le proxy. Voir aussi [l'architecture](docs/architecture.md).

## Développement local sans Docker

Après `scripts/setup.ps1`, ouvrir trois terminaux PowerShell depuis la racine :

```powershell
# Terminal 1 : auth
$env:JWT_SECRET_FILE="$PWD/.secrets/jwt_secret"
$env:DEMO_PASSWORD_HASH_FILE="$PWD/.secrets/demo_password_hash"
./.venv/Scripts/python.exe -m uvicorn services.auth.main:app --port 8001 --no-access-log
```

```powershell
# Terminal 2 : API, base SQLite locale réservée au développement
$env:JWT_SECRET_FILE="$PWD/.secrets/jwt_secret"
$env:DATABASE_URL='sqlite:///./development.db'
./.venv/Scripts/python.exe -m uvicorn services.payment.main:app --port 8000 --no-access-log
```

```powershell
# Terminal 3 : frontal avec proxy Vite, http://localhost:5173
cd apps/dashboard
npm run dev
```

Les dépendances sont verrouillées dans `requirements-dev.lock`, `services/requirements.lock`
et `apps/dashboard/package-lock.json`. Les fichiers `.in` expriment les dépendances directes.
Mettre à jour les verrous et repasser les contrôles lors d'une évolution.

## Infrastructure et périmètre de démonstration

Playbook de déploiement depuis Linux/WSL2 avec intégration Docker et Ansible installé :

```bash
ansible-galaxy collection install -r infra/ansible/requirements.yml
ansible-playbook -i infra/ansible/inventory.ini infra/ansible/deploy.yml
```

Le bind par défaut est limité à la machine locale. Pour le hotspot Windows du groupe,
remplacer `BIND_ADDRESS` dans `.env` par l'IP du PC Hôte (ex. `192.168.137.1`), puis
recréer le dashboard. Valider le pare-feu et le TLS avant la démo : l'interface utilise
`crypto.randomUUID`, qui nécessite un contexte sécurisé hors localhost.
Le PC Attaquant doit être une machine distincte sur le seul réseau autorisé du groupe.
Le setup ne change pas les règles réseau Windows et ne lance aucune attaque.

## Ce qui reste à construire

Ce dépôt initialisé ne constitue pas encore la démonstration de reprise autonome :
modèle ML entraîné, remédiation pilotée par ses alertes, RAG LangChain, WAF, collecte
Loki/SOC et gestion des secrets Vault/SOPS restent à intégrer et valider.
Les redémarrages `unless-stopped` sont un confort de développement, pas une preuve AIOps.
Les images d'infrastructure sont versionnées par tags ; leur audit et leur verrouillage
par digest font partie du durcissement avant rendu.

- [Architecture et limites](docs/architecture.md)
- [Backlog des cinq piliers](docs/backlog.md)
- [Recette de reprise](docs/acceptance.md)
- [Trame gouvernance](docs/governance.md)
- [Sécurité du laboratoire](security/README.md)

La CI vérifie le backend, le build du dashboard et le smoke test Docker sur Linux.
Elle est définie dans le dépôt ; son exécution distante dépend du push et de GitHub Actions.
