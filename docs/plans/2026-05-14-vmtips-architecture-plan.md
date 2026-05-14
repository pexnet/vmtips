# VMtips 2026 — Arkitektur- och Implementationsplan

> **Datum:** 2026-05-14  
> **Mål:** Bygga en komplett vmtips-applikation för VM 2026 med inloggning, ligor, tippning i två faser, realtidspoäng, och matchresultat-sync.  
> **Tech Stack:** React + Vite (frontend), Python FastAPI + SQLite (backend)

---

## 1. Kravspecifikation

### 1.1 Funktionella krav

| ID | Krav | Prioritet |
|---|---|---|
| F1 | Användarregistrering och inloggning (email + lösenord) | Måste |
| F2 | Användare kan skapa privata ligor med 6-teckens inbjudningskod | Måste |
| F3 | Användare kan gå med i publika ligor | Måste |
| F4 | **Fas 1:** Tippa alla 72 gruppspelsmatcher innan VM-start (spara stegvis) | Måste |
| F5 | **Fas 2:** Tippa hela slutspelet efter gruppselets slut (bracket + matcher) | Måste |
| F6 | Live-poängräkning baserat på definierat poängsystem | Måste |
| F7 | Topplistor per liga och global topplista | Måste |
| F8 | Turneringsbonusar (världsmästare, skyttekung, assistkung, totalt mål) | Måste |
| F9 | Bonusfrågor per liga (admin kan skapa egna frågor) | Bör |
| F10 | Matchresultat-sync från extern API (worldcupjson.net fallback) | Bör |
| F11 | Admin-panel för att hantera ligor och dela ut bonuspoäng | Bör |

### 1.2 Icke-funktionella krav

| ID | Krav |
|---|---|
| NF1 | SQLite för enkelhet (single-file, ingen server setup) |
| NF2 | Stateless JWT-auth (ingen sessions-server) |
| NF3 | Frontend och backend ska kunna köras separat (dev: Vite proxy → FastAPI) |
| NF4 | Allt ska funka i en Docker-container (tillval men bra att ha) |
| NF5 | Responsive design (mobil + desktop) |

---

## 2. Arkitektur

```
┌─────────────────────────────────────────────┐
│                  React + Vite                  │
│  ┌─────────┐  ┌──────────┐  ┌─────────────┐  │
│  │  Auth   │  │ Tippning │  │ Topplistor  │  │
│  │ (login) │  │(fas1/2) │  │  (liga/global)│ │
│  └─────────┘  └──────────┘  └─────────────┘  │
│                                              │
│  Vite dev proxy ────────▶ FastAPI            │
└─────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│              Python FastAPI                  │
│  ┌─────────┐  ┌──────────┐  ┌─────────────┐  │
│  │  Auth   │  │  Tips    │  │  Poäng-     │  │
│  │ (JWT)   │  │  CRUD    │  │  beräkning  │  │
│  └─────────┘  └──────────┘  └─────────────┘  │
│                                              │
│  ┌──────────┐  ┌───────────────────────────┐  │
│  │  Liga/   │  │  Matchresultat-sync       │  │
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

## 3. Databasmodell (ER-struktur)

### 3.1 Entiteter

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
  code (FIFA-kod, t.ex. "SWE")
  group (A-L)
  flag_url (emoji eller URL)

matches
  id (PK)
  match_number (1-104, för enkel identifiering)
  group (A-L eller null för slutspel)
  round (group/ro32/ro16/qf/sf/final)
  home_team_id (FK → teams)
  away_team_id (FK → teams)
  home_goals (null tills match spelats)
  away_goals (null tills match spelats)
  match_date
  status (scheduled/ongoing/finished)
  home_team_placeholder (t.ex. "1A" — gruppvinnare A)
  away_team_placeholder (t.ex. "2B")

predictions
  id (PK)
  user_id (FK → users)
  match_id (FK → matches, null för turneringsbonusar)
  home_goals (användarens tips)
  away_goals (användarens tips)
  created_at
  updated_at
  UNIQUE(user_id, match_id)

leagues
  id (PK)
  name
  invite_code (6 chars, unik)
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
  winner_team_id (FK → teams, världsmästare)
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
  answer (null tills admin sätter)
  created_at

league_bonus_answers
  id (PK)
  question_id (FK → league_bonus_questions)
  user_id (FK → users)
  answer_text
  is_correct (null tills admin bedömt)
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

## 4. API-specifikation (FastAPI)

### 4.1 Auth

```
POST /auth/register      → {email, password, display_name} → user + JWT
POST /auth/login         → {email, password} → JWT
GET  /auth/me            → aktuell användare
```

### 4.2 Matcher

```
GET  /matches            → lista alla matcher med lag och status
GET  /matches/{id}       → enskild match
GET  /matches/groups     → gruppspelsmatcher (fas 1)
GET  /matches/knockout   → slutspelsmatcher (fas 2, placeholders)
POST /matches/{id}/result (admin) → {home_goals, away_goals} (eller sync från API)
```

### 4.3 Tippning

```
GET    /predictions                → mina tips (alla matcher)
POST   /predictions/batch           → spara/uppdatera batch-tips [{match_id, home, away}]
GET    /predictions/tournament       → mina turneringsbonusar
POST   /predictions/tournament      → spara turneringsbonusar
```

### 4.4 Ligor

```
POST   /leagues              → skapa liga (auto-generera invite_code)
GET    /leagues             → lista mina ligor
GET    /leagues/{id}        → liga-detaljer med medlemmar
POST   /leagues/{id}/join   → gå med via invite_code
GET    /leagues/public      → lista publika ligor
```

### 4.5 Topplistor / Poäng

```
GET    /leaderboard/global           → global topplista
GET    /leaderboard/league/{id}      → topplista per liga
GET    /leaderboard/me               → min poängfördelning
POST   /scores/recalculate (admin)  → omräkna alla poäng
```

---

## 5. Frontend-struktur (React + Vite)

```
src/
  main.tsx
  App.tsx
  api/              → Axios-instans med JWT-interceptor
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
    GroupStagePage.tsx      → Fas 1: tippa gruppspel
    KnockoutPage.tsx        → Fas 2: tippa slutspel
    LeaderboardPage.tsx
    LeaguePage.tsx
    ProfilePage.tsx
  hooks/
    useAuth.ts
    usePredictions.ts
    useMatches.ts
  types/
    api.ts                  → TypeScript-typer för API-responses
