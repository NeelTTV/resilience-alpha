# Détection ML - contrat à implémenter

Entrées : séries Prometheus (débit, erreurs, latence) et événements Loki.
Enregistrer des fenêtres normales et perturbées avec horodatage et scénario.
Séparer apprentissage et évaluation, conserver les données et paramètres.
Isolation Forest est une première piste à comparer ; aucun modèle n'est encore entraîné.

Sortie proposée vers le moteur de remédiation :
`{incident_id, detected_at, service, model_version, anomaly_score, evidence}`.
La route doit être interne, authentifiée et protégée contre les doublons/rejeux.
Mesurer faux positifs, incidents manqués, délai de détection et dérive du modèle.
Aucun simple seuil de disponibilité ne doit être présenté comme du ML.

