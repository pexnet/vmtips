# VMTips — Scoring Rules (World Cup 2026)

> **Document Version:** 2.0  
> **Purpose:** Define all scoring rules in one place so changes can be made easily before and during the tournament.  
> **Scope:** This document reflects the actual scoring engine implemented in `backend/scoring.py` and the recalculation logic in `backend/routers/admin.py`.

---

## 1. Tournament Structure

- **Group Stage:** 12 groups (A–L), 4 teams per group. Top 2 + 8 best third-placed teams advance to the knockout stage.
- **Knockout Stage:** Round of 32 (Round of 16*) → Round of 16 → Quarterfinal → Semifinal → Final.  
  (*The "Round of 32" is labeled as "Round of 16" in some contexts due to the expanded 48-team format.)
- **Prediction happens in two phases:**
  1. **Phase 1:** Predict all 72 group stage matches before the WC deadline (save incrementally).
  2. **Phase 2:** Predict the entire knockout stage (bracket + matches) after the group stage ends.

---

## 2. Match Result Points

Points for a single match prediction are calculated by checking five independent criteria. Each criterion that is satisfied adds its point value — they are **additive** and not mutually exclusive.

| Criterion | Points | Description |
|---|---|---|
| **Correct outcome (1X2)** | 3 p | You correctly picked the winner (home win, away win, or draw) |
| **Correct home score** | 2 p | You predicted the exact number of goals scored by the home team |
| **Correct away score** | 2 p | You predicted the exact number of goals scored by the away team |
| **Correct total goals** | 1 p | The sum of your predicted goals equals the sum of the actual goals (home + away) |
| **Correct goal margin** | 1 p | The goal difference (home − away) in your prediction matches the actual goal difference |

### Maximum per match

A **perfect prediction** (exact scoreline) automatically satisfies all five criteria:

3 (outcome) + 2 (home score) + 2 (away score) + 1 (total goals) + 1 (margin) = **9 points**

> **Note:** A perfect prediction earns 9 points, not 7. The correct-outcome and correct-score bonuses stack with the total-goals and margin bonuses.

### When do the bonus criteria overlap?

- **Total goals** can be correct even when individual scores are wrong.  
  Example: You predict 3-0 (total 3), actual is 2-1 (total 3) → total goals correct (+1 p) but neither individual score is right.
- **Goal margin** can be correct even when total goals differ.  
  Example: You predict 3-1 (margin +2), actual is 2-0 (margin +2) → margin correct (+1 p) but total goals differ (4 vs 2).
- For **draws**, correct margin (goal difference 0) and correct outcome (draw) always coincide.

### Examples

| # | Your Prediction | Actual Result | Outcome (3p) | Home Score (2p) | Away Score (2p) | Total Goals (1p) | Margin (1p) | **Total** |
|---|---||---|---|---|---|---|---|
| 1 | 2-1 | **2-1** | ✅ 3 | ✅ 2 | ✅ 2 | ✅ 1 | ✅ 1 | **9 p** |
| 2 | 1-1 | **1-1** | ✅ 3 | ✅ 2 | ✅ 2 | ✅ 1 | ✅ 1 | **9 p** |
| 3 | 3-1 | **2-0** | ✅ 3 | ❌ | ❌ | ❌ | ✅ 1 | **4 p** |
| 4 | 3-0 | **2-1** | ✅ 3 | ❌ | ❌ | ✅ 1 | ❌ | **4 p** |
| 5 | 2-1 | **3-1** | ✅ 3 | ❌ | ✅ 2 | ❌ | ❌ | **5 p** |
| 6 | 2-0 | **2-3** | ❌ | ✅ 2 | ❌ | ❌ | ❌ | **2 p** |
| 7 | 1-1 | **0-0** | ✅ 3 | ❌ | ❌ | ❌ | ✅ 1 | **4 p** |
| 8 | 3-2 | **2-0** | ✅ 3 | ❌ | ❌ | ❌ | ❌ | **3 p** |
| 9 | 2-0 | **0-1** | ❌ | ❌ | ❌ | ❌ | ❌ | **0 p** |

---

## 3. Knockout Bracket Points (Bonus)

> Applies only if you predicted the correct team in the correct knockout round.

| Round | Points per team |
|---|---|
| Round of 32 (Round of 16) | 4 p |
| Round of 16 | 6 p |
| Quarterfinal | 8 p |
| Semifinal | 10 p |
| Final | 15 p |
| **Max total bracket** | ~228 p |

### Note: Dual match result points in knockout stage

For knockout matches, points are calculated in two parallel tracks:

1. **Match result points** — You get points for correct outcome/goals on each match slot (regardless of which teams actually play). For example, if you predicted Germany–South Korea 3-1 in Round of 32 match #1, and the real match becomes Brazil–Scotland 3-1, you still get 9p for your result prediction (if the scores match).

2. **Team bonus** — Extra points for each team you correctly placed in the right round.

---