```

---

## 6. Poängberäkningslogik (Python)

```python
def calculate_match_points(pred_home, pred_away, actual_home, actual_goals):
    points = 0
    # Utfall (1X2)
    pred_outcome = sign(pred_home - pred_away)
    actual_outcome = sign(actual_home - actual_away)
    if pred_outcome == actual_outcome:
        points += 3
    # Exakta mål
    if pred_home == actual_home:
        points += 2
    if pred_away == actual_away:
        points += 2
    return points

def calculate_bracket_points(user_bracket, actual_bracket):
    # Jämför lag per runda
    round_points = {"ro32": 4, "ro16": 6, "qf": 8, "sf": 10, "final": 15}
    points = 0
    for round_name, point_value in round_points.items():
        for team in user_bracket.get(round_name, []):
            if team in actual_bracket.get(round_name, []):
                points += point_value
    return points
```

---

## 7. Matchresultat-sync

### Strategi

1. **Primär källa:** `worldcupjson.net` — gratis, JSON, realtid.  
   Endpoints: `GET /matches`, `GET /matches/today`, `GET /matches/current`

2. **Fallback:** `football-data.org` — gratis tier finns, kräver API-nyckel.

3. **Backup:** Manuell inmatning via admin-panel.

### Sync-jobb

En bakgrundscron eller endpoint som:
1. Hämtar alla matcher från worldcupjson.net
2. Mappar `match_number` eller datum+lag till vår `matches`-tabell
3. Uppdaterar `home_goals`, `away_goals`, `status`
4. Triggern omräkning av poäng (async eller on-demand)

```bash
# Manuell sync
POST /admin/sync-results

# Automatisk: köras var 15:e minut under VM via cronjob eller APScheduler
```

---

## 8. Implementationsplan — Bite-Sized Tasks

> Varje task = 5-15 minuter fokuserat arbete. TDD där det är praktiskt.

### Fas A: Backend-grund (FastAPI + SQLite + Auth)

#### Task A1: Projektstruktur och dependencies
**Fil:** `backend/requirements.txt`, `backend/main.py`  
**Steg:**
1. Skapa `backend/` med `requirements.txt`: `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `passlib[bcrypt]`, `python-jose[cryptography]`, `python-multipart`
2. Skapa `backend/main.py` med grundläggande FastAPI-app
3. Testa: `uvicorn main:app --reload` → `curl http://localhost:8000/health`

