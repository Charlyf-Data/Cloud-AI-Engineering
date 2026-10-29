# Politique de sécurité

## Versions prises en charge

Seule la dernière version publiée (branche `main`, dernier tag `vX.Y.Z`) reçoit des correctifs de sécurité.

| Version | Prise en charge |
|---|---|
| 1.0.x | Oui |
| < 1.0 | Non |

## Signaler une vulnérabilité

**N'ouvrez pas d'issue publique pour une faille de sécurité.**

Utilisez le signalement privé de GitHub : onglet **Security** du dépôt, puis **Report a vulnerability**.
Indiquez :

- la description de la faille et son impact possible ;
- les étapes pour la reproduire (requête, configuration, version) ;
- une proposition de correction, si vous en avez une.

Nous accusons réception sous 7 jours et tenons le rapporteur informé jusqu'à la correction.
La faille est rendue publique seulement après la publication d'un correctif.

## Mesures en place

- **Secrets** : aucun secret dans le code ni dans git ; la configuration passe par des variables d'environnement
  et le fichier `.env`, exclu de git et de l'image Docker.
- **Entrées de l'API** : chaque requête est validée strictement (types, bornes, valeurs autorisées) et les champs
  inconnus sont refusés (code 422). Les erreurs internes ne renvoient aucun détail technique au client.
- **Image Docker** : image `slim` multi-stage, exécutée par un utilisateur non-root, sans les outils de build.
- **Conteneurs** : système de fichiers en lecture seule, aucune capacité Linux, élévation de privilèges interdite,
  mémoire limitée, volume du modèle monté en lecture seule pour l'API.
- **Dépendances** : versions figées dans `requirements.txt` et `requirements-train.txt`.

## Limites connues

- Le modèle est chargé avec `joblib` (pickle) : ne chargez que des artefacts produits par votre propre job
  d'entraînement, jamais un fichier d'origine inconnue.
- L'API n'a pas encore d'authentification : ne l'exposez pas directement sur Internet sans passerelle
  (reverse proxy, API gateway) qui contrôle les accès.
