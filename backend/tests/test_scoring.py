"""
Tests for the scoring engine.

Scoring rules:
  - Correct outcome/winner (home/draw/away): 3p
  - Correct home score: 2p
  - Correct away score: 2p
  - Perfect (all 3): 7p

Bracket round points:
  - round_of_32: 1p
  - round_of_16: 1p
  - quarter_final: 1p
  - semi_final: 1p
  - final: 1p
  - match_for_third_place: 1p
  - world_champion: 1p

Tournament bonus points (Excel):
  - World champion: 20p
  - Top scorer: 20p
  - Bronze match winner: 20p
  - Most goals team: 10p
  - Most conceded team: 10p
  - Custom bonus 1/2: 10p each
"""
import pytest
from scoring import calculate_match_points, calculate_tournament_bonus_points, calculate_bracket_points, BRACKET_ROUND_POINTS


# ── Match scoring ───────────────────────────────────────────

class TestMatchScoring:
    def test_perfect_prediction(self):
        """Exact result: outcome(3) + home(2) + away(2) = 7."""
        result = calculate_match_points(2, 1, 2, 1)
        assert result["points"] == 7
        assert result["perfect"] is True
        assert result["outcome_correct"] is True
        assert result["home_score_correct"] is True
        assert result["away_score_correct"] is True

    def test_correct_outcome_only(self):
        """Correct winner but wrong scores: 3p only."""
        result = calculate_match_points(3, 0, 2, 1)
        assert result["points"] == 3
        assert result["outcome_correct"] is True
        assert result["home_score_correct"] is False
        assert result["away_score_correct"] is False

    def test_correct_outcome_and_home_score(self):
        """Correct winner + home score: 3+2 = 5."""
        result = calculate_match_points(2, 0, 2, 1)
        assert result["points"] == 5
        assert result["outcome_correct"] is True
        assert result["home_score_correct"] is True

    def test_correct_outcome_and_away_score(self):
        """Correct winner + away score: 3+2 = 5."""
        result = calculate_match_points(3, 1, 2, 1)
        assert result["points"] == 5
        assert result["outcome_correct"] is True
        assert result["away_score_correct"] is True

    def test_draw_prediction_wrong_scores(self):
        """Predict draw but wrong scores: outcome(3) only."""
        result = calculate_match_points(1, 1, 0, 0)
        assert result["points"] == 3
        assert result["outcome_correct"] is True
        assert result["home_score_correct"] is False
        assert result["away_score_correct"] is False

    def test_correct_draw_exact(self):
        """Exact draw: 3+2+2 = 7."""
        result = calculate_match_points(1, 1, 1, 1)
        assert result["points"] == 7
        assert result["perfect"] is True

    def test_wrong_outcome_right_home_score(self):
        """Wrong outcome but correct home score: 2 points."""
        result = calculate_match_points(2, 0, 2, 3)
        assert result["points"] == 2
        assert result["outcome_correct"] is False
        assert result["home_score_correct"] is True

    def test_wrong_outcome_right_away_score(self):
        """Wrong outcome but correct away score: 2 points."""
        result = calculate_match_points(0, 1, 2, 1)
        assert result["points"] == 2
        assert result["outcome_correct"] is False
        assert result["away_score_correct"] is True

    def test_wrong_outcome_nothing_else(self):
        """Only correct outcome: pred 3-2 vs actual 2-0."""
        result = calculate_match_points(3, 2, 2, 0)
        assert result["points"] == 3
        assert result["outcome_correct"] is True
        assert result["home_score_correct"] is False
        assert result["away_score_correct"] is False

    def test_completely_wrong(self):
        """Everything wrong gives 0 points."""
        result = calculate_match_points(0, 0, 3, 1)
        assert result["points"] == 0
        assert result["outcome_correct"] is False
        assert result["home_score_correct"] is False
        assert result["away_score_correct"] is False


# ── Tournament bonus scoring ────────────────────────────────

