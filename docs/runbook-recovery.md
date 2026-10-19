# Procédure de reprise après saturation applicative

## Vérifier une reprise après quarantaine

La quarantaine bloque pendant 300 secondes l'adresse IP source dans la politique
d'admission de l'API. Le détecteur utilise un OneClassSVM entraîné sur les métadonnées
HTTP normales du laboratoire. Le quota de capacité à 20 requêtes par seconde est une
limite de ressource, distincte du modèle de détection.

Le moteur appelle un exécuteur Ansible interne, authentifié et limité à l'action
`quarantine_source`. Le playbook publie atomiquement `/policy/blocks.json`. Aucun
redémarrage de conteneur n'est nécessaire et aucune transaction n'est supprimée.

Après l'action, le moteur se connecte comme `recovery-check` à travers le WAF et le
proxy. Il relit jusqu'à 20 de ses transactions précédentes, crée une nouvelle
transaction fictive de 101 centimes EUR avec une nouvelle clé d'idempotence, puis
relit l'historique. Il vérifie que la nouvelle transaction est enregistrée et que
les montants, devises et états précédents sont inchangés. Cinq tentatives au maximum
sont autorisées. Une vérification réussie produit `recovered` et l'identifiant de
la nouvelle transaction dans la chronologie.

La preuve complémentaire `scripts/demo.py` contrôle la préservation d'une transaction
opérateur créée avant l'attaque et la disponibilité alors que le trafic offensif
continue. Une IP bloquée reçoit HTTP 403 ; une capacité épuisée donne HTTP 503.

## Si la reprise échoue

L'état `failed` est conservé avec la catégorie d'erreur. Consulter la chronologie
et les journaux ; ne pas corriger silencieusement le système pendant une démo
annoncée comme autonome. Vérifier le réseau, le modèle, l'exécuteur, la politique
et les identifiants de vérification. Refaire ensuite une recette distincte.

## Limites

La preuve concerne le scénario de quota partagé. La quarantaine ne corrige ni une
exfiltration, ni une attaque distribuée, ni une compromission de la base. Des clients
derrière le même NAT peuvent être bloqués ensemble. Les quarantaines expirent au
bout de cinq minutes. Le RAG lit les procédures et n'exécute aucune action.
