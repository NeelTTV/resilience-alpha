# Architecture livrée

Client -> WAF ModSecurity/OWASP CRS -> Nginx/React -> auth ou API -> PostgreSQL.
Seul le WAF publie les ports applicatifs HTTP/TLS. Il écrase l'identité source reçue.
JWT RS256 de 15 min : clé privée dans auth, clé publique dans les services lecteurs.
Compte de vérification distinct `recovery-check` et idempotence métier persistante.

Les logs WAF/API sont lus depuis des volumes par le superviseur, enregistrés avec
offsets puis envoyés vers Loki. Prometheus collecte les métriques, Grafana affiche
les sources provisionnées. Le superviseur offre une fonction SOC et conserve les
incidents, preuves et états dans SQLite. Aucune donnée de corps ou de jeton n'est collectée.

Le détecteur charge un OneClassSVM RBF appris sur le trafic normal observé. Un score
anormal sur deux cycles peut créer un incident ; une politique de sécurité réserve
la quarantaine à une source dominante non protégée. Les sources de calibration et
les composants de contrôle sont protégés. Ne jamais calibrer pendant l'attaque.

Le superviseur appelle l'exécuteur sur le réseau control interne avec une clé dédiée.
L'exécuteur valide IP/CIDR/UUID, n'accepte qu'une quarantaine de 300 s et écrit la
politique atomiquement via Ansible. L'API monte cette politique en lecture seule.
Aucun service applicatif ne dispose du socket Docker. Le moteur vérifie un nouveau
paiement à travers le WAF et relit les opérations précédentes avant `recovered`.

Le RAG consulte les fichiers Markdown via TF-IDF et LangChain/ChatOllama. Il ne monte
ni politique ni secret de remédiation. Modèle CPU 0.6B par défaut, allowlist <=8B,
sources citées et mode dégradé explicite.

Limites : un seul hôte, comptes de labo, absence de révocation/MFA, volume local sans
haute disponibilité, sources protégées compromises hors remédiation, scénario à une
source, schéma initialisé par create_all sans migrations. Une quarantaine ne corrige
ni exfiltration ni compromission. Voir `governance.md` pour les risques et le PCA/PRA.

Références techniques : [FastAPI](https://fastapi.tiangolo.com/deployment/docker/),
[scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.svm.OneClassSVM.html),
[CRS](https://github.com/coreruleset/modsecurity-crs-docker),
[Loki](https://grafana.com/docs/loki/latest/reference/loki-http-api/),
[LangChain/Ollama](https://docs.langchain.com/oss/python/integrations/chat/ollama).
