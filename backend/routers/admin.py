"""
Admin router: protected endpoints for manual result entry, sync, and score recalculation.
All endpoints require admin status (checked via user_id against env ADMIN_USER_ID or first user).
"""
import os

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from errors import NotFoundError, ForbiddenError
from models import Match, User, Prediction, Score, BracketPrediction, TournamentResult
from schemas import MatchResultUpdate
from security import fetch_current_user
from scoring import calculate_match_points, calculate_bracket_points, BRACKET_ROUND_POINTS

router = APIRouter(prefix="/admin", tags=["admin"])


def _is_admin(current_user: User) -> bool:
    """Check if current user is the designated admin."""
    if current_user.is_admin:
        return True
    admin_id_env = os.environ.get("ADMIN_USER_ID")
    if admin_id_env:
        return str(current_user.id) == admin_id_env
    # Fallback: first registered user is admin
    return current_user.id == 1


def require_admin(current_user: User = Depends(fetch_current_user)) -> User:
    """Dependency: raises 403 if user is not admin."""
    if not _is_admin(current_user):
        raise ForbiddenError(detail="admin_only", error_code="admin_only")
    return current_user


class TournamentResultUpdate(BaseModel):
    winner_team_id: int | None = None
    top_scorer_name: str | None = None
    top_assist_name: str | None = None
    total_goals: int | None = None


