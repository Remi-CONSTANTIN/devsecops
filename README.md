# Mini Kanban DevSecOps

Application Kanban minimale réalisée pour un TP DevSecOps de deux jours.

## Rendu TP — synthèse

- **Dépôt de code et rapport :** [Remi-CONSTANTIN/devsecops](https://github.com/Remi-CONSTANTIN/devsecops). Ce README constitue le rapport court demandé ; le [modèle de menace](docs/threat-model.md) complète les hypothèses et limites.
- **CI sécurité / publication :** [workflow DevSecOps](https://github.com/Remi-CONSTANTIN/devsecops/actions/workflows/main.yml).
- **CD locale / DAST :** [workflow de déploiement](https://github.com/Remi-CONSTANTIN/devsecops/actions/workflows/deploy.yml). Les SBOM et rapports de scans sont publiés comme artefacts des exécutions GitHub Actions.

Le projet livre une application Flask/SQLite conteneurisée. Toute contribution passe d'abord par la CI : tests, détection de secrets, SAST (Bandit, Semgrep et CodeQL), audit de dépendances, scan de configuration et génération de SBOM. Sur `main`, l'image est construite, scannée, publiée dans GHCR puis signée avec Cosign/OIDC. Le runner auto-hébergé ne reçoit que cette image signée, référencée par digest immuable ; il vérifie la signature, déploie, contrôle `/health` puis lance OWASP ZAP.

### Règles Git et workflows de travail

- `main` est protégée : passage par pull request et contrôles CI requis avant intégration ; les pushes directs, la suppression et le force-push sont bloqués.
- Les workflows et `CODEOWNERS` sont des chemins sensibles détenus par les collaborateurs désignés. Une contribution externe peut proposer du code, mais ne doit pas faire exécuter un workflow qu'elle contrôle avec des privilèges d'écriture ou l'accès au runner local.
- Les PR internes peuvent être fusionnées automatiquement en squash après succès des contrôles. Les PR provenant d'un fork ne sont éligibles à l'auto-merge que depuis un workflow de confiance défini sur `main`, et uniquement si elles ne modifient que `app.py`, `templates/**`, `static/**` ou `tests/**` ; les workflows, dépendances, Docker et la politique de sécurité sont exclus.
- Les permissions GitHub Actions suivent le moindre privilège : lecture par défaut ; écriture de paquet et jeton OIDC uniquement pour la publication/signature, écriture de PR uniquement pour l'auto-merge.

**Limite assumée du TP :** des contrôles automatisés réduisent le risque mais ne prouvent pas l'intention métier d'un changement. La revue des chemins sensibles, l'isolation du runner et la vérification de signature restent nécessaires ; le service exposé sur le port `8000` n'est pas une configuration de production.

## Fonctions

- Trois colonnes : **À faire**, **En cours**, **Terminé**.
- Création de cartes avec titre et description.
- Déplacement d'une carte entre les colonnes.
- Persistance dans une base **SQLite** locale (`instance/kanban.db`).
- Endpoint de santé : `GET /health`.

## Stack

- **Flask** et **Jinja** : application web monolithique.
- **Flask-SQLAlchemy / SQLite** : persistance locale.
- **Gunicorn** : serveur WSGI du conteneur ; Flask n'est pas exécuté avec son serveur de développement.
- **Docker** : image non-root avec filesystem en lecture seule au runtime.
- **GitHub-hosted runners** : contrôles CI, build, scan, SBOM, publication et signature.
- **Runner auto-hébergé isolé** : vérification de signature, déploiement local, healthcheck et DAST.

## Lancer localement

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
PYTHONPATH=. .venv/bin/pytest tests/ -q
.venv/bin/gunicorn --bind 127.0.0.1:8000 app:app
```

L'application écoute alors sur `http://127.0.0.1:8000`.

## Lancer avec Docker

```bash
docker build -t mini-kanban .
docker run --rm -p 8000:8000 --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=16m \
  --cap-drop ALL --security-opt no-new-privileges:true \
  -v mini-kanban-data:/app/instance mini-kanban
```

La base SQLite est conservée dans le volume `/app/instance`.

## Chaîne DevSecOps

| Étape | Contrôle | Outil | Décision automatisée |
|---|---|---|---|
| Commit / PR | Recherche de secrets | Gitleaks | échec si secret détecté |
| Commit / PR | SAST Python | Bandit | échec si finding non justifié |
| Commit / PR | SAST générique | Semgrep | échec sur finding bloquant |
| Commit / PR | SCA | pip-audit | échec sur dépendance vulnérable connue |
| Commit / PR | SBOM Python | pip-audit CycloneDX | artifact GitHub Actions |
| Commit / PR | IaC/configuration | Trivy config sur Dockerfile et Compose | échec sur finding critique |
| Après build | Scan d'image | Trivy image | blocage des CVE critiques corrigées |
| Après build | SBOM d'image | Trivy CycloneDX | artifact GitHub Actions |
| Après build | Intégrité/provenance | Cosign avec OIDC GitHub | signature et vérification requises |
| Après déploiement | DAST | OWASP ZAP baseline | rapport conservé comme artifact |

L'image candidate est publiée dans GitHub Container Registry, signée avec une identité OIDC GitHub, puis déployée par **digest** (`@sha256:...`) après vérification de signature. Un tag Git est lisible, mais le digest est l'identifiant immuable effectivement déployé.

Les contrôles CI et la construction d'image utilisent des runners GitHub hébergés. Le runner local n'est sollicité qu'après succès du pipeline sur `main`, pour les opérations qui nécessitent réellement son Docker local et l'application en cours d'exécution.

## Limites de lab

- Le runner auto-hébergé accède au socket Docker pour ce déploiement : il doit rester isolé, réservé au dépôt et ne pas exécuter de code issu de forks non approuvés.
- Le port `8000` est intentionnellement exposé sur `0.0.0.0` pour le TP. Il faudrait un reverse proxy TLS et un filtrage réseau pour une exposition de production.
- L'application ne contient aucune authentification : ne pas y stocker de données sensibles.

Le modèle de menace et les décisions de sécurité sont détaillés dans [`docs/threat-model.md`](docs/threat-model.md).
