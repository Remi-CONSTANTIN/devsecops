# Mini Kanban DevSecOps

Application Kanban minimale réalisée pour un TP DevSecOps de deux jours.

## Rendu du TP

Le code, la configuration et ce court compte rendu sont dans ce dépôt : [Remi-CONSTANTIN/devsecops](https://github.com/Remi-CONSTANTIN/devsecops).

- La [pipeline CI](https://github.com/Remi-CONSTANTIN/devsecops/actions/workflows/main.yml) lance les tests et les contrôles de sécurité, puis construit et publie l'image si la branche est `main`.
- La [pipeline de déploiement](https://github.com/Remi-CONSTANTIN/devsecops/actions/workflows/deploy.yml) récupère cette image, la vérifie et la déploie localement. Elle lance aussi un contrôle de santé et un scan OWASP ZAP.
- Les SBOM et les rapports de scan restent disponibles dans les artefacts GitHub Actions. Le [modèle de menace](docs/threat-model.md) explique les choix et ce qu'ils ne couvrent pas.

L'application est volontairement simple : Flask, SQLite et Docker. L'idée du TP était surtout de sécuriser ce qui l'entoure. Chaque pull request passe par les tests, Gitleaks, Bandit, Semgrep, CodeQL, l'audit des dépendances et les scans de configuration. Sur `main`, l'image est scannée, envoyée dans GHCR et signée avec Cosign via OIDC. Le runner de déploiement n'accepte ensuite qu'une image signée et identifiée par son digest, pas un tag que quelqu'un pourrait déplacer.

### Règles de travail

`main` est protégée : pas de push direct, pas de force-push et pas de suppression. Les changements passent par une pull request et les contrôles doivent réussir avant intégration.

Les fichiers de workflow et `CODEOWNERS` sont traités à part. Seuls les collaborateurs prévus peuvent les valider. Une contribution externe peut proposer du code applicatif, mais elle ne peut pas faire tourner un workflow qu'elle a elle-même modifié avec des droits d'écriture ou sur le runner local.

Les PR internes passent en squash merge automatiquement quand les contrôles sont verts. Pour un fork, l'auto-merge est plus limité : un workflow de confiance, défini sur `main`, vérifie que seuls `app.py`, `templates/**`, `static/**` ou `tests/**` ont changé. Les dépendances, Docker, les workflows et les règles de sécurité restent exclus. Les permissions GitHub Actions sont en lecture par défaut ; les droits d'écriture sont donnés uniquement au job qui en a besoin.

Ce montage réduit les risques, mais il ne transforme pas un scan en revue humaine. Les outils détectent bien des secrets, dépendances vulnérables ou appels suspects. Ils ne savent pas toujours déterminer si une modification apparemment normale cache une mauvaise intention. Le runner séparé et la vérification de signature limitent les conséquences, mais ce déploiement sur le port `8000` reste une démonstration de TP, pas une configuration de production.

### Retour d'expérience GitLab : quatre gates contournés par leur configuration

Le test est documenté dans la [MR GitLab !3](https://gitlab.com/parthenox-group/jellyfin-secure-delivery/-/merge_requests/3). Une seule MR, sans modification du code applicatif, a suffi à neutraliser quatre contrôles : Gitleaks, Semgrep, Trivy filesystem et Trivy image.

Le problème est simple : les jobs prennent leurs fichiers de configuration dans la branche qu'ils sont censés auditer. La MR ajoute donc `.gitleaks.toml` avec une allowlist globale, `.semgrepignore` avec `*`, `.trivyignore` qui ignore 94 CVE et `trivy-secret.yaml` qui désactive deux règles de secrets. Les quatre jobs passent alors au vert. Dans le même temps, la charge de démonstration `k8s/db-credentials.yaml`, contenant une clé privée et des identifiants de production, n'est plus signalée.

Le rejet des résultats est parlant : sans ces fichiers, Gitleaks détecte les clés privées, Semgrep retourne six findings et Trivy échoue sur les vulnérabilités et secrets. Avec eux, les mêmes commandes renvoient un succès. Le dépôt contenait aussi déjà une clé privée dans `config.env`, huit vulnérabilités HIGH dans les dépendances Python, une image exécutée en root et un conteneur Kubernetes privilégié. Le renommage du job `trivy-iac` en `trivy-fs` avait par ailleurs fait disparaître le scan de configuration sans faire échouer la pipeline.

La correction est de sortir la configuration des scanners de la branche auditée : la CI doit fournir ses propres fichiers de règles et d'exclusion. Les fichiers `*.toml`, `.*ignore` et `trivy-*.yaml` doivent aussi être protégés par `CODEOWNERS` et approbation obligatoire. Enfin, GitLab doit activer `only_allow_merge_if_pipeline_succeeds`, aujourd'hui désactivé sur ce projet, et comparer les exclusions présentes dans le dépôt à une baseline signée. Il faut aussi remettre un scan de manifestes avec `trivy config` ou `trivy fs --scanners misconfig`.

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
