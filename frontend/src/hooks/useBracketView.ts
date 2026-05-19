import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { bracketApi } from "../api/client";

export interface BracketViewMatch {
  match_id: number;
  match_number: number;
  round: string;
  match_date: string | null;
  predicted: {
    home_team_id: number | null;
    home_team_name: string | null;
    home_team_flag: string | null;
    home_team_placeholder: string | null;
    away_team_id: number | null;
    away_team_name: string | null;
    away_team_flag: string | null;
    away_team_placeholder: string | null;
    home_goals: number | null;
    away_goals: number | null;
  };
  actual: {
    home_team_id: number | null;
    home_team_name: string | null;
    home_team_flag: string | null;
    home_team_placeholder: string | null;
    away_team_id: number | null;
    away_team_name: string | null;
    away_team_flag: string | null;
    away_team_placeholder: string | null;
    home_goals: number | null;
    away_goals: number | null;
    status: string;
  };
}

export interface BracketViewStanding {
  position: number;
  team_id: number;
  name: string;
  code: string;
  flag_emoji: string | null;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd: number;
  points: number;
}

export interface BracketViewThird {
  rank: number;
  team_id: number;
  name: string;
  code: string;
  flag_emoji: string | null;
  group: string;
  points: number;
  gd: number;
  gf: number;
}

export interface BracketViewResponse {
  group_standings: Record<string, BracketViewStanding[]>;
  third_places: BracketViewThird[];
  knockout_matches: BracketViewMatch[];
}

/** Fetch the full bracket view generated from group predictions. */
export function useBracketView(leagueId?: number) {
  return useQuery<BracketViewResponse>({
    queryKey: ["bracket", "view", leagueId],
    queryFn: async () => {
      if (!leagueId) throw new Error("No league selected");
      const res = await bracketApi.view(leagueId);
      return res.data as BracketViewResponse;
    },
    enabled: !!leagueId,
  });
}

/** Generate bracket from group predictions. */
export function useGenerateBracket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (leagueId: number) => {
      const res = await bracketApi.generate(leagueId);
      return res.data;
    },
    onSuccess: (_, leagueId) => {
      queryClient.invalidateQueries({ queryKey: ["bracket", "view", leagueId] });
      queryClient.invalidateQueries({ queryKey: ["predictions", "bracket", leagueId] });
    },
  });
}