class TestTournamentBonusScoring:
    def test_winner_correct(self):
        result = calculate_tournament_bonus_points(
            pred_winner_id=1, actual_winner_id=1,
            pred_top_scorer=None, actual_top_scorer=None,
            pred_bronze_winner_id=None, actual_bronze_winner_id=None,
            pred_most_goals_team_id=None, actual_most_goals_team_id=None,
            pred_most_conceded_team_id=None, actual_most_conceded_team_id=None,
            pred_custom_bonus_1=None, actual_custom_bonus_1=None,
            pred_custom_bonus_2=None, actual_custom_bonus_2=None,
        )
        assert result["points"] == 20
        assert result["winner_correct"] is True

    def test_top_scorer_correct(self):
        result = calculate_tournament_bonus_points(
            pred_winner_id=None, actual_winner_id=None,
            pred_top_scorer="Mbappe", actual_top_scorer="mbappe",
            pred_bronze_winner_id=None, actual_bronze_winner_id=None,
            pred_most_goals_team_id=None, actual_most_goals_team_id=None,
            pred_most_conceded_team_id=None, actual_most_conceded_team_id=None,
            pred_custom_bonus_1=None, actual_custom_bonus_1=None,
            pred_custom_bonus_2=None, actual_custom_bonus_2=None,
        )
        assert result["points"] == 20
        assert result["top_scorer_correct"] is True

    def test_bronze_winner_correct(self):
        result = calculate_tournament_bonus_points(
            pred_winner_id=None, actual_winner_id=None,
            pred_top_scorer=None, actual_top_scorer=None,
            pred_bronze_winner_id=3, actual_bronze_winner_id=3,
            pred_most_goals_team_id=None, actual_most_goals_team_id=None,
            pred_most_conceded_team_id=None, actual_most_conceded_team_id=None,
            pred_custom_bonus_1=None, actual_custom_bonus_1=None,
            pred_custom_bonus_2=None, actual_custom_bonus_2=None,
        )
        assert result["points"] == 20
        assert result["bronze_winner_correct"] is True

    def test_runner_up_correct(self):
        result = calculate_tournament_bonus_points(
            pred_winner_id=None, actual_winner_id=None,
            pred_runner_up_id=2, actual_runner_up_id=2,
            pred_top_scorer=None, actual_top_scorer=None,
            pred_bronze_winner_id=None, actual_bronze_winner_id=None,
        )
        assert result["points"] == 20
        assert result["runner_up_correct"] is True

    def test_most_goals_correct(self):
        result = calculate_tournament_bonus_points(
            pred_winner_id=None, actual_winner_id=None,
            pred_top_scorer=None, actual_top_scorer=None,
            pred_bronze_winner_id=None, actual_bronze_winner_id=None,
            pred_most_goals_team_id=5, actual_most_goals_team_id=5,
            pred_most_conceded_team_id=None, actual_most_conceded_team_id=None,
            pred_custom_bonus_1=None, actual_custom_bonus_1=None,
            pred_custom_bonus_2=None, actual_custom_bonus_2=None,
        )
        assert result["points"] == 0
        assert result["most_goals_team_correct"] is False

    def test_most_conceded_correct(self):
        result = calculate_tournament_bonus_points(
            pred_winner_id=None, actual_winner_id=None,
            pred_top_scorer=None, actual_top_scorer=None,
            pred_bronze_winner_id=None, actual_bronze_winner_id=None,
            pred_most_goals_team_id=None, actual_most_goals_team_id=None,
            pred_most_conceded_team_id=7, actual_most_conceded_team_id=7,
            pred_custom_bonus_1=None, actual_custom_bonus_1=None,
            pred_custom_bonus_2=None, actual_custom_bonus_2=None,
        )
        assert result["points"] == 0
        assert result["most_conceded_team_correct"] is False

    def test_all_correct(self):
        result = calculate_tournament_bonus_points(
            pred_winner_id=1, actual_winner_id=1,
            pred_runner_up_id=2, actual_runner_up_id=2,
            pred_top_scorer="Mbappe", actual_top_scorer="mbappe",
            pred_bronze_winner_id=3, actual_bronze_winner_id=3,
            pred_most_goals_team_id=5, actual_most_goals_team_id=5,
            pred_most_conceded_team_id=7, actual_most_conceded_team_id=7,
            pred_custom_bonus_1="Sweden", actual_custom_bonus_1="Sweden",
            pred_custom_bonus_2="Brazil", actual_custom_bonus_2="Brazil",
        )
        # Winner + runner-up + third place + top scorer = 80
        assert result["points"] == 80
        assert result["winner_correct"] is True
        assert result["runner_up_correct"] is True
        assert result["top_scorer_correct"] is True
        assert result["bronze_winner_correct"] is True
        assert result["most_goals_team_correct"] is False
        assert result["most_conceded_team_correct"] is False
        assert result["custom_bonus_1_correct"] is False
        assert result["custom_bonus_2_correct"] is False

    def test_none_correct(self):
        result = calculate_tournament_bonus_points(
            pred_winner_id=1, actual_winner_id=2,
            pred_top_scorer="Mbappe", actual_top_scorer="Kane",
            pred_bronze_winner_id=3, actual_bronze_winner_id=4,
            pred_most_goals_team_id=5, actual_most_goals_team_id=6,
            pred_most_conceded_team_id=7, actual_most_conceded_team_id=8,
            pred_custom_bonus_1="A", actual_custom_bonus_1="B",
            pred_custom_bonus_2="C", actual_custom_bonus_2="D",
        )
        assert result["points"] == 0
        assert result["winner_correct"] is False
        assert result["top_scorer_correct"] is False

    def test_case_insensitive_names(self):
        """Top scorer matching is case-insensitive."""
        result = calculate_tournament_bonus_points(
            pred_winner_id=None, actual_winner_id=None,
            pred_top_scorer="MBAPPE", actual_top_scorer="mbappe",
            pred_bronze_winner_id=None, actual_bronze_winner_id=None,
            pred_most_goals_team_id=None, actual_most_goals_team_id=None,
            pred_most_conceded_team_id=None, actual_most_conceded_team_id=None,
            pred_custom_bonus_1=None, actual_custom_bonus_1=None,
            pred_custom_bonus_2=None, actual_custom_bonus_2=None,
        )
        assert result["points"] == 20
        assert result["top_scorer_correct"] is True

    def test_none_predictions(self):
        """None predictions don't cause errors."""
        result = calculate_tournament_bonus_points(
            pred_winner_id=None, actual_winner_id=1,
            pred_top_scorer=None, actual_top_scorer="Kane",
            pred_bronze_winner_id=None, actual_bronze_winner_id=None,
            pred_most_goals_team_id=None, actual_most_goals_team_id=None,
            pred_most_conceded_team_id=None, actual_most_conceded_team_id=None,
            pred_custom_bonus_1=None, actual_custom_bonus_1=None,
            pred_custom_bonus_2=None, actual_custom_bonus_2=None,
        )
        assert result["points"] == 0
        assert result["winner_correct"] is False


