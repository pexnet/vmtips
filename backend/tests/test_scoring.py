"""
Tests for the scoring engine.
"""
import pytest
from scoring import calculate_match_points, calculate_tournament_bonus_points


# ── Match scoring ───────────────────────────────────────────

class TestMatchScoring:
    def test_perfect_prediction(self):
        """Exact result gives 7 points (3+2+2) + total goals (1) + margin (1) = 9?"""
        # Actually perfect = outcome(3) + home(2) + away(2) = 7
        # Total goals +1, margin +1 = 9 total
        result = calculate_match_points(2, 1, 2, 1)
        assert result["points"] == 9
        assert result["perfect"] is True
        assert result["outcome_correct"] is True
        assert result["home_score_correct"] is True
        assert result["away_score_correct"] is True
        assert result["total_goals_correct"] is True
        assert result["margin_correct"] is True

    def test_correct_outcome_only(self):
        """Correct winner but wrong scores gives 3 points (margin differs)."""
        result = calculate_match_points(3, 0, 2, 1)
        # outcome(3) + total_goals(1) = 4 because 3+0=3 and 2+1=3
        assert result["points"] == 4
        assert result["outcome_correct"] is True
        assert result["home_score_correct"] is False
        assert result["away_score_correct"] is False
        assert result["total_goals_correct"] is True

    def test_correct_outcome_and_home_score(self):
        """Correct winner + home score gives 5 points (3+2)."""
        result = calculate_match_points(2, 0, 2, 1)
        assert result["points"] == 5
        assert result["outcome_correct"] is True
        assert result["home_score_correct"] is True

    def test_correct_outcome_and_away_score(self):
        """Correct winner + away score gives 5 points (3+2)."""
        result = calculate_match_points(3, 1, 2, 1)
        assert result["points"] == 5
        assert result["outcome_correct"] is True
        assert result["away_score_correct"] is True

    def test_draw_prediction_wrong_scores(self):
        """Predict draw but wrong scores: outcome(3) + margin(1) = 4."""
        result = calculate_match_points(1, 1, 0, 0)
        assert result["points"] == 4
        assert result["outcome_correct"] is True
        assert result["home_score_correct"] is False
        assert result["away_score_correct"] is False
        assert result["margin_correct"] is True
        assert result["total_goals_correct"] is False

    def test_correct_draw_exact(self):
        """Exact draw prediction gives 7 + 1 + 1 = 9 points."""
        result = calculate_match_points(1, 1, 1, 1)
        assert result["points"] == 9
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

    def test_correct_margin_wrong_scores(self):
        """Same margin but different scores: margin(1) + maybe goals."""
        result = calculate_match_points(3, 1, 2, 0)
        assert result["margin_correct"] is True
        assert result["outcome_correct"] is True
        # outcome(3) + margin(1) = 4
        assert result["points"] == 4

    def test_correct_total_goals_wrong_scores(self):
        """Same total goals but different scores."""
        result = calculate_match_points(3, 0, 2, 1)
        assert result["total_goals_correct"] is True
        assert result["outcome_correct"] is True
        # outcome(3) + total_goals(1) = 4
        assert result["points"] == 4

    def test_correct_outcome_nothing_else(self):
        """Only correct outcome: pred 3-2 vs actual 2-0."""
        result = calculate_match_points(3, 2, 2, 0)
        assert result["points"] == 3
        assert result["outcome_correct"] is True
        assert result["home_score_correct"] is False
        assert result["away_score_correct"] is False
        assert result["total_goals_correct"] is False
        assert result["margin_correct"] is False

    def test_completely_wrong(self):
        """Everything wrong gives 0 points."""
        result = calculate_match_points(0, 0, 3, 1)
        assert result["points"] == 0
        assert result["outcome_correct"] is False
        assert result["home_score_correct"] is False
        assert result["away_score_correct"] is False


# ── Tournament bonus scoring ─────────────────────────────────

class TestTournamentBonusScoring:
    def test_winner_correct(self):
        result = calculate_tournament_bonus_points(
            pred_winner_id=1, actual_winner_id=1,
            pred_top_scorer=None, actual_top_scorer=None,
            pred_top_assist=None, actual_top_assist=None,
            pred_total_goals=None, actual_total_goals=None,
        )
        assert result["points"] == 25
        assert result["winner_correct"] is True

    def test_all_correct(self):
        result = calculate_tournament_bonus_points(
            pred_winner_id=1, actual_winner_id=1,
            pred_top_scorer="Mbappe", actual_top_scorer="mbappe",
            pred_top_assist="De Bruyne", actual_top_assist="De Bruyne",
            pred_total_goals=150, actual_total_goals=150,
        )
        assert result["points"] == 100
        assert result["winner_correct"] is True
        assert result["top_scorer_correct"] is True
        assert result["top_assist_correct"] is True
        assert result["total_goals_correct"] is True

    def test_none_correct(self):
        result = calculate_tournament_bonus_points(
            pred_winner_id=1, actual_winner_id=2,
            pred_top_scorer="Mbappe", actual_top_scorer="Kane",
            pred_top_assist="De Bruyne", actual_top_assist="Bellingham",
            pred_total_goals=150, actual_total_goals=200,
        )
        assert result["points"] == 0
        assert result["winner_correct"] is False
        assert result["top_scorer_correct"] is False

    def test_case_insensitive_names(self):
        """Top scorer/assist matching is case-insensitive."""
        result = calculate_tournament_bonus_points(
            pred_winner_id=None, actual_winner_id=None,
            pred_top_scorer="MBAPPE", actual_top_scorer="mbappe",
            pred_top_assist=None, actual_top_assist=None,
            pred_total_goals=None, actual_total_goals=None,
        )
        assert result["points"] == 25
        assert result["top_scorer_correct"] is True

    def test_none_predictions(self):
        """None predictions don't cause errors."""
        result = calculate_tournament_bonus_points(
            pred_winner_id=None, actual_winner_id=1,
            pred_top_scorer=None, actual_top_scorer="Kane",
            pred_top_assist=None, actual_top_assist="De Bruyne",
            pred_total_goals=None, actual_total_goals=150,
        )
        assert result["points"] == 0
        assert result["winner_correct"] is False


