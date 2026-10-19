# Modèle de nouveauté du laboratoire

Modèle : OneClassSVM RBF, nu=0,05, gamma=auto, centré sans division par l'écart-type.
Version : empreinte des observations et des paramètres de prétraitement/algorithme.
Fenêtres réelles non vides de 3 s par source. Variables : log(1+débit), ratio d'erreurs,
latence moyenne en secondes, ratio 401. Apprentissage normal, split chronologique.

Le premier prétraitement normalisait chaque variable par sa dispersion. Une faible
dispersion des latences normales amplifiait des variations anodines ; une évaluation
de développement a trouvé 9 alertes sur 13 fenêtres supposées calmes. Ces observations
ont servi à corriger le prétraitement et ne constituent donc pas un test final indépendant.

Le modèle révisé conserve l'échelle physique de latence et les ratios bornés. Il a été
réajusté sur la même période normale initiale, sans utiliser les requêtes offensives.
Une nouvelle attaque et 45 s de trafic normal authentifié ont ensuite confirmé, sur
un petit échantillon : 12/12 fenêtres offensives reconnues, 0 fausse alerte sur 15
fenêtres normales. Voir `output/evidence/model-evaluation.json` et `recovery.json`.
La confirmation a ensuite été prolongée à 180 secondes sans réentraînement :
0 fausse alerte sur 61 fenêtres normales authentifiées. La première confirmation
est conservée dans `model-evaluation-initial.json`, la prolongation dans
`model-evaluation.json`. Le trafic reste celui du laboratoire, sans diversité
de clientèle ni essai multi-jours ; il ne remplace pas une campagne sur charges variées.
Les fenêtres sont corrélées et incluent du trafic déjà mis en quarantaine ; ces
résultats ne prouvent ni un taux général de détection ni une performance industrielle.

L'autorisation de quarantaine reste séparée du score : source dominante unique,
au moins 12 observations, hors sources protégées de calibration et composants de
contrôle. Deux décisions anormales consécutives sont requises. Une source protégée
compromise, un changement d'IP et les attaques distribuées sont des limites explicites.

Les fichiers joblib ne doivent provenir que du processus d'apprentissage de confiance.
La somme SHA256 détecte une incohérence de fichiers, pas un auteur malveillant capable
de remplacer aussi les métadonnées. Aucun téléversement de modèle n'est accepté.
