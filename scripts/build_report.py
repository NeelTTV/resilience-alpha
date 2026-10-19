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
    if not recovery["passed"]:
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
                "Les rôles ci-dessous sont la répartition choisie à la demande de l'équipe. "
                "Ils ne constituent pas une attestation des contributions effectivement réalisées. "
                "Ces contributions doivent être consignées dans docs/contributions.md. Le numéro "
                "de groupe n'étant pas connu, le nom provisoire de livraison est Équipe DIVET.",
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
                f"La sauvegarde PostgreSQL a été restaurée dans une base neuve en "
                f"{backup['restore_seconds']} secondes sur ce poste. Le test compare le nombre "
                "de transactions et l'empreinte de leur contenu trié. Il supprime uniquement "
                "sa base temporaire et n'écrase pas le métier. Les copies sont locales ; un "
                "PRA perte d'hôte demande une copie externe et un exercice sur un autre poste.",
                "Les secrets sont générés aléatoirement, ignorés par Git et montés seulement "
                "dans les services qui les utilisent. SOPS/age chiffre le bundle partageable, "
                "contrôlé par un déchiffrement identique. La clé age privée reste hors archive. "
                "Le workflow refuse d'écraser des identifiants locaux différents sans traitement "
                "explicite. Les permissions Unix et les ACL Windows doivent être adaptées au poste.",
                "Le WAF est verrouillé par digest et l'application offre TLS avec certificat "
                "de laboratoire. Le groupe doit établir la confiance du certificat et filtrer "
                "le hotspot avant usage. Les services internes ne publient pas de port réseau. "
                "Les limites restent les comptes partagés, l'absence de révocation/MFA, la "
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
                "Les vérifications restantes sont explicites : essai depuis le deuxième PC "
                "physique, contrôle du hotspot/pare-feu et de la confiance TLS, campagne ML "
                "indépendante prolongée, PRA perte d'hôte, journal des contributions et vidéo "
                "continue de soixante secondes. La CI est définie dans le dépôt ; son exécution "
                "distante n'est pas prouvée par une réussite locale.",
                "[1] ANSSI, méthode EBIOS RM : https://cyber.gouv.fr/securisation/analyse-des-risques/"
                "methode-ebios-rm/\n[2] Commission européenne, NIS2 : "
                "https://digital-strategy.ec.europa.eu/en/policies/nis2-directive\n"
                "[3] EIOPA, DORA : https://www.eiopa.europa.eu/digital-operational-resilience-act-dora_en\n"
                "Sources du besoin : sujet national EPSI BAC+5 2026 fourni par l'équipe, "
                "sections 3 à 8, et présentation de workshop. Sources des résultats : "
                "output/evidence/calibration.json, recovery.json et backup.json. Date : 19 octobre 2026.",
            ],
        ),
    ]
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
                Paragraph("RESILIENCE-ALPHA · Workshop EPSI M2 · 19 octobre 2026", styles["small"])
            )
        markdown.append("\n## " + title)
        for paragraph in paragraphs:
            style = styles["small"] if paragraph.startswith("[1]") else styles["body"]
            story.append(Paragraph(escape(paragraph).replace("\n", "<br/>"), style))
            markdown.append("\n" + paragraph)
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
        canvas.drawString(52, 30, "Équipe DIVET · Démonstrateur fictif · Validation locale")
        canvas.drawRightString(A4[0] - 52, 30, str(document.page))

    SimpleDocTemplate(
        str(pdf),
        pagesize=A4,
        leftMargin=52,
        rightMargin=52,
        topMargin=48,
        bottomMargin=52,
        title="Resilience Alpha - Dossier d'ingénierie et de gouvernance",
        author="Équipe DIVET",
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    (output / (project["delivery_slug"] + "-Dossier.md")).write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )
    print(pdf)


if __name__ == "__main__":
    build()
