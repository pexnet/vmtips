# VMTips — Scoring Rules (World Cup 2026)

> **Document Version:** 1.0  
> **Purpose:** Define all scoring rules in one place so changes can be made easily before and during the tournament.

---

## 1. Tournament Structure

- **Group Stage:** 12 groups (A–L), 4 teams per group. Top 2 + 8 best third-placed teams advance to the knockout stage.
- **Knockout Stage:** Round of 32 (Round of 16) → Round of 16 → Quarterfinal → Semifinal → Final.
- **Prediction happens in two phases:**
  1. **Phase 1:** Predict all 72 group stage matches before the WC deadline (save incrementally).
  2. **Phase 2:** Predict the entire knockout stage (bracket + matches) after the group stage ends.

---

## 2. Match Result Points (Group Stage + Knockout)

| Point Type | Points | Description |
|---|---|---|
| **Correct outcome (1X2)** | 3 p | Correct winner or draw |
| **Correct home score** | 2 p | Exact number of goals for the home team |
| **Correct away score** | 2 p | Exact number of goals for the away team |
| **Perfect prediction** | 7 p | Correct outcome + both exact scores (3+2+2) |

### Examples

| Prediction | Result | Outcome | Home | Away | Total |
|---|---|---|---|---|---|
| 2-1 | **2-1** | ✅ 3p | ✅ 2p | ✅ 2p | **7p** |
| 2-1 | **3-1** | ✅ 3p | ❌ | ✅ 2p | **5p** |
| 2-1 | **1-1** | ❌ | ❌ | ✅ 2p | **2p** |
| 2-1 | **0-2** | ❌ | ❌ | ❌ | **0p** |

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

1. **Match result points** — You get points for correct outcome/goals on each match slot (regardless of which teams actually play). For example, if you predicted Germany–South Korea 3-1 in Round of 32 match #1, and the real match becomes Brazil–Scotland 3-1, you still get 7p for your result prediction.

2. **Team bonus** — Extra points for each team you correctly placed in the right round.

---

## 4. Tournament Bonuses (Long-term predictions before WC starts)

| Bonus | Points | Description |
|---|---|---|
| **World Champion** | 25 p | Predict which team wins the WC |
| **Top Scorer** | 25 p | Predict who scores the most goals in the tournament |
| **Top Assists** | 30 p | Predict who gets the most assists |
| **Total Goals** | 20 p | Guess the total number of goals in the entire WC |
| **Tournament bonuses max** | **100 p** | |

> Tournament bonuses are counted in the global leaderboard.

---

## 5. Bonus Questions (per league)

League administrators can create custom bonus questions:
- Flexible points (1–100 p per question)
- Example: "Which team scores the most goals in the group stage?"
- Admin decides the answer and awards points manually

---

## 6. Maximum Points Summary

| Category | Max Points |
|---|---|
| Group stage matches (72 × 7p) | 504 p |
| Knockout matches (31 × 7p) | 217 p |
| Knockout bracket bonus | ~228 p |
| Tournament bonuses | 100 p |
| **Total theoretical max** | **~1049 p** |

---

## 7. Change Log

| Date | Change | Done by |
|---|---|---|
| 2026-05-14 | Initial version | Hermes / pexnet |
