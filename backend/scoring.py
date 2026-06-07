"""
Scoring engine for the VMTips application.
Calculates points for match predictions, bracket predictions, and tournament bonuses.

Scoring rules match the VM-tips-2026 Excel template (7p per match variant).
"""
from typing import Optional


# ── Match points (group + knockout) ──────────────────────────────
# Correct outcome (1X2): 3 points
# Correct home goals:     2 points
# Correct away goals:     2 points
# Maximum per match:      7 points

# ── Bracket round point values ────────────────────────────────────
# Points per correctly predicted team in each knockout round.
# A team reaching the Round of 32 earns 1 point. Each further correct
# knockout step is worth +2 points, separate from tournament bonuses.
BRACKET_ROUND_POINTS = {
    "round_of_32": 1,
    "round_of_16": 3,
    "quarter_final": 5,
    "semi_final": 7,
    "match_for_third_place": 9,
    "final": 9,
    "world_champion": 11,
}

# ── Tournament bonus point values ─────────────────────────────────
BONUS_POINTS = {
    "world_champion": 20,
    "runner_up": 20,
    "third_place": 20,
    "top_scorer": 20,
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

    Scoring (matches Excel template):
        - Correct outcome (1X2):       3 points
        - Correct home team goals:      2 points
        - Correct away team goals:      2 points
        - Maximum per match:            7 points

    Returns a dict with:
        - points: total points earned
        - outcome_correct: bool
        - home_score_correct: bool
        - away_score_correct: bool
        - perfect: bool (exact scoreline match)
    """
    pred_outcome = _determine_outcome(pred_home, pred_away)
    actual_outcome = _determine_outcome(actual_home, actual_away)

    outcome_correct = pred_outcome == actual_outcome
    home_score_correct = pred_home == actual_home
    away_score_correct = pred_away == actual_away
    perfect = outcome_correct and home_score_correct and away_score_correct

    points = 0
    if outcome_correct:
        points += 3
    if home_score_correct:
        points += 2
    if away_score_correct:
        points += 2

    return {
        "points": points,
        "outcome_correct": outcome_correct,
        "home_score_correct": home_score_correct,
        "away_score_correct": away_score_correct,
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
    pred_bronze_winner_id: Optional[int],
    actual_bronze_winner_id: Optional[int],
    pred_most_goals_team_id: Optional[int] = None,
    actual_most_goals_team_id: Optional[int] = None,
    pred_most_conceded_team_id: Optional[int] = None,
    actual_most_conceded_team_id: Optional[int] = None,
    pred_custom_bonus_1: Optional[str] = None,
    actual_custom_bonus_1: Optional[str] = None,
    pred_custom_bonus_2: Optional[str] = None,
    actual_custom_bonus_2: Optional[str] = None,
    pred_runner_up_id: Optional[int] = None,
    actual_runner_up_id: Optional[int] = None,
) -> dict:
    """
    Calculate points for tournament bonus predictions.

    Current tournament bonus questions:
        - Correct World Cup winner: 20 points
        - Correct runner-up:        20 points
        - Correct third place:      20 points
        - Correct top scorer:       20 points
        - Maximum total bonus:      80 points

    Legacy fields for most goals/conceded/custom bonuses are accepted for
    backwards-compatible callers but are no longer scored.
    """
    points = 0
    result = {
        "winner_correct": False,
        "runner_up_correct": False,
        "top_scorer_correct": False,
        "bronze_winner_correct": False,
        "most_goals_team_correct": False,
        "most_conceded_team_correct": False,
        "custom_bonus_1_correct": False,
        "custom_bonus_2_correct": False,
        "points": 0,
    }

    if pred_winner_id is not None and actual_winner_id is not None and pred_winner_id == actual_winner_id:
        points += BONUS_POINTS["world_champion"]
        result["winner_correct"] = True

    if pred_runner_up_id is not None and actual_runner_up_id is not None and pred_runner_up_id == actual_runner_up_id:
        points += BONUS_POINTS["runner_up"]
        result["runner_up_correct"] = True

    if pred_bronze_winner_id is not None and actual_bronze_winner_id is not None and pred_bronze_winner_id == actual_bronze_winner_id:
        points += BONUS_POINTS["third_place"]
        result["bronze_winner_correct"] = True

    if pred_top_scorer is not None and actual_top_scorer is not None:
        if pred_top_scorer.strip().lower() == actual_top_scorer.strip().lower():
            points += BONUS_POINTS["top_scorer"]
            result["top_scorer_correct"] = True

    result["points"] = points
    return result