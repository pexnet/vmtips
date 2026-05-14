# VMtips — Deployment Guide

> **Mål:** Publicera en Docker-image på Docker Hub så du kan dra ner den till valfri server utan auth.

---

## Arkitektur

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
│            Din Prod-Server                   │
│  docker compose -f docker-compose.prod.yml   │
│  volumes: ./data:/data (SQLite beständig)    │
└─────────────────────────────────────────────┘
```

---

## 1. Setup (one-time)

### 1.1 Skapa Docker Hub-konto och access token

1. Gå till https://hub.docker.com/
2. Skapa konto (gratis) om du inte har ett
3. Gå till **Account Settings → Security → New Access Token**
4. Namn: `github-actions-vmtips`, Scope: `Read, Write, Delete`
5. Kopiera token

### 1.2 Lägg till secrets i GitHub-repo

Gå till https://github.com/pexnet/vmtips/settings/secrets/actions

Lägg till:
- `DOCKERHUB_USERNAME` — ditt Docker Hub-användarnamn (t.ex. `pexnet`)
- `DOCKERHUB_TOKEN` — access token från steg 1.1

### 1.3 Valfritt: Multi-arch build (AMD64 + ARM64)

Workflowen bygger redan för både `linux/amd64` och `linux/arm64` så det funkar på både x86-servrar och Raspberry Pi / ARM VPS.

---

## 2. Bygg och push (automatiskt)

Varje push till `main` triggar GitHub Actions som:
1. Bygger frontend (React → static files)
2. Kopierar in i backend-container
3. Bygger multi-arch image
4. Pushar till Docker Hub

Du kan även trigga manuellt:
**GitHub → Actions → "Build and Push Docker Image" → Run workflow**

---

## 3. Deploy på prod-server

### 3.1 Skapa compose-fil på servern

Kopiera `docker-compose.prod.yml` till servern:

```bash
scp docker-compose.prod.yml user@din-server:/opt/vmtips/
```

### 3.2 Starta appen

```bash
cd /opt/vmtips

# Sätt hemligheter
export JWT_SECRET_KEY="byt-ut-denna-till-en-lång-och-säker-sträng"

# Dra senaste imagen och starta
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# Verifiera
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8000/health
```

### 3.3 Uppdatera till ny version

```bash
cd /opt/vmtips
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### 3.4 Reverse proxy (nginx / Caddy / traefik)

Rekommenderas för HTTPS. Exempel med Caddy:

```Caddyfile
vmtips.dindomain.se {
    reverse_proxy localhost:8000
}
```

---

## 4. Utveckling lokalt

```bash
# Clone repo
git clone https://github.com/pexnet/vmtips.git
cd vmtips

# Start dev environment (backend + frontend hot reload)
./scripts/dev.sh up

# Öppna:
# Frontend: http://localhost:5173
# Backend:  http://localhost:8000
# API docs: http://localhost:8000/docs

# Vanliga kommandon:
./scripts/dev.sh down          # stoppa
./scripts/dev.sh build         # rebuilda images
./scripts/dev.sh logs          # följ loggar
./scripts/dev.sh db-reset      # nollställ DB och seeda om
./scripts/dev.sh seed          # seed:a VM-data
```

---

## 5. Miljövariabler

| Variabel | Default | Beskrivning |
|---|---|---|
| `DATABASE_URL` | `sqlite:////data/vmtips.db` | SQLite-sökväg |
| `JWT_SECRET_KEY` | *(krävs i prod)* | HMAC-nyckel för JWT |
| `JWT_EXPIRATION_HOURS` | `168` (7 dagar) | JWT-livslängd |
| `ADMIN_EMAIL` | `admin@example.com` | Admin-användare |
| `WORLD_CUP_JSON_URL` | `https://worldcupjson.net/matches` | Matchresultat-API |
| `CORS_ORIGINS` | *(tom i prod)* | Tillåtna frontend-origins |

---

## 6. Filsystem (prod)

```
/opt/vmtips/
├── docker-compose.prod.yml
└── data/
    └── vmtips.db          ← SQLite (beständig volym)
```

---

## 7. Troubleshooting

| Problem | Lösning |
|---|---|
| Image inte tillgänglig | `docker pull pexnet/vmtips:latest` direkt på servern |
| DB-skrivfel | Se till att `/data` är en volym i compose-filen |
| CORS-fel | Sätt `CORS_ORIGINS=https://dindomän.se` |
| JWT-expired | Användaren måste logga in igen (7 dagars expiry) |
