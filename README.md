# ⚽ VMTips

A full-stack football prediction game for the FIFA World Cup 2026.

**Backend:** FastAPI + SQLAlchemy + SQLite + JWT auth
**Frontend:** Vite + React + TypeScript + MUI v9 + react-i18next

## Quick Start

### Development

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

```bash
docker compose up --build
```

## Features

- Predict all 104 World Cup 2026 matches (72 group stage + 32 knockout)
- Tournament bonus questions (winner, top scorer, top assist, total goals)
- Private leagues with invite codes
- Live leaderboard (global, per-league, personal)
- Match dates displayed and predictions auto-lock after kickoff
- Admin panel for result entry and score recalculation
- Dual themes (light/dark) and bilingual UI (Swedish/English)

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.11, FastAPI, SQLAlchemy, PyJWT, pytest |
| Frontend | React 19, TypeScript, Vite, MUI v9, react-i18next |
| Infra | Docker, docker-compose |

## Project Structure

```
vmtips/
├── backend/          FastAPI app
│   ├── routers/      API endpoints
│   ├── models.py     SQLAlchemy ORM
│   ├── seed.py       World Cup 2026 data
│   └── tests/        pytest suite (67 tests)
├── frontend/         React SPA
│   ├── src/pages/    Route components
│   ├── src/locales/  i18n translations
│   └── src/api/      Axios client
├── Dockerfile        Multi-stage build
└── docker-compose.yml
```

## Deployment Checklist

1. Set `SECRET_KEY` environment variable
2. Configure `CORS_ORIGINS` for your domain
3. Run `docker compose up --build`
4. Visit `http://localhost:8000`

## License

MIT
