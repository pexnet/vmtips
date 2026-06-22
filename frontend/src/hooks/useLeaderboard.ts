import { useQuery } from "@tanstack/react-query";
import { leaderboardApi } from "../api/client";
import type { LeaderboardEntry, PersonalScore, GlobalLeaderboardResponse, MatchdaysResponse } from "../types/api";

export function useGlobalLeaderboard(leagueId?: number | null) {
  return useQuery<LeaderboardEntry[]>({
    queryKey: ["leaderboard", "global", leagueId],
    queryFn: async () => {
      const res = await leaderboardApi.global(leagueId ?? undefined);
      const data = res.data as GlobalLeaderboardResponse;
      return data.leaderboard;
    },
  });
}

export function usePersonalScore(enabled = true, leagueId?: number | null) {
  return useQuery<PersonalScore>({
    queryKey: ["leaderboard", "me", leagueId],
    queryFn: async () => {
      const res = await leaderboardApi.me(leagueId ?? undefined);
      return res.data as PersonalScore;
    },
    enabled,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
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
    staleTime: 60_000, // 1 min — scores change only when matches finish
    refetchOnWindowFocus: false,
  });
}

export function useMatchdays(leagueId?: number | null, matchdays: number = 5, enabled = true) {
  return useQuery<MatchdaysResponse>({
    queryKey: ["leaderboard", "matchdays", leagueId, matchdays],
    queryFn: async () => {
      const res = await leaderboardApi.matchdays(leagueId ?? undefined, matchdays);
      return res.data as MatchdaysResponse;
    },
    enabled,
    staleTime: 60_000, // 1 min
    refetchOnWindowFocus: false,
  });
}
