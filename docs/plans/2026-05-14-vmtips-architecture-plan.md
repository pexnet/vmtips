# VMTips 2026 — Architecture and Implementation Plan

> **Date:** 2026-05-14  
> **Goal:** Build a complete World Cup prediction app with login, leagues, two-phase predictions, live scoring, and match result sync.  
> **Tech Stack:** React + Vite + MUI (frontend), Python FastAPI + SQLite (backend), flag emojis per team

---

## 1. Requirements Specification

### 1.1 Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| F1 | User registration and login (email + password) | Must |
| F2 | Users can create private leagues with 6-character invite code | Must |
| F3 | Users can join public leagues | Must |
| F4 | **Phase 1:** Predict all 72 group stage matches before WC starts (save incrementally) | Must |
| F5 | **Phase 2:** Predict entire knockout stage after group stage ends (bracket + matches) | Must |
| F6 | Live scoring based on defined scoring rules | Must |
| F7 | Leaderboards per league and global leaderboard | Must |
| F8 | Tournament bonuses (world champion, top scorer, top assists, total goals) | Must |
| F9 | Bonus questions per league (admin can create custom questions) | Should |
| F10 | Match result sync from external API (worldcupjson.net fallback) | Should |
| F11 | Admin panel to manage leagues and award bonus points | Should |

### 1.2 Non-Functional Requirements

| ID | Requirement |
|---|---|
| NF1 | SQLite for simplicity (single file, no server setup) |
| NF2 | Stateless JWT auth (no session server) |
| NF3 | Frontend and backend should be runnable separately (dev: Vite proxy → FastAPI) |
| NF4 | Everything should work in one Docker container (optional but good to have) |
| NF5 | Responsive design (mobile + desktop) |

---

## 2. Architecture

```
┌─────────────────────────────────────────────┐
│                  React + Vite                  │
│  ┌─────────┐  ┌──────────┐  ┌─────────────┐  │
│  │  Auth   │  │ Predict  │  │ Leaderboard │  │
│  │ (login) │  │ (p1/p2)  │  │ (league/global)││
│  └─────────┘  └──────────┘  └─────────────┘  │
│                                              │
│  Vite dev proxy ────────▶ FastAPI            │
└─────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│              Python FastAPI                  │
│  ┌─────────┐  ┌──────────┐  ┌─────────────┐  │
│  │  Auth   │  │  Tips    │  │  Scoring    │  │
│  │ (JWT)   │  │  CRUD    │  │  Engine     │  │
│  └─────────┘  └──────────┘  └─────────────┘  │
│                                              │
│  ┌──────────┐  ┌───────────────────────────┐  │
│  │  League/ │  │  Match Result Sync        │  │
│  │  Admin   │  │  (worldcupjson.net)       │  │
│  └──────────┘  └───────────────────────────┘  │
└─────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│                SQLite (.db)                  │
│  users, teams, matches, predictions,       │
│  leagues, league_members, scores, bonuses   │
└─────────────────────────────────────────────┘
```

---

## 3. Database Model (ER Structure)

### 3.1 Entities

