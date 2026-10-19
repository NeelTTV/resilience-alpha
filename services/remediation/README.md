# Reprise autonome

Automate : `services/supervisor/main.py`. Exécuteur : `services/executor/main.py`.
Playbook : `infra/ansible/quarantine.yml`. États persistés detected, recovering,
verifying, recovered et failed. Quarantaine 300 s, une action autorisée, CIDR validés,
clé distincte, aucun socket Docker et cinq vérifications métier maximum.
Procédure et limites : `docs/runbook-recovery.md`.