# ── Bracket scoring ────────────────────────────────────────────

class TestBracketScoring:
    def test_no_predictions(self):
        """Empty predictions give 0 points."""
        from scoring import calculate_bracket_points
        result = calculate_bracket_points([], [])
        assert result["points"] == 0
        assert result["details"] == []

    def test_no_actual_advancements(self):
        """Predictions with no actual advancements give 0 points."""
        from scoring import calculate_bracket_points
        preds = [{"team_id": 1, "round": "quarter_final"}]
        result = calculate_bracket_points(preds, [])
        assert result["points"] == 0

    def test_correct_round_of_32(self):
        """Correct round_of_32 placement earns 4 points."""
        from scoring import calculate_bracket_points
        preds = [{"team_id": 1, "round": "round_of_32"}]
        actuals = [{"team_id": 1, "round": "round_of_32"}]
        result = calculate_bracket_points(preds, actuals)
        assert result["points"] == 4
        assert len(result["details"]) == 1
        assert result["details"][0]["team_id"] == 1
        assert result["details"][0]["round"] == "round_of_32"
        assert result["details"][0]["points"] == 4

    def test_correct_round_of_16(self):
        """Correct round_of_16 placement earns 6 points."""
        from scoring import calculate_bracket_points
        preds = [{"team_id": 1, "round": "round_of_16"}]
        actuals = [{"team_id": 1, "round": "round_of_16"}]
        result = calculate_bracket_points(preds, actuals)
        assert result["points"] == 6

    def test_correct_quarter_final(self):
        """Correct quarter_final placement earns 8 points."""
        from scoring import calculate_bracket_points
        preds = [{"team_id": 1, "round": "quarter_final"}]
        actuals = [{"team_id": 1, "round": "quarter_final"}]
        result = calculate_bracket_points(preds, actuals)
        assert result["points"] == 8

    def test_correct_semi_final(self):
        """Correct semi_final placement earns 10 points."""
        from scoring import calculate_bracket_points
        preds = [{"team_id": 1, "round": "semi_final"}]
        actuals = [{"team_id": 1, "round": "semi_final"}]
        result = calculate_bracket_points(preds, actuals)
        assert result["points"] == 10

    def test_correct_final(self):
        """Correct final placement earns 15 points."""
        from scoring import calculate_bracket_points
        preds = [{"team_id": 1, "round": "final"}]
        actuals = [{"team_id": 1, "round": "final"}]
        result = calculate_bracket_points(preds, actuals)
        assert result["points"] == 15

    def test_wrong_team_same_round(self):
        """Wrong team in same round gives 0 points for that placement."""
        from scoring import calculate_bracket_points
        preds = [{"team_id": 2, "round": "quarter_final"}]
        actuals = [{"team_id": 1, "round": "quarter_final"}]
        result = calculate_bracket_points(preds, actuals)
        assert result["points"] == 0

    def test_team_in_wrong_round(self):
        """Team predicted in wrong round gives 0 points."""
        from scoring import calculate_bracket_points
        preds = [{"team_id": 1, "round": "quarter_final"}]
        actuals = [{"team_id": 1, "round": "semi_final"}]
        result = calculate_bracket_points(preds, actuals)
        assert result["points"] == 0

    def test_multiple_correct_predictions(self):
        """Multiple correct placements accumulate points."""
        from scoring import calculate_bracket_points
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
        # 6 + 8 + 10 = 24
        assert result["points"] == 24
        assert len(result["details"]) == 3

    def test_mixed_correct_and_wrong(self):
        """Only matching placements earn points."""
        from scoring import calculate_bracket_points
        preds = [
            {"team_id": 1, "round": "round_of_16"},
            {"team_id": 99, "round": "quarter_final"},
        ]
        actuals = [
            {"team_id": 1, "round": "round_of_16"},
            {"team_id": 2, "round": "quarter_final"},
        ]
        result = calculate_bracket_points(preds, actuals)
        assert result["points"] == 6
        assert len(result["details"]) == 1

    def test_bracket_round_points_constant(self):
        """BRACKET_ROUND_POINTS has expected values."""
        from scoring import BRACKET_ROUND_POINTS
        assert BRACKET_ROUND_POINTS["round_of_32"] == 4
        assert BRACKET_ROUND_POINTS["round_of_16"] == 6
        assert BRACKET_ROUND_POINTS["quarter_final"] == 8
        assert BRACKET_ROUND_POINTS["semi_final"] == 10
        assert BRACKET_ROUND_POINTS["final"] == 15
