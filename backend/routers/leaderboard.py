"""
Leaderboard router: global, per-league, and personal score breakdown.
"""
import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from errors import NotFoundError, ForbiddenError
from models import User, Prediction, Match, League, LeagueMember, Score, BracketPrediction, TournamentResult, TournamentBonus
from security import fetch_current_user
from scoring import calculate_match_points, calculate_bracket_points, calculate_tournament_bonus_points, BRACKET_ROUND_POINTS

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


def _calculate_user_score(user_id: int, db: Session) -> dict:
    """Calculate a user's total score and breakdown from predictions + match results + bracket."""
    predictions = (
        db.query(Prediction)
        .filter(
            Prediction.user_id == user_id,
            Prediction.home_goals.isnot(None),
            Prediction.away_goals.isnot(None),
        )
        .all()
    )

    match_points = []
    total_match_points = 0
    perfect_count = 0

    for pred in predictions:
        match = pred.match
        if match.home_goals is None or match.away_goals is None:
            continue  # Match not yet played

        score = calculate_match_points(
            pred.home_goals,
            pred.away_goals,
            match.home_goals,
            match.away_goals,
        )
        total_match_points += score["points"]
        if score["perfect"]:
            perfect_count += 1

        match_points.append({
            "match_id": match.id,
            "match_number": match.match_number,
            "round": match.round,
            "home_team": match.home_team.name if match.home_team else match.home_team_placeholder,
            "away_team": match.away_team.name if match.away_team else match.away_team_placeholder,
            "predicted": f"{pred.home_goals}-{pred.away_goals}",
            "actual": f"{match.home_goals}-{match.away_goals}",
            "points": score["points"],
            "perfect": score["perfect"],
        })

    # ── Bracket points ──
    # Build actual advancements from finished knockout matches
    actual_advancements = _build_actual_advancements(db)
    bracket_preds = (
        db.query(BracketPrediction)
        .filter(BracketPrediction.user_id == user_id)
        .all()
    )
    bracket_result = calculate_bracket_points(
        predictions=[{"team_id": bp.team_id, "round": bp.round} for bp in bracket_preds],
        actual_advancements=list(actual_advancements),
    )
    total_bracket_points = bracket_result["points"]

    # Tournament bonus points
    actual_result = db.query(TournamentResult).first()
    actual_winner_id = actual_result.winner_team_id if actual_result else None
    actual_top_scorer = actual_result.top_scorer_name if actual_result else None
    actual_top_assist = actual_result.top_assist_name if actual_result else None
    actual_total_goals = actual_result.total_goals if actual_result else None

    tb = db.query(TournamentBonus).filter(TournamentBonus.user_id == user_id).first()
    tournament_bonus_points = 0
    tournament_bonus_details = {
        "winner_correct": False,
        "top_scorer_correct": False,
        "top_assist_correct": False,
        "total_goals_correct": False,
    }
    if tb:
        tb_result = calculate_tournament_bonus_points(
            pred_winner_id=tb.winner_team_id,
            actual_winner_id=actual_winner_id,
            pred_top_scorer=tb.top_scorer_name,
            actual_top_scorer=actual_top_scorer,
            pred_top_assist=tb.top_assist_name,
            actual_top_assist=actual_top_assist,
            pred_total_goals=tb.total_goals,
            actual_total_goals=actual_total_goals,
        )
        tournament_bonus_points = tb_result["points"]
        tournament_bonus_details = {
            "winner_correct": tb_result["winner_correct"],
            "top_scorer_correct": tb_result["top_scorer_correct"],
            "top_assist_correct": tb_result["top_assist_correct"],
            "total_goals_correct": tb_result["total_goals_correct"],
        }

    total_points = total_match_points + total_bracket_points + tournament_bonus_points

    return {
        "total_points": total_points,
        "match_points": total_match_points,
        "bracket_points": total_bracket_points,
        "tournament_bonus_points": tournament_bonus_points,
        "tournament_bonus_details": tournament_bonus_details,
        "predictions_made": len(predictions),
        "matches_scored": len(match_points),
        "perfect_predictions": perfect_count,
        "bracket_details": bracket_result["details"],
        "breakdown": match_points,
    }


