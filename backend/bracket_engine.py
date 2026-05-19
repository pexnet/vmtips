"""
Bracket engine: computes predicted group standings from a user's predictions
and generates bracket predictions (which teams advance to each knockout round).

Follows the World Cup 2026 48-team format with 12 groups of 4.
Top 2 from each group + 8 best third-place teams advance to Round of 32.
"""
from collections import defaultdict
from typing import Optional
from sqlalchemy.orm import Session
from models import Prediction, Match, Team, BracketPrediction


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

    for pred in predictions:
        match = pred.match
        if not match.home_team or not match.away_team:
            continue

        home = match.home_team
        away = match.away_team
        hg = pred.home_goals
        ag = pred.away_goals
        outcome = _determine_outcome(hg, ag)

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
        standings[group] = sorted(
            teams_by_id.values(),
            key=lambda t: (-t["points"], -t["gd"], -t["gf"], -t["won"], t["name"] or ""),
        )

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
        sorted_teams = sorted(
            teams.values(),
            key=lambda t: (-t["points"], -t["gd"], -t["gf"], -t["won"]),
        )
        standings[group] = sorted_teams

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
        key=lambda t: (-t["points"], -t["gd"], -t["gf"], -t["won"]),
    )


# Group winner/runner-up to R32 match mapping
# Each R32 match has a home slot and an away slot.
# Format: "1A" = winner of group A, "2B" = runner-up of group B
R32_GROUP_SLOTS = {
    "2A": (73, "home"), "2B": (73, "away"),
    "1E": (74, "home"),
    "2C": (75, "home"), "1F": (75, "away"),
    "1C": (76, "home"), "2F": (76, "away"),
    "1I": (77, "home"),
    "2E": (78, "home"), "2I": (78, "away"),
    "1A": (79, "home"),
    "1L": (80, "home"),
    "1D": (81, "home"),
    "1G": (82, "home"),
    "2K": (83, "home"), "2L": (83, "away"),
    "1H": (84, "home"), "2J": (84, "away"),
    "1B": (85, "home"),
    "1J": (86, "home"), "2H": (86, "away"),
    "1K": (87, "home"),
    "2D": (88, "home"), "2G": (88, "away"),
}

# 3rd-place to R32 match mapping (simplified)
# In WC 2026, 8 of the 12 3rd-place teams advance.
# The exact match assignment depends on WHICH groups qualify.
# For auto-generation from predictions, we use rank order assignment.
R32_THIRD_SLOTS = [
    (74, "away"),  # 3A/B/C/D/F
    (77, "away"),  # 3C/D/F/G/H
    (79, "away"),  # 3C/E/F/H/I
    (80, "away"),  # 3E/H/I/J/K
    (81, "away"),  # 3B/E/F/I/J
    (82, "away"),  # 3A/E/H/I/J
    (85, "away"),  # 3E/F/G/I/J
    (87, "away"),  # 3D/E/I/J/L
]


def resolve_r32_teams(standings: dict, third_places: list) -> dict:
    """
    Resolve all Round of 32 teams from predicted group standings.
    Returns {match_number: {"home": team_id, "away": team_id,
                           "home_name": ..., "away_name": ...}}
    """
    r32 = {m: {"home": None, "away": None, "home_name": None, "away_name": None,
                             "home_flag": None, "away_flag": None}
           for m in range(73, 89)}

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

    # Fill 3rd-place teams (top 8 in rank order)
    for i, third in enumerate(third_places[:8]):
        if i < len(R32_THIRD_SLOTS):
            mn, side = R32_THIRD_SLOTS[i]
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
            else:
                # Draw in knockout: default to home for prediction simulation
                match_winners[mn] = home_id
                match_losers[mn] = away_id
        else:
            match_winners[mn] = None
            match_losers[mn] = None

    # Collect teams per round
    round_teams = {r: set() for r in round_order}

    # R32: all teams assigned to R32 matches
    for mn in range(73, 89):
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
    # Check if group stage has actual results
    actual_standings = compute_actual_group_standings(db, league_id)
    has_actual_results = len(actual_standings) > 0
    
    # Use actual standings if available, otherwise use predicted
    if has_actual_results:
        standings = actual_standings
        third_places = compute_third_place_rankings(standings)
        r32_teams = resolve_r32_teams(standings, third_places)
        result = simulate_full_bracket(db, user_id, league_id, r32_teams)
    else:
        standings = compute_predicted_group_standings(db, user_id, league_id)
        third_places = compute_third_place_rankings(standings)
        r32_teams = resolve_r32_teams(standings, third_places)
        result = simulate_full_bracket(db, user_id, league_id, r32_teams)

    # Get all knockout matches with actual results
    knockout_matches = (
        db.query(Match)
        .filter(Match.round != "group")
        .order_by(Match.match_number)
        .all()
    )

    matches_view = []
    for match in knockout_matches:
        mn = match.match_number
        rnd = match.round

        # Predicted teams for this match
        if mn in result["r32_teams"]:
            pred_home_id = result["r32_teams"][mn]["home"]
            pred_away_id = result["r32_teams"][mn]["away"]
            pred_home_name = result["r32_teams"][mn]["home_name"]
            pred_away_name = result["r32_teams"][mn]["away_name"]
        else:
            home_ph = match.home_team_placeholder
            away_ph = match.away_team_placeholder
            pred_home_id = _resolve_placeholder(home_ph, result["match_winners"], result["match_losers"])
            pred_away_id = _resolve_placeholder(away_ph, result["match_winners"], result["match_losers"])
            pred_home_name = None
            pred_away_name = None

        # Actual teams (if match has real teams assigned)
        actual_home = match.home_team
        actual_away = match.away_team

        # User's prediction for this match
        pred = (
            db.query(Prediction)
            .filter(
                Prediction.user_id == user_id,
                Prediction.league_id == league_id,
                Prediction.match_id == match.id,
            )
            .first()
        )

        # Resolve flag emojis for predicted teams (bracket engine predictions)
        pred_home_flag = None
        pred_away_flag = None
        if pred_home_id:
            pred_home_flag = db.query(Team).filter(Team.id == pred_home_id).first()
            pred_home_flag = pred_home_flag.flag_emoji if pred_home_flag else None
        if pred_away_id:
            pred_away_flag = db.query(Team).filter(Team.id == pred_away_id).first()
            pred_away_flag = pred_away_flag.flag_emoji if pred_away_flag else None

        # Resolve flag emojis for actual teams
        actual_home_flag = actual_home.flag_emoji if actual_home else None
        actual_away_flag = actual_away.flag_emoji if actual_away else None

        # Resolve flag emojis for predicted team names if only ID available
        if not pred_home_name and pred_home_id:
            th = db.query(Team).filter(Team.id == pred_home_id).first()
            pred_home_name = th.name if th else None
        if not pred_away_name and pred_away_id:
            ta = db.query(Team).filter(Team.id == pred_away_id).first()
            pred_away_name = ta.name if ta else None

        matches_view.append({
            "match_id": match.id,
            "match_number": mn,
            "round": rnd,
            "match_date": match.match_date.isoformat() if match.match_date else None,
            "user_prediction": {
                "home_goals": pred.home_goals if pred else None,
                "away_goals": pred.away_goals if pred else None,
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
    for group, teams in standings.items():
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
            }
            for i, t in enumerate(third_places[:8])
        ],
        "knockout_matches": matches_view,
    }
