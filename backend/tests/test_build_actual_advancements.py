"""
Tests for bracket_engine.build_actual_advancements.

The helper is the single source of truth for "which teams actually
advanced to which knockout round". Both admin and leaderboard routers
depend on it. These tests cover:

1. Empty database (no advancements, no finished matches) -> empty list.
2. Only explicit KnockoutAdvancement rows -> returns those, ignoring
   any finished matches.
3. Fallback to finished knockout matches when no explicit rows.
4. Deduplication when the same (team_id, round) appears in multiple
   matches (shouldn't happen in practice but the helper is defensive).
5. Group matches are ignored even when finished.
"""
from bracket_engine import build_actual_advancements
from models import Match, KnockoutAdvancement, Team


def _team(db, code: str, group: str = "A") -> Team:
    t = Team(name=code, code=code, group=group, flag_emoji="x")
    db.add(t)
    db.flush()
    return t


def _match(db, number: int, round_: str, home: Team, away: Team, finished: bool) -> Match:
    m = Match(
        match_number=number,
        group=None if round_ != "group" else home.group,
        round=round_,
        home_team_id=home.id,
        away_team_id=away.id,
        match_date=__import__("datetime").datetime(2026, 6, 1),
        status="finished" if finished else "scheduled",
    )
    if finished:
        m.home_goals = 2
        m.away_goals = 1
    db.add(m)
    db.flush()
    return m


class TestBuildActualAdvancements:
    def test_empty_db_returns_empty_list(self, db):
        """No advancements, no finished matches -> empty result."""
        result = build_actual_advancements(db)
        assert result == []

    def test_uses_explicit_advancement_rows(self, db):
        """When KnockoutAdvancement rows exist, finished matches are ignored."""
        t1 = _team(db, "BRA")
        # An explicit advancement for team 1 in round_of_32
        adv = KnockoutAdvancement(team_id=t1.id, round="round_of_32")
        db.add(adv)
        db.commit()

        result = build_actual_advancements(db)
        assert len(result) == 1
        assert result[0] == {"team_id": t1.id, "round": "round_of_32"}

    def test_explicit_advancements_ignore_finished_matches(self, db):
        """If explicit rows exist, finished matches don't add more entries."""
        t1 = _team(db, "BRA")
        t2 = _team(db, "GER")
        # Explicit advancement for t1 only
        db.add(KnockoutAdvancement(team_id=t1.id, round="round_of_32"))
        # But t2 also appears in a finished round_of_32 match
        _match(db, 73, "round_of_32", t1, t2, finished=True)
        db.commit()

        result = build_actual_advancements(db)
        # Only the explicit row is returned
        assert result == [{"team_id": t1.id, "round": "round_of_32"}]

    def test_fallback_to_finished_matches(self, db):
        """With no explicit rows, derive from finished knockout matches."""
        t1 = _team(db, "BRA")
        t2 = _team(db, "GER")
        _match(db, 73, "round_of_32", t1, t2, finished=True)
        db.commit()

        result = build_actual_advancements(db)
        # t1 and t2 both appear in round_of_32
        assert {"team_id": t1.id, "round": "round_of_32"} in result
        assert {"team_id": t2.id, "round": "round_of_32"} in result
        assert len(result) == 2

    def test_finished_group_matches_ignored(self, db):
        """Group matches with status=finished must not appear in the result."""
        t1 = _team(db, "BRA", group="A")
        t2 = _team(db, "GER", group="A")
        _match(db, 1, "group", t1, t2, finished=True)
        db.commit()

        result = build_actual_advancements(db)
        assert result == []

    def test_scheduled_knockout_matches_ignored(self, db):
        """Knockout matches that are scheduled (not finished) are skipped."""
        t1 = _team(db, "BRA")
        t2 = _team(db, "GER")
        _match(db, 73, "round_of_32", t1, t2, finished=False)
        db.commit()

        result = build_actual_advancements(db)
        assert result == []

    def test_deduplicates_team_round_pairs(self, db):
        """If the same (team_id, round) appears in multiple matches, only one entry."""
        t1 = _team(db, "BRA")
        t2 = _team(db, "GER")
        # Two separate finished matches in the same round with overlapping teams
        _match(db, 73, "round_of_32", t1, t2, finished=True)
        _match(db, 74, "round_of_32", t1, t2, finished=True)
        db.commit()

        result = build_actual_advancements(db)
        # Each (team, round) pair appears once
        pairs = {(a["team_id"], a["round"]) for a in result}
        assert pairs == {(t1.id, "round_of_32"), (t2.id, "round_of_32")}
        assert len(result) == 2

    def test_mixed_rounds(self, db):
        """Teams advance through multiple rounds; all should be captured."""
        t1 = _team(db, "BRA")
        t2 = _team(db, "GER")
        # t1 wins R32 and R16
        _match(db, 73, "round_of_32", t1, t2, finished=True)
        _match(db, 89, "round_of_16", t1, t2, finished=True)
        db.commit()

        result = build_actual_advancements(db)
        rounds_by_team = {a["team_id"]: set() for a in result}
        for a in result:
            rounds_by_team[a["team_id"]].add(a["round"])
        # Both teams appear in both rounds (finished match = both teams advanced)
        assert rounds_by_team[t1.id] == {"round_of_32", "round_of_16"}
        assert rounds_by_team[t2.id] == {"round_of_32", "round_of_16"}
