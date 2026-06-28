"""
Sync service: fetch match results from the openfootball 2026 GitHub JSON and
update the local database.

The stale worldcupjson.net path was removed because it returned 2022 data.
"""
import json
import logging
import os
import urllib.request
import urllib.error
from typing import Optional

from config import settings
from models import SyncConfig

logger = logging.getLogger("vmtips.sync")

REQUEST_TIMEOUT = 15
DEFAULT_OPENFOOTBALL_URL = (
    "https://raw.githubusercontent.com/openfootball/worldcup.json/refs/heads/master/2026/worldcup.json"
)


class SyncError(Exception):
    """Raised when the external sync fails."""
    pass


# ───────────────────────────────────────────────────────────────
# High-level helpers
# ───────────────────────────────────────────────────────────────

def _fetch_json(url: str) -> dict | list:
    """Fetch raw JSON from a URL."""
    logger.info("Fetching from %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": "VMTips/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        logger.error("HTTP %s from %s", exc.code, url)
        raise SyncError(f"HTTP error {exc.code}") from exc
    except urllib.error.URLError as exc:
        logger.error("Cannot reach %s: %s", url, exc.reason)
        raise SyncError(f"Cannot reach {url}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON from %s: %s", url, exc)
        raise SyncError("Invalid JSON") from exc


def _normalize_status(api_status: str) -> str:
    """Map external API status values to our internal status strings."""
    status_map = {
        "scheduled": "scheduled",
        "future": "scheduled",
        "in_play": "ongoing",
        "in_progress": "ongoing",
        "live": "ongoing",
        "paused": "ongoing",
        "half_time": "ongoing",
        "finished": "finished",
        "completed": "finished",
        "completed_after_extra_time": "finished",
        "completed_after_penalties": "finished",
    }
    return status_map.get(api_status.lower(), "scheduled")


def _parse_goals(score_data) -> Optional[int]:
    """Safely extract a goal count from various API score formats."""
    if score_data is None:
        return None
    if isinstance(score_data, int):
        return score_data
    if isinstance(score_data, dict):
        return score_data.get("full_time", score_data.get("goals", None))
    if isinstance(score_data, (list, tuple)) and score_data:
        try:
            return int(score_data[0])
        except (ValueError, TypeError):
            return None
    try:
        return int(score_data)
    except (ValueError, TypeError):
        return None


def _parse_openfootball_score_pair(score_data) -> tuple[Optional[int], Optional[int]]:
    """Extract full-time goals from openfootball's score shape."""
    if not isinstance(score_data, dict):
        return None, None
    full_time = score_data.get("ft") or score_data.get("full_time")
    if isinstance(full_time, (list, tuple)) and len(full_time) >= 2:
        return _parse_goals(full_time[0]), _parse_goals(full_time[1])
    if isinstance(full_time, dict):
        return _parse_goals(full_time.get("home")), _parse_goals(full_time.get("away"))
    return None, None


# ───────────────────────────────────────────────────────────────
# Source parsers
# ───────────────────────────────────────────────────────────────

def _parse_openfootball_match(raw: dict) -> Optional[dict]:
    """Parse an openfootball JSON match entry into normalised form."""
    # 2026 openfootball rows are ordered 1..104 but group-stage rows may omit
    # explicit `num`; _fetch_openfootball injects __match_number from file order.
    match_number = raw.get("num") or raw.get("match_number") or raw.get("__match_number")
    if match_number is not None:
        try:
            match_number = int(match_number)
        except (ValueError, TypeError):
            match_number = None

    if match_number is None:
        return None

    home_name = raw.get("team1") or raw.get("home_team") or raw.get("homeTeam") or ""
    away_name = raw.get("team2") or raw.get("away_team") or raw.get("awayTeam") or ""

    score_home, score_away = _parse_openfootball_score_pair(raw.get("score"))
    home_goals = score_home
    away_goals = score_away
    if home_goals is None:
        home_goals = _parse_goals(raw.get("goals1") or raw.get("home_goals") or raw.get("score1"))
    if away_goals is None:
        away_goals = _parse_goals(raw.get("goals2") or raw.get("away_goals") or raw.get("score2"))

    raw_status = raw.get("status") or raw.get("match_status")
    if raw_status:
        status = _normalize_status(str(raw_status))
    elif home_goals is not None and away_goals is not None:
        status = "finished"
    else:
        status = "scheduled"

    match_date = raw.get("date") or raw.get("match_date") or raw.get("datetime")
    if match_date and isinstance(match_date, str):
        match_date = match_date.replace("Z", "+00:00")

    return {
        "match_number": match_number,
        "home_code": "",
        "home_name": home_name,
        "away_code": "",
        "away_name": away_name,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "status": status,
        "match_date": match_date,
    }


# ───────────────────────────────────────────────────────────────
# Fetch pipeline
# ───────────────────────────────────────────────────────────────

def _fetch_openfootball(url: str | None = None) -> list[dict]:
    """Fetch matches from openfootball GitHub JSON format."""
    fetch_url = url or settings.openfootball_url or DEFAULT_OPENFOOTBALL_URL
    data = _fetch_json(fetch_url)
    if not isinstance(data, dict):
        raise SyncError("Unexpected openfootball response structure")
    matches = data.get("matches", [])
    if not isinstance(matches, list):
        raise SyncError("Unexpected openfootball matches structure")
    numbered_matches = []
    for index, match in enumerate(matches, start=1):
        if isinstance(match, dict):
            item = dict(match)
            item.setdefault("__match_number", index)
            numbered_matches.append(item)
    parsed = [_parse_openfootball_match(m) for m in numbered_matches]
    return [m for m in parsed if m is not None]


def _fetch_matches(source: str | None = None, db=None) -> list[dict]:
    """Fetch matches from the configured source."""
    if source is None and db is not None:
        row = db.query(SyncConfig).first()
        source = row.source if row else None
    return _fetch_openfootball()


# Backward-compatible alias used by tests
_parse_api_match = _parse_openfootball_match


# ───────────────────────────────────────────────────────────────
# Apply updates to database
# ───────────────────────────────────────────────────────────────

def sync_match_results(db, source: str | None = None) -> dict:
    """
    Fetch results from the external API and update local Match rows.

    Args:
        db: SQLAlchemy session
        source: optional override of config.sync_source

    Returns:
        {"synced": bool, "updated": int, "total_finished": int, "errors": list[str]}
    """
    from models import Match, Team

    # B-16: resolve the source we are about to use so both the fetch
    # and the log line below agree on it. Previously the log printed
    # `settings.sync_source` (the raw config value, which may be None
    # or empty), and a per-call `source` override was silently
    # invisible in the logs.
    row_source = None
    if db is not None:
        row = db.query(SyncConfig).first()
        row_source = row.source if row else None
    resolved_source = source or os.environ.get("SYNC_SOURCE") or row_source or settings.sync_source or "openfootball"

    raw_matches = _fetch_matches(resolved_source, db=db)

    local_matches = {m.match_number: m for m in db.query(Match).all()}
    team_by_code = {t.code: t for t in db.query(Team).all()}
    team_by_name = {t.name: t for t in db.query(Team).all()}

    updated = 0
    total_finished = 0
    errors = []

    for parsed in raw_matches:
        match_number = parsed["match_number"]
        if match_number is None or match_number not in local_matches:
            continue

        local = local_matches[match_number]

        # Resolve team IDs for placeholder matches.
        # openfootball knockout rows carry team *names* but no codes,
        # so we fall back to name lookup when code is empty.
        if local.home_team_id is None:
            home_team = None
            if parsed["home_code"]:
                home_team = team_by_code.get(parsed["home_code"])
            if home_team is None and parsed["home_name"]:
                home_team = team_by_name.get(parsed["home_name"])
            if home_team:
                local.home_team_id = home_team.id
                local.home_team_placeholder = None
                changed = True

        if local.away_team_id is None:
            away_team = None
            if parsed["away_code"]:
                away_team = team_by_code.get(parsed["away_code"])
            if away_team is None and parsed["away_name"]:
                away_team = team_by_name.get(parsed["away_name"])
            if away_team:
                local.away_team_id = away_team.id
                local.away_team_placeholder = None
                changed = True

        new_status = parsed["status"]
        if local.status == "finished" and new_status != "finished":
            # External feeds can temporarily omit results or mark rows as scheduled.
            # Never downgrade a scored local match back to an unplayed state.
            continue

        changed = False

        if local.status != new_status:
            local.status = new_status
            changed = True

        # Update goals (only for ongoing/finished)
        if new_status in ("ongoing", "finished"):
            new_home = parsed["home_goals"]
            new_away = parsed["away_goals"]
            if new_home is not None and (local.home_goals != new_home or local.away_goals != new_away):
                local.home_goals = new_home
                local.away_goals = new_away
                changed = True

            if new_status == "finished":
                total_finished += 1
                if local.status != "finished":
                    local.status = "finished"
                    changed = True

        if changed:
            updated += 1

    db.commit()

    logger.info(
        "Sync complete (%s): %d matches updated, %d finished from API",
        resolved_source,
        updated,
        total_finished,
    )

    return {
        "synced": True,
        "source": resolved_source,
        "updated": updated,
        "total_finished": total_finished,
        "errors": errors,
    }
