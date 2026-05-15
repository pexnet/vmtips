"""
Scoring engine for the VMTips application.
Calculates points for match predictions, bracket predictions, and tournament bonuses.
"""
from typing import Optional


# ── Bracket round point values (Section 3 of SCORING_RULES.md) ────────
BRACKET_ROUND_POINTS = {
    "round_of_32": 4,
    "round_of_16": 6,
    "quarter_final": 8,
    "semi_final": 10,
    "final": 15,
    "match_for_third_place": 3,
}


def _determine_outcome(home_goals: int, away_goals: int) -> str:
    """Return 'home', 'draw', or 'away' based on goals."""
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


def calculate_match_points(
    pred_home: int,
    pred_away: int,
    actual_home: int,
    actual_away: int,
) -> dict:
    """
    Calculate points for a single match prediction.

    Returns a dict with:
        - points: total points earned
        - outcome_correct: bool
        - home_score_correct: bool
        - away_score_correct: bool
        - total_goals_correct: bool
        - margin_correct: bool
        - perfect: bool
    """
    pred_outcome = _determine_outcome(pred_home, pred_away)
    actual_outcome = _determine_outcome(actual_home, actual_away)

    outcome_correct = pred_outcome == actual_outcome
    home_score_correct = pred_home == actual_home
    away_score_correct = pred_away == actual_away
    total_goals_correct = (pred_home + pred_away) == (actual_home + actual_away)
    margin_correct = (pred_home - pred_away) == (actual_home - actual_away)
    perfect = outcome_correct and home_score_correct and away_score_correct

    points = 0
    if outcome_correct:
        points += 3
    if home_score_correct:
        points += 2
    if away_score_correct:
        points += 2
    if total_goals_correct:
        points += 1
    if margin_correct:
        points += 1

    return {
        "points": points,
        "outcome_correct": outcome_correct,
        "home_score_correct": home_score_correct,
        "away_score_correct": away_score_correct,
        "total_goals_correct": total_goals_correct,
        "margin_correct": margin_correct,
        "perfect": perfect,
    }


def calculate_bracket_points(
    predictions: list[dict],
    actual_advancements: list[dict],
) -> dict:
    """
    Calculate bracket (knockout team placement) points.

    Each prediction and advancement entry is a dict:
        {"team_id": int, "round": str}

    A team earns points when it appears in both the user's predictions and
    the actual advancements for the same round.  Points per round are defined
    in BRACKET_ROUND_POINTS.

    Returns:
        {
            "points": int,
            "details": [{"team_id": int, "round": str, "points": int}, ...],
        }
    """
    # Build a set of (team_id, round) from actual advancements for fast lookup
    actual_set = {(a["team_id"], a["round"]) for a in actual_advancements}

    total_points = 0
    details = []

    for pred in predictions:
        key = (pred["team_id"], pred["round"])
        if key in actual_set:
            round_pts = BRACKET_ROUND_POINTS.get(pred["round"], 0)
            total_points += round_pts
            details.append({
                "team_id": pred["team_id"],
                "round": pred["round"],
                "points": round_pts,
            })

    return {
        "points": total_points,
        "details": details,
    }


def calculate_tournament_bonus_points(
    pred_winner_id: Optional[int],
    actual_winner_id: Optional[int],
    pred_top_scorer: Optional[str],
    actual_top_scorer: Optional[str],
    pred_top_assist: Optional[str],
    actual_top_assist: Optional[str],
    pred_total_goals: Optional[int],
    actual_total_goals: Optional[int],
) -> dict:
    """
    Calculate points for tournament bonus predictions.

    Each correct prediction gives 25 points.
    """
    points = 0
    result = {
        "winner_correct": False,
        "top_scorer_correct": False,
        "top_assist_correct": False,
        "total_goals_correct": False,
        "points": 0,
    }

    if pred_winner_id is not None and pred_winner_id == actual_winner_id:
        points += 25
        result["winner_correct"] = True

    if pred_top_scorer is not None and actual_top_scorer is not None:
        if pred_top_scorer.strip().lower() == actual_top_scorer.strip().lower():
            points += 25
            result["top_scorer_correct"] = True

    if pred_top_assist is not None and actual_top_assist is not None:
        if pred_top_assist.strip().lower() == actual_top_assist.strip().lower():
            points += 25
            result["top_assist_correct"] = True

    if pred_total_goals is not None and actual_total_goals is not None:
        if pred_total_goals == actual_total_goals:
            points += 25
            result["total_goals_correct"] = True

    result["points"] = points
    return result