```
users
  id (PK)
  email (unique)
  password_hash
  display_name
  created_at

teams
  id (PK)
  name
  code (FIFA code, e.g. "SWE")
  group (A-L)
  flag_emoji (e.g. "🇸🇪")
  flag_svg (from country-flag-icons/lib/flags/1x1/SE.svg)

matches
  id (PK)
  match_number (1-104, for easy identification)
  group (A-L or null for knockout)
  round (group/ro32/ro16/qf/sf/final)
  home_team_id (FK → teams)
  away_team_id (FK → teams)
  home_goals (null until match played)
  away_goals (null until match played)
  match_date
  status (scheduled/ongoing/finished)
  home_team_placeholder (e.g. "1A" — group A winner)
  away_team_placeholder (e.g. "2B")

predictions
  id (PK)
  user_id (FK → users)
  match_id (FK → matches, null for tournament bonuses)
  home_goals (user's prediction)
  away_goals (user's prediction)
  created_at
  updated_at
  UNIQUE(user_id, match_id)

leagues
  id (PK)
  name
  invite_code (6 chars, unique)
  is_public (boolean)
  admin_user_id (FK → users)
  created_at

league_members
  id (PK)
  league_id (FK → leagues)
  user_id (FK → users)
  joined_at
  UNIQUE(league_id, user_id)

tournament_bonuses
  id (PK)
  user_id (FK → users)
  winner_team_id (FK → teams, world champion)
  top_scorer_name (str)
  top_assist_name (str)
  total_goals (int)
  created_at
  updated_at

league_bonus_questions
  id (PK)
  league_id (FK → leagues)
  question_text
  points_value
  answer (null until admin sets)
  created_at

league_bonus_answers
  id (PK)
  question_id (FK → league_bonus_questions)
  user_id (FK → users)
  answer_text
  is_correct (null until admin grades)
  points_awarded

scores
  id (PK)
  user_id (FK → users)
  league_id (FK → leagues, null = global)
  match_points
  bracket_points
  tournament_bonus_points
  league_bonus_points
  total_points
  updated_at
```

---

## 4. API Specification (FastAPI)

### 4.1 Auth

```
POST /auth/register      → {email, password, display_name} → user + JWT
POST /auth/login         → {email, password} → JWT
GET  /auth/me            → current user
```

### 4.2 Matches

```
GET  /matches            → list all matches with team info and status
GET  /matches/{id}       → single match
GET  /matches/groups     → group stage matches (phase 1)
GET  /matches/knockout   → knockout matches (phase 2, placeholders)
POST /matches/{id}/result (admin) → {home_goals, away_goals} (or sync from API)
```

### 4.3 Predictions

```
GET    /predictions                → my predictions (all matches)
POST   /predictions/batch           → save/update batch predictions [{match_id, home, away}]
GET    /predictions/tournament       → my tournament bonuses
POST   /predictions/tournament      → save tournament bonuses
```

### 4.4 Leagues

```
POST   /leagues              → create league (auto-generate invite_code)
GET    /leagues             → list my leagues
GET    /leagues/{id}        → league details with members
POST   /leagues/{id}/join   → join via invite_code
GET    /leagues/public      → list public leagues
```

### 4.5 Leaderboards / Scores

```
GET    /leaderboard/global           → global leaderboard
GET    /leaderboard/league/{id}      → leaderboard per league
GET    /leaderboard/me               → my score breakdown
POST   /scores/recalculate (admin)  → recalculate all scores
```

---

## 5. Frontend Structure (React + Vite + MUI)

### 5.1 Theme System (light/dark)

```
src/
  theme/
    ThemeContext.tsx      → React Context for light/dark toggle
    lightTheme.ts         → MUI createTheme({ palette: { mode: 'light', ... } })
    darkTheme.ts          → MUI createTheme({ palette: { mode: 'dark', ... } })
    index.ts              → export useThemeMode() hook
  i18n/
    I18nProvider.tsx      → Wraps app, provides locale context
    locales/
      sv.json             → Swedish translations (default)
      en.json             → English translations
    useTranslation.ts     → Hook: t('key') returns string in current locale
    types.ts              → Type-safe keys for all translation strings
```

**Design principles:**
- **Light:** White background, dark blue primary (`#1a237e`), clean cards with subtle shadows
- **Dark:** `#121212` background, electric blue accent (`#82b1ff`), high-contrast text
- Consistent `border-radius: 12px` on cards, `8px` on buttons
- Flags as emoji (🇸🇪) or SVG via `country-flag-icons` per team
- MUI `CssBaseline` + `ThemeProvider` wraps entire app in `main.tsx`

**Internationalization:**
- Default language: **Swedish** (`sv`)
- Secondary language: **English** (`en`)
- Language toggle in Navbar (e.g. 🇸🇪 / 🇬🇧 button)
- All UI strings sourced from `i18n/locales/*.json` — no hardcoded text in components
- User's language preference persisted in localStorage + sent to backend in `Accept-Language` header
- Backend errors returned with message keys that frontend translates

