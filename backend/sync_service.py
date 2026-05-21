"""
Sync service: fetch match results from external World Cup APIs and update
the local database.

Supports two sources:
  1. worldcupjson.net  — live scores, status, real-time during tournament
  2. openfootball.json  — static GitHub-hosted JSON, updated during tournament

Toggle the source via config.sync_source and auto-sync via config.auto_sync_enabled.
"""
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional

from config import settings
from models import SyncConfig

logger = logging.getLogger("vmtips.sync")

REQUEST_TIMEOUT = 15
DEFAULT_API_URL = "https://worldcupjson.net/matches"
DEFAULT_OPENFOOTBALL_URL = (
    "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
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
    try:
        return int(score_data)
    except (ValueError, TypeError):
        return None


# ───────────────────────────────────────────────────────────────
# Source parsers
# ───────────────────────────────────────────────────────────────

def _parse_worldcupjson_match(raw: dict) -> Optional[dict]:
    """Parse a worldcupjson.net match entry into normalised form."""
    match_number = raw.get("match_number") or raw.get("matchNumber") or raw.get("fifa_id")
    if match_number is not None:
        match_number = int(match_number)

    home_raw = raw.get("home_team") or raw.get("homeTeam") or {}
    away_raw = raw.get("away_team") or raw.get("awayTeam") or {}

    if isinstance(home_raw, str):
        home_code, home_name = home_raw, home_raw
    elif isinstance(home_raw, dict):
        home_code = home_raw.get("code", home_raw.get("country", ""))
        home_name = home_raw.get("name", home_raw.get("country", home_code))
    else:
        return None

    if isinstance(away_raw, str):
        away_code, away_name = away_raw, away_raw
    elif isinstance(away_raw, dict):
        away_code = away_raw.get("code", away_raw.get("country", ""))
        away_name = away_raw.get("name", away_raw.get("country", away_code))
    else:
        return None

    home_goals = _parse_goals(
        raw.get("home_goals", raw.get("homeGoals", home_raw.get("goals") if isinstance(home_raw, dict) else None))
    )
    away_goals = _parse_goals(
        raw.get("away_goals", raw.get("awayGoals", away_raw.get("goals") if isinstance(away_raw, dict) else None))
    )

    raw_status = raw.get("status", raw.get("match_status", "scheduled"))
    if isinstance(raw_status, dict):
        raw_status = raw_status.get("code", "scheduled")
    status = _normalize_status(str(raw_status))

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


def _parse_openfootball_match(raw: dict) -> Optional[dict]:
    """Parse an openfootball JSON match entry into normalised form."""
    # openfootball uses 'num' for match number and 'team1'/'team2' for team names
    match_number = raw.get("num") or raw.get("match_number")
    if match_number is not None:
        try:
            match_number = int(match_number)
        except (ValueError, TypeError):
            match_number = None

    # If there's no match_number this is likely a group-stage match we cannot map
    if match_number is None:
        return None

    home_name = raw.get("team1") or raw.get("home_team") or raw.get("homeTeam") or ""
    away_name = raw.get("team2") or raw.get("away_team") or raw.get("awayTeam") or ""

    # Goals in openfootball usually appear as top-level keys during/after the match
    home_goals = _parse_goals(raw.get("goals1") or raw.get("home_goals") or raw.get("score1"))
    away_goals = _parse_goals(raw.get("goals2") or raw.get("away_goals") or raw.get("score2"))

    # Status detection: if goals are present → finished; if date is in the past → likely finished
    # openfootball does not always include status, so we infer:
    status = "scheduled"
    if home_goals is not None and away_goals is not None:
        status = "finished"
    else:
        raw_date = raw.get("date")
        if raw_date:
            try:
                match_dt = datetime.strptime(raw_date, "%Y-%m-%d")
                # If the match date + 3 hours is in the past, assume finished
                if match_dt + timedelta(hours=3) < datetime.now(timezone.utc).replace(tzinfo=None):
                    status = "finished"
            except ValueError:
                pass

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

def _fetch_worldcupjson(api_url: str | None = None) -> list[dict]:
    """Fetch matches from worldcupjson.net format."""
    url = api_url or settings.world_cup_json_url or DEFAULT_API_URL
    data = _fetch_json(url)
    if isinstance(data, dict) and "matches" in data:
        data = data["matches"]
    if not isinstance(data, list):
        raise SyncError("Unexpected worldcupjson response structure")
    parsed = [_parse_worldcupjson_match(m) for m in data]
    return [m for m in parsed if m is not None]


def _fetch_openfootball(url: str | None = None) -> list[dict]:
    """Fetch matches from openfootball GitHub JSON format."""
    fetch_url = url or settings.openfootball_url or DEFAULT_OPENFOOTBALL_URL
    data = _fetch_json(fetch_url)
    if not isinstance(data, dict):
        raise SyncError("Unexpected openfootball response structure")
    matches = data.get("matches", [])
    if not isinstance(matches, list):
        raise SyncError("Unexpected openfootball matches structure")
    parsed = [_parse_openfootball_match(m) for m in matches]
    return [m for m in parsed if m is not None]


def _fetch_matches(source: str | None = None, db=None) -> list[dict]:
    """Fetch matches from the configured source."""
    if source is None and db is not None:
        row = db.query(SyncConfig).first()
        source = row.source if row else None
    src = source or settings.sync_source or "worldcupjson"
    if src == "openfootball":
        return _fetch_openfootball()
    return _fetch_worldcupjson()


# Backward-compatible alias used by tests
_parse_api_match = _parse_worldcupjson_match


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

    raw_matches = _fetch_matches(source, db=db)

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

        # Resolve team IDs for placeholder matches
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

        new_status = parsed["status"]
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
        settings.sync_source,
        updated,
        total_finished,
    )

    return {
        "synced": True,
        "updated": updated,
        "total_finished": total_finished,
        "errors": errors,
        "source": settings.sync_source,
    }
