"""FIFA World Cup 2026 group-stage tiebreaker logic."""

from collections import defaultdict
from typing import Any, Callable, Iterable, List


def _get_val(obj: Any, attr: str):
    """Get attribute from object or dict."""
    if hasattr(obj, attr):
        return getattr(obj, attr)
    return obj.get(attr)


def _h2h_stats(team_ids: set, matches: List[Any]) -> dict:
    """Compute head-to-head stats for a subset of teams."""
    stats = {tid: {"points": 0, "gf": 0, "ga": 0, "gd": 0} for tid in team_ids}

    for m in matches:
        hid = _get_val(m, "home_team_id")
        aid = _get_val(m, "away_team_id")
        hg = _get_val(m, "home_goals")
        ag = _get_val(m, "away_goals")

        if hid not in team_ids or aid not in team_ids:
            continue
        if hg is None or ag is None:
            continue

        # Home
        stats[hid]["gf"] += hg
        stats[hid]["ga"] += ag
        if hg > ag:
            stats[hid]["points"] += 3
        elif hg == ag:
            stats[hid]["points"] += 1

        # Away
        stats[aid]["gf"] += ag
        stats[aid]["ga"] += hg
        if ag > hg:
            stats[aid]["points"] += 3
        elif hg == ag:
            stats[aid]["points"] += 1

    for tid in stats:
        stats[tid]["gd"] = stats[tid]["gf"] - stats[tid]["ga"]

    return stats


def _partition_by_value(teams: Iterable[dict], value_fn: Callable[[dict], Any], reverse: bool) -> list[list[dict]]:
    """Sort teams by a criterion and partition teams that remain equal."""
    sorted_teams = sorted(teams, key=value_fn, reverse=reverse)
    groups: list[list[dict]] = []
    for team in sorted_teams:
        value = value_fn(team)
        if not groups or value_fn(groups[-1][0]) != value:
            groups.append([team])
        else:
            groups[-1].append(team)
    return groups


def _has_any_value(teams: list[dict], keys: tuple[str, ...]) -> bool:
    return any(any(team.get(key) is not None for key in keys) for team in teams)


def _conduct_score(team: dict) -> int | None:
    value = team.get("conduct_score", team.get("fair_play_score"))
    return int(value) if value is not None else None


def _fifa_ranking(team: dict) -> int | None:
    value = team.get("fifa_ranking")
    return int(value) if value is not None else None


def _rank_by_overall(teams: list[dict]) -> list[dict]:
    criteria: list[tuple[Callable[[dict], Any], bool]] = [
        (lambda t: t.get("gd", 0), True),
        (lambda t: t.get("gf", 0), True),
    ]

    if _has_any_value(teams, ("conduct_score", "fair_play_score")):
        criteria.append((lambda t: _conduct_score(t) if _conduct_score(t) is not None else -10_000, True))
    if _has_any_value(teams, ("fifa_ranking",)):
        criteria.append((lambda t: _fifa_ranking(t) if _fifa_ranking(t) is not None else 10_000, False))

    remaining = teams
    for value_fn, reverse in criteria:
        groups = _partition_by_value(remaining, value_fn, reverse)
        if len(groups) > 1:
            ranked: list[dict] = []
            for group in groups:
                ranked.extend(_rank_by_overall(group) if len(group) > 1 else group)
            return ranked

    return sorted(remaining, key=lambda t: (t.get("team_id") or 0, (t.get("name") or "").lower()))


def _rank_points_tie(teams: list[dict], matches: List[Any]) -> list[dict]:
    """Resolve a same-points tie with recursive FIFA head-to-head criteria."""
    if len(teams) <= 1:
        return teams

    team_ids = {t["team_id"] for t in teams}
    h2h = _h2h_stats(team_ids, matches)
    criteria = (
        lambda t: h2h.get(t["team_id"], {}).get("points", 0),
        lambda t: h2h.get(t["team_id"], {}).get("gd", 0),
        lambda t: h2h.get(t["team_id"], {}).get("gf", 0),
    )

    for value_fn in criteria:
        groups = _partition_by_value(teams, value_fn, True)
        if len(groups) > 1:
            ranked: list[dict] = []
            for group in groups:
                ranked.extend(_rank_points_tie(group, matches) if len(group) > 1 else group)
            return ranked

    return _rank_by_overall(teams)


def sort_group_teams(teams: List[dict], matches: List[Any]) -> List[dict]:
    """
    Sort teams within a group using FIFA tiebreakers.

    Args:
        teams:  Team stat dicts with keys team_id, points, gf, ga, gd, name.
        matches: Match objects (SQLA or dicts) with home_team_id, away_team_id,
                 home_goals, away_goals.

    Returns:
        Sorted list of teams (1st place first).
    """
    if not teams:
        return []

    points_groups = defaultdict(list)
    for team in teams:
        points_groups[team["points"]].append(team)

    result = []
    for points in sorted(points_groups.keys(), reverse=True):
        tied = points_groups[points]
        result.extend(_rank_points_tie(tied, matches) if len(tied) > 1 else tied)

    return result
