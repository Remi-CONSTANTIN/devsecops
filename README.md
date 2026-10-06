# Mini Kanban DevSecOps

Petit Kanban Flask/SQLite réalisé pour un TP DevSecOps de deux jours.

## Ce qui est livré

- Trois colonnes, création et déplacement de cartes, stockage SQLite.
- Une CI qui lance tests, Gitleaks, Bandit, Semgrep, CodeQL, pip-audit et Trivy.
- Sur `main`, l'image est scannée, publiée dans GHCR et signée avec Cosign/OIDC.
- Le runner local vérifie la signature par digest, déploie, vérifie `/health` et lance OWASP ZAP.

Liens : [CI](https://github.com/Remi-CONSTANTIN/devsecops/actions/workflows/main.yml) · [déploiement](https://github.com/Remi-CONSTANTIN/devsecops/actions/workflows/deploy.yml) · [modèle de menace](docs/threat-model.md).

`main` est protégée : pas de push direct, de force-push ni de suppression. Les changements passent par PR. Les workflows et `CODEOWNERS` demandent une validation dédiée. L'auto-merge externe est limité aux fichiers applicatifs ; les workflows, Docker, dépendances et règles de sécurité restent exclus.

## Retour d'expérience GitLab

La [MR !3](https://gitlab.com/parthenox-group/jellyfin-secure-delivery/-/merge_requests/3) montre qu'une seule MR sans modification du code applicatif peut neutraliser quatre gates : Gitleaks, Semgrep, Trivy filesystem et Trivy image. Les scanners lisaient leur configuration depuis la branche auditée : une allowlist globale Gitleaks, un `.semgrepignore` à `*`, 94 CVE ignorées par Trivy et deux règles de secrets désactivées suffisaient à rendre les jobs verts.

La MR ajoute alors un manifeste avec clé privée et identifiants de production sans alerte. Les vérifications ont aussi relevé une clé déjà présente dans `config.env`, huit CVE HIGH Python, une image root et un conteneur privilégié. Le correctif est de fournir la configuration des scanners depuis la CI, de protéger ces fichiers avec CODEOWNERS et approbations, d'activer `only_allow_merge_if_pipeline_succeeds` et de remettre le scan de manifestes Trivy.

## Lancer localement

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
PYTHONPATH=. .venv/bin/pytest tests/ -q
.venv/bin/gunicorn --bind 127.0.0.1:8000 app:app
```

L'application écoute sur `http://127.0.0.1:8000`.

## Lancer avec Docker

```bash
docker build -t mini-kanban .
docker run --rm -p 8000:8000 --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=16m \
  --cap-drop ALL --security-opt no-new-privileges:true \
  -v mini-kanban-data:/app/instance mini-kanban
```

Le port `8000` est exposé pour le TP. Il faut un reverse proxy TLS et un filtrage réseau pour une exposition réelle.
