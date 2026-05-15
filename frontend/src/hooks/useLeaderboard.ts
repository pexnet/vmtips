import { useQuery } from "@tanstack/react-query";
import { leaderboardApi } from "../api/client";
import type { LeaderboardEntry, PersonalScore, GlobalLeaderboardResponse } from "../types/api";

export function useGlobalLeaderboard() {
  return useQuery<LeaderboardEntry[]>({
    queryKey: ["leaderboard", "global"],
    queryFn: async () => {
      const res = await leaderboardApi.global();
      const data = res.data as GlobalLeaderboardResponse;
      return data.leaderboard;
    },
  });
}

export function usePersonalScore() {
  return useQuery<PersonalScore>({
    queryKey: ["leaderboard", "me"],
    queryFn: async () => {
      const res = await leaderboardApi.me();
      return res.data as PersonalScore;
    },
  });
}

export function useLeagueLeaderboard(leagueId: number | null) {
  return useQuery<LeaderboardEntry[]>({
    queryKey: ["leaderboard", "league", leagueId],
    queryFn: async () => {
      if (!leagueId) return [];
      const res = await leaderboardApi.league(leagueId);
      const data = res.data as { leaderboard: LeaderboardEntry[] };
      return data.leaderboard;
    },
    enabled: !!leagueId,
  });
}