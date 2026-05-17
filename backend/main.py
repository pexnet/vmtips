"""
VMTips backend entrypoint.
Provides a FastAPI application with health check, CORS, and modular routers.
"""
import os
import time
import uuid
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from database import engine, Base
from config import settings
from rate_limit import limiter
from routers import auth, matches, predictions, leagues, leaderboard, admin, league_bonus_questions, teams, bracket
from errors import AppError
from logging_config import setup_logging, request_id_ctx

# Initialise structured logging as early as possible
setup_logging()
logger = logging.getLogger("vmtips")

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="VMTips API",
    description="Backend API for the VMTips World Cup 2026 prediction game.",
    version="0.1.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ---------------------------------------------------------------------------
# Global exception handlers — every error is returned as {"error": ..., "detail": ...}
# ---------------------------------------------------------------------------

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle typed AppError (and its subclasses) with a consistent body."""
    logger.warning(
        "AppError: %s [%s] %s %s",
        exc.error_code,
        exc.status_code,
        request.method,
        request.url.path,
    )
    body = {"error": exc.error_code, "detail": exc.detail}
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle bare HTTPException — wrap into the same consistent format."""
    logger.warning(
        "HTTPException: %s %s %s",
        exc.status_code,
        request.method,
        request.url.path,
    )
    # Derive a machine-readable error code from the status phrase
    error_code = getattr(exc, "error_code", None) or _status_to_code(exc.status_code)
    body = {"error": error_code, "detail": exc.detail}
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected errors — log at ERROR level, return 500."""
    logger.exception(
        "Unhandled exception on %s %s", request.method, request.url.path
    )
    body = {"error": "internal_error", "detail": "Internal server error"}
    return JSONResponse(status_code=500, content=body)


def _status_to_code(status_code: int) -> str:
    """Derive a snake_case error code from an HTTP status code."""
    _map = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "validation_error",
        429: "rate_limit_exceeded",
        500: "internal_error",
    }
    return _map.get(status_code, f"error_{status_code}")


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log method, path, status code, and duration for every request."""
    rid = request.headers.get("X-Request-ID", str(uuid.uuid4())[:12])
    request_id_ctx.set(rid)

    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    logger.info(
        "%s %s → %s (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    response.headers["X-Request-ID"] = rid
    return response


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0"}

# API Routers
app.include_router(auth.router, prefix="/api")
app.include_router(matches.router, prefix="/api")
app.include_router(predictions.router, prefix="/api")
app.include_router(leagues.router, prefix="/api")
app.include_router(leaderboard.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(league_bonus_questions.router, prefix="/api")
app.include_router(teams.router, prefix="/api")
app.include_router(bracket.router, prefix="/api")

# Static files — serve SPA index.html for all non-API, non-health paths
API_PREFIXES = (
    "api", "health",
)

static_dir = os.getenv("STATIC_DIR", "../frontend/dist")

if os.path.isdir(static_dir):
    @app.get("/{path:path}")
    async def serve_static(path: str):
        # API routes should be handled by routers, not static files
        if any(path.startswith(p) for p in API_PREFIXES):
            raise HTTPException(status_code=404, detail="Not found")
        file_path = os.path.join(static_dir, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Not found")