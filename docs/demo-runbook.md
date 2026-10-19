# Démonstration et Clip Chrono

## Préparation hors capture

Sur le PC Hôte, démarrer Docker, `docker compose --profile ai up --build -d --wait`,
vérifier `scripts/smoke.py` puis calibrer avec `scripts/calibrate.py --seconds 75`.
Le modèle est appris depuis les observations réelles et conservé dans le volume du
superviseur. Ne jamais calibrer pendant une attaque. Attendre la fin d'une éventuelle
quarantaine précédente (300 secondes) ou employer une nouvelle source du labo.

Configurer le hotspot Windows et l'adresse hôte dans `.env`, valider les seuls accès
autorisés, puis ouvrir le dashboard sur le PC Hôte. Le PC Attaquant distinct dispose
de Python 3.10+ et du seul script `security/scenarios/request_flood.py`.
Ne copier aucun secret sur le PC Attaquant.

## Séquence continue de 60 secondes maximum

- 0 à 8 s : montrer une transaction fictive réussie et l'état disponible.
- 8 à 12 s : sur le PC Attaquant lancer le flux borné vers l'IP autorisée du PC Hôte.
- 12 à 25 s : montrer l'indisponibilité métier, l'incident ML et son score.
- 25 à 45 s : montrer la quarantaine Ansible et la nouvelle transaction automatique.
- 45 à 60 s : vérifier les données précédentes et le rétablissement pendant le flux.

Ces durées sont un conducteur de tournage, pas une garantie de performance.
La capture doit conserver les deux machines visibles (caméra ou partage combiné)
et ne doit masquer aucune intervention corrective. Aucun clip n'est fabriqué par
le script d'intégration local.

```powershell
# À exécuter exclusivement sur le PC Attaquant du groupe, avec l'IP approuvée
py request_flood.py --target http://192.168.137.1:8080 --lab-host 192.168.137.1 --seconds 35 --rps 70
```

Le script est limité à un hôte privé nommé explicitement, 100 requêtes/s, 60 secondes,
8 requêtes simultanées, sans suivi des redirections ni utilisation d'identifiants.
Le scénario sollicite la capacité partagée de l'API, pas les ressources du campus.

## Démonstration locale automatisée

`python scripts/demo.py` lance un conteneur client isolé sur le réseau Compose.
Il produit `output/evidence/recovery.json`. Cette recette ne remplace pas l'essai
sur un second PC physique ni la vidéo continue attendue pour le rendu.

## Pitch de cinq minutes

Ethan : problème métier et paiement. Josselin : déploiement et observation.
Lucas : modèle, données et limites. Maxime : attaque, défense et droits.
Jean-christophe : risques, continuité et recommandations. Prévoir le temps de la
démonstration et éviter de lire les diapositives. À la finale, préparer l'introduction
individuelle en anglais et le déroulé demandé par le campus.
