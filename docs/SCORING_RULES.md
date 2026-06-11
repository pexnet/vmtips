# VMTips — Scoring Rules (World Cup 2026)

> **Document Version:** 3.0  
> **Purpose:** Single source of truth for all scoring rules. This document reflects the actual engine implemented in `backend/scoring.py` and the recalculation logic in `backend/routers/admin.py`.  
> **Important:** FIFA group-stage and best-third-place rules are implemented for the data the app stores. Fair play/team conduct score and FIFA ranking are supported by the ranking helpers if present, but they are not currently stored in the database.

---

## 1. Tournament Structure

- **Group Stage:** 12 groups (A–L), 4 teams per group. Top 2 + 8 best third-placed teams advance to the knockout stage.
- **Knockout Stage:** Round of 32 -> Round of 16 -> Quarterfinal -> Semifinal -> Match for Third Place -> Final.
- **Prediction happens in two phases:**
  1. **Phase 1:** Predict all 72 group stage matches before the WC deadline (save incrementally).
  2. **Phase 2:** Predict the entire knockout stage (bracket + matches) after the group stage ends.

---

## 2. Match Result Points

Points for a single match prediction are calculated by checking three independent criteria. Each criterion that is satisfied adds its point value — they are **additive** and not mutually exclusive.

| Criterion | Points | Description |
|---|---|---|
| **Correct outcome (1X2)** | 3 p | You correctly picked the winner (home win, away win, or draw) |
| **Correct home score** | 2 p | You predicted the exact number of goals scored by the home team |
| **Correct away score** | 2 p | You predicted the exact number of goals scored by the away team |

### Maximum per match

A **perfect prediction** (exact scoreline) automatically satisfies all three criteria:

3 (outcome) + 2 (home score) + 2 (away score) = **7 points**

### Examples

| # | Your Prediction | Actual Result | Outcome (3p) | Home Score (2p) | Away Score (2p) | **Total** |
|---|---|---|---|---|---|---|
| 1 | 2-1 | **2-1** | ✅ 3 | ✅ 2 | ✅ 2 | **7 p** |
| 2 | 1-1 | **1-1** | ✅ 3 | ✅ 2 | ✅ 2 | **7 p** |
| 3 | 3-1 | **2-0** | ✅ 3 | ❌ | ❌ | **3 p** |
| 4 | 2-1 | **3-1** | ✅ 3 | ❌ | ✅ 2 | **5 p** |
| 5 | 2-0 | **2-3** | ❌ | ✅ 2 | ❌ | **2 p** |
| 6 | 1-1 | **0-0** | ✅ 3 | ❌ | ❌ | **3 p** |
| 7 | 3-2 | **2-0** | ✅ 3 | ❌ | ❌ | **3 p** |
| 8 | 2-0 | **0-1** | ❌ | ❌ | ❌ | **0 p** |

---

## 3. Knockout Bracket Points (Bonus)

> Applies only if you predicted the correct team in the correct knockout round.

| Round | Points per team |
|---|---|
| Round of 32 | 1 p |
| Round of 16 | 1 p |
| Quarterfinal | 1 p |
| Semifinal | 1 p |
| Match for Third Place | 1 p |
| Final | 1 p |
| **World Champion** | **1 p** |
| **Max total bracket** | **65 p** |

### Note: Dual match result points in knockout stage

For knockout matches, points are calculated in two parallel tracks:

1. **Match result points** — You get points for correct outcome/goals on each match slot (regardless of which teams actually play). For example, if you predicted Germany–South Korea 3-1 in Round of 32 match #73, and the real match becomes Brazil–Scotland 3-1, you still get 7p for your result prediction (if the scores match).

2. **Team bonus** — Extra points for each team you correctly placed in the right round.

---

## 4. Tournament Bonus Predictions

Before the tournament begins, you can make four long-term predictions. Each correct prediction awards the points shown below.

| Bonus | Points | Description | Matching Rule |
|---|---|---|---|
| **World Champion** | 20 p | Predict which team wins the World Cup | Must match the team by ID (exact team) |
| **Runner-up** | 20 p | Predict which team finishes second | Must match the team by ID |
| **Bronze Match Winner** | 20 p | Predict the winner of the 3rd-place match | Must match the team by ID |
| **Top Scorer** | 20 p | Predict the player who scores the most goals | Matched case-insensitively (e.g., "Mbappe" = "MBAPPE") |
| **Tournament bonuses max** | **80 p** | | |

> Tournament bonuses are counted in the global leaderboard.

---

## 5. Grand Total

| Category | Max Points |
|---|---|
| Match results (72 group + 32 knockout = 104 matches) | 728 p |
| Bracket bonus | 65 p |
| Tournament bonuses | 80 p |
| **Grand total** | **873 p** |

---

## 6. Tiebreakers for Group Standings

The app uses the FIFA Article 13 hierarchy for group standings:

1. Points obtained in all group matches
2. Head-to-head points among teams tied on points
3. Head-to-head goal difference among those tied teams
4. Head-to-head goals scored among those tied teams
5. Re-apply head-to-head criteria to any still-tied subset
6. Goal difference in all group matches
7. Goals scored in all group matches
8. Fair play/team conduct score, if available
9. FIFA ranking, if available
10. App-only deterministic fallback by team ID when unavailable data leaves teams tied

For best third-place ranking, the app uses points, goal difference, goals scored, conduct score if available, FIFA ranking if available, then the same deterministic fallback. Wins are not a tiebreaker.

> **Note:** Conduct score and FIFA ranking data are not currently tracked in the database, so real unresolved ties fall back to deterministic team ID ordering unless those fields are added.

---

## 7. Best Third-Place Teams (Annex C)

From the 12 groups, the 8 best third-placed teams advance to the Round of 32. Their slot assignments in the knockout bracket depend on which specific 8 groups produce a third-place team. The app stores the official 495-row FIFA Annex C lookup and resolves the exact mapping at runtime.

Implementation references:

- `backend/fifa_standings.py` ranks each group with FIFA-style head-to-head recursion.
- `backend/bracket_engine.py` ranks third-place teams and resolves predicted bracket paths.
- `backend/third_place_table.py` contains the full 495-row Annex C lookup.

## 8. Sources

- [FIFA: groups, qualification rules and tie-breakers](https://www.fifa.com/en/articles/groups-how-teams-qualify-tie-breakers)
- [FIFA: World Cup 2026 format](https://gpcustomersupportfwc2026.tickets.fifa.com/hc/en-gb/articles/28784798873117-8-What-is-the-format-for-the-FIFA-World-Cup-26-tournament)
- FIFA Regulations Annex C: third-place assignment table.
