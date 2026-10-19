# Journal des contributions

Le socle et les évolutions de cette session ont été produits avec l'aide de Codex.
Répartition attribuée à la demande de l'équipe le 19 octobre 2026. Chaque membre
est référent des livrables ci-dessous et doit pouvoir les expliquer. Cette attribution
ne constitue pas une preuve d'auteur individuel des fichiers ni de recette personnelle.

| Membre | Travaux attribués et à défendre | Livrables et preuves du projet | Validation personnelle |
| --- | --- | --- | --- |
| Ethan DIVET - DEV | API de paiement, idempotence, authentification RS256, interface et intégration métier | `services/payment/`, `services/auth/`, `apps/dashboard/`, `tests/`, preuves recovery/browser | À confirmer par Ethan |
| Josselin LENAOUR - INFRA | Compose, Ansible, observabilité, déploiement reproductible et sauvegarde/restauration | `compose.yaml`, `infra/`, `scripts/repro_check.py`, preuves reproducibility/backup | À confirmer par Josselin |
| Lucas CHEVALIER - IA/DATA | Collecte des données, calibration, OneClassSVM, évaluation et RAG local | `services/supervisor/`, `services/assistant/`, scripts calibrate/confirm_model, model-card et preuves ML | À confirmer par Lucas |
| Maxime DUSSORT - CYBER | Scénario d'attaque borné, WAF/SOC, protection des secrets et contrôle des privilèges | `security/`, `services/executor/`, `scripts/security_check.py`, preuve security | À confirmer par Maxime |
| Jean-christophe MALINUR - TRANSFORMATION | EBIOS RM, coûts métier, PCA/PRA, matrice NIS2/DORA, recommandations et conducteur | `docs/governance.md`, `docs/soutenance.md`, dossier PDF et présentation | À confirmer par Jean-christophe |

## Trace commune

L'équipe a fourni sa composition et délégué l'affectation des rôles et travaux.
L'implémentation, les scripts et les supports ont été préparés avec l'aide de Codex.
Les preuves automatisées décrivent les essais du laboratoire ; elles n'identifient
pas une personne ayant réalisé un atelier ou manipulé un second ordinateur.
Après la répétition, chaque membre ajoute ici la date, la vérification effectuée,
son résultat et le chemin de preuve. La validation collective et celle du coach
restent à consigner dans `recette-terrain.md`.
