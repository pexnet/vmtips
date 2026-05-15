import { useQuery, useQueryClient } from "@tanstack/react-query";
import { leaguesApi } from "../api/client";
import type { League, LeagueDetail, UserLeaguesResponse } from "../types/api";

export function useLeagues() {
  return useQuery<League[]>({
    queryKey: ["leagues"],
    queryFn: async () => {
      const res = await leaguesApi.list();
      const data = res.data as UserLeaguesResponse;
      return data.leagues || [];
    },
  });
}

export function useLeagueDetail(id: number | null) {
  return useQuery<LeagueDetail>({
    queryKey: ["leagues", id],
    queryFn: async () => {
      if (!id) throw new Error("League ID is required");
      const res = await leaguesApi.detail(id);
      return res.data as LeagueDetail;
    },
    enabled: !!id,
  });
}

/** Invalidate leagues cache so a refetch is triggered after mutations (create/join). */
export function useInvalidateLeagues() {
  const queryClient = useQueryClient();
  return () =>
    queryClient.invalidateQueries({ queryKey: ["leagues"] });
}