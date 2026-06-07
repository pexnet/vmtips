# VMTips - Session Handoff (2026-06-07)

## Summary

Addressed the two High-severity issues from the code review plus one
infra issue. Backend tests still 174/174, frontend lint clean, build OK.

## What changed

### Frontend - AdminPage.tsx split

1092-line admin page split into a thin shell (108 lines) plus 9 per-tab
files under `frontend/src/pages/admin/`:

```
src/pages/
- AdminPage.tsx          (was 1092, now 108 lines; tabs + error/success banners only)
- admin/
    - MatchResultsTab.tsx        (148 lines)
    - GroupStandingsTab.tsx      (116)
    - TournamentResultTab.tsx    (86)
    - PhaseTab.tsx               (80)
    - KnockoutAdvancementsTab.tsx (190)
    - ScoringOverviewTab.tsx     (60)
    - ScoreManagementTab.tsx     (83)
    - AllPredictionsTab.tsx      (185)
    - LeagueManagementTab.tsx    (161)
```

Each tab owns its own useState/useEffect and API calls. The parent
passes a `notify: (kind, message) => void` callback so tab-local actions
surface success/error to the shared Alert banners, plus a
`standingsReloadKey: number` that bumps after every `notify` so the
Standings tab auto-refreshes after e.g. a group-result save.

Bundle size: AdminPage chunk is 28.68 kB (gzip 6.02 kB), essentially
unchanged from before. Split is for maintainability, not bundle size.

### Frontend - dead code removed

- `frontend/src/pages/PredictionsPage.tsx` - deleted (was 218 lines, was
  only reachable via `/predictions` which `App.tsx:48` redirects to
  `/matches`).
- `frontend/src/pages/KnockoutPage.tsx` - deleted (was 843 lines, was
  only reachable via `/knockout` which `App.tsx:49` redirects to
  `/matches`). Was the largest single dead file.

Neither file had any consumer (grep confirmed `export default function
X` only, no imports). Saving 1061 lines of dead code.

### Backend / Infra - DB persistence fix

**Problem**: `docker-compose.prod.yml` binds `./data:/data` but never
told anyone to create `./data` on the host. If missing, Docker
auto-creates the directory owned by root, and the non-root appuser
(uid 1000) inside the container can't write -> SQLite "unable to open
database file".

Additionally, `backend/start.sh` was hardcoding `mkdir -p /app/data`,
which is the wrong path for production - the prod compose uses
`/data` not `/app/data`.

**Fix**:
1. `backend/start.sh` now derives the data dir from `$DATABASE_URL`
   via a small `ensure_data_dir` helper. Works for all three layouts:
   - `sqlite:///./vmtips.db` (local dev) -> dir `.`
   - `sqlite:////app/data/vmtips.db` (Dockerfile default) -> dir `/app/data`
   - `sqlite:////data/vmtips.db` (prod compose) -> dir `/data`
2. `scripts/dev.sh` does `mkdir -p "$PROJECT_ROOT/data"` before
   `docker compose up`. Idempotent.
3. `docker-compose.prod.yml` has a comment explaining the requirement.
4. `.gitignore` has `/data/` added (host bind-mount dir, never tracked).

### Housekeeping

- Deleted `backend/.venv2/` (stale duplicate venv, 125 MB).
- Deleted `vmtips.db` (200 KB local dev DB, untracked).

## How to resume

- Local dev: `cd backend && .venv/bin/python -m pytest tests/ -q` (174 pass).
- Frontend: `cd frontend && npm run lint && npm run build` (clean).
- Prod deploy: `./scripts/dev.sh up` (or `docker compose -f
  docker-compose.prod.yml up -d` after `mkdir -p ./data`).

## Open follow-ups from the review (not addressed yet)

**Medium**:
- B-1: `_build_actual_advancements` duplicated in `admin.py` and
  `leaderboard.py` with different return types - extract to one helper.
- F-3: `AdminPage` was already partially fixed by the split; remaining
  react-query migration is per-tab and can happen incrementally.
- F-4: FE copy of `calculateMatchPoints` should have a "keep in sync
  with backend/scoring.py" comment + a small test.

**Low** (16 backend + 9 frontend items) - listed in the review report.
None are blocking.

## Pitfalls hit during the work (saved for future sessions)

1. **Python f-string `{{` gotcha**: When building large TS files via
   `execute_code` f-strings, every `{{` in a Python f-string becomes
   literal `{` in the output. The first pass of all 9 admin tab files
   came out with `import {{
   useState }}` and `import type {{
   Match }}` - both invalid TS. Fix: write the imports as a plain
   string constant and concatenate, or escape with `{{{{` (ugly).
2. **Skill rule that paid off**: "For files over ~200 lines, always
   read the entire file first, make all edits in a single Python
   script via `execute_code` that rewrites the file in one pass, or
   use `write_file` if the file is small enough. Never chain more than
   2-3 `patch` calls on the same large file." The split was done in
   one Python script via `execute_code` - would have been 50+ patch
   calls otherwise.
3. **`.gitignore` `!` exclusion does not work for files inside an
   ignored directory** (`!` patterns don't override directory
   matches). Tried to track `data/.gitkeep` so the host bind-mount
   dir would be present after a fresh clone; git refused. Reverted
   to "document the mkdir in start.sh and dev.sh" - works fine,
   the folder is created on first run anyway.
