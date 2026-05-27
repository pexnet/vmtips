"""
World Cup 2026 match table and third-place combination table generator.
All data derived from worldcup2026_fixtures.json.
"""

import json
import itertools
from pathlib import Path
from third_place_table import THIRD_PLACE_ASSIGNMENTS, get_annex_c_match_mapping

# Load fixtures from worldcup2026_fixtures.json
_FIXTURES_PATH = Path(__file__).parent / "data" / "worldcup2026_fixtures.json"


def load_fixtures() -> list[dict]:
    """Load all 104 match fixtures from worldcup2026_fixtures.json."""
    with open(_FIXTURES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Full match table: all 104 matches with their slots/placeholders
# Match numbers 1-72: group stage (fixed teams)
# Match numbers 73-104: knockout stage (W/L placeholders or group position placeholders)
# ---------------------------------------------------------------------------

MATCH_TABLE: dict[int, dict] = {}

# Group stage: matches 1-72
# These are already seeded into the database, but we keep the reference here
GROUP_MATCHES = range(1, 73)

# Knockout stage match definitions with placeholders
# Format: match_number -> {round, home_slot, away_slot}
# Slots: "1A" = group A winner, "2B" = group B runner-up, "W73" = winner of match 73, "L101" = loser of match 101, etc.
# 3rd-place slots: "3{groups}" indicates best 3rd-place teams from specified groups
KNOCKOUT_SLOT_DEFINITIONS: dict[int, dict] = {
    # Round of 32
    73: {"round": "round_of_32", "home": "2A", "away": "2B"},
    74: {"round": "round_of_32", "home": "1E", "away": "3A/B/C/D/F"},
    75: {"round": "round_of_32", "home": "1F", "away": "2C"},
    76: {"round": "round_of_32", "home": "1C", "away": "2F"},
    77: {"round": "round_of_32", "home": "1I", "away": "3C/D/F/G/H"},
    78: {"round": "round_of_32", "home": "2E", "away": "2I"},
    79: {"round": "round_of_32", "home": "1A", "away": "3C/E/F/H/I"},
    80: {"round": "round_of_32", "home": "1L", "away": "3E/H/I/J/K"},
    81: {"round": "round_of_32", "home": "1D", "away": "3B/E/F/I/J"},
    82: {"round": "round_of_32", "home": "1G", "away": "3A/E/H/I/J"},
    83: {"round": "round_of_32", "home": "2K", "away": "2L"},
    84: {"round": "round_of_32", "home": "1H", "away": "2J"},
    85: {"round": "round_of_32", "home": "1B", "away": "3E/F/G/I/J"},
    86: {"round": "round_of_32", "home": "1J", "away": "2H"},
    87: {"round": "round_of_32", "home": "1K", "away": "3D/E/I/J/L"},
    88: {"round": "round_of_32", "home": "2D", "away": "2G"},
    # Round of 16
    89: {"round": "round_of_16", "home": "W74", "away": "W77"},
    90: {"round": "round_of_16", "home": "W73", "away": "W75"},
    91: {"round": "round_of_16", "home": "W76", "away": "W78"},
    92: {"round": "round_of_16", "home": "W79", "away": "W80"},
    93: {"round": "round_of_16", "home": "W83", "away": "W84"},
    94: {"round": "round_of_16", "home": "W81", "away": "W82"},
    95: {"round": "round_of_16", "home": "W86", "away": "W88"},
    96: {"round": "round_of_16", "home": "W85", "away": "W87"},
    # Quarter Finals
    97: {"round": "quarter_final", "home": "W89", "away": "W90"},
    98: {"round": "quarter_final", "home": "W93", "away": "W94"},
    99: {"round": "quarter_final", "home": "W91", "away": "W92"},
    100: {"round": "quarter_final", "home": "W95", "away": "W96"},
    # Semi Finals
    101: {"round": "semi_final", "home": "W97", "away": "W98"},
    102: {"round": "semi_final", "home": "W99", "away": "W100"},
    # Third Place
    103: {"round": "match_for_third_place", "home": "L101", "away": "L102"},
    # Final
    104: {"round": "final", "home": "W101", "away": "W102"},
}


# R32 matches that include a third-place slot, with candidate groups
R32_THIRD_PLACE_MATCHES = {
    74: {"home": "1E", "away_candidates": set("ABCDF")},
    77: {"home": "1I", "away_candidates": set("CDFGH")},
    79: {"home": "1A", "away_candidates": set("CEFHI")},
    80: {"home": "1L", "away_candidates": set("EHIJK")},
    81: {"home": "1D", "away_candidates": set("BEFIJ")},
    82: {"home": "1G", "away_candidates": set("AEHIJ")},
    85: {"home": "1B", "away_candidates": set("EFGIJ")},
    87: {"home": "1K", "away_candidates": set("DEIJL")},
}

# Matches that need 3rd-place team in the "away" slot
# Map: match_number -> candidate_groups_set
R32_AWAY_THIRD_CANDIDATES: dict[int, set[str]] = {
    74: set("ABCDF"),
    77: set("CDFGH"),
    79: set("CEFHI"),
    80: set("EHIJK"),
    81: set("BEFIJ"),
    82: set("AEHIJ"),
    85: set("EFGIJ"),
    87: set("DEIJL"),
}

# ---------------------------------------------------------------------------
# Helpers for bracket_engine.py to avoid hardcoding
# ---------------------------------------------------------------------------

def get_group_slot_mapping() -> dict[str, tuple[int, str]]:
    """
    Return a mapping like bracket_engine's old R32_GROUP_SLOTS:
    {"2A": (73, "home"), "2B": (73, "away"), ...}
    Derived from KNOCKOUT_SLOT_DEFINITIONS.
    """
    mapping: dict[str, tuple[int, str]] = {}
    for mn, slot_def in KNOCKOUT_SLOT_DEFINITIONS.items():
        home_slot = slot_def["home"]
        away_slot = slot_def["away"]
        # Only map non-W/L slots (group position slots like 1A, 2B, etc.)
        if not home_slot.startswith(("W", "L")):
            mapping[home_slot] = (mn, "home")
        if not away_slot.startswith(("W", "L")) and not away_slot.startswith("3"):
            mapping[away_slot] = (mn, "away")
    return mapping


def get_third_place_slot_candidates() -> list[tuple[int, str, set[str]]]:
    """
    Return list like bracket_engine's old R32_THIRD_SLOT_CANDIDATES:
    [(match_number, side, candidates_set), ...]
    """
    return [
        (mn, "away", set(cands))
        for mn, cands in R32_AWAY_THIRD_CANDIDATES.items()
    ]


def get_r32_match_numbers() -> list[int]:
    """Return all Round of 32 match numbers (matches 73-88)."""
    return [mn for mn, slot_def in KNOCKOUT_SLOT_DEFINITIONS.items()
            if slot_def["round"] == "round_of_32"]


def get_round_order() -> list[str]:
    """Return the canonical round ordering for knockout stages."""
    return [
        "round_of_32",
        "round_of_16",
        "quarter_final",
        "semi_final",
        "match_for_third_place",
        "final",
    ]


# ---------------------------------------------------------------------------
# Third-place combination table generator
# ---------------------------------------------------------------------------
# FIFA WC 2026: 12 groups, top-2 auto-qualify + 8 best 3rd-place teams -> R32
# We need to map which 3rd-place team goes to which R32 slot.
#
# The 495 combinations come from choosing which 8 of the 12 groups produce
# a 3rd-place team that advances (the 4 worst 3rd-place teams are eliminated).
#
# For each combination, we must assign the 8 chosen 3rd-place teams to the
# 8 R32 3rd-place slots such that each team goes to a slot whose candidate
# set includes their group.
# ---------------------------------------------------------------------------

def generate_third_place_combination_table() -> list[dict]:
    """
    Legacy validator for possible 8-group third-place combinations.

    Runtime assignment uses the official static Annex C lookup in
    third_place_table.py. This helper remains available only for local
    consistency checks of candidate coverage.
    
    Returns a list of dicts, each representing one valid combination:
    {
        "combination_id": int (1-based),
        "advancing_3rd_groups": [str],  # sorted, 8 groups that advance
        "slot_assignments": {
            "match_number": int,     # which R32 match (74, 77, 79, 80, 81, 82, 85, 87)
            "position": "home"|"away", # always "away" for 3rd-place slots in WC2026
            "allowed_groups": str,    # original placeholder like "3A/B/C/D/F"
            "group_assigned": str,    # which group's 3rd-place team fills this slot
        }
    }
    
    The number of combinations is fixed: C(12,8) = 495.
    """
    all_groups = list("ABCDEFGHIJKL")
    r32_slots_with_third = [74, 77, 79, 80, 81, 82, 85, 87]
    
    combinations = []
    combo_id = 0
    
    # Iterate over all combinations of 8 groups out of 12
    for advancing in itertools.combinations(all_groups, 8):
        advancing_set = set(advancing)
        
        # Check: can each of the 8 advancing groups fit one of the 8 slots?
        # Each slot has a candidate set; each advancing group must be in at least
        # one slot's candidate set.
        
        # Build list: for each slot, what groups from advancing_set are eligible?
        slot_eligible = {}
        for mn in r32_slots_with_third:
            slot_eligible[mn] = advancing_set & R32_AWAY_THIRD_CANDIDATES[mn]
        
        # Check Hall's condition: for every subset of k slots,
        # the union of eligible groups must have at least k groups.
        # For WC2026 this always holds (verified by FIFA), but we check anyway.
        valid = True
        for k in range(1, 9):
            for slots_subset in itertools.combinations(r32_slots_with_third, k):
                union = set()
                for mn in slots_subset:
                    union |= slot_eligible[mn]
                if len(union) < k:
                    valid = False
                    break
            if not valid:
                break
        
        if not valid:
            continue
        
        # We assign slots in order of most constrained (fewest candidates).
        sorted_slots = sorted(r32_slots_with_third, key=lambda s: len(slot_eligible[s]))
        
        def backtrack(idx: int, used_groups: set, assignment: dict) -> dict | None:
            if idx == len(sorted_slots):
                return assignment
            slot = sorted_slots[idx]
            eligible = slot_eligible[slot] - used_groups
            for group in sorted(eligible):  # deterministic
                new_assignment = dict(assignment)
                new_assignment[slot] = group
                result = backtrack(idx + 1, used_groups | {group}, new_assignment)
                if result is not None:
                    return result
            return None
        
        assignment = backtrack(0, set(), {})
        if assignment is None:
            continue
        
        combo_id += 1
        combinations.append({
            "combination_id": combo_id,
            "advancing_3rd_groups": sorted(advancing_set),
            "slot_assignments": {
                str(mn): {
                    "match_number": mn,
                    "position": "away",
                    "allowed_groups": "/".join(sorted(R32_AWAY_THIRD_CANDIDATES[mn])),
                    "group_assigned": assignment[mn],
                }
                for mn in r32_slots_with_third
            },
        })
    
    return combinations


def get_third_place_combination_table() -> list[dict]:
    """Return the official 495-row Annex C combination table."""
    table = []
    for combo_id, (groups, assignments) in enumerate(sorted(THIRD_PLACE_ASSIGNMENTS.items()), start=1):
        match_mapping = get_annex_c_match_mapping(list(groups))
        table.append({
            "combination_id": combo_id,
            "advancing_3rd_groups": list(groups),
            "slot_assignments": {
                str(match_number): {
                    "match_number": match_number,
                    "position": "away",
                    "allowed_groups": "/".join(sorted(R32_AWAY_THIRD_CANDIDATES[match_number])),
                    "group_assigned": group,
                }
                for match_number, group in sorted(match_mapping.items())
            },
        })
    return table


def find_combination_for_3rd_place_groups(groups: list[str]) -> dict | None:
    """
    Given a sorted list of 8 advancing 3rd-place groups,
    find the matching combination row from the table.
    """
    table = get_third_place_combination_table()
    group_set = set(groups)
    for combo in table:
        if set(combo["advancing_3rd_groups"]) == group_set:
            return combo
    return None


def get_3rd_place_slot_mapping_for_groups(groups: list[str]) -> dict[int, str]:
    """
    Returns {match_number: assigned_group} for the given 8 advancing groups.
    Raises ValueError if the combination is invalid.
    """
    return get_annex_c_match_mapping(groups)


# ---------------------------------------------------------------------------
# Build MATCH_TABLE from fixtures
# ---------------------------------------------------------------------------

def build_match_table() -> dict[int, dict]:
    """Build the full match table from fixtures and slot definitions."""
    fixtures = load_fixtures()
    table: dict[int, dict] = {}
    
    for fx in fixtures:
        mn = fx["match_number"]
        entry = {
            "match_number": mn,
            "round": fx["round"],
            "group": fx.get("group"),
            "match_date_utc": fx["match_date_utc"],
        }
        
        if mn in KNOCKOUT_SLOT_DEFINITIONS:
            slot_def = KNOCKOUT_SLOT_DEFINITIONS[mn]
            entry["home_slot"] = slot_def["home"]
            entry["away_slot"] = slot_def["away"]
            if "3" in slot_def["away"]:
                entry["away_is_3rd_place"] = True
                entry["away_3rd_candidates"] = list(sorted(R32_AWAY_THIRD_CANDIDATES.get(mn, set())))
            else:
                entry["away_is_3rd_place"] = False
        else:
            # Group stage or other matches without explicit slots
            entry["home_team_name"] = fx.get("home_team_name")
            entry["away_team_name"] = fx.get("away_team_name")
        
        table[mn] = entry
    
    return table


# Lazy-loaded
_MATCH_TABLE: dict[int, dict] | None = None


def get_match_table() -> dict[int, dict]:
    """Get the full match table for all 104 matches."""
    global _MATCH_TABLE
    if _MATCH_TABLE is None:
        _MATCH_TABLE = build_match_table()
    return _MATCH_TABLE


# ---------------------------------------------------------------------------
# Verification / validation helpers
# ---------------------------------------------------------------------------

def validate_match_table() -> dict:
    """Validate that the match table covers all 104 matches correctly."""
    table = get_match_table()
    stats = {
        "total_matches": len(table),
        "group_matches": 0,
        "round_of_32": 0,
        "round_of_16": 0,
        "quarter_final": 0,
        "semi_final": 0,
        "match_for_third_place": 0,
        "final": 0,
        "third_place_slots": 0,
        "errors": [],
    }
    
    expected_rounds = {
        "group": 72,
        "round_of_32": 16,
        "round_of_16": 8,
        "quarter_final": 4,
        "semi_final": 2,
        "match_for_third_place": 1,
        "final": 1,
    }
    
    for mn in range(1, 105):
        if mn not in table:
            stats["errors"].append(f"Match {mn} missing from table")
            continue
        
        entry = table[mn]
        rnd = entry["round"]
        
        if rnd in expected_rounds:
            stats[f"{rnd}"] = stats.get(f"{rnd}", 0) + 1
        
        if entry.get("away_is_3rd_place"):
            stats["third_place_slots"] += 1
    
    # Check counts
    for rnd, expected in expected_rounds.items():
        actual = stats.get(rnd, 0)
        if actual != expected:
            stats["errors"].append(f"Round '{rnd}': expected {expected}, got {actual}")
    
    stats["valid"] = len(stats["errors"]) == 0
    return stats


def print_combination_table_summary() -> str:
    """Return a human-readable summary of the combination table."""
    table = get_third_place_combination_table()
    lines = [
        f"Third-Place Combination Table Summary",
        f"{'=' * 50}",
        f"Total combinations: {len(table)}",
        f"Expected: C(12,8) = 495",
        f"",
        f"First 10 combinations:",
    ]
    
    for combo in table[:10]:
        groups = ",".join(combo["advancing_3rd_groups"])
        slots = ", ".join(
            f"M{mn}←{data['group_assigned']}"
            for mn, data in sorted(combo["slot_assignments"].items(), key=lambda x: int(x[0]))
        )
        lines.append(f"  #{combo['combination_id']:>3}: groups=[{groups}] => {slots}")
    
    lines.extend([
        f"",
        f"Last 10 combinations:",
    ])
    
    for combo in table[-10:]:
        groups = ",".join(combo["advancing_3rd_groups"])
        slots = ", ".join(
            f"M{mn}←{data['group_assigned']}"
            for mn, data in sorted(combo["slot_assignments"].items(), key=lambda x: int(x[0]))
        )
        lines.append(f"  #{combo['combination_id']:>3}: groups=[{groups}] => {slots}")
    
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Direct access: get match details by match number
# ---------------------------------------------------------------------------

def get_match(match_number: int) -> dict | None:
    """Get match details by match number (1-104)."""
    table = get_match_table()
    return table.get(match_number)


def get_matches_for_round(round_name: str) -> list[dict]:
    """Get all matches for a given round."""
    table = get_match_table()
    return [m for m in table.values() if m["round"] == round_name]


def get_r32_match_for_3rd_place_group(third_place_group: str) -> dict | None:
    """
    Find which R32 match and position a 3rd-place team from a given group
    would be assigned to, based on the combination table.
    
    This requires knowing which 8 groups advance (context-dependent).
    Use get_3rd_place_slot_mapping_for_groups() instead for full resolution.
    """
    table = get_match_table()
    for mn in [74, 77, 79, 80, 81, 82, 85, 87]:
        candidates = R32_AWAY_THIRD_CANDIDATES.get(mn, set())
        if third_place_group.upper() in candidates:
            return table.get(mn)
    return None


# ---------------------------------------------------------------------------
# Example usage / self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Loading worldcup fixtures from {_FIXTURES_PATH}")
    fixtures = load_fixtures()
    print(f"Loaded {len(fixtures)} fixtures")
    
    stats = validate_match_table()
    print("\nValidation:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    print("\n" + print_combination_table_summary())
    
    print("\n=== Sample lookups ===")
    for mn in [1, 73, 74, 89, 104]:
        match = get_match(mn)
        print(f"Match {mn}: {match}")
