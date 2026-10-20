# Recette sur deux PC et contrôle du rendu

Inclure la [recette caméra USB hôte / ESP8266](additional-auth.md) et conserver ses
preuves séparées des tests simulés. Renseigner `physical_auth` et `esp8266` dans
`acceptance.json` uniquement après vérification sur le matériel réel.

Statut initial : NON RÉALISÉE. Ce document est la procédure préparée pour l'équipe.
Le client Docker des essais automatisés n'est pas un second ordinateur physique.

## Réseau - Josselin et Maxime

- [ ] Activer le point d'accès mobile Windows du PC Hôte sur le seul réseau du groupe.
- [ ] Faire valider le nom provisoire RESILIENCE-Equipe-DIVET en l'absence de numéro.
- [ ] Connecter le PC Attaquant et relever les IP distinctes des deux postes.
- [ ] Dans `.env`, choisir l'IP du hotspot pour BIND_ADDRESS et limiter LAB_CIDRS au labo.
- [ ] Publier uniquement 8080/8443 vers le hotspot ; garder DB, administration et métriques internes/locales.
- [ ] Dans le pare-feu, autoriser seulement le sous-réseau du groupe sur ces deux ports.
- [ ] Redémarrer le WAF après changement de bind : `docker compose up -d waf`.
- [ ] Vérifier le SAN du certificat, transférer seulement le certificat public au poste autorisé et établir sa confiance.
- [ ] Vérifier depuis le PC Attaquant que l'hôte reste identifiable par son IP source dans le SOC ; si tout est NATé sous une seule IP, corriger le réseau avant de démontrer la quarantaine.

Ne pas changer les règles du réseau campus. Ne transférer ni `.env`, ni `.secrets`,
ni mots de passe au PC Attaquant. Le script offensif utilise HTTP sans identifiants ;
le parcours authentifié du jury utilise HTTPS avec confiance établie.

## Scénario - Ethan, Lucas et Maxime

- [ ] Démarrer le profil ai, charger qwen3:0.6b et vérifier une réponse RAG citée.
- [ ] Exécuter smoke.py, puis calibrer uniquement avec le trafic légitime du PC Hôte.
- [ ] Vérifier le modèle chargé ; ne pas calibrer avec le poste attaquant.
- [ ] Créer une transaction, noter son identifiant et montrer la disponibilité.
- [ ] Lancer depuis le PC Attaquant le script borné du demo-runbook, cible IP du PC Hôte.
- [ ] Constater au moins un refus métier, la source distincte, le score ML et la chronologie.
- [ ] Sans correction humaine, observer recovering -> verifying -> recovered.
- [ ] Vérifier un nouveau paiement et la transaction précédente pendant le flux offensif.
- [ ] Conserver la chronologie, les IP, les horaires et les captures sans secret.
- [ ] En cas de failed, conserver l'échec puis diagnostiquer hors capture ; refaire une recette distincte.

## Clip - toute l'équipe

- [ ] Faire une prise continue <= 60 s, avec les deux machines identifiables et les écrans lisibles.
- [ ] Filmer le paiement initial, le lancement réel, la détection, la quarantaine et le paiement final.
- [ ] Garder les mots de passe hors champ ; se connecter avant la prise.
- [ ] Relire la vidéo en entier et vérifier sa durée ; aucune coupe ne masque une action corrective.
- [ ] Déposer le fichier sous le nom `<delivery_slug>-VidChrono.mp4` dans le dossier de rendu.

## Validation - Jean-christophe et équipe

- [ ] Faire valider l'architecture et les hypothèses EBIOS/coûts/RTO/RPO par l'équipe et le coach.
- [ ] Chaque référent confirme ses travaux, sa compréhension et ses vérifications dans contributions.md.
- [ ] Répéter le conducteur de 5 minutes et les questions pendant 5 minutes.
- [ ] Faire valider la dénomination sans numéro par le campus.
- [ ] Régénérer les supports et le ZIP après toute correction ; contrôler le README-RENDU.
- [ ] Respecter le gel à 17 h et la remise avant jeudi 23 h 59 selon le planning du sujet.

## Procès-verbal à renseigner après exécution

| Élément | Valeur constatée |
| --- | --- |
| Date et opérateurs présents | Non renseignés |
| PC Hôte / IP | Non renseignés |
| PC Attaquant physique / IP | Non renseignés |
| Incident / transaction avant / transaction après | Non renseignés |
| Résultat et interventions éventuelles | Non renseignés |
| Vidéo et durée | Non renseignées |
| Validation coach et nom de groupe accepté | Non obtenues |

Reporter chaque validation réellement obtenue dans `docs/acceptance.json`, avec
une référence de preuve, puis lancer `python scripts/delivery_check.py --strict`.
Une case cochée sans exécution ne constitue pas une recette.
