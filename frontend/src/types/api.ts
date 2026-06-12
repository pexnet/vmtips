// Shared TypeScript interfaces for all VMTips API responses.
// Shapes mirror the Pydantic schemas in backend/schemas.py and
// the computed responses from backend/routers/leaderboard.py.

// ── Auth ────────────────────────────────────────────────────

export interface User {
  id: number;
  email: string;
  display_name: string | null;
  first_name: string | null;
  last_name: string | null;
  avatar_url: string | null;
  is_admin?: boolean;
  is_active?: boolean;
  last_login_at?: string | null;
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
  knockout_winner_side: "home" | "away" | null;
  knockout_resolution: "extra_time" | "penalties" | null;
  created_at: string;
  updated_at: string;
}

export interface TournamentBonus {
  winner_team_id: number | null;
  runner_up_team_id: number | null;
  top_scorer_name: string | null;
  bronze_winner_team_id: number | null;
  most_goals_team_id: number | null;
  most_conceded_team_id: number | null;
  custom_bonus_1: string | null;
  custom_bonus_2: string | null;
}

// ── Leagues ──────────────────────────────────────────────────

export interface LeagueMember {
  id: number;
  display_name: string | null;
  first_name: string | null;
  last_name: string | null;
  avatar_url: string | null;
}

export interface League {
  id: number;
  name: string;
  invite_code?: string;
  created_at: string | null;
  admin_user_id?: number;
  is_admin?: boolean;
  member_count?: number;
}

export interface LeagueDetail extends League {
  is_admin: boolean;
  members: LeagueMember[];
}

// ── Leaderboard ──────────────────────────────────────────────

export interface LeaderboardEntry {
  user_id: number;
  display_name: string;
  first_name: string | null;
  last_name: string | null;
  avatar_url: string | null;
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

export interface BracketDetail {
  team_id: number;
  round: string;
  points: number;
}

export interface PersonalScore {
  user_id: number;
  display_name: string;
  first_name: string | null;
  last_name: string | null;
  avatar_url: string | null;
  total_points: number;
  match_points: number;
  bracket_points: number;
  league_bonus_points: number;
  predictions_made: number;
  matches_scored: number;
  perfect_predictions: number;
  tournament_bonus_points: number;
  tournament_bonus_details?: {
    winner_correct: boolean;
    runner_up_correct: boolean;
    top_scorer_correct: boolean;
    bronze_winner_correct: boolean;
    most_goals_team_correct: boolean;
    most_conceded_team_correct: boolean;
    custom_bonus_1_correct: boolean;
    custom_bonus_2_correct: boolean;
  };
  bracket_details: BracketDetail[];
  breakdown: ScoreBreakdown[];
}

// ── API response wrappers ────────────────────────────────────

export interface GlobalLeaderboardResponse {
  leaderboard: LeaderboardEntry[];
  league_id?: number;
  league_name?: string;
}

export interface LeagueLeaderboardResponse {
  leaderboard: LeaderboardEntry[];
  league_name: string;
}

// ── Bracket Predictions ──────────────────────────────────────

export interface BracketPredictionEntry {
  id?: number;
  team_id: number;
  round: string;
  source?: string;
}

// ── Tournament Phase ─────────────────────────────────────────

export interface PhaseInfo {
  phase: "group_open" | "group_closed" | "knockout_open" | "knockout_closed";
  group_deadline: string | null;
  knockout_opens_at: string | null;
  knockout_deadline: string | null;
  extra_questions_lock_at: string | null;
  computed_extra_questions_lock_at: string | null;
  extra_questions_lock_is_override: boolean;
}

export interface AdminUser extends User {
  is_admin: boolean;
  is_active: boolean;
  league_ids: number[];
}

// ── Group Standings ───────────────────────────────────────────

export interface GroupStanding {
  team_id: number;
  team_name: string;
  team_code: string;
  group: string;
  position: number | null;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goals_for: number;
  goals_against: number;
  goal_difference: number;
  points: number;
}

// ── Knockout Advancement ──────────────────────────────────────

export interface KnockoutAdvancement {
  id: number;
  team_id: number;
  team_name: string;
  team_code: string;
  round: string;
  match_number: number | null;
}

// ── Scoring Overview (admin) ──────────────────────────────────

export interface ScoringOverviewEntry {
  user_id: number;
  display_name: string;
  match_points: number;
  bracket_points: number;
  tournament_bonus_points: number;
  league_bonus_points: number;
  total_points: number;
}

// ── Helper: extract error detail from axios errors ───────────

export function getErrorDetail(err: unknown): string {
  if (err instanceof Error) {
    const axiosErr = err as { response?: { data?: { detail?: string; error?: string } } };
    return axiosErr.response?.data?.detail || axiosErr.response?.data?.error || err.message;
  }
  return String(err);
}

// ── Matchday Leaderboard View ─────────────────────────────────

export interface MatchdayTeam {
  id: number;
  name: string;
  code: string;
  flag_emoji: string;
}

export interface MatchdayPredictionEntry {
  user_id: number;
  display_name: string;
  first_name: string | null;
  last_name: string | null;
  avatar_url: string | null;
  predicted: string;
  knockout_winner_side?: "home" | "away";
  points?: number;
}

export interface MatchdayMatch {
  id: number;
  match_number: number;
  kickoff: string;
  status: string;
  home_team: MatchdayTeam;
  away_team: MatchdayTeam;
  actual?: string;
  predictions: MatchdayPredictionEntry[];
}

export interface MatchdayGroup {
  date: string;
  matches: MatchdayMatch[];
}

export interface MatchdaysResponse {
  league_id: number | null;
  league_name: string | null;
  matchdays_back: number;
  now: string;
  upcoming: MatchdayGroup | null;
  past: MatchdayGroup[];
}
