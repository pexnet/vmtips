# ⚽ VMTips

A full-stack football prediction game for the FIFA World Cup 2026.

**Backend:** FastAPI + SQLAlchemy + SQLite + JWT auth
**Frontend:** Vite + React + TypeScript + MUI v9 + react-i18next

## Quick Start

### Development (no Docker)

```bash
# Backend
cd backend
uv sync
uv run uvicorn main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Docker Production

Prerequisites: Docker and Docker Compose installed.

```bash
# Start everything (single container on port 8000)
./scripts/dev.sh up

# Or with docker compose directly
docker compose up --build
```

Then open **http://localhost:8000**

### Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `JWT_SECRET_KEY` | `change-me-in-production` | **Yes** | JWT signing secret — **change this** |
| `ADMIN_EMAIL` | `admin@example.com` | Required in prod | Admin account email. Production startup rejects the default. |
| `ADMIN_PASSWORD` | `admin` | Required in prod | Admin password. Production startup rejects `admin` and `change-me-in-production`. |
| `CORS_ORIGINS` | `http://localhost:8000` | No | Comma-separated allowed origins |
| `DATABASE_URL` | `sqlite:///app/data/vmtips.db` | No | SQLite database path |

Set them in a `.env` file or pass directly:

```bash
JWT_SECRET_KEY=my-secret-key docker compose up --build
```

For production, store `JWT_SECRET_KEY`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` in your secret manager or deployment environment, not in source control. To rotate secrets, replace the deployment secret, restart the service, then update or remove any old admin credentials in the database so the previous password can no longer authenticate.

## Features

- Predict all 104 World Cup 2026 matches (72 group stage + 32 knockout)
- FIFA World Cup 2026 format support: 12 groups, 8 best third-place teams, Round of 32 bracket, and Annex C third-place placement
- Tournament bonus questions (winner, top scorer, top assist, total goals)
- Private leagues with invite codes
- Live leaderboard (global, per-league, personal)
- Match dates displayed and predictions auto-lock after kickoff
- Admin panel for result entry and score recalculation
- Dual themes (light/dark) and bilingual UI (Swedish/English)

### Development Commands

```bash
./scripts/dev.sh up        # Start app
./scripts/dev.sh down      # Stop app
./scripts/dev.sh build     # Rebuild image
./scripts/dev.sh logs      # View logs
./scripts/dev.sh shell     # Shell into container
./scripts/dev.sh seed      # Run database seed
./scripts/dev.sh db-reset  # Reset database
```

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.11, FastAPI, SQLAlchemy, PyJWT, pytest |
| Frontend | React 19, TypeScript, Vite, MUI v9, react-i18next |
| Infra | Docker, docker-compose, GitHub Actions |

## Project Structure

```
vmtips/
├── backend/          FastAPI app
│   ├── routers/      API endpoints
│   ├── models.py     SQLAlchemy ORM
│   ├── seed.py       World Cup 2026 teams and fixtures
│   ├── fifa_standings.py
│   ├── bracket_engine.py
│   ├── third_place_table.py
│   └── tests/        pytest suite
├── frontend/         React SPA
│   ├── src/pages/    Route components
│   ├── src/locales/  i18n translations
│   └── src/api/      Axios client
├── Dockerfile        Multi-stage build
├── docker-compose.yml
└── scripts/
    └── dev.sh        Development helper
```

## Documentation

- [Scoring rules](docs/SCORING_RULES.md)
- [World Cup 2026 bracket implementation](docs/WC2026_BRACKET.md)
- [Third-place Annex C mapping](docs/WC2026_THIRD_PLACE_COMBINATIONS.md)
- [Deployment guide](docs/DEPLOY.md)

## CI/CD

- **CI:** Backend tests + frontend build on every push/PR
- **Docker:** Image built and pushed to `ghcr.io/pexnet/vmtips` on version tags

## License

MIT
