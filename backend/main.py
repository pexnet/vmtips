"""
VMTips backend entrypoint.
Provides a FastAPI application with health check, CORS, and modular routers.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from config import settings
from routers import auth, matches, predictions, leagues, leaderboard

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="VMTips API",
    description="Backend API for the VMTips World Cup 2026 prediction game.",
    version="0.1.0",
)

# CORS — parse comma-separated origins
def _parse_origins(raw: str) -> list[str]:
    """Split a comma-separated string of origins into a list."""
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_origins(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(matches.router)
app.include_router(predictions.router)
app.include_router(leagues.router)
app.include_router(leaderboard.router)


@app.get("/health")
def health_check() -> dict:
    """Health endpoint used by Docker and load balancers."""
    return {"status": "ok"}


@app.get("/")
def root() -> dict:
    """API root redirecting to documentation."""
    return {
        "message": "Welcome to VMTips API",
        "docs": "/docs",
        "health": "/health",
    }
