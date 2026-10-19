# Détection ML

Implémentation : `services/supervisor/model.py`, boucle `services/supervisor/main.py`.
Calibration : `scripts/calibrate.py --seconds 75`, uniquement sans attaque.
Fenêtres réelles par source, StandardScaler + OneClassSVM RBF, split chronologique
et frontière calibrée sur données normales. Deux décisions anormales sont requises.
La politique de sécurité protège les sources normales de calibration et les composants
de contrôle. Les métriques de calibration ne remplacent pas une évaluation indépendante.
