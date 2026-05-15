"""
Admin router: protected endpoints for manual result entry, sync, and score recalculation.
All endpoints require admin status (checked via user_id against env ADMIN_USER_ID or first user).
"""
import os

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from errors import NotFoundError, ForbiddenError
from models import Match, User, Prediction, Score
from schemas import MatchResultUpdate
from security import fetch_current_user
from scoring import calculate_match_points

router = APIRouter(prefix="/admin", tags=["admin"])


def _is_admin(current_user: User) -> bool:
    """Check if current user is the designated admin."""
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
    Stub: currently returns 501 (not implemented).
    Future: fetch from worldcupjson.net and update matches.
    """
    return {
        "synced": False,
        "message": "External sync not yet implemented. Use /admin/matches/{id}/result for manual entry.",
    }


@router.post("/scores/recalculate")
def recalculate_scores(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Recalculate and update cached total scores for all users."""
    from models import Prediction, Match
    from sqlalchemy import func

    finished_matches = db.query(Match).filter(Match.status == "finished").all()

    # Calculate match points per user
    user_points = {}
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
            user_points[pred.user_id] = user_points.get(pred.user_id, 0) + pts

    # Update Score rows
    total_updated = 0
    for user_id, total in user_points.items():
        score_row = db.query(Score).filter(Score.user_id == user_id).first()
        if score_row:
            score_row.match_points = total
            score_row.total_points = (
                score_row.match_points
                + score_row.bracket_points
                + score_row.tournament_bonus_points
                + score_row.league_bonus_points
            )
        else:
            score_row = Score(
                user_id=user_id,
                match_points=total,
                total_points=total,
            )
            db.add(score_row)
        total_updated += 1

    db.commit()

    return {
        "recalculated": True,
        "matches_processed": len(finished_matches),
        "users_updated": total_updated,
    }
