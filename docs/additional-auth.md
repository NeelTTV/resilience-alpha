# Consigne additionnelle 1 : visage, caméra hôte et ESP8266

Implémentation de la consigne fournie dans « WorkShop 2026-27 M2 - Consigne
Additionnelle.pdf ». La caméra utilisée est celle branchée en USB au **PC hôte
Windows**, qui héberge Docker et le hotspot `RESILIENCE-G<n>`. Aucune webcam du
navigateur ou du second PC n'est utilisée. Le numéro de groupe n'est pas inventé.

## Parcours livré

| Étape | Caméra hôte | LED | Suite autorisée par le serveur |
| --- | --- | --- | --- |
| Repos | Éteinte | Éteinte | Saisie de l'identifiant |
| Identifiant validé par Entrée/bouton | Activée, reconnaissance ≤ 8 s | Éteinte | Attente du résultat facial |
| Visage reconnu | Active | Vert clignotant | Mot de passe accessible pendant 90 s |
| Visage refusé | Active jusqu'à la fin des 30 s | Rouge fixe 30 s | Identifiant vidé ; nouvelle tentative après extinction |
| Mot de passe refusé | Extinction après l'animation | Rouge, 10 clignotements à 1 Hz | Identifiant vidé ; toute l'identification recommence |
| Mot de passe correct | Extinction en fin de temporisation | Vert fixe 30 s puis éteinte | JWT délivré et back-office ouvert seulement après 30 s |

Après deux échecs d'identification complets (visage ou mot de passe), le poste
est bloqué cinq minutes, à compter de la fin de l'animation de refus. Ce compteur
est global au poste, persiste dans SQLite et ne peut pas être évité en changeant
d'identifiant ou en rechargeant la page. Après le blocage, un nouveau cycle de
deux essais est possible. Une identification réussie remet le compteur à zéro.
Une seule identification utilise la caméra/LED à la fois. Les sessions expirent,
les challenges sont aléatoires et liés à l'identifiant, et leur consommation est
unique. Un watchdog continue les extinctions si le navigateur est fermé ; l'agent
hôte libère aussi la caméra au bout de 130 s maximum si Docker s'arrête.

## Installation sur le PC hôte Windows

1. Brancher **la caméra USB externe** sur le PC hôte. Identifier son index OpenCV
   et vérifier physiquement que c'est son voyant qui s'allume. La caméra intégrée
   n'est pas sélectionnée implicitement : `USB_CAMERA_INDEX` est obligatoire.
2. Dans PowerShell, depuis la racine du dépôt :

   ```powershell
   ./.venv/Scripts/python.exe scripts/init-secrets.py
   $env:USB_CAMERA_INDEX = '1' # exemple à adapter à la caméra USB externe réelle
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-camera.ps1 --bootstrap
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-camera.ps1
   ```

   Le premier appel enrôle uniquement l'administrateur initial (`operator`, ou
   `DEMO_USERNAME` explicitement défini dans ce terminal et dans `.env`). Présenter
   son visage seul, bien éclairé, en variant légèrement sa pose pendant 18 s.
   Le bootstrap refuse de remplacer un modèle existant : les remplacements
   suivants passent par les habilitations du back-office. Le second appel doit
   rester actif pendant la démonstration. L'environnement `.camera-venv` est
   distinct de `.venv` pour isoler les dépendances OpenCV.
3. Le service hôte écoute en HTTPS sur 8765. Autoriser ce port dans le pare-feu
   **uniquement depuis Docker Desktop/WSL2**, selon ses adresses réelles. Les
   postes du hotspot n'ont pas besoin d'y accéder. Docker utilise
   `host.docker.internal`, une clé dédiée et le certificat caméra local vérifié.
   Ne pas publier ce port par redirection du routeur. La clé `camera_key` et la
   clé privée `camera_tls_key` restent sur l'hôte et les secrets Docker nécessaires.
4. Configurer puis flasher l'ESP8266 suivant la section ci-dessous.
5. Mettre à jour les conteneurs :

   ```powershell
   docker compose up --build -d --wait
    docker compose restart waf
   ```

Sans caméra, sans modèle facial ou sans connexion récente de l'ESP8266,
l'authentification humaine échoue. Aucun interrupteur de contournement logiciel
n'est fourni. Ne pas supprimer le volume `auth_data` : il contient habilitations,
compteur de blocage et état des identifications.
Le redémarrage du WAF renouvelle sa résolution DNS après remplacement du dashboard.

## ESP8266 : CLion + PlatformIO

Projet : `infra/esp8266/platformio.ini`, cible NodeMCU ESP8266 (`nodemcuv2`).
Utiliser **JetBrains CLion avec l'intégration PlatformIO**, ouvrir ce projet,
puis utiliser les actions PlatformIO Build et Upload. Adapter la cible si la carte
ESP8266 du groupe n'est pas une NodeMCU. Les commandes ci-dessous sont également
utilisables depuis le terminal de CLion avec PlatformIO installé.

LED bicolore **à cathode commune** : cathode vers GND ; anode verte vers D1/GPIO5
via une résistance de 330 Ω ; anode rouge vers D2/GPIO4 via une seconde résistance
de 330 Ω. Une LED à anode commune ou deux broches nécessite d'adapter le câblage
et le pilotage ; ne pas utiliser ce montage sans vérifier le composant.

```powershell
./.venv/Scripts/python.exe scripts/configure-esp.py
pio run --project-dir infra/esp8266
pio run --project-dir infra/esp8266 --target upload
```

