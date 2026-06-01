#!/usr/bin/env python3
"""
Run a deterministic full-tournament simulation for VMTips.

The script resets and seeds the database by default, creates the test user,
then advances the tournament from the start up to the selected phase.

Usage:
    python scripts/simulate_tournament.py --phase summary
    python scripts/simulate_tournament.py --phase group_scored
    python scripts/simulate_tournament.py --phase final_scored --no-reset

Phases:
    start
    group_tipped, group_scored
    r32_tipped, r32_scored
    r16_tipped, r16_scored
    qf_tipped, qf_scored
    sf_tipped, sf_scored
    bronze_tipped, bronze_scored
    final_tipped, final_scored
    summary
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from database import Base, SessionLocal, engine  # noqa: E402
from models import (  # noqa: E402
    BracketPrediction,
    GroupStanding,
    KnockoutAdvancement,
    League,
    LeagueMember,
    Match,
    Prediction,
    Score,
    Team,
    TournamentPhase,
    User,
)
from routers.admin import recalculate_scores  # noqa: E402
from scoring import BRACKET_ROUND_POINTS  # noqa: E402
from security import get_password_hash  # noqa: E402
from seed import (  # noqa: E402
    seed_admin,
    seed_default_league,
    seed_group_matches,
    seed_knockout_matches,
    seed_teams,
    seed_tournament_phase,
    seed_tournament_result,
)
from bracket_engine import (  # noqa: E402
    compute_third_place_rankings,
    resolve_r32_teams,
    save_generated_bracket,
)
from fifa_standings import sort_group_teams  # noqa: E402


TEST_EMAIL = "test@vmtips.se"
TEST_PASSWORD = "test123"
TEST_NAME = "Testare"

PHASE_ORDER = [
    "start",
    "group_tipped",
    "group_scored",
    "r32_tipped",
    "r32_scored",
    "r16_tipped",
    "r16_scored",
    "qf_tipped",
    "qf_scored",
    "sf_tipped",
    "sf_scored",
    "bronze_tipped",
    "bronze_scored",
    "final_tipped",
    "final_scored",
    "summary",
]

PHASE_ALIASES = {
    "gruppspel_tippat": "group_tipped",
    "gruppspel_rattat": "group_scored",
    "16_delsfinal_tippad": "r32_tipped",
    "16_delsfinal_rattad": "r32_scored",
    "sextondelsfinal_tippad": "r32_tipped",
    "sextondelsfinal_rattad": "r32_scored",
    "8_delsfinal_tippad": "r16_tipped",
    "8_delsfinal_rattad": "r16_scored",
    "attondelsfinal_tippad": "r16_tipped",
    "attondelsfinal_rattad": "r16_scored",
    "kvartsfinal_tippad": "qf_tipped",
    "kvartsfinal_rattad": "qf_scored",
    "semifinal_tippad": "sf_tipped",
    "semifinal_rattad": "sf_scored",
    "bronsmatch_tippad": "bronze_tipped",
    "bronsmatch_rattad": "bronze_scored",
    "final_tippad": "final_tipped",
    "final_rattad": "final_scored",
    "slutsummering": "summary",
}

ROUND_MATCHES = {
    "group": range(1, 73),
    "round_of_32": range(73, 89),
    "round_of_16": range(89, 97),
    "quarter_final": range(97, 101),
    "semi_final": range(101, 103),
    "match_for_third_place": range(103, 104),
    "final": range(104, 105),
}

ADVANCEMENT_ROUND_BY_MATCH_ROUND = {
    "round_of_32": "round_of_32",
    "round_of_16": "round_of_16",
    "quarter_final": "quarter_final",
    "semi_final": "semi_final",
    "match_for_third_place": "match_for_third_place",
    "final": "final",
}


def print_step(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def seed_database(reset: bool) -> None:
    if reset:
        print_step("Reset and seed database")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print("[simulate] Dropped and recreated all tables")
    else:
        print_step("Seed missing base data")
        Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_teams(db)
        seed_group_matches(db)
        seed_knockout_matches(db)
        seed_admin(db)
        seed_tournament_phase(db)
        seed_tournament_result(db)
        seed_default_league(db)
        ensure_test_user(db)
    finally:
        db.close()


def ensure_test_user(db):
    user = db.query(User).filter(User.email == TEST_EMAIL).first()
    if not user:
        user = User(
            email=TEST_EMAIL,
            password_hash=get_password_hash(TEST_PASSWORD),
            display_name=TEST_NAME,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"[simulate] Created test user: {TEST_EMAIL} / {TEST_PASSWORD}")

    league = db.query(League).filter(League.name == "VM2026").first()
    if not league:
        raise RuntimeError("VM2026 league was not created by seed_default_league")

    membership = (
        db.query(LeagueMember)
        .filter(LeagueMember.user_id == user.id, LeagueMember.league_id == league.id)
        .first()
    )
    if not membership:
        db.add(LeagueMember(user_id=user.id, league_id=league.id))
        db.commit()
        print("[simulate] Test user joined VM2026")

    return user, league


def get_user_and_league(db):
    user = db.query(User).filter(User.email == TEST_EMAIL).first()
    league = db.query(League).filter(League.name == "VM2026").first()
    if not user or not league:
        raise RuntimeError("Missing test user or VM2026 league. Run with --reset first.")
    return user, league


def set_phase(db, phase_name: str) -> None:
    row = db.query(TournamentPhase).first()
    if not row:
        row = TournamentPhase(phase=phase_name)
        db.add(row)
    else:
        row.phase = phase_name
    db.commit()
    print(f"[simulate] Tournament phase: {phase_name}")


def score_for_prediction(match_number: int, salt: int = 0) -> tuple[int, int]:
    """Deterministic varied scores, including draws for group matches."""
    home = (match_number * 3 + salt) % 5
    away = (match_number * 7 + salt + 1) % 4
    return home, away


def _outcome(home: int, away: int) -> int:
    return (home > away) - (home < away)


def _match_points(pred_home: int, pred_away: int, actual_home: int, actual_away: int) -> int:
    points = 0
    if _outcome(pred_home, pred_away) == _outcome(actual_home, actual_away):
        points += 3
    if pred_home == actual_home:
        points += 2
    if pred_away == actual_away:
        points += 2
    return points


def _find_prediction_with_points(
    actual_home: int,
    actual_away: int,
    target_points: int,
    *,
    change_both_scores: bool = False,
) -> tuple[int, int]:
    for home in range(0, 8):
        for away in range(0, 8):
            if change_both_scores and (home == actual_home or away == actual_away):
                continue
            if _match_points(home, away, actual_home, actual_away) == target_points:
                return home, away
    raise RuntimeError("Could not generate requested prediction score")


def group_prediction_for_match(match_number: int) -> tuple[int, int]:
    """Create predictable test coverage for all match scoring variants."""
    actual_home, actual_away = score_for_prediction(match_number, salt=3)

    variant = match_number % 5
    if variant == 0:
        # Perfect: outcome + both team scores = 7p.
        return actual_home, actual_away
    if variant == 1:
        # Correct outcome only = 3p.
        return _find_prediction_with_points(actual_home, actual_away, 3, change_both_scores=True)
    if variant in {2, 3}:
        # One team score correct only = 2p.
        return _find_prediction_with_points(actual_home, actual_away, 2)

    # No scoring component correct = 0p.
    return _find_prediction_with_points(actual_home, actual_away, 0)


def knockout_score(match_number: int, salt: int = 0) -> tuple[int, int]:
    """Deterministic non-draw knockout scores."""
    if (match_number + salt) % 2 == 0:
        return 2 + ((match_number + salt) % 2), 1
    return 0, 1 + ((match_number + salt) % 3)


def upsert_prediction(db, user_id: int, league_id: int, match: Match, home: int, away: int) -> None:
    pred = (
        db.query(Prediction)
        .filter(
            Prediction.user_id == user_id,
            Prediction.league_id == league_id,
            Prediction.match_id == match.id,
        )
        .first()
    )
    if pred:
        pred.home_goals = home
        pred.away_goals = away
    else:
        db.add(
            Prediction(
                user_id=user_id,
                league_id=league_id,
                match_id=match.id,
                home_goals=home,
                away_goals=away,
            )
        )


def tip_matches(db, user, league, round_name: str) -> None:
    matches = (
        db.query(Match)
        .filter(Match.round == round_name)
        .order_by(Match.match_number)
        .all()
    )
    for match in matches:
        if round_name == "group":
            home, away = group_prediction_for_match(match.match_number)
        else:
            home, away = knockout_score(match.match_number, salt=2)
        upsert_prediction(db, user.id, league.id, match, home, away)
    db.commit()

    if round_name != "group":
        result = save_generated_bracket(db, user.id, league.id)
        print(f"[simulate] Regenerated bracket predictions: {result['created']}")

    print(f"[simulate] Tipped {len(matches)} {round_name} matches for {TEST_EMAIL}")


def score_matches(db, round_name: str) -> None:
    matches = (
        db.query(Match)
        .filter(Match.round == round_name)
        .order_by(Match.match_number)
        .all()
    )
    for match in matches:
        if round_name == "group":
            home, away = score_for_prediction(match.match_number, salt=3)
        else:
            home, away = knockout_score(match.match_number, salt=5)
        match.home_goals = home
        match.away_goals = away
        match.status = "finished"
    db.commit()
    print(f"[simulate] Scored {len(matches)} {round_name} matches")


def compute_group_standings(db) -> dict[str, list[dict]]:
    db.query(GroupStanding).delete(synchronize_session=False)

    teams = db.query(Team).all()
    standings = {
        team.id: {
            "team_id": team.id,
            "name": team.name,
            "code": team.code,
            "flag_emoji": team.flag_emoji,
            "group": team.group,
            "played": 0,
            "won": 0,
            "drawn": 0,
            "lost": 0,
            "gf": 0,
            "ga": 0,
            "gd": 0,
            "points": 0,
        }
        for team in teams
    }

    matches = db.query(Match).filter(Match.round == "group", Match.status == "finished").all()
    for match in matches:
        if match.home_team_id is None or match.away_team_id is None:
            continue
        for team_id, goals_for, goals_against in [
            (match.home_team_id, match.home_goals, match.away_goals),
            (match.away_team_id, match.away_goals, match.home_goals),
        ]:
            row = standings[team_id]
            row["played"] += 1
            row["gf"] += goals_for
            row["ga"] += goals_against
            row["gd"] = row["gf"] - row["ga"]
            if goals_for > goals_against:
                row["won"] += 1
                row["points"] += 3
            elif goals_for == goals_against:
                row["drawn"] += 1
                row["points"] += 1
            else:
                row["lost"] += 1

    groups: dict[str, list[dict]] = {}
    for row in standings.values():
        groups.setdefault(row["group"], []).append(row)

    group_matches = db.query(Match).filter(Match.round == "group", Match.status == "finished").all()
    for group, group_rows in groups.items():
        groups[group] = sort_group_teams(group_rows, group_matches)

    for group, group_rows in groups.items():
        for index, row in enumerate(group_rows, start=1):
            db.add(
                GroupStanding(
                    team_id=row["team_id"],
                    group=group,
                    position=index,
                    played=row["played"],
                    won=row["won"],
                    drawn=row["drawn"],
                    lost=row["lost"],
                    goals_for=row["gf"],
                    goals_against=row["ga"],
                    goal_difference=row["gd"],
                    points=row["points"],
                )
            )
    db.commit()
    print("[simulate] Computed group standings")
    return groups


def populate_round_of_32(db, groups: dict[str, list[dict]]) -> None:
    third_places = compute_third_place_rankings(groups)
    r32 = resolve_r32_teams(groups, third_places)

    for match_number, sides in r32.items():
        match = db.query(Match).filter(Match.match_number == match_number).first()
        if not match:
            continue
        if sides["home"]:
            match.home_team_id = sides["home"]
            match.home_team_placeholder = None
        if sides["away"]:
            match.away_team_id = sides["away"]
            match.away_team_placeholder = None
    db.commit()
    record_round_advancements(db, "round_of_32")
    print("[simulate] Populated Round of 32 teams")


def winner_id(match: Match) -> int | None:
    if match.home_team_id is None or match.away_team_id is None:
        return None
    if match.home_goals is None or match.away_goals is None:
        return None
    return match.home_team_id if match.home_goals > match.away_goals else match.away_team_id


def loser_id(match: Match) -> int | None:
    if match.home_team_id is None or match.away_team_id is None:
        return None
    if match.home_goals is None or match.away_goals is None:
        return None
    return match.away_team_id if match.home_goals > match.away_goals else match.home_team_id


def resolve_placeholder(placeholder: str | None, winners: dict[int, int], losers: dict[int, int]) -> int | None:
    if not placeholder:
        return None
    source = placeholder.strip().upper()
    try:
        if source.startswith("W"):
            return winners.get(int(source[1:]))
        if source.startswith("L"):
            return losers.get(int(source[1:]))
    except ValueError:
        return None
    return None


def populate_round_from_previous(db, round_name: str) -> None:
    matches = db.query(Match).filter(Match.status == "finished").all()
    winners = {match.match_number: winner_id(match) for match in matches}
    losers = {match.match_number: loser_id(match) for match in matches}

    target_matches = (
        db.query(Match)
        .filter(Match.round == round_name)
        .order_by(Match.match_number)
        .all()
    )
    for match in target_matches:
        home_id = resolve_placeholder(match.home_team_placeholder, winners, losers)
        away_id = resolve_placeholder(match.away_team_placeholder, winners, losers)
        if home_id:
            match.home_team_id = home_id
        if away_id:
            match.away_team_id = away_id
    db.commit()
    record_round_advancements(db, round_name)
    print(f"[simulate] Populated {round_name} teams")


def record_round_advancements(db, round_name: str) -> None:
    db.query(KnockoutAdvancement).filter(KnockoutAdvancement.round == round_name).delete(
        synchronize_session=False
    )
    matches = db.query(Match).filter(Match.round == round_name).all()
    for match in matches:
        if match.home_team_id:
            db.add(
                KnockoutAdvancement(
                    team_id=match.home_team_id,
                    round=round_name,
                    match_number=match.match_number,
                )
            )
        if match.away_team_id:
            db.add(
                KnockoutAdvancement(
                    team_id=match.away_team_id,
                    round=round_name,
                    match_number=match.match_number,
                )
            )
    db.commit()


def record_world_champion(db) -> None:
    final = db.query(Match).filter(Match.round == "final").first()
    champion = winner_id(final) if final else None
    if not champion:
        return
    db.query(KnockoutAdvancement).filter(KnockoutAdvancement.round == "world_champion").delete(
        synchronize_session=False
    )
    db.add(KnockoutAdvancement(team_id=champion, round="world_champion", match_number=104))
    db.commit()
    print("[simulate] Recorded world champion advancement")


def recalculate(db, user, league) -> None:
    result = recalculate_scores(admin=user, db=db)
    score = (
        db.query(Score)
        .filter(Score.user_id == user.id, Score.league_id == league.id)
        .first()
    )
    print(
        "[simulate] Recalculated scores: "
        f"matches={result['matches_processed']} users={result['users_updated']}"
    )
    if score:
        print(
            "[simulate] Test user score: "
            f"match={score.match_points}, bracket={score.bracket_points}, "
            f"bonus={score.tournament_bonus_points}, total={score.total_points}"
        )


def print_summary(db, user, league) -> None:
    print_step("Simulation summary")
    phase = db.query(TournamentPhase).first()
    score = (
        db.query(Score)
        .filter(Score.user_id == user.id, Score.league_id == league.id)
        .first()
    )
    print(f"User: {user.display_name} <{user.email}> password={TEST_PASSWORD}")
    print(f"League: {league.name} (id={league.id})")
    print(f"Phase: {phase.phase if phase else 'missing'}")

    for round_name, match_numbers in ROUND_MATCHES.items():
        total = len(list(match_numbers))
        finished = (
            db.query(Match)
            .filter(Match.round == round_name, Match.status == "finished")
            .count()
        )
        print(f"{round_name}: {finished}/{total} finished")

    predictions = db.query(Prediction).filter(Prediction.user_id == user.id).count()
    bracket_predictions = db.query(BracketPrediction).filter(BracketPrediction.user_id == user.id).count()
    print(f"Predictions: {predictions}")
    print(f"Bracket predictions: {bracket_predictions}")

    if score:
        print(
            f"Score: match={score.match_points}, bracket={score.bracket_points}, "
            f"bonus={score.tournament_bonus_points}, league_bonus={score.league_bonus_points}, "
            f"total={score.total_points}"
        )
    else:
        print("Score: no score row")

    print("Bracket advancement counts:")
    for round_name in BRACKET_ROUND_POINTS:
        count = db.query(KnockoutAdvancement).filter(KnockoutAdvancement.round == round_name).count()
        print(f"  {round_name}: {count}")


def run_until(target_phase: str, reset: bool) -> None:
    seed_database(reset=reset)

    db = SessionLocal()
    try:
        user, league = get_user_and_league(db)
        target_index = PHASE_ORDER.index(target_phase)

        if target_index >= PHASE_ORDER.index("group_tipped"):
            print_step("Group stage tipped")
            set_phase(db, "group_open")
            tip_matches(db, user, league, "group")

        if target_index >= PHASE_ORDER.index("group_scored"):
            print_step("Group stage scored")
            score_matches(db, "group")
            groups = compute_group_standings(db)
            populate_round_of_32(db, groups)
            set_phase(db, "group_closed")
            recalculate(db, user, league)

        if target_index >= PHASE_ORDER.index("r32_tipped"):
            print_step("Round of 32 tipped")
            set_phase(db, "knockout_open")
            tip_matches(db, user, league, "round_of_32")

        if target_index >= PHASE_ORDER.index("r32_scored"):
            print_step("Round of 32 scored")
            score_matches(db, "round_of_32")
            populate_round_from_previous(db, "round_of_16")
            recalculate(db, user, league)

        if target_index >= PHASE_ORDER.index("r16_tipped"):
            print_step("Round of 16 tipped")
            tip_matches(db, user, league, "round_of_16")

        if target_index >= PHASE_ORDER.index("r16_scored"):
            print_step("Round of 16 scored")
            score_matches(db, "round_of_16")
            populate_round_from_previous(db, "quarter_final")
            recalculate(db, user, league)

        if target_index >= PHASE_ORDER.index("qf_tipped"):
            print_step("Quarter-finals tipped")
            tip_matches(db, user, league, "quarter_final")

        if target_index >= PHASE_ORDER.index("qf_scored"):
            print_step("Quarter-finals scored")
            score_matches(db, "quarter_final")
            populate_round_from_previous(db, "semi_final")
            recalculate(db, user, league)

        if target_index >= PHASE_ORDER.index("sf_tipped"):
            print_step("Semi-finals tipped")
            tip_matches(db, user, league, "semi_final")

        if target_index >= PHASE_ORDER.index("sf_scored"):
            print_step("Semi-finals scored")
            score_matches(db, "semi_final")
            populate_round_from_previous(db, "match_for_third_place")
            populate_round_from_previous(db, "final")
            recalculate(db, user, league)

        if target_index >= PHASE_ORDER.index("bronze_tipped"):
            print_step("Bronze match tipped")
            tip_matches(db, user, league, "match_for_third_place")

        if target_index >= PHASE_ORDER.index("bronze_scored"):
            print_step("Bronze match scored")
            score_matches(db, "match_for_third_place")
            recalculate(db, user, league)

        if target_index >= PHASE_ORDER.index("final_tipped"):
            print_step("Final tipped")
            tip_matches(db, user, league, "final")

        if target_index >= PHASE_ORDER.index("final_scored"):
            print_step("Final scored")
            score_matches(db, "final")
            record_world_champion(db)
            set_phase(db, "knockout_closed")
            recalculate(db, user, league)

        if target_index >= PHASE_ORDER.index("summary"):
            recalculate(db, user, league)

        print_summary(db, user, league)
    finally:
        db.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate the VMTips tournament flow")
    parser.add_argument(
        "--phase",
        default="summary",
        help=(
            "Run from start through this phase. English values: "
            f"{', '.join(PHASE_ORDER)}. Swedish aliases use ASCII, e.g. "
            "gruppspel_tippat, gruppspel_rattat, 16_delsfinal_tippad, "
            "8_delsfinal_rattad, kvartsfinal_tippad, semifinal_rattad, "
            "bronsmatch_tippad, final_rattad, slutsummering."
        ),
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Do not wipe the database before running. Default is to reset.",
    )
    args = parser.parse_args()
    args.phase = PHASE_ALIASES.get(args.phase, args.phase)
    if args.phase not in PHASE_ORDER:
        valid = ", ".join(PHASE_ORDER + sorted(PHASE_ALIASES))
        parser.error(f"invalid --phase '{args.phase}'. Valid values: {valid}")
    return args


def main() -> None:
    args = parse_args()
    run_until(target_phase=args.phase, reset=not args.no_reset)


if __name__ == "__main__":
    main()
