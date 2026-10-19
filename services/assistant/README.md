# Assistant RAG - à implémenter

Profil Compose `ai` : serveur Ollama local. Aucun modèle téléchargé automatiquement.
Choix initial proposé : `qwen3:4b` (4 milliards de paramètres ; budget <= 8B).
Après démarrage : `docker compose exec ollama ollama pull qwen3:4b`.

Construire le service LangChain de recherche sur `docs/`, retourner des citations,
gérer l'absence de source et les documents non fiables. Mesurer la pertinence sur un
jeu de questions. Aucun accès d'administration, aucun secret dans les documents indexés.
Le RAG assiste l'opérateur ; il ne décide ni n'exécute la remédiation.

