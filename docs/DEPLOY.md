# VMTips — Deployment Guide

> **Goal:** Publish a Docker image to Docker Hub so you can pull it to any server without auth.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│           GitHub (pexnet/vmtips)            │
│  push to main ──▶ GitHub Actions            │
└─────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│           Docker Hub (pexnet/vmtips)        │
│  Public image: docker.io/pexnet/vmtips      │
│  Tags: latest, <sha>                          │
└─────────────────────────────────────────────┘
                       │
            docker pull pexnet/vmtips:latest
                       │
                       ▼
┌─────────────────────────────────────────────┐
│            Your Production Server            │
│  docker compose -f docker-compose.prod.yml   │
│  volumes: ./data:/data (SQLite persistent) │
└─────────────────────────────────────────────┘
```

---

## 1. Setup (one-time)

### 1.1 Create Docker Hub account and access token

1. Go to https://hub.docker.com/
2. Create a free account if you don't have one
3. Go to **Account Settings → Security → New Access Token**
4. Name: `github-actions-vmtips`, Scope: `Read, Write, Delete`
5. Copy the token

### 1.2 Add secrets to GitHub repo

Go to https://github.com/pexnet/vmtips/settings/secrets/actions

Add:
- `DOCKERHUB_USERNAME` — your Docker Hub username (e.g. `pexnet`)
- `DOCKERHUB_TOKEN` — access token from step 1.1

### 1.3 Optional: Multi-arch build (AMD64 + ARM64)

The workflow already builds for both `linux/amd64` and `linux/arm64` so it works on both x86 servers and Raspberry Pi / ARM VPS.

---

## 2. Build and Push (automatic)

Every push to `main` triggers GitHub Actions which:
1. Builds frontend (React → static files)
2. Copies into backend container
3. Builds multi-arch image
4. Pushes to Docker Hub

You can also trigger manually:
**GitHub → Actions → "Build and Push Docker Image" → Run workflow**

---

## 3. Deploy on Production Server

### 3.1 Copy compose file to server

Copy `docker-compose.prod.yml` to your server:

```bash
scp docker-compose.prod.yml user@your-server:/opt/vmtips/
```

### 3.2 Start the app

```bash
cd /opt/vmtips

# Set secrets
export JWT_SECRET_KEY="replace-this-with-a-long-secure-string"

# Pull latest image and start
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# Verify
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8000/health
```

### 3.3 Update to new version

```bash
cd /opt/vmtips
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### 3.4 Reverse proxy (nginx / Caddy / traefik)

Recommended for HTTPS. Example with Caddy:

```Caddyfile
vmtips.yourdomain.se {
    reverse_proxy localhost:8000
}
```

---

## 4. Local Development

```bash
# Clone repo
git clone https://github.com/pexnet/vmtips.git
cd vmtips

# Start dev environment (backend + frontend hot reload)
./scripts/dev.sh up

# Open:
#   Frontend: http://localhost:5173
#   Backend:  http://localhost:8000
#   API docs: http://localhost:8000/docs

# Common commands:
./scripts/dev.sh down          # stop
./scripts/dev.sh build         # rebuild images
./scripts/dev.sh logs          # follow logs
./scripts/dev.sh db-reset      # reset DB and re-seed
./scripts/dev.sh seed          # seed WC data
```

---

## 5. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:////data/vmtips.db` | SQLite path |
| `JWT_SECRET_KEY` | *(required in prod)* | HMAC key for JWT |
| `JWT_EXPIRATION_HOURS` | `168` (7 days) | JWT lifetime |
| `ADMIN_EMAIL` | `admin@example.com` | Admin user |
| `WORLD_CUP_JSON_URL` | `https://worldcupjson.net/matches` | Match result API |
| `CORS_ORIGINS` | *(empty in prod)* | Allowed frontend origins |

---

## 6. Filesystem (production)

```
/opt/vmtips/
├── docker-compose.prod.yml
└── data/
    └── vmtips.db          ← SQLite (persistent volume)
```

---

## 7. Troubleshooting

| Problem | Solution |
|---|---|
| Image not available | `docker pull pexnet/vmtips:latest` directly on server |
| DB write error | Ensure `/data` is a volume in compose file |
| CORS error | Set `CORS_ORIGINS=https://yourdomain.com` |
| JWT expired | User must log in again (7 day expiry) |
