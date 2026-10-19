# Reprise autonome - contrat à implémenter

Machine à états prévue : observed -> detected -> recovering -> verifying -> recovered/failed.
Accepter uniquement des services et actions explicitement autorisés ; sérialiser les actions,
dédupliquer incident_id, limiter les tentatives et conserver un journal horodaté.

Prévoir un exécuteur Ansible isolé avec droits limités. Aucun socket Docker n'est monté dans
l'application, le futur détecteur ou le RAG. Ne jamais accepter une commande arbitraire.
Un redémarrage Docker automatique ne démontre pas une remédiation pilotée par le ML.

La validation exige une nouvelle transaction avec une nouvelle clé d'idempotence et une
vérification des anciennes données. Ne déclarer recovered qu'après cette vérification.

