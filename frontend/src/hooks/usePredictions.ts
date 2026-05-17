import { useQuery } from "@tanstack/react-query";
import { predictionsApi, matchesApi } from "../api/client";
import type { Prediction, TournamentBonus, Team, Match } from "../types/api";

export function usePredictions(leagueId?: number) {
  return useQuery<Prediction[]>({
    queryKey: ["predictions", leagueId],
    queryFn: async () => {
      const res = await predictionsApi.list(leagueId);
      return res.data as Prediction[];
    },
  });
}

export function useTournamentBonuses(leagueId?: number) {
  return useQuery<TournamentBonus>({
    queryKey: ["predictions", "tournament", leagueId],
    queryFn: async () => {
      const res = await predictionsApi.tournament(leagueId);
      return res.data as TournamentBonus;
    },
  });
}

/** Extract unique teams from the matches list (used for winner autocomplete). */
export function useTeamsFromMatches() {
  return useQuery<Team[]>({
    queryKey: ["matches", "teams"],
    queryFn: async () => {
      const res = await matchesApi.list();
      const matches = res.data as Match[];
      const teamMap = new Map<number, Team>();
      matches.forEach((m: Match) => {
        if (m.home_team) teamMap.set(m.home_team.id, m.home_team);
        if (m.away_team) teamMap.set(m.away_team.id, m.away_team);
      });
      return Array.from(teamMap.values()).sort((a, b) => a.name.localeCompare(b.name));
    },
  });
}
