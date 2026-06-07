import axios, { type InternalAxiosRequestConfig, type AxiosResponse } from "axios";

const API_URL = import.meta.env.VITE_API_URL || "/api";

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach auth token to every request
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem("token");
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 globally — dispatch event for AuthContext to handle
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: unknown) => {
    if (
      error instanceof Error &&
      "response" in error &&
      (error as { response?: { status?: number } }).response?.status === 401
    ) {
      localStorage.removeItem("token");
      window.dispatchEvent(new CustomEvent("auth:401"));
    }
    return Promise.reject(error);
  }
);

// Auth endpoints
export const authApi = {
  register: (data: { email: string; password: string; display_name?: string }) =>
    api.post("/auth/register", data),
  login: (data: { identifier: string; password: string }) =>
    api.post("/auth/login", data),
  me: () => api.get("/auth/me"),
  updateMe: (data: {
    email: string;
    first_name: string;
    last_name: string;
    display_name: string;
  }) => api.patch("/auth/me", data),
  uploadAvatar: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post("/auth/me/avatar", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  deleteAvatar: () => api.delete("/auth/me/avatar"),
};

// Matches
export const matchesApi = {
  list: () => api.get("/matches"),
  groups: () => api.get("/matches/groups"),
  knockout: () => api.get("/matches/knockout"),
  detail: (id: number) => api.get(`/matches/${id}`),
};

// Teams
export const teamsApi = {
  list: () => api.get("/teams"),
  knockoutAdvancements: () => api.get("/teams/knockout-advancements"),
};

// Predictions
export const predictionsApi = {
  list: (leagueId?: number) =>
    api.get(`/predictions${leagueId !== undefined ? `?league_id=${leagueId}` : ""}`),
  batch: (leagueId: number, predictions: Array<{
    match_id: number;
    home_goals: number;
    away_goals: number;
    knockout_winner_side?: "home" | "away";
    knockout_resolution?: "extra_time" | "penalties";
  }>) =>
    api.post("/predictions/batch", { league_id: leagueId, predictions }),
  tournament: (leagueId?: number) =>
    api.get(`/predictions/tournament${leagueId !== undefined ? `?league_id=${leagueId}` : ""}`),
  saveTournament: (leagueId: number, data: {
    winner_team_id?: number;
    runner_up_team_id?: number;
    top_scorer_name?: string;
    bronze_winner_team_id?: number;
    most_goals_team_id?: number;
    most_conceded_team_id?: number;
    custom_bonus_1?: string;
    custom_bonus_2?: string;
  }) => api.post("/predictions/tournament", { league_id: leagueId, ...data }),
  bracket: (leagueId?: number) =>
    api.get(`/predictions/bracket${leagueId !== undefined ? `?league_id=${leagueId}` : ""}`),
  saveBracket: (leagueId: number, entries: Array<{ team_id: number; round: string }>) =>
    api.post("/predictions/bracket", { league_id: leagueId, entries }),
};

// Leagues
export const leaguesApi = {
  list: () => api.get("/leagues"),
  create: (name: string) => api.post("/leagues", { name }),
  detail: (id: number) => api.get(`/leagues/${id}`),
  join: (id: number, invite_code: string) =>
    api.post(`/leagues/${id}/join`, { invite_code }),
  public: () => api.get("/leagues/public"),
  listBonusQuestions: (league_id: number) =>
    api.get(`/leagues/${league_id}/bonus-questions`),
  createBonusQuestion: (league_id: number, payload: { question_text: string; points_value: number; answer?: string; closed_at?: string }) =>
    api.post(`/leagues/${league_id}/bonus-questions`, payload),
  updateBonusQuestion: (league_id: number, question_id: number, payload: { question_text?: string; points_value?: number; answer?: string; closed_at?: string | null }) =>
    api.patch(`/leagues/${league_id}/bonus-questions/${question_id}`, payload),
  deleteBonusQuestion: (league_id: number, question_id: number) =>
    api.delete(`/leagues/${league_id}/bonus-questions/${question_id}`),
  getMyBonusAnswer: (league_id: number, question_id: number) =>
    api.get(`/leagues/${league_id}/bonus-questions/${question_id}/answer`),
  saveBonusAnswer: (league_id: number, question_id: number, answer_text: string) =>
    api.put(`/leagues/${league_id}/bonus-questions/${question_id}/answer`, { answer_text }),
};

// Leaderboard
export const leaderboardApi = {
  global: (leagueId?: number) => api.get(`/leaderboard/global${leagueId !== undefined ? `?league_id=${leagueId}` : ""}`),
  me: (leagueId?: number) => api.get(`/leaderboard/me${leagueId !== undefined ? `?league_id=${leagueId}` : ""}`),
  league: (id: number) => api.get(`/leaderboard/league/${id}`),
};

// Phase (public endpoint)
export const phaseApi = {
  get: () => api.get("/admin/phase"),
};

// Admin
export const adminApi = {
  setResult: (id: number, data: { home_goals: number; away_goals: number }) =>
    api.post(`/admin/matches/${id}/result`, data),
  sync: () => api.post("/admin/sync-results"),
  recalc: () => api.post("/admin/scores/recalculate"),
  tournamentResult: () => api.get("/admin/tournament-result"),
  setTournamentResult: (data: {
    winner_team_id?: number;
    runner_up_team_id?: number;
    top_scorer_name?: string;
    bronze_winner_team_id?: number;
    most_goals_team_id?: number;
    most_conceded_team_id?: number;
    custom_bonus_1_answer?: string;
    custom_bonus_2_answer?: string;
  }) => api.post("/admin/tournament-result", data),
  syncConfig: () => api.get("/admin/sync-config"),
  updateSyncConfig: (data: {
    source?: string;
    auto_sync_enabled?: boolean;
    auto_sync_interval_minutes?: number;
  }) => api.post("/admin/sync-config", data),
  // Phase management
  updatePhase: (data: {
    phase?: string;
    group_deadline?: string;
    knockout_opens_at?: string;
    knockout_deadline?: string;
    extra_questions_lock_at?: string;
  }) => api.post("/admin/phase", data),
  resetExtraQuestionsLock: () =>
    api.post("/admin/phase/reset-extra-questions-lock"),
  // Group standings
  computeStandings: () => api.post("/admin/compute-standings"),
  getStandings: () => api.get("/admin/group-standings"),
  // Knockout advancement
  getAdvancements: () => api.get("/admin/knockout-advancements"),
  setAdvancement: (data: { team_id: number; round: string; match_number?: number }) =>
    api.post("/admin/set-advancement", data),
  resolveKnockoutTeams: () => api.post("/admin/resolve-knockout-teams"),
  // Scoring overview
  scoringOverview: () => api.get("/admin/scoring-overview"),
  // All users' predictions
  allPredictions: () => api.get("/admin/all-predictions"),
  // League management
  listLeagues: () => api.get("/admin/leagues"),
  updateLeague: (id: number, data: { name?: string; is_public?: boolean }) => api.patch(`/admin/leagues/${id}`, data),
  deleteLeague: (id: number) => api.delete(`/admin/leagues/${id}`),
  listUsers: () => api.get("/admin/users"),
  createUser: (data: {
    email: string;
    password: string;
    display_name: string;
    first_name?: string;
    last_name?: string;
    is_admin: boolean;
    is_active: boolean;
    league_ids: number[];
  }) => api.post("/admin/users", data),
  updateUser: (id: number, data: {
    email?: string;
    password?: string;
    display_name?: string;
    first_name?: string;
    last_name?: string;
    is_admin?: boolean;
    is_active?: boolean;
    league_ids?: number[];
  }) => api.patch(`/admin/users/${id}`, data),
};

// Bracket
export const bracketApi = {
  generate: (leagueId: number) => api.post(`/bracket/generate?league_id=${leagueId}`),
  view: (leagueId: number) => api.get(`/bracket/view?league_id=${leagueId}`),
};

export default api;