## 4. Tournament Bonus Predictions

Before the tournament begins, you can make four long-term predictions. Each correct prediction awards **25 points**.

| Bonus | Points | Description | Matching Rule |
|---|---|---|---|
| **World Champion** | 25 p | Predict which team wins the World Cup | Must match the team by ID (exact team) |
| **Top Scorer** | 25 p | Predict the player who scores the most goals | Matched case-insensitively (e.g., "Mbappe" = "MBAPPE") |
| **Top Assist** | 25 p | Predict the player who gets the most assists | Matched case-insensitively |
| **Total Goals** | 25 p | Guess the total number of goals in the entire tournament | Must be an exact integer match |

| **Tournament bonuses max** | **100 p** | | |

> Tournament bonuses are counted in the global leaderboard.

### Examples

- You predict **France** as champion, **Mbappe** as top scorer, **De Bruyne** as top assist, and **160** total goals.
  - If France wins, Mbappe is top scorer, De Bruyne is top assist, and there are exactly 160 goals → **100 p**
  - If France wins and nothing else matches → **25 p**
  - If you predicted "Kane" for top scorer but the actual top scorer is "Haaland" → **0 p** for that category
- Name matching is case-insensitive and whitespace-trimmed: `"  MBAPPE  "` matches `"mbappe"`.

---

## 5. League Bonus Questions

League administrators can create custom bonus questions for their league:

- Each question has a flexible point value (1–100 p per question, set by the admin).
- Example: "Which team scores the most goals in the group stage?"
- The admin decides the correct answer and awards points manually.

These points are tracked in the `league_bonus_points` column on the `scores` table and count toward the user's total.

---

## 6. Match Locking

Predictions are **locked at kickoff** — once a match has started, you can no longer create or update a prediction for that match.

### How it works

- Every match has a `match_date` field (the scheduled kickoff time in UTC).
- When you submit a batch of predictions, the server checks **all** predictions atomically before saving any.
- If **any** match in the batch has a `match_date` that is at or before the current UTC time, the entire batch is rejected with a `403 match_locked` error, including the `match_id` and `kickoff` time of the locked match.
- This means you cannot partially save a batch if one match is locked — fix the locked match (remove it) and resubmit.
- Predictions that were already saved before kickoff remain valid and are scored once the match result is entered.

### Error response example

```json
{
  "error": "match_locked",
  "match_id": 42,
  "kickoff": "2026-06-11T18:00:00"
}
```

---

## 7. Score Recalculation

Scores are **cached** in the `scores` table and must be recalculated when match results are entered or corrected.

### How recalculation works

1. The admin triggers recalculation via `POST /admin/scores/recalculate` (requires admin authentication).
2. The system queries **all finished matches** (status = `"finished"`) and **all predictions** for those matches.
3. For each prediction, the scoring engine (`calculate_match_points`) computes the points based on the five criteria.
4. The `match_points` column is updated to the sum of all match prediction points for each user.
5. The `total_points` column is recalculated as:  
   `total_points = match_points + bracket_points + tournament_bonus_points + league_bonus_points`
6. If a user has predictions but no `Score` row, one is created automatically.

### When to recalculate

- After entering or correcting a match result via `POST /admin/matches/{match_id}/result`.
- After updating tournament bonus results.
- Any time you suspect cached scores are out of sync with actual results.

### Response example

```json
{
  "recalculated": true,
  "matches_processed": 15,
  "users_updated": 42
}
```

---

## 8. Score Breakdown

Each user's total score is the sum of four independent categories:

| Category | Source |
|---|---|
| **match_points** | Sum of points from all match predictions (Section 2) |
| **bracket_points** | Sum of points from knockout bracket predictions (Section 3) |
| **tournament_bonus_points** | Sum of points from tournament bonus predictions (Section 4) |
| **league_bonus_points** | Sum of points from league bonus questions (Section 5) |
| **total_points** | match_points + bracket_points + tournament_bonus_points + league_bonus_points |

---

## 9. Maximum Points Summary

| Category | Max Points | Detail |
|---|---|---|
| Group stage matches (72 × 9p) | 648 p | 9p per match with perfect prediction |
| Knockout matches (31 × 9p) | 279 p | 9p per match with perfect prediction |
| Knockout bracket bonus | ~228 p | Correct teams in correct rounds |
| Tournament bonuses | 100 p | 4 × 25p |
| League bonus questions | varies | Set by league admin |
| **Total theoretical max** | **~1255 p** | Excluding league bonus questions |

---

## 10. Change Log

| Date | Change | Done by |
|---|---|---|
| 2026-05-14 | Initial version | Hermes / pexnet |
| 2026-05-15 | v2.0 — Updated to match actual backend scoring engine: added total-goals (+1p) and margin (+1p) criteria; corrected tournament bonus values (all 25p each); added match locking, recalculation, and score breakdown sections; updated max points from ~1049 to ~1255 | Hermes / pexnet |