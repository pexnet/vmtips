from types import SimpleNamespace

from bracket_engine import _assign_third_place_slots, compute_third_place_rankings, get_bracket_view
from fifa_standings import sort_group_teams
from models import League, Match, Prediction, User
from third_place_table import get_annex_c_match_mapping


def _team(team_id, points=0, gf=0, ga=0, won=0, name=None):
    return {
        "team_id": team_id,
        "name": name or f"Team {team_id}",
        "points": points,
        "gf": gf,
        "ga": ga,
        "gd": gf - ga,
        "won": won,
    }


def _match(home, away, hg, ag):
    return SimpleNamespace(home_team_id=home, away_team_id=away, home_goals=hg, away_goals=ag)


def test_group_head_to_head_beats_overall_goal_difference():
    teams = [
        _team(1, points=6, gf=3, ga=3, name="A"),
        _team(2, points=6, gf=6, ga=1, name="B"),
        _team(3, points=3, gf=3, ga=4, name="C"),
        _team(4, points=3, gf=1, ga=5, name="D"),
    ]
    matches = [
        _match(1, 2, 1, 0),
        _match(1, 3, 0, 3),
        _match(1, 4, 2, 0),
        _match(2, 3, 4, 0),
        _match(2, 4, 2, 0),
        _match(3, 4, 0, 1),
    ]

    assert [team["team_id"] for team in sort_group_teams(teams, matches)[:2]] == [1, 2]


def test_best_third_place_ranking_does_not_use_wins():
    standings = {
        "A": [_team(1), _team(2), _team(10, points=4, gf=4, ga=3, won=2)],
        "B": [_team(3), _team(4), _team(5, points=4, gf=4, ga=3, won=0)],
    }

    third_places = compute_third_place_rankings(standings)

    assert [team["team_id"] for team in third_places] == [5, 10]


def test_annex_c_lookup_known_combinations():
    assert get_annex_c_match_mapping(list("EFGHIJKL")) == {
        79: "E",
        85: "J",
        81: "I",
        74: "F",
        82: "H",
        77: "G",
        87: "L",
        80: "K",
    }
    assert get_annex_c_match_mapping(list("DEFGHIJK")) == {
        79: "E",
        85: "G",
        81: "J",
        74: "D",
        82: "H",
        77: "F",
        87: "I",
        80: "K",
    }


def test_third_place_slot_assignment_uses_only_advancing_groups():
    third_places = [
        {"team_id": 101 + i, "group": group, "name": group, "flag_emoji": None}
        for i, group in enumerate("EFGHIJKL")
    ]
    reversed_third_places = list(reversed(third_places))

    first = {(mn, group["group"]) for group, mn, _ in _assign_third_place_slots(third_places)}
    second = {(mn, group["group"]) for group, mn, _ in _assign_third_place_slots(reversed_third_places)}

    assert first == second


def test_bracket_view_uses_predictions_until_all_group_matches_finished(seeded_db):
    user = seeded_db.query(User).filter(User.email == "admin@vmtips.se").one()
    league = seeded_db.query(League).filter(League.name == "VM2026").one()
    match = seeded_db.query(Match).filter(Match.match_number == 1).one()

    match.home_goals = 5
    match.away_goals = 0
    match.status = "finished"
    seeded_db.add(Prediction(
        user_id=user.id,
        league_id=league.id,
        match_id=match.id,
        home_goals=0,
        away_goals=5,
    ))
    seeded_db.commit()

    view = get_bracket_view(seeded_db, user.id, league.id)
    group_a = view["group_standings"]["A"]

    assert group_a[0]["team_id"] == match.away_team_id


def test_knockout_draw_predictions_are_rejected(client, set_phase):
    set_phase("knockout_open")
    client.post("/auth/register", json={
        "email": "draws@example.com",
        "password": "secret123",
        "display_name": "Draws",
    })
    login = client.post("/auth/login", json={"email": "draws@example.com", "password": "secret123"})
    token = login.json()["access_token"]

    response = client.post(
        "/predictions/batch",
        json={"predictions": [{"match_id": 73, "home_goals": 1, "away_goals": 1}]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "knockout_draws_not_supported"
