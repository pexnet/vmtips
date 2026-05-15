// Shared TypeScript interfaces for all VMTips API responses.
// Shapes mirror the Pydantic schemas in backend/schemas.py and
// the computed responses from backend/routers/leaderboard.py.

// ── Auth ────────────────────────────────────────────────────

export interface User {
  id: number;
  email: string;
  display_name: string | null;
  is_admin?: boolean;
}

export interface Token {
  access_token: string;
  token_type: string;
}

// ── Teams ────────────────────────────────────────────────────

export interface Team {
  id: number;
  name: string;
  code: string;
  group: string;
  flag_emoji: string | null;
}

// ── Matches ──────────────────────────────────────────────────

export interface Match {
  id: number;
  match_number: number;
  group: string | null;
  round: string;
  home_team: Team | null;
  away_team: Team | null;
  home_team_placeholder: string | null;
  away_team_placeholder: string | null;
  home_goals: number | null;
  away_goals: number | null;
  match_date: string;
  status: string;
}

// ── Predictions ──────────────────────────────────────────────

export interface Prediction {
  id: number;
  match_id: number;
  home_goals: number;
  away_goals: number;
  created_at: string;
  updated_at: string;
}

export interface TournamentBonus {
  winner_team_id: number | null;
  top_scorer_name: string | null;
  top_assist_name: string | null;
  total_goals: number | null;
}

// ── Leagues ──────────────────────────────────────────────────

export interface LeagueMember {
  id: number;
  display_name: string | null;
}

export interface League {
  id: number;
  name: string;
  invite_code: string;
  created_at: string | null;
  admin_user_id: number;
  is_admin?: boolean;
}

export interface LeagueDetail extends League {
  is_admin: boolean;
  members: LeagueMember[];
}

// ── Leaderboard ──────────────────────────────────────────────

export interface LeaderboardEntry {
  user_id: number;
  display_name: string;
  total_points: number;
  predictions_made: number;
  perfect_predictions: number;
  rank: number;
}

export interface ScoreBreakdown {
  match_id: number;
  match_number: number;
  round: string;
  home_team: string;
  away_team: string;
  predicted: string;
  actual: string;
  points: number;
  perfect: boolean;
}

export interface PersonalScore {
  user_id: number;
  display_name: string;
  total_points: number;
  predictions_made: number;
  matches_scored: number;
  perfect_predictions: number;
  breakdown: ScoreBreakdown[];
}

// ── API response wrappers ────────────────────────────────────

export interface GlobalLeaderboardResponse {
  leaderboard: LeaderboardEntry[];
}

export interface LeagueLeaderboardResponse {
  leaderboard: LeaderboardEntry[];
  league_name: string;
}

export interface UserLeaguesResponse {
  leagues: League[];
}

// ── Helper: extract error detail from axios errors ───────────

export function getErrorDetail(err: unknown): string {
  if (err instanceof Error) {
    const axiosErr = err as { response?: { data?: { detail?: string } } };
    return axiosErr.response?.data?.detail || err.message;
  }
  return String(err);
}