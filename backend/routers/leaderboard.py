"""
Leaderboard router: global, per-league, and personal score breakdown.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User, Prediction, Match, League, LeagueMember, Score
from security import fetch_current_user
from scoring import calculate_match_points

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


def _calculate_user_score(user_id: int, db: Session) -> dict:
    """Calculate a user's total score and breakdown from predictions + match results."""
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
    total_points = 0
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
        total_points += score["points"]
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

    return {
        "total_points": total_points,
        "predictions_made": len(predictions),
        "matches_scored": len(match_points),
        "perfect_predictions": perfect_count,
        "breakdown": match_points,
    }


@router.get("/global")
def global_leaderboard(db: Session = Depends(get_db)):
    """Return the global leaderboard across all users, sorted by total points."""
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

    return {"leaderboard": entries}


@router.get("/league/{league_id}")
def league_leaderboard(
    league_id: int,
    current_user=Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Return leaderboard for a specific league (members only)."""
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        raise HTTPException(status_code=404, detail="league_not_found")

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
        raise HTTPException(status_code=403, detail="not_a_member")

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
        "predictions_made": score["predictions_made"],
        "matches_scored": score["matches_scored"],
        "perfect_predictions": score["perfect_predictions"],
        "breakdown": score["breakdown"],
    }
