# Sécurité du laboratoire

WAF ModSecurity/OWASP CRS verrouillé par digest ; métadonnées WAF/API collectées
sans corps ni jetons. Les logs bruts d'audit ModSecurity sont désactivés pour éviter
la capture de données sensibles. Le SOC corrèle les statuts et les incidents ML.

JWT RS256 : seule auth reçoit la clé privée. L'exécuteur est sur un réseau interne
sans port hôte, avec une clé distincte, une action et des CIDR bornés. Aucun socket
Docker n'est monté dans l'application ni le RAG. Les conteneurs Python sont non root,
avec système de fichiers en lecture seule et capacités supprimées.

SOPS/age : `scripts/manage_secrets.py bootstrap`, puis `encrypt`. Le bundle
`secrets.enc.json` est chiffré et contrôlé par déchiffrement identique. La clé privée
`.secrets/lab.agekey` reste hors Git et hors archive. Ajouter les destinataires
autorisés avant partage. `decrypt` refuse d'écraser des secrets locaux différents.
Sous Unix : dossier 0700, secrets applicatifs 0640 et GID local transmis aux services.
Sous Windows : vérifier également les ACL NTFS. Aucun secret n'est imprimé au setup.

TLS est disponible avec certificat de labo. Avant exposition sur le hotspot,
établir sa confiance sur les seuls postes autorisés et valider le pare-feu hôte.
Base, secrets, métriques et interfaces de commande ne doivent pas être publiés au LAN.

Le flux offensif est borné à un hôte privé nommé explicitement, 60 s, 100 req/s et
8 requêtes simultanées. Aucune action ne vise le campus, un autre groupe ou Internet.
Le quota partagé est un modèle de capacité choisi pour le démonstrateur. La remise
en disponibilité ne prouve pas la correction d'une compromission ou d'une fuite.