@router.get("/tournament-result")
def get_tournament_result(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get the currently set actual tournament results."""
    result = db.query(TournamentResult).first()
    if not result:
        return {
            "winner_team_id": None,
            "top_scorer_name": None,
            "top_assist_name": None,
            "total_goals": None,
            "updated_at": None,
        }
    return {
        "winner_team_id": result.winner_team_id,
        "top_scorer_name": result.top_scorer_name,
        "top_assist_name": result.top_assist_name,
        "total_goals": result.total_goals,
        "updated_at": result.updated_at.isoformat() if result.updated_at else None,
    }


@router.post("/tournament-result")
def set_tournament_result(
    payload: TournamentResultUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Set the actual tournament results (for bonus scoring). Admin only."""
    result = db.query(TournamentResult).first()
    if result:
        if payload.winner_team_id is not None:
            result.winner_team_id = payload.winner_team_id
        if payload.top_scorer_name is not None:
            result.top_scorer_name = payload.top_scorer_name
        if payload.top_assist_name is not None:
            result.top_assist_name = payload.top_assist_name
        if payload.total_goals is not None:
            result.total_goals = payload.total_goals
    else:
        result = TournamentResult(
            winner_team_id=payload.winner_team_id,
            top_scorer_name=payload.top_scorer_name,
            top_assist_name=payload.top_assist_name,
            total_goals=payload.total_goals,
        )
        db.add(result)
    db.commit()
    return {"saved": True}


@router.post("/matches/{match_id}/result")
def set_match_result(
    match_id: int,
    payload: MatchResultUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Manually set the result for a specific match."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise NotFoundError(detail="match_not_found", error_code="match_not_found")

    match.home_goals = payload.home_goals
    match.away_goals = payload.away_goals
    match.status = "finished"
    db.commit()

    return {
        "match_id": match_id,
        "result": f"{payload.home_goals}-{payload.away_goals}",
        "status": "finished",
    }


@router.post("/sync-results")
def sync_results(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Trigger a sync of match results from external API.

    Uses the source configured in SYNC_SOURCE (worldcupjson or openfootball).
    Fetches all match data, updates local Match rows with new goals/status,
    and resolves placeholder teams where the actual teams are now known.

    Returns a summary of how many matches were updated.
    """
    from sync_service import sync_match_results, SyncError

    try:
        result = sync_match_results(db)
    except SyncError as exc:
        return {
            "synced": False,
            "message": str(exc),
            "updated": 0,
            "total_finished": 0,
            "errors": [str(exc)],
        }

    return result


@router.get("/sync-config")
def get_sync_config(admin: User = Depends(require_admin)):
    """Return current sync configuration (read-only for admin)."""
    return {
        "source": settings.sync_source,
        "auto_sync_enabled": settings.auto_sync_enabled,
        "auto_sync_interval_minutes": settings.auto_sync_interval_minutes,
        "world_cup_json_url": settings.world_cup_json_url,
        "openfootball_url": settings.openfootball_url,
    }


class SyncConfigUpdate(BaseModel):
    source: str | None = None
    auto_sync_enabled: bool | None = None
    auto_sync_interval_minutes: int | None = None


@router.post("/sync-config")
def update_sync_config(
    payload: SyncConfigUpdate,
    admin: User = Depends(require_admin),
):
    """Update sync configuration. Admin only. Requires restart to take full effect."""
    # Note: these are in-memory changes only; for persistence update .env file
    if payload.source is not None:
        if payload.source not in ("worldcupjson", "openfootball"):
            raise HTTPException(status_code=422, detail="source must be 'worldcupjson' or 'openfootball'")
        settings.sync_source = payload.source
    if payload.auto_sync_enabled is not None:
        settings.auto_sync_enabled = payload.auto_sync_enabled
    if payload.auto_sync_interval_minutes is not None:
        if payload.auto_sync_interval_minutes < 1:
            raise HTTPException(status_code=422, detail="interval must be >= 1")
        settings.auto_sync_interval_minutes = payload.auto_sync_interval_minutes

    return {
        "saved": True,
        "source": settings.sync_source,
        "auto_sync_enabled": settings.auto_sync_enabled,
        "auto_sync_interval_minutes": settings.auto_sync_interval_minutes,
    }


@router.post("/scores/recalculate")
def recalculate_scores(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Recalculate and update cached total scores for all users.

    Computes:
      - match_points: from match prediction scoring (outcome, scores, etc.)
      - bracket_points: from knockout bracket team placement scoring
      - tournament_bonus_points: from tournament bonus predictions
      - league_bonus_points: unchanged here (managed per league)

    Then sets total_points = match_points + bracket_points + tournament_bonus_points + league_bonus_points
    """
    from models import Prediction, Match
    from scoring import calculate_tournament_bonus_points

    # ── 1. Match-result points ──────────────────────────────────────
    finished_matches = db.query(Match).filter(Match.status == "finished").all()

    user_match_points = {}
    for match in finished_matches:
        predictions = db.query(Prediction).filter(Prediction.match_id == match.id).all()
        for pred in predictions:
            if pred.home_goals is None or pred.away_goals is None:
                continue
            pts = calculate_match_points(
                pred.home_goals,
                pred.away_goals,
                match.home_goals,
                match.away_goals,
            )["points"]
            user_match_points[pred.user_id] = user_match_points.get(pred.user_id, 0) + pts

    # ── 2. Bracket points ───────────────────────────────────────────
    # Build actual advancements: which teams actually reached each knockout round
    actual_advancements = _build_actual_advancements(db)

    bracket_preds = db.query(BracketPrediction).all()
    user_bracket_points = {}
    for bp in bracket_preds:
        key = (bp.team_id, bp.round)
        if key in actual_advancements:
            round_pts = BRACKET_ROUND_POINTS.get(bp.round, 0)
            user_bracket_points[bp.user_id] = user_bracket_points.get(bp.user_id, 0) + round_pts

    # ── 3. Tournament bonus points ──────────────────────────────────
    from models import TournamentBonus
    bonuses = db.query(TournamentBonus).all()
    actual_result = db.query(TournamentResult).first()
    actual_winner_id = actual_result.winner_team_id if actual_result else None
    actual_top_scorer = actual_result.top_scorer_name if actual_result else None
    actual_top_assist = actual_result.top_assist_name if actual_result else None
    actual_total_goals = actual_result.total_goals if actual_result else None

    user_bonus_points = {}
    for bonus in bonuses:
        result = calculate_tournament_bonus_points(
            pred_winner_id=bonus.winner_team_id,
            actual_winner_id=actual_winner_id,
            pred_top_scorer=bonus.top_scorer_name,
            actual_top_scorer=actual_top_scorer,
            pred_top_assist=bonus.top_assist_name,
            actual_top_assist=actual_top_assist,
            pred_total_goals=bonus.total_goals,
            actual_total_goals=actual_total_goals,
        )
        user_bonus_points[bonus.user_id] = result["points"]

    # ── 4. Update Score rows ────────────────────────────────────────
    all_user_ids = set(user_match_points) | set(user_bracket_points) | set(user_bonus_points)
    total_updated = 0

    for user_id in all_user_ids:
        mp = user_match_points.get(user_id, 0)
        bp = user_bracket_points.get(user_id, 0)
        tbp = user_bonus_points.get(user_id, 0)
        total = mp + bp + tbp

        score_row = db.query(Score).filter(Score.user_id == user_id).first()
        if score_row:
            score_row.match_points = mp
            score_row.bracket_points = bp
            score_row.tournament_bonus_points = tbp
            score_row.total_points = (
                mp + bp + tbp + score_row.league_bonus_points
            )
        else:
            score_row = Score(
                user_id=user_id,
                match_points=mp,
                bracket_points=bp,
                tournament_bonus_points=tbp,
                total_points=total,
            )
            db.add(score_row)
        total_updated += 1

    db.commit()

    return {
        "recalculated": True,
        "matches_processed": len(finished_matches),
        "users_updated": total_updated,
        "total_match_points": sum(user_match_points.values()),
        "total_bracket_points": sum(user_bracket_points.values()),
        "total_tournament_bonus_points": sum(user_bonus_points.values()),
    }


def _build_actual_advancements(db) -> set[tuple[int, str]]:
    """
    Determine which teams actually advanced to each knockout round.

    Inspects finished matches. A team is considered to have "reached" a
    knockout round if there is a finished match in that round where the
    team is listed as home or away.  (Even the losing team "reached" that
    round — they were present but lost.)

    Returns a set of (team_id, round_name) tuples.
    """
    finished_knockout = (
        db.query(Match)
        .filter(
            Match.status == "finished",
            Match.round != "group",
        )
        .all()
    )

    advancements = set()
    for match in finished_knockout:
        if match.home_team_id is not None:
            advancements.add((match.home_team_id, match.round))
        if match.away_team_id is not None:
            advancements.add((match.away_team_id, match.round))

    return advancements