# FIFA World Cup 2026 Bracket — Official Specification

This document records the FIFA World Cup 2026 bracket structure used by VMTips. It covers the official 48-team format, fixed knockout slots, and the Annex C third-place assignment lookup implemented in the backend.

## Tournament Format

- **48 teams** in **12 groups** (A–L), 4 teams per group.
- Group stage: round-robin, top 2 from each group advance automatically (24 teams).
- **8 best third-placed teams** also advance, giving **32 teams** in the knockout stage.
- Knockout stage: single-elimination Round of 32 through to the Final, plus a match for third place.

## Round of 32 (Matches 73–88)

**Group winners and runners-up slots** are fixed regardless of third-place combinations:

| Match | Date | Fixture | Venue |
|-------|------|---------|-------|
| 73 | Jun 28 | 2A vs 2B | Los Angeles |
| 74 | Jun 29 | 1E vs 3rd (A/B/C/D/F) | Boston |
| 75 | Jun 29 | 1F vs 2C | Monterrey |
| 76 | Jun 29 | 1C vs 2F | Houston |
| 77 | Jun 30 | 1I vs 3rd (C/D/F/G/H) | New York/New Jersey |
| 78 | Jun 30 | 2E vs 2I | Dallas |
| 79 | Jun 30 | 1A vs 3rd (C/E/F/H/I) | Mexico City |
| 80 | Jul 1 | 1L vs 3rd (E/H/I/J/K) | Atlanta |
| 81 | Jul 1 | 1D vs 3rd (B/E/F/I/J) | San Francisco |
| 82 | Jul 1 | 1G vs 3rd (A/E/H/I/J) | Seattle |
| 83 | Jul 2 | 2K vs 2L | Toronto |
| 84 | Jul 2 | 1H vs 2J | Los Angeles |
| 85 | Jul 2 | 1B vs 3rd (E/F/G/I/J) | Vancouver |
| 86 | Jul 3 | 1J vs 2H | Miami |
| 87 | Jul 3 | 1K vs 3rd (D/E/I/J/L) | Kansas City |
| 88 | Jul 3 | 2D vs 2G | Dallas |

## Third-Place Team Advancement

There are **495 possible combinations** of which 8 third-place teams advance (C(12,8) = 495). FIFA published the full combination table in **Annex C** of the tournament regulations.

### Slot Candidate Sets

Each group winner that plays a third-place team has a set of candidate third-place groups:

| Group Winner | Match | Side | Possible 3rd-Place Opponents |
|--------------|-------|------|----------------------------|
| 1A | 79 | away | C, E, F, H, I |
| 1B | 85 | away | E, F, G, I, J |
| 1D | 81 | away | B, E, F, I, J |
| 1E | 74 | away | A, B, C, D, F |
| 1G | 82 | away | A, E, H, I, J |
| 1I | 77 | away | C, D, F, G, H |
| 1K | 87 | away | D, E, I, J, L |
| 1L | 80 | away | E, H, I, J, K |

### Resolution Logic

Given the 8 advancing third-place groups, assign them to the slots above using the fixed FIFA Annex C table. The best third-place ranking is used only to decide which 8 groups advance; placement does not depend on the order of those 8 teams.

1. Each third-place team goes to exactly one slot whose candidate set includes that team's group.
2. No two teams assigned to the same slot.
3. The FIFA combination table in Annex C defines the exact assignment for each of the 495 combinations.

The bracket engine uses the static `third_place_table.py` Annex C lookup in `_assign_third_place_slots()`.

## Later Rounds

### Round of 16 (Matches 89–96)

| Match | Fixture |
|-------|---------|
| 89 | Winner 74 vs Winner 77 |
| 90 | Winner 73 vs Winner 75 |
| 91 | Winner 76 vs Winner 78 |
| 92 | Winner 79 vs Winner 80 |
| 93 | Winner 83 vs Winner 84 |
| 94 | Winner 81 vs Winner 82 |
| 95 | Winner 86 vs Winner 88 |
| 96 | Winner 85 vs Winner 87 |

### Quarter-finals (Matches 97–100)

| Match | Fixture |
|-------|---------|
| 97 | Winner 89 vs Winner 90 |
| 98 | Winner 93 vs Winner 94 |
| 99 | Winner 91 vs Winner 92 |
| 100 | Winner 95 vs Winner 96 |

### Semi-finals (Matches 101–102)

| Match | Fixture |
|-------|---------|
| 101 | Winner 97 vs Winner 98 |
| 102 | Winner 99 vs Winner 100 |

### Finals Weekend

| Match | Fixture | Date |
|-------|---------|------|
| 103 | Loser 101 vs Loser 102 (Bronze) | July 18 |
| 104 | Winner 101 vs Winner 102 (Final) | July 19 |

## Implementation

- `backend/data/worldcup2026_fixtures.json` seeds all 104 match records and kickoff times.
- `backend/match_table.py` defines the knockout slot placeholders and Round of 32 candidate sets.
- `backend/fifa_standings.py` ranks teams within groups.
- `backend/bracket_engine.py` computes predicted/actual R32 teams and propagates knockout winners.
- `backend/third_place_table.py` stores the full 495-row Annex C assignment lookup.

## Notes

- The bracket is seeded so that `match_for_third_place` (match 103) is resolved **before** the `final` (match 104) in rendering order. Bronze medal match first, then the final.
- The `admin.py` endpoint `resolve-r32-placeholders` must compute actual group standings, determine the 8 best third-place teams, and use `_assign_third_place_slots()` or equivalent combination logic to populate the R32 matches with correct third-place opponents.
- The bracket engine's `resolve_r32_teams()` handles both **predicted** and **actual** standings via the same code path.

## Sources

- [FIFA: World Cup 2026 format](https://gpcustomersupportfwc2026.tickets.fifa.com/hc/en-gb/articles/28784798873117-8-What-is-the-format-for-the-FIFA-World-Cup-26-tournament)
- [FIFA: knockout stage match schedule](https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/knockout-stage-match-schedule-bracket)
- FIFA Regulations Annex C: third-place assignment table.
- [Wikipedia template mirror of Annex C](https://en.wikipedia.org/wiki/Template:2026_FIFA_World_Cup_third-place_table), used as the extraction source for `backend/third_place_table.py`.
