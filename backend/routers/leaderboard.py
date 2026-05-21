"""
Leaderboard router: global, per-league, and personal score breakdown.
"""
import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session, joinedload

from database import get_db
from errors import NotFoundError, ForbiddenError
from models import (
    User, Prediction, Match, League, LeagueMember, Score,
    BracketPrediction, TournamentResult, TournamentBonus,
    KnockoutAdvancement,
)
from security import fetch_current_user
from scoring import calculate_match_points, calculate_bracket_points, calculate_tournament_bonus_points, BRACKET_ROUND_POINTS

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


def _empty_score() -> dict:
    return {
        "total_points": 0,
        "match_points": 0,
        "bracket_points": 0,
        "tournament_bonus_points": 0,
        "predictions_made": 0,
        "perfect_predictions": 0,
    }


def _batch_calculate_scores(
    db: Session,
    user_ids: list[int],
    league_id: int | None = None,
) -> dict[int, dict]:
    """Calculate leaderboard score aggregates for many users without per-user queries."""
    if not user_ids:
        return {}

    scores = {user_id: _empty_score() for user_id in user_ids}

    pred_filters = [
        Prediction.user_id.in_(user_ids),
        Prediction.home_goals.isnot(None),
        Prediction.away_goals.isnot(None),
    ]
    if league_id is not None:
        pred_filters.append(Prediction.league_id == league_id)

    pred_home_win = Prediction.home_goals > Prediction.away_goals
    pred_away_win = Prediction.home_goals < Prediction.away_goals
    pred_draw = Prediction.home_goals == Prediction.away_goals
    actual_home_win = Match.home_goals > Match.away_goals
    actual_away_win = Match.home_goals < Match.away_goals
    actual_draw = Match.home_goals == Match.away_goals
    outcome_correct = or_(
        and_(pred_home_win, actual_home_win),
        and_(pred_away_win, actual_away_win),
        and_(pred_draw, actual_draw),
    )
    scored_match = and_(Match.home_goals.isnot(None), Match.away_goals.isnot(None))
    perfect = and_(
        scored_match,
        outcome_correct,
        Prediction.home_goals == Match.home_goals,
        Prediction.away_goals == Match.away_goals,
    )

    match_rows = (
        db.query(
            Prediction.user_id,
            func.count(Prediction.id).label("predictions_made"),
            func.coalesce(func.sum(case((and_(scored_match, outcome_correct), 3), else_=0)), 0).label("outcome_points"),
            func.coalesce(func.sum(case((and_(scored_match, Prediction.home_goals == Match.home_goals), 2), else_=0)), 0).label("home_goal_points"),
            func.coalesce(func.sum(case((and_(scored_match, Prediction.away_goals == Match.away_goals), 2), else_=0)), 0).label("away_goal_points"),
            func.coalesce(func.sum(case((perfect, 1), else_=0)), 0).label("perfect_predictions"),
        )
        .join(Match, Prediction.match_id == Match.id)
        .filter(*pred_filters)
        .group_by(Prediction.user_id)
        .all()
    )
    for row in match_rows:
        match_points = int(row.outcome_points or 0) + int(row.home_goal_points or 0) + int(row.away_goal_points or 0)
        scores[row.user_id]["match_points"] = match_points
        scores[row.user_id]["predictions_made"] = int(row.predictions_made or 0)
        scores[row.user_id]["perfect_predictions"] = int(row.perfect_predictions or 0)

    actual_advancements = _build_actual_advancements(db)
    if actual_advancements:
        bracket_filters = [BracketPrediction.user_id.in_(user_ids)]
        if league_id is not None:
            bracket_filters.append(BracketPrediction.league_id == league_id)
        advancement_filter = or_(*[
            and_(
                BracketPrediction.team_id == advancement["team_id"],
                BracketPrediction.round == advancement["round"],
            )
            for advancement in actual_advancements
        ])
        bracket_points_case = case(
            *[
                (BracketPrediction.round == round_name, points)
                for round_name, points in BRACKET_ROUND_POINTS.items()
            ],
            else_=0,
        )
        bracket_rows = (
            db.query(
                BracketPrediction.user_id,
                func.coalesce(func.sum(bracket_points_case), 0).label("bracket_points"),
            )
            .filter(*bracket_filters)
            .filter(advancement_filter)
            .group_by(BracketPrediction.user_id)
            .all()
        )
        for row in bracket_rows:
            scores[row.user_id]["bracket_points"] = int(row.bracket_points or 0)

    actual_result = db.query(TournamentResult).first()
    if actual_result:
        bonus_filters = [TournamentBonus.user_id.in_(user_ids)]
        if league_id is not None:
            bonus_filters.append(TournamentBonus.league_id == league_id)

        def _text_matches(pred_col, actual_value):
            if actual_value is None:
                return False
            return func.lower(func.trim(pred_col)) == actual_value.strip().lower()

        bonus_points = (
            case((and_(TournamentBonus.winner_team_id.isnot(None), TournamentBonus.winner_team_id == actual_result.winner_team_id), 20), else_=0)
            + case((_text_matches(TournamentBonus.top_scorer_name, actual_result.top_scorer_name), 20), else_=0)
            + case((and_(TournamentBonus.bronze_winner_team_id.isnot(None), TournamentBonus.bronze_winner_team_id == actual_result.bronze_winner_team_id), 20), else_=0)
            + case((and_(TournamentBonus.most_goals_team_id.isnot(None), TournamentBonus.most_goals_team_id == actual_result.most_goals_team_id), 10), else_=0)
            + case((and_(TournamentBonus.most_conceded_team_id.isnot(None), TournamentBonus.most_conceded_team_id == actual_result.most_conceded_team_id), 10), else_=0)
            + case((_text_matches(TournamentBonus.custom_bonus_1, actual_result.custom_bonus_1_answer), 10), else_=0)
            + case((_text_matches(TournamentBonus.custom_bonus_2, actual_result.custom_bonus_2_answer), 10), else_=0)
        )
        bonus_rows = (
            db.query(
                TournamentBonus.user_id,
                func.coalesce(func.sum(bonus_points), 0).label("tournament_bonus_points"),
            )
            .filter(*bonus_filters)
            .group_by(TournamentBonus.user_id)
            .all()
        )
        for row in bonus_rows:
            scores[row.user_id]["tournament_bonus_points"] = int(row.tournament_bonus_points or 0)

    for score in scores.values():
        score["total_points"] = (
            score["match_points"]
            + score["bracket_points"]
            + score["tournament_bonus_points"]
        )

    return scores


