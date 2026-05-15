"""
Sync service: fetch match results from the external World Cup API
(worldcupjson.net) and update the local database.

Uses only the standard library (urllib) so no extra dependency is needed.
"""
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

from config import settings

logger = logging.getLogger("vmtips.sync")

# How long to wait for the external API (seconds)
REQUEST_TIMEOUT = 15

# The API endpoint is configurable via the WORLD_CUP_JSON_URL setting
DEFAULT_API_URL = "https://worldcupjson.net/matches"


def _fetch_matches(api_url: Optional[str] = None) -> list[dict]:
    """
    Fetch match data from the external API.

    Returns a list of dicts; each dict has at least:
        - match_number (int)
        - home_team (str, team code or name)
        - away_team (str, team code or name)
        - home_goals (int or None)
        - away_goals (int or None)
        - status (str: "scheduled", "in_play", "finished", etc.)
        - match_date (ISO-8601 str)
    """
    url = api_url or settings.world_cup_json_url
    logger.info("Fetching match results from %s", url)

    req = urllib.request.Request(url, headers={"User-Agent": "VMTips/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
    except urllib.error.HTTPError as exc:
        logger.error("External API returned HTTP %s", exc.code)
        raise SyncError(f"External API HTTP error: {exc.code}") from exc
    except urllib.error.URLError as exc:
        logger.error("Cannot reach external API: %s", exc.reason)
        raise SyncError(f"Cannot reach external API: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON from external API: %s", exc)
        raise SyncError("Invalid JSON from external API") from exc

    if not isinstance(data, list):
        # Some APIs wrap data in a top-level key
        if isinstance(data, dict) and "matches" in data:
            data = data["matches"]
        else:
            raise SyncError("Unexpected API response structure")

    return data


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
    normalized = status_map.get(api_status.lower(), "scheduled")
    return normalized


def _parse_goals(score_data) -> Optional[int]:
    """Safely extract a goal count from various API score formats."""
    if score_data is None:
        return None
    if isinstance(score_data, int):
        return score_data
    if isinstance(score_data, dict):
        # Some APIs use {"full_time": 2, "half_time": 1}
        return score_data.get("full_time", score_data.get("goals", None))
    try:
        return int(score_data)
    except (ValueError, TypeError):
        return None


def _parse_api_match(raw: dict) -> Optional[dict]:
    """
    Parse a raw API match object into a normalised dict.

    Handles both the worldcupjson.net format and common variations.

    Returns None if the match can't be parsed.
    """
    # ── match number ──
    match_number = raw.get("match_number") or raw.get("matchNumber") or raw.get("fifa_id")
    if match_number is not None:
        match_number = int(match_number)

    # ── teams ──
    home_raw = raw.get("home_team") or raw.get("homeTeam") or {}
    away_raw = raw.get("away_team") or raw.get("awayTeam") or {}

    # Teams may be strings (names) or dicts with "name"/"code"
    if isinstance(home_raw, str):
        home_code = home_raw
        home_name = home_raw
    elif isinstance(home_raw, dict):
        home_code = home_raw.get("code", home_raw.get("country", ""))
        home_name = home_raw.get("name", home_raw.get("country", home_code))
    else:
        return None

    if isinstance(away_raw, str):
        away_code = away_raw
        away_name = away_raw
    elif isinstance(away_raw, dict):
        away_code = away_raw.get("code", away_raw.get("country", ""))
        away_name = away_raw.get("name", away_raw.get("country", away_code))
    else:
        return None

    # ── goals ──
    home_goals = _parse_goals(raw.get("home_goals", raw.get("homeGoals", home_raw.get("goals") if isinstance(home_raw, dict) else None)))
    away_goals = _parse_goals(raw.get("away_goals", raw.get("awayGoals", away_raw.get("goals") if isinstance(away_raw, dict) else None)))

    # ── status ──
    raw_status = raw.get("status", raw.get("match_status", "scheduled"))
    if isinstance(raw_status, dict):
        raw_status = raw_status.get("code", "scheduled")
    status = _normalize_status(str(raw_status))

    # ── match date ──
    match_date = raw.get("match_date") or raw.get("matchDate") or raw.get("datetime")
    if match_date and isinstance(match_date, str):
        match_date = match_date.replace("Z", "+00:00")

    return {
        "match_number": match_number,
        "home_code": home_code,
        "home_name": home_name,
        "away_code": away_code,
        "away_name": away_name,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "status": status,
        "match_date": match_date,
    }


def sync_match_results(db) -> dict:
    """
    Fetch results from the external API and update local Match rows.

    Args:
        db: SQLAlchemy session

    Returns:
        {
            "synced": bool,
            "updated": int,        # number of matches whose result changed
            "total_finished": int,  # finished matches from API
            "errors": list[str],    # non-fatal parse errors
        }
    """
    from models import Match, Team

    raw_matches = _fetch_matches()

    # Load local matches keyed by match_number for efficient lookup
    local_matches = {m.match_number: m for m in db.query(Match).all()}

    # Load team code → team_id mapping
    team_by_code = {t.code: t for t in db.query(Team).all()}
    team_by_name = {t.name: t for t in db.query(Team).all()}

    updated = 0
    total_finished = 0
    errors = []

    for raw in raw_matches:
        parsed = _parse_api_match(raw)
        if parsed is None:
            continue

        match_number = parsed["match_number"]
        if match_number is None or match_number not in local_matches:
            continue

        local = local_matches[match_number]

        # ── Resolve team IDs for placeholder matches ──
        if local.home_team_id is None and parsed["home_code"]:
            home_team = team_by_code.get(parsed["home_code"]) or team_by_name.get(parsed["home_name"])
            if home_team:
                local.home_team_id = home_team.id
                local.home_team_placeholder = None

        if local.away_team_id is None and parsed["away_code"]:
            away_team = team_by_code.get(parsed["away_code"]) or team_by_name.get(parsed["away_name"])
            if away_team:
                local.away_team_id = away_team.id
                local.away_team_placeholder = None

        # ── Update status ──
        new_status = parsed["status"]
        changed = False

        if local.status != new_status:
            local.status = new_status
            changed = True

        # ── Update goals (only for ongoing/finished) ──
        if new_status in ("ongoing", "finished"):
            new_home = parsed["home_goals"]
            new_away = parsed["away_goals"]
            if new_home is not None and (local.home_goals != new_home or local.away_goals != new_away):
                local.home_goals = new_home
                local.away_goals = new_away
                changed = True

            if new_status == "finished":
                total_finished += 1
                # Ensure status is "finished"
                if local.status != "finished":
                    local.status = "finished"
                    changed = True

        if changed:
            updated += 1

    db.commit()

    logger.info(
        "Sync complete: %d matches updated, %d finished from API",
        updated,
        total_finished,
    )

    return {
        "synced": True,
        "updated": updated,
        "total_finished": total_finished,
        "errors": errors,
    }


class SyncError(Exception):
    """Raised when the external sync fails."""
    pass