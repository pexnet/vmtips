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

Recommended production layout:

```text
/opt/apps/
├── reverse-proxy/
│   ├── docker-compose.yml
│   └── Caddyfile
└── vmtips/
    ├── docker-compose.prod.yml
    ├── .env
    └── data/
        ├── start_users.json
        └── vmtips.db
```

Copy `docker-compose.prod.yml` to the server:

```bash
ssh deploy@your-server 'mkdir -p /opt/apps/vmtips/data'
scp docker-compose.prod.yml deploy@your-server:/opt/apps/vmtips/
scp backend/data/start_users.example.json deploy@your-server:/opt/apps/vmtips/data/start_users.json
```

Create `/opt/apps/vmtips/.env` on the server:

```bash
cd /opt/apps/vmtips
umask 077
cat > .env <<'EOF'
JWT_SECRET_KEY=replace-this-with-output-from-openssl-rand-hex-32
ADMIN_EMAIL=admin@yourdomain.example
ADMIN_PASSWORD=replace-this-admin-password
CORS_ORIGINS=https://vmtips.duckdns.org
EOF
```

Generate a strong JWT secret with:

```bash
openssl rand -hex 32
```

Create the private initial-user file before first startup:

```bash
chmod 600 /opt/apps/vmtips/.env
chmod 600 /opt/apps/vmtips/data/start_users.json
```

Replace every example password. The file is gitignored and appears inside the
production container as `/data/start_users.json`. It is only used to create
missing accounts; editing it later does not reset existing passwords.

Start the app:

```bash
cd /opt/apps/vmtips
docker compose --env-file .env -f docker-compose.prod.yml pull
docker compose --env-file .env -f docker-compose.prod.yml up -d
docker compose --env-file .env -f docker-compose.prod.yml ps
curl http://127.0.0.1:8000/api/health
```

Production compose binds the app to `127.0.0.1:8000`, so it is not directly
reachable from the public internet. Put Caddy, nginx, or another reverse proxy
in front of it for HTTPS.

## Caddy HTTPS Reverse Proxy

Create `/opt/apps/reverse-proxy/docker-compose.yml`:

```yaml
services:
  caddy:
    image: caddy:2
    container_name: caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config

volumes:
  caddy_data:
  caddy_config:
```

Create `/opt/apps/reverse-proxy/Caddyfile`:

```caddyfile
{
    email admin@yourdomain.example
}

vmtips.duckdns.org {
    reverse_proxy 127.0.0.1:8000
}
```

Start Caddy:

```bash
cd /opt/apps/reverse-proxy
docker compose up -d
docker compose ps
```

Verify HTTPS:

```bash
curl -I https://vmtips.duckdns.org/api/health
```

## Updates

```bash
cd /opt/apps/vmtips
docker compose --env-file .env -f docker-compose.prod.yml pull
docker compose --env-file .env -f docker-compose.prod.yml up -d
docker compose --env-file .env -f docker-compose.prod.yml ps
curl http://127.0.0.1:8000/api/health
```

## Persistent Data

Production compose stores SQLite data in `./data`:

```text
/opt/apps/vmtips/
├── docker-compose.prod.yml
├── .env
└── data/
    └── vmtips.db
```

Back up `data/vmtips.db`, `data/start_users.json`, and `.env` before destructive
maintenance or server migration.

## Troubleshooting

| Problem | Check |
|---|---|
| Image not available | Confirm the tag exists in GHCR and the server can pull `ghcr.io/pexnet/vmtips:latest`. |
| Database write errors | Ensure `./data` exists and is writable by Docker. |
| CORS errors | Set `CORS_ORIGINS` to the public frontend origin. |
| Health check fails | Test `curl http://127.0.0.1:8000/api/health` on the server. |