def _calculate_user_score(user_id: int, db: Session, league_id: int | None = None) -> dict:
    """Calculate a user's total score and breakdown from predictions + match results + bracket."""
    prediction_query = db.query(Prediction).filter(
        Prediction.user_id == user_id,
        Prediction.home_goals.isnot(None),
        Prediction.away_goals.isnot(None),
    )
    if league_id is not None:
        prediction_query = prediction_query.filter(Prediction.league_id == league_id)
    predictions = prediction_query.options(
        joinedload(Prediction.match).joinedload(Match.home_team),
        joinedload(Prediction.match).joinedload(Match.away_team),
    ).all()

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
    actual_advancements = _build_actual_advancements(db)
    bracket_query = db.query(BracketPrediction).filter(BracketPrediction.user_id == user_id)
    if league_id is not None:
        bracket_query = bracket_query.filter(BracketPrediction.league_id == league_id)
    bracket_preds = bracket_query.all()
    bracket_result = calculate_bracket_points(
        predictions=[{"team_id": bp.team_id, "round": bp.round} for bp in bracket_preds],
        actual_advancements=list(actual_advancements),
    )
    total_bracket_points = bracket_result["points"]

    # ── Tournament bonus points ──
    actual_result = db.query(TournamentResult).first()
    bonus_query = db.query(TournamentBonus).filter(TournamentBonus.user_id == user_id)
    if league_id is not None:
        bonus_query = bonus_query.filter(TournamentBonus.league_id == league_id)
    tb = bonus_query.first()

    actual_winner_id = actual_result.winner_team_id if actual_result else None
    actual_top_scorer = actual_result.top_scorer_name if actual_result else None
    actual_bronze_winner_id = actual_result.bronze_winner_team_id if actual_result else None
    actual_most_goals_team_id = actual_result.most_goals_team_id if actual_result else None
    actual_most_conceded_team_id = actual_result.most_conceded_team_id if actual_result else None
    actual_custom_bonus_1 = actual_result.custom_bonus_1_answer if actual_result else None
    actual_custom_bonus_2 = actual_result.custom_bonus_2_answer if actual_result else None

    tournament_bonus_points = 0
    tournament_bonus_details = {
        "winner_correct": False,
        "top_scorer_correct": False,
        "bronze_winner_correct": False,
        "most_goals_team_correct": False,
        "most_conceded_team_correct": False,
        "custom_bonus_1_correct": False,
        "custom_bonus_2_correct": False,
    }

    if tb:
        tb_result = calculate_tournament_bonus_points(
            pred_winner_id=tb.winner_team_id,
            actual_winner_id=actual_winner_id,
            pred_top_scorer=tb.top_scorer_name,
            actual_top_scorer=actual_top_scorer,
            pred_bronze_winner_id=tb.bronze_winner_team_id,
            actual_bronze_winner_id=actual_bronze_winner_id,
            pred_most_goals_team_id=tb.most_goals_team_id,
            actual_most_goals_team_id=actual_most_goals_team_id,
            pred_most_conceded_team_id=tb.most_conceded_team_id,
            actual_most_conceded_team_id=actual_most_conceded_team_id,
            pred_custom_bonus_1=tb.custom_bonus_1,
            actual_custom_bonus_1=actual_custom_bonus_1,
            pred_custom_bonus_2=tb.custom_bonus_2,
            actual_custom_bonus_2=actual_custom_bonus_2,
        )
        tournament_bonus_points = tb_result["points"]
        tournament_bonus_details = {
            "winner_correct": tb_result.get("winner_correct", False),
            "top_scorer_correct": tb_result.get("top_scorer_correct", False),
            "bronze_winner_correct": tb_result.get("bronze_winner_correct", False),
            "most_goals_team_correct": tb_result.get("most_goals_team_correct", False),
            "most_conceded_team_correct": tb_result.get("most_conceded_team_correct", False),
            "custom_bonus_1_correct": tb_result.get("custom_bonus_1_correct", False),
            "custom_bonus_2_correct": tb_result.get("custom_bonus_2_correct", False),
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

    Prefers explicit KnockoutAdvancement entries, falls back to
    deriving from finished knockout matches.
    """
    # Check explicit advancements first
    advancements_db = db.query(KnockoutAdvancement).all()
    if advancements_db:
        return [{"team_id": a.team_id, "round": a.round} for a in advancements_db]

    # Fallback: derive from finished knockout matches
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
    score_by_user_id = _batch_calculate_scores(db, [user.id for user in users])
    entries = []

    for user in users:
        score = score_by_user_id[user.id]
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
    score_by_user_id = _batch_calculate_scores(db, [member.id for member in members], league_id=league_id)

    entries = []
    for user in members:
        score = score_by_user_id[user.id]
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
    league_id: Optional[int] = Query(None, description="Filter score by league"),
    current_user=Depends(fetch_current_user),
    db: Session = Depends(get_db),
):
    """Return the current user's full score breakdown."""
    if league_id is not None:
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

    score = _calculate_user_score(current_user.id, db, league_id=league_id)
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
