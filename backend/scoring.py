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
# A user predicts which teams advance; if a team they predicted for round X
# actually appears in that round, they earn these points.
BRACKET_ROUND_POINTS = {
    "round_of_32": 1,
    "round_of_16": 2,
    "quarter_final": 4,
    "semi_final": 6,
    "match_for_third_place": 8,
    "final": 8,
    "world_champion": 20,
}

# ── Tournament bonus point values ─────────────────────────────────
BONUS_POINTS = {
    "world_champion": 20,
    "top_scorer": 20,
    "bronze_match_winner": 20,
    "most_goals_team": 10,
    "most_conceded_team": 10,
    "custom_bonus_1": 10,
    "custom_bonus_2": 10,
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
    pred_most_goals_team_id: Optional[int],
    actual_most_goals_team_id: Optional[int],
    pred_most_conceded_team_id: Optional[int],
    actual_most_conceded_team_id: Optional[int],
    pred_custom_bonus_1: Optional[str],
    actual_custom_bonus_1: Optional[str],
    pred_custom_bonus_2: Optional[str],
    actual_custom_bonus_2: Optional[str],
) -> dict:
    """
    Calculate points for tournament bonus predictions.

    Scoring (matches Excel template):
        - Correct world champion:        20 points
        - Correct top scorer:            20 points
        - Correct bronze match winner:   20 points
        - Correct most goals team:       10 points
        - Correct most conceded team:     10 points
        - Correct custom bonus 1:        10 points
        - Correct custom bonus 2:        10 points
        - Maximum total bonus:         100 points

    Note: Top scorer name must be spelled exactly the same as the admin answer.
    """
    points = 0
    result = {
        "winner_correct": False,
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

    if pred_top_scorer is not None and actual_top_scorer is not None:
        if pred_top_scorer.strip().lower() == actual_top_scorer.strip().lower():
            points += BONUS_POINTS["top_scorer"]
            result["top_scorer_correct"] = True

    if pred_bronze_winner_id is not None and actual_bronze_winner_id is not None and pred_bronze_winner_id == actual_bronze_winner_id:
        points += BONUS_POINTS["bronze_match_winner"]
        result["bronze_winner_correct"] = True

    if pred_most_goals_team_id is not None and actual_most_goals_team_id is not None and pred_most_goals_team_id == actual_most_goals_team_id:
        points += BONUS_POINTS["most_goals_team"]
        result["most_goals_team_correct"] = True

    if pred_most_conceded_team_id is not None and actual_most_conceded_team_id is not None and pred_most_conceded_team_id == actual_most_conceded_team_id:
        points += BONUS_POINTS["most_conceded_team"]
        result["most_conceded_team_correct"] = True

    if pred_custom_bonus_1 is not None and actual_custom_bonus_1 is not None:
        if pred_custom_bonus_1.strip().lower() == actual_custom_bonus_1.strip().lower():
            points += BONUS_POINTS["custom_bonus_1"]
            result["custom_bonus_1_correct"] = True

    if pred_custom_bonus_2 is not None and actual_custom_bonus_2 is not None:
        if pred_custom_bonus_2.strip().lower() == actual_custom_bonus_2.strip().lower():
            points += BONUS_POINTS["custom_bonus_2"]
            result["custom_bonus_2_correct"] = True

    result["points"] = points
    return result