#### Task A2: Databas-setup (SQLAlchemy + SQLite)
**Fil:** `backend/database.py`, `backend/models.py`  
**Steg:**
1. `database.py`: skapa engine, SessionLocal, Base
2. `models.py`: definiera alla tabeller (users, teams, matches, predictions, leagues, league_members, tournament_bonuses, scores)
3. Skapa migrering: `Base.metadata.create_all(bind=engine)`
4. Testa: verifiera att SQLite-fil skapas

#### Task A3: Seed VM 2026 data (grupper + matcher)
**Fil:** `backend/seed.py`  
**Steg:**
1. Definiera alla 12 grupper (A-L) med 4 lag vardera
2. Definiera alla 72 gruppspelsmatcher (runda robin inom grupp)
3. Definiera slutspelsstrukturen med placeholders (1A, 2B, etc.)
4. Seed:a in i databasen
5. Testa: `SELECT COUNT(*) FROM matches` → 104

#### Task A4: JWT Auth (register + login)
**Fil:** `backend/routers/auth.py`, `backend/security.py`  
**Steg:**
1. `security.py`: bcrypt hashing, JWT encode/decode
2. `auth.py`: `/auth/register`, `/auth/login`
3. Dependency `get_current_user` för skyddade routes
4. Testa: registrera + logga in via curl, verifiera JWT

#### Task A5: Matcher API
**Fil:** `backend/routers/matches.py`  
**Steg:**
1. `GET /matches` — lista alla matcher med lag-info
2. `GET /matches/groups` — gruppspelsmatcher
3. `GET /matches/knockout` — slutspelsmatcher
4. Testa: curl endpoints, verifiera JSON-struktur

#### Task A6: Tippning API (batch-save)
**Fil:** `backend/routers/predictions.py`  
**Steg:**
1. `GET /predictions` — hämta aktuell användares tips
2. `POST /predictions/batch` — spara/uppdatera tips för flera matcher
3. Validera: deadline-kontroll (före matchstart)
4. Testa: spara tips, hämta, verifiera unik constraint

#### Task A7: Turneringsbonusar API
**Fil:** `backend/routers/predictions.py` (utöka)  
**Steg:**
1. `GET /predictions/tournament` — hämta bonus-tips
2. `POST /predictions/tournament` — spara bonus-tips
3. Testa: spara och hämta

#### Task A8: Liga API (skapa, gå med, lista)
**Fil:** `backend/routers/leagues.py`  
**Steg:**
1. `POST /leagues` — skapa liga med auto-genererad 6-siffrig kod
2. `GET /leagues` — mina ligor
3. `POST /leagues/{id}/join` — gå med via kod
4. `GET /leagues/public` — publika ligor
5. Testa: skapa liga, bjud in, gå med

#### Task A9: Poängberäkningsmotor
**Fil:** `backend/scoring.py`  
**Steg:**
1. Implementera `calculate_match_points()` enligt regelverket
2. Implementera `calculate_bracket_points()`
3. Implementera `calculate_tournament_bonus_points()`
4. Testa: enhetstester med olika scenarios

#### Task A10: Topplista API
**Fil:** `backend/routers/leaderboard.py`  
**Steg:**
1. `GET /leaderboard/global` — summera poäng per användare
2. `GET /leaderboard/league/{id}` — summera per liga
3. `GET /leaderboard/me` — detaljerad poängfördelning
4. Testa: skapa data, verifiera ranking

#### Task A11: Matchresultat-sync endpoint
**Fil:** `backend/routers/admin.py`, `backend/sync.py`  
**Steg:**
1. `sync.py`: funktion för att hämta från worldcupjson.net och uppdatera `matches`
2. `admin.py`: `POST /admin/sync-results` (skyddat, endast admin)
3. Efter sync: trigger poängomräkning
4. Testa: mocka extern API, verifiera uppdatering

### Fas B: Frontend-grund (React + Vite)

#### Task B1: Vite-setup + routing
**Fil:** `frontend/` (hela projektet)
**Steg:**
1. `npm create vite@latest frontend -- --template react-ts`
2. Installera: `react-router-dom`, `axios`, `tailwindcss` (eller valfritt CSS)
3. Konfigurera proxy i `vite.config.ts`: `/api` → `http://localhost:8000`
4. Testa: `npm run dev`, verifiera routing

#### Task B2: API-klient + Auth-hanterare
**Fil:** `frontend/src/api/client.ts`, `frontend/src/hooks/useAuth.ts`  
**Steg:**
1. `client.ts`: Axios med baseURL, JWT-interceptor
2. `useAuth.ts`: context eller zustand-store för auth-state
3. Testa: login-request via frontend

