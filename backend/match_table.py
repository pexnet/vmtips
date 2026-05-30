"""World Cup 2026 knockout slot definitions used by the bracket engine."""

# Knockout stage match definitions with placeholders
# Format: match_number -> {round, home, away}
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


def get_r32_match_numbers() -> list[int]:
    """Return all Round of 32 match numbers (matches 73-88)."""
    return [mn for mn, slot_def in KNOCKOUT_SLOT_DEFINITIONS.items()
            if slot_def["round"] == "round_of_32"]
