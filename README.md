# Resilience Alpha

Démonstrateur de cyber-résilience EPSI M2 2026, **Équipe DIVET**.
Paiements et données entièrement fictifs, sans banque ni prestataire externe.

La chaîne implémentée relie WAF, API de paiement, collecte de journaux, détection ML,
quarantaine Ansible et vérification d'une nouvelle transaction. Le RAG local assiste
l'opérateur avec des procédures citées. [Rôles de l'équipe](docs/team.md).

## Démarrage Windows

Prérequis : Docker Desktop en mode Linux/WSL2, Python 3.10+ accessible avec `py`,
Node.js 20.17+ et npm. Node 22 est utilisé dans Docker et la CI.
Prévoir au moins 16 Go de RAM et 50 Go libres pour le laboratoire complet.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1
docker compose --profile ai up --build -d --wait
docker compose exec ollama ollama pull qwen3:0.6b
```

Dashboard : **http://localhost:8080** ou **https://localhost:8443**.
Compte `operator`, mot de passe local : `Get-Content .secrets/demo_password`.
Le certificat TLS de laboratoire est dans `.secrets/tls_cert`. Établir sa confiance
sur les postes autorisés avant d'utiliser HTTPS ; ne pas désactiver la validation
des certificats sur les postes ou réseaux tiers.

```powershell
./.venv/Scripts/python.exe scripts/smoke.py
# Calibrer uniquement en situation normale, sans attaque en cours
./.venv/Scripts/python.exe scripts/calibrate.py --seconds 75
# Recette autonome avec client offensif dans un conteneur distinct
./.venv/Scripts/python.exe scripts/demo.py
# Sauvegarde et restauration dans une nouvelle base d'essai, sans écraser le métier
./.venv/Scripts/python.exe scripts/backup_check.py
./.venv/Scripts/python.exe scripts/security_check.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1
```

Recette d'installation isolée, sans réutiliser les secrets ou volumes existants :

```powershell
./.venv/Scripts/python.exe scripts/repro_check.py
./.venv/Scripts/python.exe scripts/confirm_model.py --seconds 180
```

La première commande déploie par Ansible dans un projet Docker temporaire, vérifie
un second passage sans changement et un paiement, puis supprime ce projet isolé.
Son contrôleur temporaire accède au socket Docker pour le déploiement ; aucun
service applicatif ne reçoit cet accès. Cela ne valide pas une autre machine physique.

La recette écrit `output/evidence/recovery.json`, avec chronologie, score/version ML,
statuts HTTP, transaction de preuve et contrôle de la transaction créée avant l'attaque.
La reprise doit intervenir alors que le flux continue. Cette recette en conteneurs
**ne remplace pas l'essai depuis le deuxième PC physique** ni le Clip Chrono.

## Architecture

| Service | Rôle | Accès hôte |
| --- | --- | --- |
| waf | ModSecurity/OWASP CRS, entrée HTTP/TLS | 127.0.0.1:8080 et 8443 |
| dashboard | React, TypeScript, Tailwind, proxy Nginx | Via le WAF |
| auth | JWT RS256, comptes fictifs operator/recovery-check | Interne |
| api | Paiements idempotents, PostgreSQL, admission/quarantaine | Interne |
| supervisor | Collecte, SOC, modèle ML et automate de reprise | Lecture authentifiée via `/control/status` |
| executor | Action Ansible unique, réseau control interne | Aucun port hôte |
| assistant | RAG documentaire LangChain/TF-IDF/ChatOllama | Authentifié via `/assistant/ask` |
| db | PostgreSQL 17 et volume persistant | Aucun port hôte |
| prometheus | Débit, erreurs, latence et santé | 127.0.0.1:9090 |
| grafana | Dashboard métriques et source Loki | 127.0.0.1:3000 |
| loki | Journaux WAF et API collectés | Interne |
| ollama | Modèle local optionnel, profil ai | 127.0.0.1:11434 |

Grafana : `admin`, mot de passe dans `.secrets/grafana_password`.
Sans profil `ai`, le RAG signale explicitement son mode de recherche seule si le
modèle n'est pas joignable. Aucun modèle supérieur à 8B n'est accepté par l'assistant.

Le quota partagé de l'API est volontairement petit (20 requêtes/s) pour un scénario
borné de saturation. Ce quota fixe est une limite de ressource, **distincte de la
détection ML**. Il ne représente pas une vulnérabilité découverte dans un système tiers.

## Détection et remédiation

La calibration collecte un trafic HTTP normal réel, constitue des fenêtres par source
de 3 s et sépare chronologiquement apprentissage/validation. Le modèle est un
StandardScaler + OneClassSVM RBF. Deux scores anormaux consécutifs sont nécessaires.
La frontière est calibrée sur le trafic normal ; ses métriques ne constituent pas
une évaluation indépendante de production.
Le centrage conserve l'échelle physique des variables : la faible variance d'une
latence normale n'est pas amplifiée. `scripts/confirm_model.py` vérifie un trafic
authentifié neuf après l'exercice, sans réentraîner le modèle.

Pour autoriser une quarantaine, la source doit dominer le trafic et cumuler au moins
12 observations par fenêtre. Elle ne doit être ni une source protégée de calibration
ni un composant de contrôle. Ce choix
limite les dommages collatéraux mais ne traite pas une source protégée compromise.
Ne pas calibrer avec le PC Attaquant. Le modèle et les données sont dans le volume
`supervisor_data` ; l'interface indique clairement l'absence de modèle.

L'exécuteur reçoit une clé distincte, valide l'IP et les CIDR du labo, puis publie
atomiquement une politique de quarantaine de 300 s avec Ansible. Il n'accepte aucune
commande arbitraire et ne monte aucun socket Docker. Le moteur vérifie ensuite,
à travers le WAF, une nouvelle transaction et jusqu'à 20 anciennes opérations du
compte de contrôle. Cinq essais maximum, puis `failed` si la preuve n'est pas obtenue.

## Secrets SOPS/age

```powershell
./.venv/Scripts/python.exe scripts/manage_secrets.py bootstrap
./.venv/Scripts/python.exe scripts/manage_secrets.py encrypt
```

Les versions des outils Windows sont précisées dans le script et leurs assets
vérifiés par SHA256 avant exécution. Le bundle `security/secrets.enc.json` est chiffré.
La clé privée `.secrets/lab.agekey` reste locale et hors archive. Ajouter les destinataires
age autorisés avant partage. Le mode `decrypt` refuse d'écraser des secrets locaux
différents. Un nouvel environnement peut aussi générer ses propres secrets via le setup.

Les secrets applicatifs sont montés seulement au besoin. Le dossier Unix est 0700,
les fichiers applicatifs 0640, et le GID du propriétaire est ajouté aux services via
`SECRET_GID` dans `.env`. Vérifier aussi les ACL NTFS sur Windows. Ne pas publier `.env`,
`.secrets`, données ou dumps. Aucun secret n'est affiché par les scripts d'installation.

## API métier

- `POST /auth/token` : username/password fictifs, JWT de 15 min.
- `GET /api/health` : API et connexion DB, sans preuve de disponibilité métier.
- `POST /api/transactions` : `{ "amount_cents": 1250, "currency": "EUR" }` avec
  `Authorization: Bearer <token>` et `Idempotency-Key: <référence unique>`.
- `GET /api/transactions` : 100 dernières transactions du compte.
- `GET /control/status` : modèle, état du collecteur, SOC et incidents.
- `POST /assistant/ask` : `{ "question": "Comment vérifier la reprise ?" }`.

Les montants sont des centimes entiers positifs, plafonnés à 1 000 000 EUR fictifs.
Rejouer une clé avec les mêmes données retourne la même transaction ; un changement
de données retourne 409. Réutiliser la clé lors d'une réponse réseau ambiguë.
Les schémas OpenAPI et `/metrics` restent internes.

## Réseau et déploiement

Le bind est local par défaut. Pour le hotspot du groupe, modifier `BIND_ADDRESS` dans
`.env` avec l'IP hôte autorisée, contrôler le pare-feu et vérifier `LAB_CIDRS`.
Le certificat inclut localhost, 127.0.0.1 et 192.168.137.1. Pour une autre adresse,
générer un certificat adapté. L'interface utilise un contexte sécurisé hors localhost.
Les ports des données, secrets et commandes restent internes.

Depuis Linux/WSL2 avec Ansible et l'intégration Docker :

```bash
ansible-galaxy collection install -r infra/ansible/requirements.yml
ansible-playbook -i infra/ansible/inventory.ini infra/ansible/deploy.yml
```

```powershell
docker compose ps
docker compose logs --tail=100 supervisor executor
docker compose down
```

L'arrêt conserve les volumes. Le schéma utilise `create_all` : ajouter des migrations
avant de faire évoluer le modèle de données. Les dépendances sont verrouillées dans
les fichiers `.lock` et `apps/dashboard/package-lock.json`.

## Équipe, preuves et livrables

- [Équipe et rôles](docs/team.md)
- [Architecture et limites](docs/architecture.md)
- [Procédure de reprise](docs/runbook-recovery.md)
- [Risques EBIOS, PCA/PRA et matrice NIS2/DORA](docs/governance.md)
- [Conducteur démo et Clip Chrono](docs/demo-runbook.md)
- [Travaux attribués par membre](docs/contributions.md)
- [Conducteur de soutenance et questions](docs/soutenance.md)
- [Recette sur deux PC et tournage](docs/recette-terrain.md)

Le dossier PDF, la présentation et l'archive sont préparés dans
`output/Workshop2026-M2-Equipe-DIVET/`. Aucun numéro de groupe n'est inventé.
La vidéo continue doit être tournée sur les deux PC physiques. Les scripts de
génération PDF/PPTX sont optionnels ; ils utilisent ReportLab et le runtime Artifact Tool.

La CI définie teste le backend, le frontend, la calibration, la reprise et la restauration
en conteneurs Linux. Son exécution distante n'est pas déduite des contrôles locaux.
Restent à valider pour la remise : matériel/réseau réel, maîtrise personnelle des
travaux attribués, validation coach et rendu vidéo. Une campagne ML sur charges variées
et un PRA perte d'hôte restent des renforcements du prototype. Il ne revendique aucune
certification ni conformité réglementaire démontrée.

Après génération des supports et du ZIP, `python scripts/delivery_check.py` vérifie
les fichiers, l'intégrité et la concordance des sources, puis écrit `ETAT-DU-RENDU.txt`.
Le mode `--strict` échoue tant que le rendu n'est pas complet. Après les vérifications
réelles, renseigner `docs/acceptance.json` avec une référence de preuve pour chaque
validation humaine ; ne pas cocher les validations avant leur exécution.