### 5.2 Project Structure

```
src/
  main.tsx
  App.tsx
  api/              → Axios instance with JWT interceptor
    client.ts
  components/
    Auth/
      LoginForm.tsx
      RegisterForm.tsx
    Matches/
      MatchCard.tsx
      MatchList.tsx
      PredictionForm.tsx
    Leagues/
      LeagueList.tsx
      LeagueCreate.tsx
      LeagueJoin.tsx
      Leaderboard.tsx
    Layout/
      Navbar.tsx
      ProtectedRoute.tsx
  pages/
    HomePage.tsx
    LoginPage.tsx
    RegisterPage.tsx
    GroupStagePage.tsx      → Phase 1: predict group stage
    KnockoutPage.tsx        → Phase 2: predict knockout stage
    LeaderboardPage.tsx
    LeaguePage.tsx
    ProfilePage.tsx
  hooks/
    useAuth.ts
    usePredictions.ts
    useMatches.ts
  types/
    api.ts                  → TypeScript types for API responses
```

---

## 6. Scoring Engine Logic (Python)

```python
def calculate_match_points(pred_home, pred_away, actual_home, actual_away):
    points = 0
    # Outcome (1X2)
    pred_outcome = sign(pred_home - pred_away)
    actual_outcome = sign(actual_home - actual_away)
    if pred_outcome == actual_outcome:
        points += 3
    # Exact goals
    if pred_home == actual_home:
        points += 2
    if pred_away == actual_away:
        points += 2
    return points

def calculate_bracket_points(user_bracket, actual_bracket):
    # Compare teams per round
    round_points = {"ro32": 4, "ro16": 6, "qf": 8, "sf": 10, "final": 15}
    points = 0
    for round_name, point_value in round_points.items():
        for team in user_bracket.get(round_name, []):
            if team in actual_bracket.get(round_name, []):
                points += point_value
    return points
```

---

## 7. Match Result Sync

### Strategy

1. **Primary source:** `worldcupjson.net` — free, JSON, real-time.  
   Endpoints: `GET /matches`, `GET /matches/today`, `GET /matches/current`

2. **Fallback:** `football-data.org` — free tier available, requires API key.

3. **Backup:** Manual entry via admin panel.

### Sync Job

A background cron or endpoint that:
1. Fetches all matches from worldcupjson.net
2. Maps `match_number` or date+team to our `matches` table
3. Updates `home_goals`, `away_goals`, `status`
4. Triggers score recalculation (async or on-demand)

```bash
# Manual sync
POST /admin/sync-results

# Automatic: runs every 15 minutes during WC via cronjob or APScheduler
```

---

## 8. Implementation Plan — Bite-Sized Tasks

> Each task = 5-15 minutes of focused work. TDD where practical.

### Phase A: Backend Foundation (FastAPI + SQLite + Auth)

#### Task A1: Project structure and dependencies
**File:** `backend/requirements.txt`, `backend/main.py`  
**Steps:**
1. Create `backend/` with `requirements.txt`: `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `passlib[bcrypt]`, `python-jose[cryptography]`, `python-multipart`
2. Create `backend/main.py` with basic FastAPI app
3. Test: `uvicorn main:app --reload` → `curl http://localhost:8000/health`

#### Task A2: Database setup (SQLAlchemy + SQLite)
**File:** `backend/database.py`, `backend/models.py`  
**Steps:**
1. `database.py`: create engine, SessionLocal, Base
2. `models.py`: define all tables (users, teams, matches, predictions, leagues, league_members, tournament_bonuses, scores)
3. Create migration: `Base.metadata.create_all(bind=engine)`
4. Test: verify SQLite file is created

#### Task A3: Seed WC 2026 data (groups + matches)
**File:** `backend/seed.py`  
**Steps:**
1. Define all 12 groups (A-L) with 4 teams each
2. Define all 72 group stage matches (round robin within group)
3. Define knockout structure with placeholders (1A, 2B, etc.)
4. Seed into database
5. Test: `SELECT COUNT(*) FROM matches` → 104

