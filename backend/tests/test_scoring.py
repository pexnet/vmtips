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
