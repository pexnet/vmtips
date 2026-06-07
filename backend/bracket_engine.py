"""
Bracket engine: computes predicted group standings from a user's predictions
and generates bracket predictions (which teams advance to each knockout round).

Follows the World Cup 2026 48-team format with 12 groups of 4.
Top 2 from each group + 8 best third-place teams advance to Round of 32.

Knockout slot definitions are sourced from match_table.py. Match records and
kickoff times are seeded from worldcup2026_fixtures.json.
"""
from collections import defaultdict
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from models import Prediction, Match, Team, BracketPrediction, KnockoutAdvancement
from fifa_standings import sort_group_teams as _sort_group_teams
from match_table import (
    get_group_slot_mapping as _get_group_slot_mapping,
    get_r32_match_numbers as _get_r32_match_numbers,
)
from third_place_table import get_annex_c_match_mapping


def _lazy_load_slot_data():
    """Load slot mappings from match_table — call once at import time."""
    global R32_GROUP_SLOTS, R32_MATCH_NUMBERS
    R32_GROUP_SLOTS = _get_group_slot_mapping()
    R32_MATCH_NUMBERS = _get_r32_match_numbers()


_lazy_load_slot_data()  # warm up on import


def build_actual_advancements(db: Session) -> list[dict]:
    """Return the set of teams that actually advanced to each knockout round.

    Prefers explicit `KnockoutAdvancement` rows (set by the admin or by
    `resolve_knockout_teams`). Falls back to deriving from finished
    knockout matches if no explicit rows exist. Duplicates are
    deduplicated by `(team_id, round)` pair.

    Returns a list of `{"team_id": int, "round": str}` dicts. Callers
    that need O(1) lookup can convert to a set:
        set((a["team_id"], a["round"]) for a in build_actual_advancements(db))
    """
    advancements = db.query(KnockoutAdvancement).all()
    if advancements:
        return [{"team_id": a.team_id, "round": a.round} for a in advancements]

    finished_knockout = (
        db.query(Match)
        .filter(
            Match.status == "finished",
            Match.round != "group",
        )
        .all()
    )

    result: list = []
    seen: set = set()
    for match in finished_knockout:
        if match.home_team_id is not None and (match.home_team_id, match.round) not in seen:
            result.append({"team_id": match.home_team_id, "round": match.round})
            seen.add((match.home_team_id, match.round))
        if match.away_team_id is not None and (match.away_team_id, match.round) not in seen:
            result.append({"team_id": match.away_team_id, "round": match.round})
            seen.add((match.away_team_id, match.round))
    return result