#### Task A4: JWT Auth (register + login)
**File:** `backend/routers/auth.py`, `backend/security.py`  
**Steps:**
1. `security.py`: bcrypt hashing, JWT encode/decode
2. `auth.py`: `/auth/register`, `/auth/login`
3. Dependency `get_current_user` for protected routes
4. Test: register + login via curl, verify JWT

#### Task A5: Matches API
**File:** `backend/routers/matches.py`  
**Steps:**
1. `GET /matches` — list all matches with team info
2. `GET /matches/groups` — group stage matches
3. `GET /matches/knockout` — knockout matches
4. Test: curl endpoints, verify JSON structure

#### Task A6: Prediction API (batch-save)
**File:** `backend/routers/predictions.py`  
**Steps:**
1. `GET /predictions` — fetch current user's predictions
2. `POST /predictions/batch` — save/update predictions for multiple matches
3. Validate: deadline check (before match start)
4. Test: save predictions, fetch, verify unique constraint

#### Task A7: Tournament Bonuses API
**File:** `backend/routers/predictions.py` (extend)  
**Steps:**
1. `GET /predictions/tournament` — fetch bonus predictions
2. `POST /predictions/tournament` — save bonus predictions
3. Test: save and fetch

#### Task A8: League API (create, join, list)
**File:** `backend/routers/leagues.py`  
**Steps:**
1. `POST /leagues` — create league with auto-generated 6-char code
2. `GET /leagues` — my leagues
3. `POST /leagues/{id}/join` — join via code
4. `GET /leagues/public` — public leagues
5. Test: create league, invite, join

#### Task A9: Scoring engine
**File:** `backend/scoring.py`  
**Steps:**
1. Implement `calculate_match_points()` per rules document
2. Implement `calculate_bracket_points()`
3. Implement `calculate_tournament_bonus_points()`
4. Test: unit tests with various scenarios

#### Task A10: Leaderboard API
**File:** `backend/routers/leaderboard.py`  
**Steps:**
1. `GET /leaderboard/global` — sum points per user
2. `GET /leaderboard/league/{id}` — sum per league
3. `GET /leaderboard/me` — detailed score breakdown
4. Test: create data, verify ranking

#### Task A11: Match result sync endpoint
**File:** `backend/routers/admin.py`, `backend/sync.py`  
**Steps:**
1. `sync.py`: function to fetch from worldcupjson.net and update `matches`
2. `admin.py`: `POST /admin/sync-results` (protected, admin only)
3. After sync: trigger score recalculation
4. Test: mock external API, verify update

### Phase B: Frontend Foundation (React + Vite)

#### Task B1: Vite setup + routing + MUI
**File:** `frontend/` (entire project)  
**Steps:**
1. `npm create vite@latest frontend -- --template react-ts`
2. Install: `react-router-dom`, `axios`, `@mui/material`, `@emotion/react`, `@emotion/styled`, `@mui/icons-material`, `country-flag-icons`
3. Configure proxy in `vite.config.ts`: `/api` → `http://localhost:8000`
4. Test: `npm run dev`, verify routing

#### Task B2: API client + Auth handler
**File:** `frontend/src/api/client.ts`, `frontend/src/hooks/useAuth.ts`  
**Steps:**
1. `client.ts`: Axios with baseURL, JWT interceptor
2. `useAuth.ts`: context or zustand store for auth state
3. Test: login request via frontend

#### Task B3: Login / Register pages
**File:** `frontend/src/pages/LoginPage.tsx`, `RegisterPage.tsx`  
**Steps:**
1. Forms with validation
2. Call `/auth/login` and `/auth/register`
3. Save JWT in localStorage
4. Redirect after login

