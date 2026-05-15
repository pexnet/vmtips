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
  login: (data: { email: string; password: string }) =>
    api.post("/auth/login", data),
  me: () => api.get("/auth/me"),
};

// Matches
export const matchesApi = {
  list: () => api.get("/matches"),
  groups: () => api.get("/matches/groups"),
  knockout: () => api.get("/matches/knockout"),
  detail: (id: number) => api.get(`/matches/${id}`),
};

// Predictions
export const predictionsApi = {
  list: () => api.get("/predictions"),
  batch: (predictions: Array<{ match_id: number; home_goals: number; away_goals: number }>) =>
    api.post("/predictions/batch", { predictions }),
  tournament: () => api.get("/predictions/tournament"),
  saveTournament: (data: {
    winner_team_id?: number;
    top_scorer_name?: string;
    top_assist_name?: string;
    total_goals?: number;
  }) => api.post("/predictions/tournament", data),
  bracket: () => api.get("/predictions/bracket"),
  saveBracket: (entries: Array<{ team_id: number; round: string }>) =>
    api.post("/predictions/bracket", { entries }),
};

// Leagues
export const leaguesApi = {
  list: () => api.get("/leagues"),
  create: (name: string) => api.post("/leagues", { name }),
  detail: (id: number) => api.get(`/leagues/${id}`),
  join: (id: number, invite_code: string) =>
    api.post(`/leagues/${id}/join`, { invite_code }),
};

// Leaderboard
export const leaderboardApi = {
  global: () => api.get("/leaderboard/global"),
  me: () => api.get("/leaderboard/me"),
  league: (id: number) => api.get(`/leaderboard/league/${id}`),
};

// Admin
export const adminApi = {
  setResult: (id: number, data: { home_goals: number; away_goals: number }) =>
    api.post(`/admin/matches/${id}/result`, data),
  sync: () => api.post("/admin/sync-results"),
  recalc: () => api.post("/admin/scores/recalculate"),
};

export default api;