"""Build the engineering dossier from implementation details and measured evidence.

Optional authoring dependency: reportlab. Output files contain no credentials.
"""

import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]


def build():
    project = json.loads((ROOT / "project.json").read_text(encoding="utf-8"))
    recovery = json.loads((ROOT / "output/evidence/recovery.json").read_text())
    calibration = json.loads((ROOT / "output/evidence/calibration.json").read_text())["model"]
    backup = json.loads((ROOT / "output/evidence/backup.json").read_text())
    evaluation = json.loads((ROOT / "output/evidence/model-evaluation.json").read_text())
    reproducibility = json.loads((ROOT / "output/evidence/reproducibility.json").read_text())
    if not recovery["passed"] or not reproducibility["passed"]:
        raise RuntimeError("A passing recovery proof is required before producing the dossier")
    incident = recovery["incident"]
    duration = round(incident["updated_at"] - incident["created_at"], 2)
    proof = next(e["detail"] for e in incident["timeline"] if e["state"] == "recovered")
    font_directory = Path("C:/Windows/Fonts")
    if not font_directory.exists():
        font_directory = Path("/usr/share/fonts/truetype/dejavu")
    regular = font_directory / (
        "arial.ttf" if (font_directory / "arial.ttf").exists() else "DejaVuSans.ttf"
    )
    bold = font_directory / (
        "arialbd.ttf" if (font_directory / "arialbd.ttf").exists() else "DejaVuSans-Bold.ttf"
    )
    pdfmetrics.registerFont(TTFont("Body", str(regular)))
    pdfmetrics.registerFont(TTFont("BodyBold", str(bold)))
    styles = {
        "title": ParagraphStyle(
            "title",
            fontName="BodyBold",
            fontSize=23,
            leading=29,
            textColor=colors.HexColor("#261E48"),
            spaceAfter=22,
        ),
        "heading": ParagraphStyle(
            "heading", fontName="BodyBold", fontSize=15, leading=20, spaceBefore=12, spaceAfter=9
        ),
        "body": ParagraphStyle(
            "body", fontName="Body", fontSize=10.5, leading=15.5, spaceAfter=12, alignment=TA_LEFT
        ),
        "small": ParagraphStyle("small", fontName="Body", fontSize=8.5, leading=12, spaceAfter=8),
    }
    chapters = [
        (
            "1. Mission et équipe",
            [
                "PROJECT RESILIENCE-ALPHA démontre la reprise d'un système de paiement fictif "
                "après un incident contrôlé. Le prototype relie développement, infrastructure, "
                "IA/Data, cybersécurité et gouvernance. Il ne communique avec aucune banque et "
                "n'utilise aucune donnée financière réelle.",
                "Le parcours comprend un frontal React/Tailwind, une authentification dédiée, "
                "une API métier et PostgreSQL. Un modèle de nouveauté analyse les observations "
                "HTTP, un automate décide d'une quarantaine et Ansible applique la politique. "
                "La preuve finale est une nouvelle transaction réussie et la relecture des données.",
                f"La recette locale a mesuré {duration} secondes entre la détection et l'état "
                "rétabli. Ce délai ne remplace pas le RTO depuis le début de l'indisponibilité. "
                "L'attaquant de recette est un conteneur isolé : la validation sur un deuxième "
                "PC physique et le Clip Chrono restent à réaliser.",
                "Travaux attribués par référent : Ethan, API/auth/interface ; Josselin, "
                "déploiement/observabilité/restauration ; Lucas, ML/données/RAG ; Maxime, "
                "attaque/WAF/secrets/privilèges ; Jean-christophe, risques/continuité/supports. "
                "Préparation avec l'aide de Codex ; cette répartition ne prouve pas un auteur "
                "individuel ou une recette personnelle. Les validations sont tracées dans "
                "docs/contributions.md. Le numéro de groupe est 3.",
            ],
        ),
        (
            "2. Architecture et flux",
            [
                "Le seul point d'entrée applicatif publié est le WAF ModSecurity/OWASP CRS. "
                "Il transmet au proxy Nginx qui sert les fichiers React et route les appels vers "
                "auth, payment, supervisor et assistant. Les adresses source reçues du client "
                "sont écrasées au niveau du WAF ; le proxy interne transmet l'identité retenue à l'API.",
                "L'authentification signe des JWT RS256 de quinze minutes. Seul auth monte la clé "
                "privée ; les services métier et de lecture montent la clé publique. Les montants "
                "sont des centimes entiers positifs. Une clé d'idempotence unique empêche qu'une "
                "nouvelle tentative réseau enregistre deux paiements. L'historique est limité aux "
                "cent dernières opérations du compte authentifié.",
                "Les volumes PostgreSQL, modèle, journal d'incidents et politique de quarantaine "
                "persistent entre redémarrages. Le superviseur lit les journaux, envoie les événements "
                "à Loki et sert le tableau de bord. Prometheus collecte les métriques de service ; "
                "Grafana visualise disponibilité, débit et latence. Le RAG consulte seulement les documents.",
                "L'exécuteur Ansible est sur un réseau control interne sans port hôte. Il ne monte "
                "aucun socket Docker. Il peut seulement écrire la politique d'admission validée dans "
                "un volume partagé, monté en lecture seule dans l'API. La topologie reste concentrée "
                "sur un hôte : elle n'apporte ni haute disponibilité ni tolérance à sa perte.",
                "Un instantané indépendant des sources a été déployé avec Ansible dans un "
                "projet Docker neuf, avec nouveaux secrets et volumes. Le second passage sans "
                "reconstruction n'a changé aucune ressource. Authentification, paiement, "
                "idempotence et accès par le port hôte ont été vérifiés, puis le projet d'essai "
                "supprimé. Preuve : output/evidence/reproducibility.json. Le moteur Docker reste "
                "celui de ce poste ; ce résultat ne valide pas l'installation d'un autre PC.",
            ],
        ),
        (
            "3. Incident et périmètre offensif",
            [
                "Le scénario retenu est un déni de service applicatif borné. L'API dispose d'un "
                "quota partagé volontairement dimensionné à vingt requêtes par seconde pour le "
                "laboratoire. Le flux de requêtes GET vers les transactions consomme ce quota, "
                "y compris lorsque les requêtes sont ensuite refusées par l'authentification. "
                "Des clients légitimes peuvent alors recevoir HTTP 503.",
                "Ce mécanisme représente la saturation d'une ressource partagée, et non une "
                "vulnérabilité découverte dans un prestataire de paiement. La limite de capacité "
                "est un seuil fixe de ressource ; la détection d'anomalie est séparée et repose "
                "sur le modèle entraîné. La quarantaine est évaluée avant le quota, ce qui libère "
                "la capacité métier pendant que les requêtes de la source hostile continuent.",
                "Le script request_flood.py exige le nom explicite de l'hôte privé autorisé, "
                "refuse les redirections et limite l'exercice à cent requêtes par seconde, "
                "soixante secondes et huit requêtes simultanées. Il n'utilise aucun identifiant "
                "et ne procède à aucun scan. Seules les machines et le SI fictif du groupe sont visés.",
                "La recette automatisée utilise trente-cinq secondes à soixante-dix requêtes "
                "par seconde depuis un conteneur client séparé. Le dossier conserve les codes "
                "HTTP, les moments d'indisponibilité et l'état de reprise. Le conducteur dans "
                "docs/demo-runbook.md décrit l'essai à répéter depuis le PC Attaquant physique.",
            ],
        ),
        (
            "4. Données et modèle ML",
            [
                f"La calibration a produit {calibration['train_windows']} fenêtres d'apprentissage "
                f"et {calibration['validation_windows']} fenêtres de validation chronologiques. "
                "Les observations viennent de requêtes HTTP réellement exécutées dans ce labo, "
                "sur une période normale distincte de l'attaque. Les fenêtres non vides sont "
                "agrégées par source sur trois secondes.",
                "Le OneClassSVM est retenu pour apprendre le comportement normal sans exiger "
                "un corpus d'attaques étiquetées, avec un coût adapté au CPU du laboratoire. "
                "Ce choix rend la calibration représentative indispensable. "
                "Les variables sont le logarithme du débit, la proportion de réponses en erreur, "
                "la latence moyenne et la proportion de refus 401. Un centrage sans amplification "
                "de la faible variance de latence précède "
                "un OneClassSVM à noyau RBF, nu=0,05. La frontière est calibrée de façon prudente "
                "sur les seules fenêtres normales de validation. Deux décisions anormales "
                "consécutives sont requises avant de créer un incident remédiable.",
                "L'attribution et l'autorisation d'action sont distinctes du score ML. La source "
                "doit dominer le trafic observé, ne pas appartenir aux sources protégées de la "
                "calibration et ne pas être un composant du contrôle. Ces garde-fous évitent de "
                "bannir une victime qui reçoit des erreurs pendant la saturation. Ils limitent "
                "aussi la couverture : une source protégée compromise ne sera pas isolée ainsi.",
                f"Le modèle utilisé porte la version {incident['evidence']['model_version']}. "
                f"Lors de l'incident, score={incident['evidence']['score']:.4f} et frontière="
                f"{incident['evidence']['threshold']:.4f}. La calibration affiche zéro faux positif "
                "sur son split, ce qui ne constitue pas une évaluation indépendante. Étendre les "
                "jeux d'essai, les charges, les sources et la durée reste nécessaire.",
                f"Sur une confirmation fraîche sans réentraînement : "
                f"{evaluation['true_positive']}/{evaluation['attack_windows']} fenêtres d'attaque "
                f"détectées et {evaluation['false_positive_on_assumed_quiet']} fausse alerte sur "
                f"{evaluation['quiet_windows']} fenêtres normales authentifiées. Ce petit échantillon "
                "corrélé ne démontre pas une précision générale ; les fenêtres d'attaque incluent "
                "aussi des requêtes déjà bloquées après la quarantaine.",
            ],
        ),
        (
            "5. Remédiation et preuve métier",
            [
                "Les états detected, recovering, verifying, recovered et failed sont persistés "
                "dans SQLite. Chaque incident conserve l'IP, la version et le score du modèle, "
                "les variables observées et sa chronologie. Une fenêtre de temporisation limite "
                "les actions répétées pour une même source. Les échecs restent visibles.",
                "L'exécuteur exige une clé de remédiation dédiée, valide l'UUID de l'incident "
                "et l'adresse dans les CIDR autorisés. Son unique action est une quarantaine "
                "de trois cents secondes. Le playbook utilise ansible.builtin.copy pour publier "
                "le JSON atomiquement. Le serveur vérifie aussi que la politique attendue a été "
                "écrite ; un code retour nul sans politique ne suffit pas.",
                "Après l'action, le moteur se connecte avec le compte distinct recovery-check "
                "à travers le WAF. Il conserve jusqu'à vingt opérations précédentes, crée un "
                "paiement de cent un centimes avec une nouvelle clé, puis relit l'historique. "
                "Il vérifie l'existence et les données du nouveau paiement ainsi que les valeurs "
                "précédentes. Cinq tentatives au maximum précèdent un échec explicite.",
                f"La transaction de preuve est {proof['transaction_id']}. La recette externe "
                f"a observé {recovery['observed_503']} refus de disponibilité et a vérifié un retour "
                "au métier pendant que le processus offensif tournait encore. Elle a aussi "
                "retrouvé la transaction opérateur créée avant l'incident. La quarantaine ne "
                "corrige ni une exfiltration ni une compromission de la base.",
            ],
        ),
        (
            "6. Observation, SOC et assistant",
            [
                "Les événements WAF et API contiennent horodatage, service, route sans paramètres, "
                "méthode, statut, durée et source. Les corps, en-têtes d'authentification et secrets "
                "ne sont pas conservés dans cette collecte. Les journaux bruts d'audit ModSecurity "
                "sont désactivés afin d'éviter la capture de données de requête sensibles.",
                "Le collecteur mémorise des offsets et traite uniquement les lignes terminées. "
                "Les métadonnées sont envoyées vers Loki. La fonction SOC du superviseur rassemble "
                "les événements par service et statut sur la dernière minute, puis associe les "
                "indices de trafic aux incidents ML. Elle ne prétend pas remplacer un SIEM "
                "industriel avec corrélations multi-systèmes et conservation immuable.",
                "Le dashboard montre les événements, le modèle chargé et les étapes de reprise, "
                "avec accès aux preuves techniques. Les métriques Prometheus/Grafana complètent "
                "le suivi. Un healthcheck API avec base disponible ne constitue pas une preuve "
                "métier : la saturation du quota peut encore empêcher un paiement.",
                "Le RAG découpe les procédures locales en objets Document LangChain et les "
                "retrouve par TF-IDF avant génération avec ChatOllama. Le modèle qwen3:0.6b "
                "est choisi pour le CPU ; une allowlist interdit les modèles au-delà de huit "
                "milliards de paramètres. Les extraits et sources sont rendus au lecteur. Sans "
                "modèle, le mode retrieval_only est explicite. L'assistant n'a aucun outil "
                "d'administration, secret de reprise ou droit d'exécuter une commande.",
            ],
        ),
        (
            "7. Analyse de risques EBIOS RM",
            [
                "L'analyse est proposée à l'équipe selon les cinq ateliers EBIOS RM [1] ; elle "
                "ne prétend pas qu'un atelier collectif ou une validation du coach a eu lieu. "
                "Le cadrage retient disponibilité, cohérence du paiement et traçabilité. Les "
                "biens supports comprennent aussi le hotspot, les procédures, l'hôte et les secrets.",
                "Les sources retenues sont un client malveillant sur le réseau du groupe, un "
                "compte compromis, un composant interne compromis et la chaîne de dépendances. "
                "Le scénario stratégique principal passe du client au WAF puis à la ressource "
                "partagée de l'API. Les scénarios complémentaires concernent doublons, abus des "
                "droits de remédiation, perte d'hôte et vol d'identifiants.",
                "Une échelle pédagogique de un à quatre sert à qualifier gravité et vraisemblance. "
                "Propositions avant/après mesures : saturation G3/V4 puis V2 ; doublon G3/V3 puis "
                "V1 ; abus de reprise G4/V3 puis V2 ; perte d'hôte G4/V2 restant V2. Ces nombres "
                "sont des hypothèses de travail à discuter, pas des fréquences observées.",
                "La quarantaine réduit le scénario à une source mais reste contournable par "
                "changement d'adresse ou attaque distribuée. Les sources protégées ne sont pas "
                "remédiées automatiquement. Le plan priorise la recette sur deux PC, la confiance "
                "TLS, une copie de sauvegarde hors hôte, les comptes individuels/MFA, la rotation "
                "et un audit de dépendances. Jean-christophe suit les écarts avec les responsables "
                "techniques. Le registre complet est dans docs/governance.md.",
            ],
        ),
        (
            "8. Continuité, sauvegarde et sécurité",
            [
                "Les objectifs proposés sont RTO inférieur ou égal à trente secondes depuis "
                "l'apparition de la saturation et RPO nul pour les paiements confirmés dans ce "
                "scénario sans restauration. Aucun de ces objectifs ne couvre une perte de l'hôte. "
                "Le temps détection/reprise de la recette n'inclut pas toute la phase précédente.",
                "Justification métier hypothétique : 30 paiements/minute, panier de 25 EUR, "
                "commission de 0,20 EUR et 50 % d'abandon. Le flux interrompu est 750 EUR/min, "
                "distinct de la perte de commissions de 3 EUR/min. Deux personnes mobilisées "
                "20 min à 45 EUR/h ajoutent 30 EUR. Une coupure de 5 min coûterait 45 EUR ; "
                "30 s représenteraient 1,50 EUR de commissions perdues. Hypothèses pédagogiques "
                "à valider, hors confiance et pénalités, sans revenu réel mesuré.",
                f"La sauvegarde PostgreSQL a été restaurée dans une base neuve en "
                f"{backup['restore_seconds']} secondes sur ce poste. Le test compare le nombre "
                "de transactions et l'empreinte de leur contenu trié. Il supprime uniquement "
                "sa base temporaire et n'écrase pas le métier. Les copies sont locales ; un "
                "PRA perte d'hôte demande une copie externe et un exercice sur un autre poste. "
                "Politique proposée avant pilote : copie externe chiffrée toutes les 15 minutes, "
                "rétention sept jours, contrôle quotidien et exercice mensuel. Ce dispositif "
                "n'est pas déployé ; son RPO cible de 15 minutes reste à mesurer.",
                "Les secrets sont générés aléatoirement, ignorés par Git et montés seulement "
                "dans les services qui les utilisent. SOPS/age chiffre le bundle partageable, "
                "contrôlé par un déchiffrement identique. La clé age privée reste hors archive. "
                "Le workflow refuse d'écraser des identifiants locaux différents sans traitement "
                "explicite. Les permissions Unix et les ACL Windows doivent être adaptées au poste.",
                "PCA : maintenir la base et isoler la source pendant la saturation. Si l'automate "
                "échoue, Josselin et Ethan conservent failed et les journaux, puis diagnostiquent "
                "hors démonstration. PRA données : arrêter les écritures, conserver la base "
                "endommagée, restaurer dans une base distincte, comparer empreintes et comptages, "
                "puis faire approuver le basculement. Une perte d'hôte exige aussi redéploiement, "
                "récupération des secrets et procédure privée pour les habilitations/biométries.",
                "Le WAF est verrouillé par digest et l'application offre TLS avec certificat "
                "de laboratoire. Le groupe doit établir la confiance du certificat et filtrer "
                "le hotspot avant usage. Les services internes ne publient pas de port réseau. "
                "Les limites restent le compte technique partagé, la biométrie sans anti-photo, la "
                "concentration sur un hôte et l'absence d'audit indépendant des images.",
            ],
        ),
        (
            "9. Gouvernance, limites et références",
            [
                "Le rapprochement NIS2/DORA reste pédagogique. NIS2 concerne notamment gestion "
                "des risques et signalement d'incidents pour les entités concernées [2]. DORA "
                "porte sur la résilience numérique du secteur financier, dont les risques TIC "
                "et les essais [3]. L'applicabilité réelle, la transposition nationale et les "
                "textes sectoriels doivent être examinés séparément.",
                "Le prototype apporte rôles, registre de risques, chronologie d'incidents, "
                "essais de reprise et protection des secrets. Il n'apporte pas de notification "
                "réglementaire, gouvernance d'une entité financière réelle, surveillance des tiers, "
                "programme de tests représentatif ou certification. Une matrice d'écarts relie "
                "ces thèmes aux composants et preuves dans docs/governance.md.",
                "Choix de gouvernance proposés : usage limité au laboratoire ; Josselin réserve "
                "une demi-journée à la recette réseau, Lucas une journée à l'évaluation ML. "
                "Jean-christophe suit le registre des écarts ; le coach et l'équipe restent "
                "décideurs de leur validation. Revoir les risques après changement du modèle, "
                "du réseau ou des privilèges. Ces budgets de temps ne sont pas des travaux attestés. "
                "Un pilote demande "
                "une sauvegarde externe chiffrée, un second hôte et une évaluation ML étendue. "
                "La matrice rapproche NIS2 art. 20-21/23 et DORA art. 5-6/9/11-12/17-19/24-25/28-30 "
                "des preuves et écarts. Ce rapprochement ne décide pas l'applicabilité des textes.",
                "Les vérifications restantes sont explicites : essai depuis le deuxième PC "
                "physique, contrôle du hotspot/pare-feu et de la confiance TLS, campagne ML "
                "sur charges variées, PRA perte d'hôte, validation des travaux attribués et vidéo "
                "continue de soixante secondes. La CI est définie dans le dépôt ; son exécution "
                "distante n'est pas prouvée par une réussite locale.",
                "[1] ANSSI, méthode EBIOS RM : https://cyber.gouv.fr/securisation/analyse-des-risques/"
                "methode-ebios-rm/\n[2] Commission européenne, NIS2 : "
                "https://digital-strategy.ec.europa.eu/en/policies/nis2-directive\n"
                "[3] EIOPA, DORA : https://www.eiopa.europa.eu/digital-operational-resilience-act-dora_en\n"
                "Identifiants des textes : directive (UE) 2022/2555 et règlement (UE) 2022/2554. "
                "Pages ANSSI, Commission et EIOPA consultées le 22 octobre 2026.\n"
                "Sources du besoin : consigne de dossier transmise dans la conversation. "
                "Sources techniques : README.md, compose.yaml, services/, docs/additional-auth.md, "
                "docs/governance.md et docs/contributions.md. Sources des résultats : "
                "output/evidence/calibration.json, recovery.json, model-evaluation.json, backup.json, "
                "reproducibility.json et security.json. Les preuves antérieures ne valent pas "
                "nouvelle recette de l'intégration matérielle du 20 octobre.",
            ],
        ),
    ]
    chapters.insert(2, (
        "3. Authentification physique et habilitations",
        [
            "Évolution intégrée au dossier du 22 octobre : la connexion humaine impose le visage "
            "devant la caméra USB du PC hôte Windows, puis le mot de passe. Auth pilote le parcours ; "
            "l'agent caméra HTTPS local reconnaît le visage ; l'ESP8266 interroge le WAF et affiche "
            "les états sur une LED bicolore. Le navigateur du second PC n'utilise pas sa webcam. "
            "Ce choix centralise l'enrôlement, au prix d'une présence physique obligatoire et d'une "
            "dépendance à la caméra, au Wi-Fi et au module.",
            "Après reconnaissance (cinq observations consécutives), le vert clignote et le mot de "
            "passe peut être saisi pendant 90 s. Visage refusé : rouge fixe 30 s. Mot de passe "
            "incorrect : dix clignotements rouges à 1 Hz. Mot de passe correct : vert fixe 30 s, "
            "puis seulement délivrance du JWT et ouverture du back-office. Deux échecs complets "
            "déclenchent un blocage global de cinq minutes, persistant dans SQLite. Les challenges "
            "sont aléatoires, liés au compte, expirables et consommés une seule fois.",
            "Les mots de passe sont hachés avec scrypt. Les clés caméra et ESP8266 sont distinctes ; "
            "le module vérifie l'empreinte TLS du WAF. "
            "Les habilitations admin/operator sont persistées dans auth_data. L'administrateur "
            "peut créer, enrôler, désactiver et supprimer les comptes ; une modification invalide "
            "leurs anciens jetons. API, SOC et RAG vérifient l'état courant auprès d'Auth ; une "
            "indisponibilité de cette vérification ferme l'accès. Cette révocation est présente "
            "dans le code actuel, même si certains anciens documents décrivent encore le socle antérieur.",
            "Le compte technique recovery-check demeure distinct du parcours humain. Ses droits "
            "sont limités aux transactions fictives de preuve ; il ne donne accès ni au SOC, ni au "
            "RAG, ni à l'administration. Ce choix permet une vérification automatique du métier, "
            "tout en faisant de son secret une dépendance de la reprise.",
            "OpenCV Haar/LBPH fonctionne sur CPU sans cloud. Le seuil de distance 55 doit être "
            "calibré ; ce n'est pas un taux de confiance. Aucune protection contre présentation "
            "d'une photo ou vidéo n'est démontrée. Modèles faciaux locaux, exclus de Git et de "
            "l'archive ; ACL, conservation et suppression sont à organiser avec les participants. "
            "Le dump PostgreSQL ne sauvegarde ni ces modèles ni les habilitations SQLite.",
            "Les automates peuvent être testés avec des périphériques simulés. L'enrôlement réel, "
            "la caméra USB, l'ESP8266 et les durées lumineuses ne sont pas validés dans "
            "docs/acceptance.json. Aucun taux d'erreur biométrique ni essai matériel réussi "
            "n'est déduit des preuves antérieures. Source : docs/additional-auth.md et "
            "services/common/security.py.",
        ],
    ))
    chapters.insert(6, (
        "7. Résultats des essais et portée des preuves",
        [
            "Cette synthèse exploite les fichiers de preuve déjà présents, sans relancer une "
            "attaque ni une recette matérielle pour produire le dossier. La campagne de reprise "
            "est datée du 19 octobre 2026 ; elle précède l'ajout de l'authentification physique. "
            "Elle valide le scénario testé et demande une nouvelle recette de bout en bout après intégration.",
            f"Reprise : {duration} s entre detected et recovered, cinq réponses HTTP 503 observées "
            "par les sondes métier, nouvelle transaction conservée et transaction antérieure "
            "préservée. L'attaque était encore active à la reprise. Le client offensif a reçu "
            "87 réponses 401, 153 réponses 503 et 2 210 réponses 403. Ces 153 refus ne sont pas "
            "les cinq refus mesurés par les sondes légitimes.",
            f"ML : {calibration['train_windows']} fenêtres d'apprentissage et "
            f"{calibration['validation_windows']} de validation. Confirmation sans réentraînement : "
            f"{evaluation['true_positive']}/{evaluation['attack_windows']} fenêtres d'attaque détectées, "
            f"{evaluation['false_positive_on_assumed_quiet']}/{evaluation['quiet_windows']} fausses "
            "alertes sur le trafic présumé normal. Fenêtres corrélées et scénario unique : "
            "aucune généralisation à une charge de production.",
            f"Sauvegarde : {backup['live']['transactions']} transactions restaurées en "
            f"{backup['restore_seconds']} s dans une base neuve ; comptage et SHA256 identiques. "
            "Le temps mesuré est celui de la restauration locale d'un petit jeu de données, "
            "pas le délai d'un PRA complet avec redéploiement et basculement.",
            "Reproductibilité : projet Docker isolé, secrets et volumes neufs, cinq contrôles "
            "positifs (secrets, déploiement, idempotence, métier, accès hôte). Durée globale "
            "208,66 s. Second passage Ansible sans changement. Le même moteur Docker a été utilisé ; "
            "le fichier conserve les empreintes de l'instantané testé, qui n'est pas une "
            "certification de toutes les évolutions actuelles.",
            "Sécurité : security.json rapporte huit contrôles positifs, dont refus de paiement "
            "anonyme, non-publication des API internes, blocage d'une sonde SQL par le WAF, "
            "vérification du certificat/nom TLS et protection des points d'accès physiques. "
            "Ces contrôles ciblés ne constituent pas un audit exhaustif. Le contrôle navigateur "
            "enregistré rapporte login, incidents et réponse RAG sans erreur ; il ne prouve "
            "pas le nouveau parcours physique.",
        ],
    ))
    chapters.append((
        "12. Contributions et validations de remise",
        [
            "La contribution attendue de chacun est rendue visible ci-dessous avec ses "
            "livrables vérifiables. Le journal du dépôt précise que le socle, les scripts et "
            "les supports ont été préparés avec l'aide de Codex. Les rôles sont attribués ; "
            "aucune preuve disponible ne permet de certifier un auteur individuel ou une "
            "manipulation personnelle. La validation de chaque membre reste à consigner.",
            "Ethan DIVET - DEV : API de paiement et idempotence, authentification RS256, "
            "dashboard et intégration. Livrables : services/payment/, services/auth/, "
            "apps/dashboard/, tests/. Preuves communes : recovery.json et browser.json. "
            "Validation personnelle : à confirmer par Ethan.",
            "Josselin LENAOUR - INFRA : Docker Compose, Ansible, réseaux, observabilité et "
            "sauvegarde/restauration. Livrables : compose.yaml, infra/, scripts/repro_check.py "
            "et backup_check.py. Preuves communes : reproducibility.json et backup.json. "
            "Validation personnelle : à confirmer par Josselin.",
            "Lucas CHEVALIER - IA/DATA : collecte, calibration OneClassSVM, évaluation et "
            "RAG local. Livrables : services/supervisor/, services/assistant/, scripts/calibrate.py, "
            "confirm_model.py et docs/model-card.md. Preuves communes : calibration.json et "
            "model-evaluation.json. Validation personnelle : à confirmer par Lucas.",
            "Maxime DUSSORT - CYBER : attaque bornée, WAF/SOC, secrets et privilèges de reprise. "
            "Livrables : security/, services/executor/, scripts/security_check.py. Preuve commune : "
            "security.json. Validation personnelle : à confirmer par Maxime.",
            "Jean-christophe MALINUR - TRANSFORMATION : analyse de risques, impact métier, "
            "PCA/PRA, rapprochement NIS2/DORA et recommandations. Livrables : docs/governance.md, "
            "docs/soutenance.md et dossier. Validation personnelle : à confirmer par Jean-christophe.",
            "Au 22 octobre, les sept validations de docs/acceptance.json sont non renseignées : "
            "authentification physique, ESP8266, laboratoire sur deux PC, maîtrise personnelle, "
            "coach, Clip Chrono et acceptation de la dénomination. Pour clore chacune, enregistrer "
            "date, vérificateur, résultat et référence de preuve après exécution. La génération "
            "de ce PDF ne modifie pas ces validations.",
        ],
    ))
    # Keep the numbering stable when chapters are inserted above.
    chapters = [(f"{i + 1}. {title.split('. ', 1)[1]}", paragraphs)
                for i, (title, paragraphs) in enumerate(chapters)]
    output = ROOT / "output" / project["delivery_slug"]
    output.mkdir(parents=True, exist_ok=True)
    pdf = output / (project["delivery_slug"] + "-Dossier.pdf")
    story = []
    markdown = ["# Dossier d'ingénierie et de gouvernance - " + project["team_label"]]
    for index, (title, paragraphs) in enumerate(chapters):
        if index:
            story.append(PageBreak())
        story.append(Paragraph(escape(title), styles["title"]))
        if index == 0:
            story.append(
                Paragraph("RESILIENCE-ALPHA · Workshop EPSI M2 · 22 octobre 2026", styles["small"])
            )
        markdown.append("\n## " + title)
        for paragraph in paragraphs:
            style = styles["small"] if paragraph.startswith("[1]") else styles["body"]
            story.append(Paragraph(escape(paragraph).replace("\n", "<br/>"), style))
            markdown.append("\n" + paragraph)
        if index == 1:
            rows = [
                ["PLAN", "FLUX ET FRONTIÈRES"],
                ["Métier", "Client > WAF HTTP/TLS > Nginx/React > Auth / API > PostgreSQL"],
                ["Observation", "Logs WAF/API > Superviseur + SQLite > Loki ; métriques > Prometheus > Grafana"],
                ["Reprise", "Modèle ML > garde-fous > exécuteur Ansible > politique > API > paiement de preuve"],
                ["Accès physique", "Auth > agent caméra HTTPS hôte ; ESP8266 > WAF > état LED"],
                ["Assistance", "Documents locaux > TF-IDF > Ollama > réponse citée ; aucun droit d'action"],
            ]
            diagram = Table([[Paragraph(escape(cell), styles["small"]) for cell in row]
                             for row in rows], colWidths=[95, 385], hAlign="LEFT")
            diagram.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E4E6F3")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F6F8FC"), colors.white]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.extend([Spacer(1, 8), diagram])
        if title.endswith("Analyse de risques EBIOS RM"):
            rows = [
                ["RISQUE", "G / V initiale", "V résiduelle", "TRAITEMENT / ÉCART"],
                ["Saturation", "3 / 4", "2", "Quarantaine ; source distribuée hors couverture"],
                ["Doublon", "3 / 3", "1", "Idempotence et unicité en base"],
                ["Abus de reprise", "4 / 3", "2", "Clé, CIDR et action bornée"],
                ["Perte d'hôte", "4 / 2", "2", "Copie externe et PRA hors hôte absents"],
                ["Usurpation faciale", "À coter", "Non mesurée", "LBPH sans anti-photo ; recette à réaliser"],
            ]
            risk_table = Table([[Paragraph(escape(cell), styles["small"]) for cell in row]
                                for row in rows], colWidths=[100, 80, 80, 220], hAlign="LEFT")
            risk_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E4E6F3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.extend([Spacer(1, 8), risk_table])
        if index == 0:
            rows = [
                [Paragraph("Membre", styles["small"]), Paragraph("Rôle principal", styles["small"])]
            ]
            rows += [
                [
                    Paragraph(escape(m["name"]), styles["small"]),
                    Paragraph(escape(m["role"]), styles["small"]),
                ]
                for m in project["members"]
            ]
            table = Table(rows, colWidths=[260, 220], hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E4E6F3")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ]
                )
            )
            story.extend([Spacer(1, 8), table])

    def footer(canvas, document):
        canvas.setFont("Body", 8)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(52, 30, "Groupe 3 · Démonstrateur fictif · Validation locale")
        canvas.drawRightString(A4[0] - 52, 30, str(document.page))

    SimpleDocTemplate(
        str(pdf),
        pagesize=A4,
        leftMargin=52,
        rightMargin=52,
        topMargin=48,
        bottomMargin=52,
        title="Resilience Alpha - Dossier d'ingénierie et de gouvernance",
        author="Groupe 3",
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    (output / (project["delivery_slug"] + "-Dossier.md")).write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )
    print(pdf)


if __name__ == "__main__":
    build()
