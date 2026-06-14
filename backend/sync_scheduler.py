"""Background score-sync scheduler for live tournament updates."""
import asyncio
import logging
import os
from contextlib import suppress
from typing import Any, Callable

from config import settings
from database import SessionLocal
from models import SyncConfig
from sync_service import SyncError, sync_match_results

logger = logging.getLogger("vmtips.sync_scheduler")

SessionFactory = Callable[[], Any]


def _effective_sync_config(db) -> tuple[bool, str, int]:
    """Return effective (enabled, source, interval_minutes) for auto sync.

    Production environment variables are allowed to force auto-sync/source even
    when an older persisted sync_config row exists from before live syncing was
    enabled. The DB row still supplies admin-visible interval settings.
    """
    row = db.query(SyncConfig).first()
    if row and row.source != "openfootball":
        row.source = "openfootball"
        db.commit()
    env_enabled = os.environ.get("AUTO_SYNC_ENABLED")
    if env_enabled is not None:
        enabled = env_enabled.strip().lower() in {"1", "true", "yes", "on"}
    else:
        enabled = bool(row.auto_sync_enabled if row else settings.auto_sync_enabled)

    source = os.environ.get("SYNC_SOURCE") or (row.source if row else None) or settings.sync_source or "openfootball"

    interval = row.auto_sync_interval_minutes if row else settings.auto_sync_interval_minutes
    env_interval = os.environ.get("AUTO_SYNC_INTERVAL_MINUTES")
    if env_interval:
        interval = int(env_interval)
    return enabled, source, max(int(interval or 5), 1)


def run_auto_sync_once(session_factory: SessionFactory = SessionLocal) -> dict:
    """Run one auto-sync tick if enabled.

    This is intentionally small and synchronous so it can be tested directly and
    run inside an asyncio.to_thread() call from the background loop.
    """
    db = session_factory()
    should_close = session_factory is SessionLocal
    try:
        enabled, source, interval = _effective_sync_config(db)
        if not enabled:
            return {"ran": False, "reason": "disabled", "interval_minutes": interval, "source": source}
        result = sync_match_results(db, source=source)
        return {"ran": True, "source": source, "interval_minutes": interval, "result": result}
    except SyncError as exc:
        logger.warning("Auto sync failed: %s", exc)
        return {"ran": False, "reason": "sync_error", "error": str(exc)}
    except Exception:
        logger.exception("Unexpected auto sync failure")
        return {"ran": False, "reason": "unexpected_error"}
    finally:
        if should_close:
            db.close()


async def _auto_sync_loop(stop_event: asyncio.Event) -> None:
    """Periodically sync match results until the app shuts down."""
    logger.info("Auto-sync loop started")
    while not stop_event.is_set():
        result = await asyncio.to_thread(run_auto_sync_once)
        logger.info("Auto-sync tick: %s", result)

        interval_minutes = result.get("interval_minutes", settings.auto_sync_interval_minutes) or 5
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=max(int(interval_minutes), 1) * 60)
        except asyncio.TimeoutError:
            continue
    logger.info("Auto-sync loop stopped")


def start_auto_sync(app) -> None:
    """Start the background auto-sync task on a FastAPI app instance."""
    stop_event = asyncio.Event()
    app.state.auto_sync_stop_event = stop_event
    app.state.auto_sync_task = asyncio.create_task(_auto_sync_loop(stop_event))


async def stop_auto_sync(app) -> None:
    """Stop the background auto-sync task if it is running."""
    task = getattr(app.state, "auto_sync_task", None)
    stop_event = getattr(app.state, "auto_sync_stop_event", None)
    if stop_event is not None:
        stop_event.set()
    if task is not None:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
