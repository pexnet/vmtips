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

export function usePersonalScore(enabled = true) {
  return useQuery<PersonalScore>({
    queryKey: ["leaderboard", "me"],
    queryFn: async () => {
      const res = await leaderboardApi.me();
      return res.data as PersonalScore;
    },
    enabled,
  });
}

export function useLeagueLeaderboard(leagueId: number | null) {
  return useQuery<{ leaderboard: LeaderboardEntry[]; league_name: string }>({
    queryKey: ["leaderboard", "league", leagueId],
    queryFn: async () => {
      if (!leagueId) return { leaderboard: [], league_name: "" };
      const res = await leaderboardApi.league(leagueId);
      return res.data as { leaderboard: LeaderboardEntry[]; league_name: string };
    },
    enabled: !!leagueId,
  });
}
