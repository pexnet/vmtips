"""
VMTips backend entrypoint.
Provides a FastAPI application with health check, CORS, and modular routers.
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from database import engine, Base
from config import settings
from routers import auth, matches, predictions, leagues, leaderboard, admin

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="VMTips API",
    description="Backend API for the VMTips World Cup 2026 prediction game.",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}

# API Routers
app.include_router(auth.router)
app.include_router(matches.router)
app.include_router(predictions.router)
app.include_router(leagues.router)
app.include_router(leaderboard.router)
app.include_router(admin.router)

# Static files — served only for non-API paths
API_PREFIXES = (
    "/auth", "/matches", "/predictions", "/leagues",
    "/leaderboard", "/admin", "/health",
)

static_dir = os.getenv("STATIC_DIR", "../frontend/dist")

if os.path.isdir(static_dir):
    @app.get("/{path:path}")
    async def serve_static(path: str):
        if any(path.startswith(p.lstrip("/")) for p in API_PREFIXES):
            raise HTTPException(status_code=404, detail="Not found")
        file_path = os.path.join(static_dir, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Not found")
