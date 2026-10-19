# État du projet

| Pilier | Implémenté | Validation terrain restante |
| --- | --- | --- |
| DEV | Paiement, auth RS256, dashboard et chronologie | Parcours sur les postes du jury |
| INFRA | Compose, Ansible avec recette neuve et second passage inchangé, observabilité, restauration isolée | Hotspot et poste physique externe |
| IA/DATA | Modèle réel, split chronologique, confirmation normale prolongée sans réentraînement, RAG sourcé | Charges variées et dérive : renforcements au-delà de la recette actuelle |
| CYBER | WAF, SOC, flux offensif borné, SOPS/age, quarantaine | Second PC physique, pare-feu et confiance TLS |
| TRANSFORMATION | EBIOS, coûts hypothétiques, PCA/PRA, matrice NIS2/DORA, travaux attribués, supports et conducteur | Validation par équipe/coachs, maîtrise individuelle et vidéo |

Les preuves mesurées sont dans `output/evidence/`. Le nom provisoire des livrables
est `Workshop2026-M2-Equipe-DIVET`. Aucun numéro de groupe n'a été inventé.
La vidéo continue doit être réalisée selon `demo-runbook.md` sur deux PC physiques.
Une présence de code ne constitue pas une preuve de validation matérielle.

Les opérations accessibles ici sont préparées et vérifiées. `recette-terrain.md`
regroupe les manipulations physiques et `soutenance.md` la répétition. Le journal
des travaux attribués est renseigné pour les cinq membres, avec validation personnelle
explicitement en attente. `scripts/delivery_check.py` distingue contrôles automatiques
et validations humaines ; `docs/acceptance.json` est à renseigner après exécution.

Renforcements avant usage industriel : PRA perte d'hôte avec copie externe, campagne
ML diversifiée, comptes individuels/MFA, rotation et audit des dépendances. Ces écarts
ne sont pas présentés comme de nouveaux livrables imposés par le workshop.