Le générateur demande le SSID réel `RESILIENCE-G<numéro>`, le mot de passe Wi-Fi
masqué et l'URL HTTPS de l'hôte. Il écrit seulement le fichier local ignoré
`include/lab_config.h`, avec une clé **distincte de la clé caméra** et l'empreinte du
certificat WAF. Ce fichier, les fichiers `.pio` et le binaire flashé contenant la
clé ne doivent pas être publiés. Après rotation du certificat WAF ou de
`device_key`, régénérer et reflasher la configuration. Le SSID doit être un hotspot
2,4 GHz accessible à l'ESP8266 ; ajuster `BIND_ADDRESS`, `LAB_CIDRS` et le pare-feu
suivant la recette réseau existante.

Le module interroge `/auth/device/status` en HTTPS avec vérification de
l'empreinte TLS. Il ne reçoit ni identifiant, ni mot de passe, ni JWT humain, ni
image. Il reste éteint au démarrage et s'éteint en cas de perte de réseau ou
d'état périmé. Les dix clignotements rouges sont exécutés localement sans requête
TLS bloquante pendant l'animation. Le polling peut introduire jusqu'à environ
500 ms de décalage d'affichage par rapport à l'horloge serveur ; vérifier les
durées au chronomètre sur la carte réelle.

## Habilitations

Après connexion de l'administrateur, la section « Habilitations et reconnaissance
faciale » permet de créer/modifier les comptes, changer le mot de passe et le rôle
(`admin`/`operator`), activer/désactiver, enrôler/remplacer le visage sur le PC hôte,
et supprimer compte et modèle facial. Un compte nouveau ne peut pas se connecter
avant son enrôlement. L'administrateur ne peut pas se supprimer ou se rétrograder
lui-même. Les opérateurs ne peuvent pas administrer les comptes.

Toute modification d'habilitation révoque les sessions d'identification et les
JWT antérieurs du compte. Les services API/SOC/RAG vérifient les habilitations
courantes auprès d'Auth et refusent l'accès si cette vérification est indisponible.
Les mots de passe sont hachés avec scrypt. Les modèles biométriques sont locaux
dans `data/biometrics`, exclus de Git, du contexte Docker et de l'archive. Restreindre
les ACL Windows de ce dossier au compte qui exécute l'agent et définir une durée
de conservation avec les participants. La suppression d'un compte efface son
modèle. Les sauvegardes métier PostgreSQL ne sauvegardent pas ces modèles ni le
volume d'habilitations ; leur sauvegarde/restauration doit rester privée et faire
l'objet d'une procédure dédiée.

Le compte technique `recovery-check` conserve le mot de passe secret de la recette
de reprise. Ses jetons sont limités aux transactions fictives et ne donnent accès
ni au SOC, ni au RAG, ni à l'administration du back-office. La recette CI sans
matériel utilise explicitement ce compte (`SMOKE_SERVICE_ACCOUNT=1`). Les recettes
opérateur (`smoke.py` sans cette variable, `calibrate.py`, `demo.py`,
`confirm_model.py`, `browser-check.cjs`) exigent la présence devant la caméra hôte.
La CI hébergée vérifie le métier, les refus d'accès et les tests d'automate ;
la recette complète ML/reprise avec authentification humaine se fait sur le labo.

## IA locale et limites à mesurer

OpenCV Haar détecte un visage unique ; LBPH compare le visage normalisé au modèle
enrôlé. Cinq observations consécutives doivent correspondre. Les traitements
s'exécutent sur CPU sur le PC hôte, sans cloud. Le seuil de distance par défaut
est 55 (`FACE_DISTANCE_THRESHOLD`) ; il doit être calibré avec le groupe sur la
caméra, l'éclairage et des personnes non habilitées. Ce seuil n'est pas un taux de
confiance. Aucun taux d'erreur biométrique n'est encore mesuré sur le matériel.
LBPH ne fournit pas de détection de présentation (photo/vidéo) : ce prototype
répond au parcours demandé et ne constitue pas une preuve de résistance à une
attaque biométrique physique sophistiquée.

Références techniques : [OpenCV LBPH](https://docs.opencv.org/4.13.0/df/d25/classcv_1_1face_1_1LBPHFaceRecognizer.html)
et [ESP8266 BearSSL](https://arduino-esp8266.readthedocs.io/en/3.0.0/esp8266wifi/bearssl-client-secure-class.html).

## Recette matérielle à exécuter, sans la déduire des tests simulés

- Depuis le second PC, saisir l'identifiant : seule la caméra USB du PC hôte s'allume.
- Visage enregistré : champ mot de passe débloqué, vert clignotant.
- Visage inconnu et visage d'un autre compte : rouge fixe 30 s, puis caméra éteinte,
  identifiant vide ; recommencer une fois puis vérifier le blocage pendant 300 s.
- Recharger la page, changer d'identifiant et redémarrer Auth pendant le blocage :
  le délai restant doit être conservé.
- Mauvais mot de passe : dix clignotements rouges, puis extinction et nouveau
  parcours complet. Vérifier au chronomètre et à la vidéo.
- Mot de passe correct : vert fixe 30 s ; aucun JWT avant la fin ; LED éteinte et
  ouverture du back-office seulement ensuite.
- Créer un opérateur, l'enrôler, vérifier le refus de gestion des comptes, le
  désactiver et vérifier le rejet immédiat de son ancien JWT ; supprimer son compte.
- Débrancher caméra puis ESP8266, fermer la page pendant une attente et couper
  Auth : vérifier refus d'accès, extinction et libération de la caméra.
- Mesurer faux rejets/fausses acceptations et essai avec photo, documenter les
  limites. Enregistrer les preuves dans `docs/acceptance.json`, clés
  `physical_auth` et `esp8266`, uniquement après exécution réelle.
