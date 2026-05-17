import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { predictionsApi, matchesApi } from "../api/client";
import type { BracketPredictionEntry, Match, Team } from "../types/api";

/** Fetch the current user's bracket predictions (per league). */
export function useBracketPredictions(leagueId?: number) {
  return useQuery<BracketPredictionEntry[]>({
    queryKey: ["predictions", "bracket", leagueId],
    queryFn: async () => {
      const res = await predictionsApi.bracket(leagueId);
      return res.data as BracketPredictionEntry[];
    },
  });
}

/** Mutation to save bracket predictions (per league). */
export function useSaveBracketPredictions(leagueId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (entries: Array<{ team_id: number; round: string }>) => {
      const res = await predictionsApi.saveBracket(leagueId, entries);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["predictions", "bracket", leagueId] });
    },
  });
}

/** Fetch knockout matches. */
export function useKnockoutMatches() {
  return useQuery<Match[]>({
    queryKey: ["matches", "knockout"],
    queryFn: async () => {
      const res = await matchesApi.knockout();
      return res.data as Match[];
    },
  });
}

/** Extract unique teams from knockout matches. */
export function useKnockoutTeams() {
  return useQuery<Team[]>({
    queryKey: ["matches", "knockout", "teams"],
    queryFn: async () => {
      const res = await matchesApi.knockout();
      const matches = res.data as Match[];
      const teamMap = new Map<number, Team>();
      matches.forEach((m: Match) => {
        if (m.home_team && m.home_team.id !== 0) teamMap.set(m.home_team.id, m.home_team);
        if (m.away_team && m.away_team.id !== 0) teamMap.set(m.away_team.id, m.away_team);
      });
      return Array.from(teamMap.values()).sort((a, b) => a.name.localeCompare(b.name));
    },
  });
}

/** Bracket round key constants matching the backend. */
export const BRACKET_ROUNDS = [
  "round_of_32",
  "round_of_16",
  "quarter_final",
  "semi_final",
  "match_for_third_place",
  "final",
  "world_champion",
] as const;

export type BracketRound = (typeof BRACKET_ROUNDS)[number];

/** Points per round (must match backend/scoring.py BRACKET_ROUND_POINTS). */
export const BRACKET_ROUND_POINTS: Record<BracketRound, number> = {
  round_of_32: 1,
  round_of_16: 2,
  quarter_final: 4,
  semi_final: 6,
  final: 8,
  match_for_third_place: 8,
  world_champion: 20,
};