#### Task B4: Layout + Navbar + Theme toggle
**File:** `frontend/src/components/Layout/Navbar.tsx`, `App.tsx`  
**Steps:**
1. Navbar with links: Matches, Leagues, Leaderboard, Profile
2. Show logged-in user / login button
3. Light/dark theme toggle button (uses MUI ThemeContext)
4. ProtectedRoute: require auth for predictions

#### Task B5: Group stage prediction (Phase 1)
**File:** `frontend/src/pages/GroupStagePage.tsx`  
**Steps:**
1. Fetch group stage matches from `/matches/groups`
2. Show matches per group (A-L)
3. Input fields for home/away goals
4. "Save all predictions" button → `POST /predictions/batch`
5. Show saved predictions on revisit

#### Task B6: Knockout prediction (Phase 2)
**File:** `frontend/src/pages/KnockoutPage.tsx`  
**Steps:**
1. Fetch knockout matches with placeholders
2. Show bracket visually (tree structure)
3. Predict each match + save
4. Show "my teams per round" for bracket bonus

#### Task B7: Leaderboards
**File:** `frontend/src/pages/LeaderboardPage.tsx`, `frontend/src/components/Leagues/Leaderboard.tsx`  
**Steps:**
1. Global leaderboard
2. Per-league leaderboard (dropdown to select league)
3. Show score breakdown: match, bracket, bonus

#### Task B8: League management
**File:** `frontend/src/pages/LeaguePage.tsx`  
**Steps:**
1. List my leagues
2. Create new league (name, public/private)
3. Show invite code
4. Join league via code
5. List public leagues

#### Task B9: Tournament bonuses page
**File:** `frontend/src/pages/TournamentBonusesPage.tsx`  
**Steps:**
1. Dropdown for world champion (all teams)
2. Text input for top scorer, top assists
3. Number input for total goals
4. Save button

### Phase C: Integration and Wrap-up

#### Task C1: Docker Compose (optional but good)
**File:** `docker-compose.yml`, `Dockerfile` (frontend + backend)  
**Steps:**
1. Backend Dockerfile with Python
2. Frontend builds to static files and served via nginx
3. `docker-compose up` should start entire stack

#### Task C2: README and documentation
**File:** `README.md`, `docs/DEPLOY.md`  
**Steps:**
1. Installation instructions
2. Environment variables (JWT_SECRET, ADMIN_EMAIL, etc.)
3. How to seed WC data
4. How to run sync job

#### Task C3: Manual test of entire flow
**Steps:**
1. Register user
2. Create league
3. Predict group stage
4. Save
5. Predict tournament bonuses
6. Check leaderboard
7. Verify scoring calculation

---

## 9. Development Setup (Docker)

### Local Development

```bash
# Start dev environment (backend + frontend hot reload)
./scripts/dev.sh up

# Open:
#   Frontend: http://localhost:5173
#   Backend API: http://localhost:8000
#   API docs: http://localhost:8000/docs
```

### Production Deploy

```bash
# On production server
docker pull pexnet/vmtips:latest
docker compose -f docker-compose.prod.yml up -d
```

See `docs/DEPLOY.md` for full details.

---

## 10. Environment Variables

```bash
# backend/.env
DATABASE_URL=sqlite:///./vmtips.db
JWT_SECRET_KEY=change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=168  # 7 days
ADMIN_EMAIL=admin@example.com
WORLD_CUP_JSON_URL=https://worldcupjson.net/matches
CORS_ORIGINS=http://localhost:5173

# frontend/.env
VITE_API_BASE_URL=/api
```

---

## 11. Time Estimate

| Phase | Tasks | Estimated Time |
|---|---|---|
| A: Backend | 11 tasks | ~6-8 hours |
| B: Frontend | 9 tasks | ~8-10 hours |
| C: Integration | 3 tasks | ~2-3 hours |
| **Total** | **23 tasks** | **~16-21 hours** |

---

## 12. Next Steps

1. **Approve the plan** — adjust scoring, scope, or priorities
2. **Choose CSS framework** — Tailwind, MUI, or plain CSS?
3. **Start implementing** — backend first (data + API), then frontend (UI + integration)
