# VMTips Deployment Guide

VMTips ships as a single Docker image. The backend serves the API and the built frontend from the same container.

## Image

The GitHub Actions workflow publishes images to GitHub Container Registry:

```text
ghcr.io/pexnet/vmtips
```

Version tags are created from git tags matching `v*`, and the workflow also publishes `latest`.

## Build And Publish

1. Push a version tag, for example `v1.0.0`, or run the `Build & Deploy` workflow manually.
2. GitHub Actions builds the frontend, copies it into the backend image, and pushes to GHCR.
3. `docker-compose.prod.yml` pulls `ghcr.io/pexnet/vmtips:latest` by default.

The workflow uses the repository `GITHUB_TOKEN`; no Docker Hub secrets are required.

## Server Setup

Copy `docker-compose.prod.yml` to the server:

```bash
scp docker-compose.prod.yml user@your-server:/opt/vmtips/
```

Set required production secrets:

```bash
cd /opt/vmtips
export JWT_SECRET_KEY="replace-this-with-a-long-secure-string"
export ADMIN_EMAIL="admin@yourdomain.example"
export ADMIN_PASSWORD="replace-this-admin-password"
export CORS_ORIGINS="https://vmtips.yourdomain.example"
```

Start the app:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8000/api/health
```

The app listens on port `8000`. Put Caddy, nginx, or another reverse proxy in front of it for HTTPS.

## Updates

```bash
cd /opt/vmtips
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

## Persistent Data

Production compose stores SQLite data in `./data`:

```text
/opt/vmtips/
├── docker-compose.prod.yml
└── data/
    └── vmtips.db
```

Back up `data/vmtips.db` before destructive maintenance or server migration.

## Troubleshooting

| Problem | Check |
|---|---|
| Image not available | Confirm the tag exists in GHCR and the server can pull `ghcr.io/pexnet/vmtips:latest`. |
| Database write errors | Ensure `./data` exists and is writable by Docker. |
| CORS errors | Set `CORS_ORIGINS` to the public frontend origin. |
| Health check fails | Test `curl http://localhost:8000/api/health` on the server. |