#### Task B3: Login / Register-sidor
**Fil:** `frontend/src/pages/LoginPage.tsx`, `RegisterPage.tsx`  
**Steg:**
1. Formulär med validering
2. Anropa `/auth/login` och `/auth/register`
3. Spara JWT i localStorage
4. Redirect efter login

#### Task B4: Layout + Navbar
**Fil:** `frontend/src/components/Layout/Navbar.tsx`, `App.tsx`  
**Steg:**
1. Navbar med länkar: Matcher, Ligor, Topplista, Profil
2. Visa inloggad användare / login-knapp
3. ProtectedRoute: kräv auth för tippning

#### Task B5: Gruppspels-tippning (Fas 1)
**Fil:** `frontend/src/pages/GroupStagePage.tsx`  
**Steg:**
1. Hämta gruppspelsmatcher från `/matches/groups`
2. Visa matcher per grupp (A-L)
3. Input-fält för hemma/borta-mål
4. "Spara alla tips"-knapp → `POST /predictions/batch`
5. Visa sparade tips vid återbesök

#### Task B6: Slutspels-tippning (Fas 2)
**Fil:** `frontend/src/pages/KnockoutPage.tsx`  
**Steg:**
1. Hämta slutspelsmatcher med placeholders
2. Visa bracket-visuellt (trädstruktur)
3. Tippa varje match + spara
4. Visa "mina lag i varje runda" för bracket-bonus

#### Task B7: Topplistor
**Fil:** `frontend/src/pages/LeaderboardPage.tsx`, `frontend/src/components/Leagues/Leaderboard.tsx`  
**Steg:**
1. Global topplista
2. Per-liga topplista (dropdown för att välja liga)
3. Visa poängfördelning: match, bracket, bonus

#### Task B8: Liga-hantering
**Fil:** `frontend/src/pages/LeaguePage.tsx`  
**Steg:**
1. Lista mina ligor
2. Skapa ny liga (namn, publik/privat)
3. Visa invite-kod
4. Gå med i liga via kod
5. Lista publika ligor

#### Task B9: Turneringsbonusar-sida
**Fil:** `frontend/src/pages/TournamentBonusesPage.tsx`  
**Steg:**
1. Dropdown för världsmästare (alla lag)
2. Text-input för skyttekung, assistkung
3. Number-input för totalt antal mål
4. Spara-knapp

### Fas C: Integration och avslutning

#### Task C1: Docker Compose (valfritt men bra)
**Fil:** `docker-compose.yml`, `Dockerfile` (frontend + backend)
**Steg:**
1. Backend-Dockerfile med Python
2. Frontend byggs till statiska filer och serveras via nginx
3. `docker-compose up` ska starta hela stacken

#### Task C2: README och dokumentation
**Fil:** `README.md`, `docs/DEPLOY.md`  
**Steg:**
1. Installationsinstruktioner
2. Miljövariabler (JWT_SECRET, ADMIN_EMAIL, etc.)
3. Hur man seed:ar VM-data
4. Hur man kör sync-jobbet

#### Task C3: Manuell test av hela flödet
**Steg:**
1. Registrera användare
2. Skapa liga
3. Tippa gruppspel
4. Spara
5. Tippa turneringsbonusar
6. Kontrollera topplista
7. Verifiera poängberäkning

---

## 9. Miljövariabler

```bash
# backend/.env
DATABASE_URL=sqlite:///./vmtips.db
JWT_SECRET_KEY=byt-ut-denna-i-produktion
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=168  # 7 dagar
ADMIN_EMAIL=admin@example.com
WORLD_CUP_JSON_URL=https://worldcupjson.net/matches

# frontend/.env
VITE_API_BASE_URL=/api
```

---

## 10. Tidsuppskattning

| Fas | Tasks | Uppskattad tid |
|---|---|---|
| A: Backend | 11 tasks | ~6-8 timmar |
| B: Frontend | 9 tasks | ~8-10 timmar |
| C: Integration | 3 tasks | ~2-3 timmar |
| **Totalt** | **23 tasks** | **~16-21 timmar** |

---

## 11. Nästa steg

1. **Godkänn planen** — justera poängsystem, scope, eller prioriteringar
2. **Välj CSS-ramverk** — Tailwind, MUI, eller plain CSS?
3. **Börja implementera** — backend först (data + API), sedan frontend (UI + integration)