def _build_actual_advancements(db) -> list[dict]:
    """
    Build a list of actual team advancements from the database.

    A team is considered to have reached a knockout round if there is a
    finished match in that round where the team is listed.
    """
    finished_knockout = (
        db.query(Match)
        .filter(
            Match.status == "finished",
            Match.round != "group",
        )
        .all()
    )

    advancements = []
    seen = set()
    for match in finished_knockout:
        if match.home_team_id is not None and (match.home_team_id, match.round) not in seen:
            advancements.append({"team_id": match.home_team_id, "round": match.round})
            seen.add((match.home_team_id, match.round))
        if match.away_team_id is not None and (match.away_team_id, match.round) not in seen:
            advancements.append({"team_id": match.away_team_id, "round": match.round})
            seen.add((match.away_team_id, match.round))

    return advancements


@router.get("/global")
def global_leaderboard(
    page: Optional[int] = Query(None, ge=1, description="Page number (1-indexed)"),
    per_page: Optional[int] = Query(None, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db),
):
    """Return the global leaderboard across all users, sorted by total points.
    
    If page and per_page are provided, returns a paginated response.
    Otherwise returns the full list (backward compatible).
    """
    users = db.query(User).all()
    entries = []

    for user in users:
        score = _calculate_user_score(user.id, db)
        entries.append({
            "user_id": user.id,
            "display_name": user.display_name or user.email,
            "total_points": score["total_points"],
            "predictions_made": score["predictions_made"],
            "perfect_predictions": score["perfect_predictions"],
        })

    entries.sort(key=lambda x: x["total_points"], reverse=True)
    for i, entry in enumerate(entries):
        entry["rank"] = i + 1

    # If no pagination params given, return full response (backward compatible)
    if page is None or per_page is None:
        return {"leaderboard": entries}

    # Paginated response
    total = len(entries)
    total_pages = math.ceil(total / per_page) if per_page > 0 else 1
    offset = (page - 1) * per_page
    paginated_entries = entries[offset:offset + per_page]

    return {
        "leaderboard": paginated_entries,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


@router.get("/league/{league_id}")
def league_leaderboard(
    league_id: int,
    current_user=Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Return leaderboard for a specific league (members only)."""
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        raise NotFoundError(detail="league_not_found", error_code="league_not_found")

    # Check if user is a member
    is_member = (
        db.query(LeagueMember)
        .filter(
            LeagueMember.league_id == league_id,
            LeagueMember.user_id == current_user.id,
        )
        .first()
    )
    if not is_member:
        raise ForbiddenError(detail="not_a_member", error_code="not_a_member")

    members = (
        db.query(User)
        .join(LeagueMember, User.id == LeagueMember.user_id)
        .filter(LeagueMember.league_id == league_id)
        .all()
    )

    entries = []
    for user in members:
        score = _calculate_user_score(user.id, db)
        entries.append({
            "user_id": user.id,
            "display_name": user.display_name or user.email,
            "total_points": score["total_points"],
            "predictions_made": score["predictions_made"],
            "perfect_predictions": score["perfect_predictions"],
        })

    entries.sort(key=lambda x: x["total_points"], reverse=True)
    for i, entry in enumerate(entries):
        entry["rank"] = i + 1

    return {"leaderboard": entries, "league_name": league.name}


@router.get("/me")
def my_scores(
    current_user=Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Return the current user's full score breakdown."""
    score = _calculate_user_score(current_user.id, db)
    return {
        "user_id": current_user.id,
        "display_name": current_user.display_name or current_user.email,
        "total_points": score["total_points"],
        "match_points": score["match_points"],
        "bracket_points": score["bracket_points"],
        "tournament_bonus_points": score["tournament_bonus_points"],
        "tournament_bonus_details": score["tournament_bonus_details"],
        "predictions_made": score["predictions_made"],
        "matches_scored": score["matches_scored"],
        "perfect_predictions": score["perfect_predictions"],
        "bracket_details": score["bracket_details"],
        "breakdown": score["breakdown"],
    }
