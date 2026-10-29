# Contribuer

Merci de contribuer au projet. Ce guide décrit le modèle de branches, les conventions et la procédure de revue.
En participant, vous acceptez de respecter le [code de conduite](CODE_OF_CONDUCT.md).

## Modèle de branches : GitFlow

| Branche | Rôle | Créée depuis | Fusionnée dans |
|---|---|---|---|
| `main` | Code en production ; chaque commit est une version taguée | — | — |
| `develop` | Intégration des fonctionnalités terminées | `main` | — |
| `feature/<sujet>` | Une fonctionnalité ou une évolution | `develop` | `develop` |
| `release/<version>` | Préparation d'une version (corrections mineures, numéro de version) | `develop` | `main` et `develop` |
| `hotfix/<version>` | Correction urgente de la production | `main` | `main` et `develop` |

On ne pousse jamais directement sur `main` ni sur `develop` : tout passe par une pull request.

### Développer une fonctionnalité

```bash
git checkout develop
git pull
git checkout -b feature/batch-predictions
# ... commits ...
git push -u origin feature/batch-predictions
# puis ouvrir une pull request vers develop
```

### Publier une version

```bash
git checkout -b release/1.1.0 develop
# mettre à jour MODEL_VERSION / la version, corriger les derniers détails
# pull request vers main, puis fusion
git checkout main && git pull
git tag -a v1.1.0 -m "Version 1.1.0"
git push origin v1.1.0
# fusionner aussi release/1.1.0 dans develop
```

La publication d'une release GitHub sur le tag déclenche la construction de l'image Docker.

## Conventions

- **Messages de commit** : [Conventional Commits](https://www.conventionalcommits.org/fr/), par exemple
  `feat: ajoute la prédiction batch`, `fix: corrige le code 404 des commandes`, `docs: complète le README`.
- **Versions** : [SemVer](https://semver.org/lang/fr/) (`MAJEUR.MINEUR.CORRECTIF`), tags préfixés par `v`.
- **Code** : Python 3.11, typage complet, docstrings, une responsabilité par classe (SOLID).
  Aucune valeur en dur : les paramètres passent par `config.py` et les variables d'environnement.
- **Contrat d'API** : toute modification d'endpoint doit rester conforme à `Start/openapi.yml`.
- **Secrets** : jamais dans le code ni dans git ; utiliser `.env` (ignoré) ou les secrets GitHub.

## Avant d'ouvrir une pull request

1. L'application démarre : `docker compose up -d --build` puis `docker compose ps` affiche `api` en `healthy`.
2. Les tests et le lint passent : `pip install -r requirements-dev.txt`, puis `pytest` et `pylint src`.
   La CI GitHub Actions les relance sur chaque pull request.
3. La documentation est à jour (README, `.env.example` si une variable est ajoutée).
4. La pull request décrit le changement, sa raison et la façon de le tester.

Une pull request est fusionnée après au moins une relecture approuvée et des vérifications automatiques au vert.

## Signaler un bug ou proposer une idée

Ouvrez une issue GitHub avec le contexte, les étapes pour reproduire, le résultat attendu et le résultat obtenu.
Pour une faille de sécurité, n'ouvrez pas d'issue publique : suivez [SECURITY.md](SECURITY.md).
