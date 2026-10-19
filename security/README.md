# Chantier cybersécurité

Le proxy Nginx fourni sert le frontal et limite les routes exposées. Ce n'est pas un WAF.
À intégrer : ModSecurity/OWASP CRS, collecte des logs, corrélation SOC/SIEM et alertes
reliées aux incidents, puis validation des faux positifs sur le parcours de paiement.

Les secrets locaux sont générés dans `.secrets/` et montés comme fichiers Compose.
Cela ne remplace pas la gestion Vault/SOPS exigée pour le rendu. Choisir SOPS + age,
chiffrer hors dépôt les secrets à partager et garder la clé privée hors archive.
Ne jamais ajouter un fichier contenant des secrets en clair au dépôt ou aux livrables.

Avant exposition sur le hotspot : filtrer le pare-feu hôte, valider TLS et limitations de
débit, et changer le bind explicitement. Seul le port applicatif est publiable au LAN.
L'auth de labo utilise un compte fictif et une clé HS256 commune auth/API : passer à
une signature asymétrique et des rôles pour isoler les privilèges avant d'étendre le périmètre.