# ── Bracket scoring ──────────────────────────────────────────

class TestBracketScoring:
    def test_no_predictions(self):
        """Empty predictions give 0 points."""
        result = calculate_bracket_points([], [])
        assert result["points"] == 0
        assert result["details"] == []

    def test_no_actual_advancements(self):
        """Predictions with no actual advancements give 0 points."""
        preds = [{"team_id": 1, "round": "quarter_final"}]
        result = calculate_bracket_points(preds, [])
        assert result["points"] == 0

    def test_correct_round_of_32(self):
        """Correct round_of_32 placement earns 1 point."""
        preds = [{"team_id": 1, "round": "round_of_32"}]
        actuals = [{"team_id": 1, "round": "round_of_32"}]
        result = calculate_bracket_points(preds, actuals)
        assert result["points"] == 1
        assert result["details"][0]["points"] == 1

    def test_correct_round_of_16(self):
        """Correct round_of_16 placement earns a flat 1 point."""
        preds = [{"team_id": 1, "round": "round_of_16"}]
        actuals = [{"team_id": 1, "round": "round_of_16"}]
        result = calculate_bracket_points(preds, actuals)
        assert result["points"] == 1

    def test_correct_quarter_final(self):
        """Correct quarter_final placement earns a flat 1 point."""
        preds = [{"team_id": 1, "round": "quarter_final"}]
        actuals = [{"team_id": 1, "round": "quarter_final"}]
        result = calculate_bracket_points(preds, actuals)
        assert result["points"] == 1

    def test_correct_semi_final(self):
        """Correct semi_final placement earns a flat 1 point."""
        preds = [{"team_id": 1, "round": "semi_final"}]
        actuals = [{"team_id": 1, "round": "semi_final"}]
        result = calculate_bracket_points(preds, actuals)
        assert result["points"] == 1

    def test_correct_final(self):
        """Correct final placement earns a flat 1 point."""
        preds = [{"team_id": 1, "round": "final"}]
        actuals = [{"team_id": 1, "round": "final"}]
        result = calculate_bracket_points(preds, actuals)
        assert result["points"] == 1

    def test_correct_match_for_third_place(self):
        """Correct match_for_third_place placement earns a flat 1 point."""
        preds = [{"team_id": 1, "round": "match_for_third_place"}]
        actuals = [{"team_id": 1, "round": "match_for_third_place"}]
        result = calculate_bracket_points(preds, actuals)
        assert result["points"] == 1

    def test_correct_world_champion(self):
        """Correct world_champion placement earns a flat 1 point."""
        preds = [{"team_id": 1, "round": "world_champion"}]
        actuals = [{"team_id": 1, "round": "world_champion"}]
        result = calculate_bracket_points(preds, actuals)
        assert result["points"] == 1

    def test_wrong_team_same_round(self):
        """Wrong team in same round gives 0 points."""
        preds = [{"team_id": 2, "round": "quarter_final"}]
        actuals = [{"team_id": 1, "round": "quarter_final"}]
        result = calculate_bracket_points(preds, actuals)
        assert result["points"] == 0

    def test_team_in_wrong_round(self):
        """Team predicted in wrong round gives 0 points."""
        preds = [{"team_id": 1, "round": "quarter_final"}]
        actuals = [{"team_id": 1, "round": "semi_final"}]
        result = calculate_bracket_points(preds, actuals)
        assert result["points"] == 0

    def test_multiple_correct_predictions(self):
        """Multiple correct placements accumulate points."""
        preds = [
            {"team_id": 1, "round": "round_of_16"},
            {"team_id": 2, "round": "quarter_final"},
            {"team_id": 3, "round": "semi_final"},
        ]
        actuals = [
            {"team_id": 1, "round": "round_of_16"},
            {"team_id": 2, "round": "quarter_final"},
            {"team_id": 3, "round": "semi_final"},
        ]
        result = calculate_bracket_points(preds, actuals)
        # 1 + 1 + 1 = 3
        assert result["points"] == 3
        assert len(result["details"]) == 3

    def test_mixed_correct_and_wrong(self):
        """Only matching placements earn points."""
        preds = [
            {"team_id": 1, "round": "round_of_16"},
            {"team_id": 99, "round": "quarter_final"},
        ]
        actuals = [
            {"team_id": 1, "round": "round_of_16"},
            {"team_id": 2, "round": "quarter_final"},
        ]
        result = calculate_bracket_points(preds, actuals)
        assert result["points"] == 1
        assert len(result["details"]) == 1

    def test_bracket_round_points_constant(self):
        """BRACKET_ROUND_POINTS has expected current VMTips values (flat 1p)."""
        assert BRACKET_ROUND_POINTS["round_of_32"] == 1
        assert BRACKET_ROUND_POINTS["round_of_16"] == 1
        assert BRACKET_ROUND_POINTS["quarter_final"] == 1
        assert BRACKET_ROUND_POINTS["semi_final"] == 1
        assert BRACKET_ROUND_POINTS["final"] == 1
        assert BRACKET_ROUND_POINTS["match_for_third_place"] == 1
        assert BRACKET_ROUND_POINTS["world_champion"] == 1