def _determine_outcome(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


def compute_predicted_group_standings(db: Session, user_id: int, league_id: int) -> dict:
    """
    Compute predicted group standings from a user's match predictions.
    Returns dict: {group_letter: [team_standings...]}
    """
    group_stats = defaultdict(lambda: defaultdict(lambda: {
        "team_id": None,
        "name": None,
        "code": None,
        "flag_emoji": None,
        "played": 0,
        "won": 0,
        "drawn": 0,
        "lost": 0,
        "gf": 0,
        "ga": 0,
        "gd": 0,
        "points": 0,
    }))

    teams = db.query(Team).all()
    for team in teams:
        group = str(team.group)
        stats = group_stats[group][team.id]
        stats["team_id"] = team.id
        stats["name"] = team.name
        stats["code"] = team.code
        stats["flag_emoji"] = team.flag_emoji

    predictions = (
        db.query(Prediction)
        .join(Match, Prediction.match_id == Match.id)
        .filter(
            Prediction.user_id == user_id,
            Prediction.league_id == league_id,
            Match.round == "group",
            Prediction.home_goals.isnot(None),
            Prediction.away_goals.isnot(None),
        )
        .all()
    )

    predicted_matches_by_group = {g: [] for g in "ABCDEFGHIJKL"}
    for pred in predictions:
        match = pred.match
        if not match.home_team or not match.away_team:
            continue

        home = match.home_team
        away = match.away_team
        hg = pred.home_goals
        ag = pred.away_goals
        outcome = _determine_outcome(hg, ag)
        group = str(home.group)
        predicted_matches_by_group.setdefault(group, []).append({
            "home_team_id": match.home_team_id,
            "away_team_id": match.away_team_id,
            "home_goals": hg,
            "away_goals": ag,
        })

        for team, is_home, goals_for, goals_against in [
            (home, True, hg, ag),
            (away, False, ag, hg),
        ]:
            group = str(team.group)
            stats = group_stats[group][team.id]
            stats["team_id"] = team.id
            stats["name"] = team.name
            stats["code"] = team.code
            stats["flag_emoji"] = team.flag_emoji
            stats["played"] += 1
            stats["gf"] += goals_for
            stats["ga"] += goals_against
            stats["gd"] = stats["gf"] - stats["ga"]

            if outcome == "draw":
                stats["drawn"] += 1
                stats["points"] += 1
            elif (outcome == "home" and is_home) or (outcome == "away" and not is_home):
                stats["won"] += 1
                stats["points"] += 3
            else:
                stats["lost"] += 1

    standings = {}
    for group, teams_by_id in group_stats.items():
        team_list = list(teams_by_id.values())
        standings[group] = _sort_group_teams(team_list, predicted_matches_by_group.get(group, []))

    return standings


def compute_actual_group_standings(db: Session, league_id: int) -> dict:
    """
    Compute ACTUAL group standings from finished match results.
    Returns dict: {group_letter: [team_standings...]}
    """
    group_stats = defaultdict(lambda: defaultdict(lambda: {
        "team_id": None,
        "name": None,
        "code": None,
        "flag_emoji": None,
        "played": 0,
        "won": 0,
        "drawn": 0,
        "lost": 0,
        "gf": 0,
        "ga": 0,
        "gd": 0,
        "points": 0,
    }))

    matches = (
        db.query(Match)
        .filter(
            Match.round == "group",
            Match.status == "finished",
            Match.home_goals.isnot(None),
            Match.away_goals.isnot(None),
        )
        .all()
    )

    for match in matches:
        if not match.home_team or not match.away_team:
            continue

        home = match.home_team
        away = match.away_team
        hg = match.home_goals
        ag = match.away_goals
        outcome = _determine_outcome(hg, ag)

        for team, is_home, goals_for, goals_against in [
            (home, True, hg, ag),
            (away, False, ag, hg),
        ]:
            g = str(team.group)
            stats = group_stats[g][team.id]
            stats["team_id"] = team.id
            stats["name"] = team.name
            stats["code"] = team.code
            stats["flag_emoji"] = team.flag_emoji
            stats["played"] += 1
            stats["gf"] += goals_for
            stats["ga"] += goals_against
            stats["gd"] = stats["gf"] - stats["ga"]

            if outcome == "draw":
                stats["drawn"] += 1
                stats["points"] += 1
            elif (outcome == "home" and is_home) or (outcome == "away" and not is_home):
                stats["won"] += 1
                stats["points"] += 3
            else:
                stats["lost"] += 1

    standings = {}
    for group, teams in group_stats.items():
        team_list = list(teams.values())
        standings[group] = _sort_group_teams(team_list, matches)

    return standings


def compute_third_place_rankings(standings: dict) -> list:
    """Rank all 3rd-place teams to find the 8 best."""
    third_places = []
    for group, teams in standings.items():
        if len(teams) >= 3:
            third = dict(teams[2])
            third["group"] = group
            third_places.append(third)

    return sorted(
        third_places,
        key=lambda t: (
            -t["points"],
            -t["gd"],
            -t["gf"],
            -(t.get("conduct_score", t.get("fair_play_score")) or -10_000),
            t.get("fifa_ranking") or 10_000,
            t.get("team_id") or 0,
            (t.get("name") or "").lower(),
        ),
    )


def _assign_third_place_slots(third_places: list) -> list[tuple[dict, int, str]]:
    """Assign third-place teams to their FIFA R32 candidate slots.

    The FIFA regulations define a fixed 495-row Annex C lookup. Placement
    depends only on which eight third-place groups advance, not their ranking.
    """
    teams = third_places[:8]
    if len(teams) < 8:
        return []

    third_by_group = {third["group"]: third for third in teams}
    mapping = get_annex_c_match_mapping(list(third_by_group.keys()))
    assigned = []
    for mn in sorted(mapping):
        group = mapping[mn]
        assigned.append((third_by_group[group], mn, "away"))
    return assigned


def resolve_r32_teams(standings: dict, third_places: list) -> dict:
    """
    Resolve all Round of 32 teams from predicted group standings.
    Returns {match_number: {"home": team_id, "away": team_id,
                           "home_name": ..., "away_name": ...}}
    """
    r32 = {m: {"home": None, "away": None, "home_name": None, "away_name": None,
                             "home_flag": None, "away_flag": None}
           for m in R32_MATCH_NUMBERS}

    # Fill group winners and runners-up
    for group in "ABCDEFGHIJKL":
        teams = standings.get(group, [])
        if len(teams) >= 1:
            key1 = f"1{group}"
            if key1 in R32_GROUP_SLOTS:
                mn, side = R32_GROUP_SLOTS[key1]
                r32[mn][side] = teams[0]["team_id"]
                r32[mn][f"{side}_name"] = teams[0]["name"]
                r32[mn][f"{side}_flag"] = teams[0]["flag_emoji"]
        if len(teams) >= 2:
            key2 = f"2{group}"
            if key2 in R32_GROUP_SLOTS:
                mn, side = R32_GROUP_SLOTS[key2]
                r32[mn][side] = teams[1]["team_id"]
                r32[mn][f"{side}_name"] = teams[1]["name"]
                r32[mn][f"{side}_flag"] = teams[1]["flag_emoji"]

    for third, mn, side in _assign_third_place_slots(third_places):
        r32[mn][side] = third["team_id"]
        r32[mn][f"{side}_name"] = third["name"]
        r32[mn][f"{side}_flag"] = third["flag_emoji"]

    return r32


def _resolve_placeholder(placeholder: Optional[str], winners: dict, losers: dict) -> Optional[int]:
    """Resolve a placeholder like 'W73' or 'L101' to a team ID."""
    if not placeholder:
        return None
    if placeholder.startswith("W"):
        try:
            mn = int(placeholder[1:])
            return winners.get(mn)
        except ValueError:
            return None
    if placeholder.startswith("L"):
        try:
            mn = int(placeholder[1:])
            return losers.get(mn)
        except ValueError:
            return None
    return None


def simulate_full_bracket(
    db: Session,
    user_id: int,
    league_id: int,
    r32_teams: dict,
) -> dict:
    """
    Simulate the full knockout bracket using user's match predictions.
    Returns dict with round_teams and match results.
    """
    # Get all knockout matches ordered by match_number
    knockout_matches = (
        db.query(Match)
        .options(joinedload(Match.home_team), joinedload(Match.away_team))
        .filter(Match.round != "group")
        .order_by(Match.match_number)
        .all()
    )

    # Build lookup for user's knockout predictions
    knockout_preds = (
        db.query(Prediction)
        .filter(
            Prediction.user_id == user_id,
            Prediction.league_id == league_id,
        )
        .all()
    )
    pred_by_match = {p.match_id: p for p in knockout_preds}

    match_winners = {}
    match_losers = {}

    round_order = [
        "round_of_32", "round_of_16", "quarter_final",
        "semi_final", "match_for_third_place", "final",
    ]

    for match in knockout_matches:
        mn = match.match_number
        rnd = match.round

        if mn in r32_teams:
            home_id = r32_teams[mn]["home"]
            away_id = r32_teams[mn]["away"]
        else:
            home_ph = match.home_team_placeholder
            away_ph = match.away_team_placeholder
            home_id = _resolve_placeholder(home_ph, match_winners, match_losers)
            away_id = _resolve_placeholder(away_ph, match_winners, match_losers)

        pred = pred_by_match.get(match.id)
        if pred and home_id and away_id:
            hg = int(pred.home_goals) if pred.home_goals is not None else 0
            ag = int(pred.away_goals) if pred.away_goals is not None else 0
            outcome = _determine_outcome(hg, ag)
            if outcome == "home":
                match_winners[mn] = home_id
                match_losers[mn] = away_id
            elif outcome == "away":
                match_winners[mn] = away_id
                match_losers[mn] = home_id
            elif pred.knockout_winner_side == "home":
                match_winners[mn] = home_id
                match_losers[mn] = away_id
            elif pred.knockout_winner_side == "away":
                match_winners[mn] = away_id
                match_losers[mn] = home_id
            else:
                match_winners[mn] = None
                match_losers[mn] = None
        else:
            match_winners[mn] = None
            match_losers[mn] = None

    # Collect teams per round
    round_teams = {r: set() for r in round_order}

    # R32: all teams assigned to R32 matches
    for mn in R32_MATCH_NUMBERS:
        if mn in r32_teams:
            for side in ["home", "away"]:
                tid = r32_teams[mn][side]
                if tid:
                    round_teams["round_of_32"].add(tid)

    # Later rounds: winners of matches in that round
    for match in knockout_matches:
        if match.round in round_order and match.match_number in match_winners:
            winner = match_winners[match.match_number]
            if winner:
                round_teams[match.round].add(winner)

    return {
        "match_winners": match_winners,
        "match_losers": match_losers,
        "round_teams": {r: list(tids) for r, tids in round_teams.items()},
        "r32_teams": r32_teams,
    }


def generate_bracket_predictions(db: Session, user_id: int, league_id: int) -> list[dict]:
    """Generate bracket predictions from user's group + knockout predictions."""
    standings = compute_predicted_group_standings(db, user_id, league_id)
    third_places = compute_third_place_rankings(standings)
    r32_teams = resolve_r32_teams(standings, third_places)
    result = simulate_full_bracket(db, user_id, league_id, r32_teams)

    entries = []
    for round_name, team_ids in result["round_teams"].items():
        for team_id in team_ids:
            if team_id:
                entries.append({
                    "user_id": user_id,
                    "league_id": league_id,
                    "team_id": team_id,
                    "round": round_name,
                    "source": "group_prediction",
                })

    # Add world champion (winner of final, match 104)
    champion_id = result["match_winners"].get(104)
    if champion_id:
        entries.append({
            "user_id": user_id,
            "league_id": league_id,
            "team_id": champion_id,
            "round": "world_champion",
            "source": "group_prediction",
        })

    return entries


def save_generated_bracket(db: Session, user_id: int, league_id: int) -> dict:
    """Generate bracket from predictions and save to database."""
    entries = generate_bracket_predictions(db, user_id, league_id)

    db.query(BracketPrediction).filter(
        BracketPrediction.user_id == user_id,
        BracketPrediction.league_id == league_id,
        BracketPrediction.source == "group_prediction",
    ).delete(synchronize_session=False)

    created = 0
    for entry in entries:
        bp = BracketPrediction(
            user_id=entry["user_id"],
            league_id=entry["league_id"],
            team_id=entry["team_id"],
            round=entry["round"],
            source=entry["source"],
        )
        db.add(bp)
        created += 1

    db.commit()
    return {"created": created}


def get_bracket_view(db: Session, user_id: int, league_id: int) -> dict:
    """
    Get a full bracket view for a user: predicted teams per match,
    actual teams when available, and points.
    """
    finished_group_matches = db.query(Match).filter(
        Match.round == "group",
        Match.status == "finished",
        Match.home_goals.isnot(None),
        Match.away_goals.isnot(None),
    ).count()
    group_stage_complete = finished_group_matches == 72

    predicted_standings = compute_predicted_group_standings(db, user_id, league_id)
    predicted_third_places = compute_third_place_rankings(predicted_standings)
    predicted_r32_teams = resolve_r32_teams(predicted_standings, predicted_third_places)
    predicted_result = simulate_full_bracket(db, user_id, league_id, predicted_r32_teams)

    # Get all knockout matches with actual results
    knockout_matches = (
        db.query(Match)
        .options(joinedload(Match.home_team), joinedload(Match.away_team))
        .filter(Match.round != "group")
        .order_by(Match.match_number)
        .all()
    )
    preds = (
        db.query(Prediction)
        .filter(
            Prediction.user_id == user_id,
            Prediction.league_id == league_id,
            Prediction.match_id.in_([m.id for m in knockout_matches]),
        )
        .all()
    )
    pred_by_match = {p.match_id: p for p in preds}
    team_ids = {
        tid
        for payload in predicted_result["r32_teams"].values()
        for tid in (payload.get("home"), payload.get("away"))
        if tid
    } | {
        tid
        for tid in list(predicted_result["match_winners"].values()) + list(predicted_result["match_losers"].values())
        if tid
    }
    teams = db.query(Team).filter(Team.id.in_(team_ids)).all() if team_ids else []
    team_by_id = {team.id: team for team in teams}

    matches_view = []
    for match in knockout_matches:
        mn = match.match_number
        rnd = match.round

        # Predicted teams for this match
        if mn in predicted_result["r32_teams"]:
            pred_home_id = predicted_result["r32_teams"][mn]["home"]
            pred_away_id = predicted_result["r32_teams"][mn]["away"]
            pred_home_name = predicted_result["r32_teams"][mn]["home_name"]
            pred_away_name = predicted_result["r32_teams"][mn]["away_name"]
        else:
            home_ph = match.home_team_placeholder
            away_ph = match.away_team_placeholder
            pred_home_id = _resolve_placeholder(home_ph, predicted_result["match_winners"], predicted_result["match_losers"])
            pred_away_id = _resolve_placeholder(away_ph, predicted_result["match_winners"], predicted_result["match_losers"])
            pred_home_name = None
            pred_away_name = None

        # Actual teams (if match has real teams assigned)
        actual_home = match.home_team
        actual_away = match.away_team

        # User's prediction for this match
        pred = pred_by_match.get(match.id)

        # Resolve flag emojis for predicted teams (bracket engine predictions)
        pred_home_flag = None
        pred_away_flag = None
        if pred_home_id:
            pred_home_flag = team_by_id.get(pred_home_id)
            pred_home_flag = pred_home_flag.flag_emoji if pred_home_flag else None
        if pred_away_id:
            pred_away_flag = team_by_id.get(pred_away_id)
            pred_away_flag = pred_away_flag.flag_emoji if pred_away_flag else None

        # Resolve flag emojis for actual teams
        actual_home_flag = actual_home.flag_emoji if actual_home else None
        actual_away_flag = actual_away.flag_emoji if actual_away else None

        # Resolve flag emojis for predicted team names if only ID available
        if not pred_home_name and pred_home_id:
            th = team_by_id.get(pred_home_id)
            pred_home_name = th.name if th else None
        if not pred_away_name and pred_away_id:
            ta = team_by_id.get(pred_away_id)
            pred_away_name = ta.name if ta else None

        matches_view.append({
            "match_id": match.id,
            "match_number": mn,
            "round": rnd,
            "match_date": match.match_date.isoformat() if match.match_date else None,
            "user_prediction": {
                "home_goals": pred.home_goals if pred else None,
                "away_goals": pred.away_goals if pred else None,
                "knockout_winner_side": pred.knockout_winner_side if pred else None,
                "knockout_resolution": pred.knockout_resolution if pred else None,
            },
            "predicted": {
                "home_team_id": pred_home_id,
                "home_team_name": pred_home_name,
                "home_team_flag": pred_home_flag,
                "home_team_placeholder": match.home_team_placeholder,
                "away_team_id": pred_away_id,
                "away_team_name": pred_away_name,
                "away_team_flag": pred_away_flag,
                "away_team_placeholder": match.away_team_placeholder,
                "home_goals": pred.home_goals if pred else None,
                "away_goals": pred.away_goals if pred else None,
                "knockout_winner_side": pred.knockout_winner_side if pred else None,
                "knockout_resolution": pred.knockout_resolution if pred else None,
            },
            "actual": {
                "home_team_id": actual_home.id if actual_home else None,
                "home_team_name": actual_home.name if actual_home else None,
                "home_team_flag": actual_home_flag,
                "home_team_placeholder": match.home_team_placeholder,
                "away_team_id": actual_away.id if actual_away else None,
                "away_team_name": actual_away.name if actual_away else None,
                "away_team_flag": actual_away_flag,
                "away_team_placeholder": match.away_team_placeholder,
                "home_goals": match.home_goals,
                "away_goals": match.away_goals,
                "status": match.status,
            },
        })

    # Group standings view
    group_view = {}
    for group, teams in predicted_standings.items():
        group_view[group] = [
            {
                "position": i + 1,
                "team_id": t["team_id"],
                "name": t["name"],
                "code": t["code"],
                "flag_emoji": t["flag_emoji"],
                "played": t["played"],
                "won": t["won"],
                "drawn": t["drawn"],
                "lost": t["lost"],
                "gf": t["gf"],
                "ga": t["ga"],
                "gd": t["gd"],
                "points": t["points"],
            }
            for i, t in enumerate(teams)
        ]

    return {
        "group_standings": group_view,
        "third_places": [
            {
                "rank": i + 1,
                "team_id": t["team_id"],
                "name": t["name"],
                "code": t["code"],
                "flag_emoji": t["flag_emoji"],
                "group": t["group"],
                "points": t["points"],
                "gd": t["gd"],
                "gf": t["gf"],
                "qualified": i < 8,
            }
            for i, t in enumerate(predicted_third_places)
        ],
        "knockout_matches": matches_view,
    }
