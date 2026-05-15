import { useQuery } from "@tanstack/react-query";
import { matchesApi } from "../api/client";
import type { Match } from "../types/api";

export function useMatches() {
  return useQuery<Match[]>({
    queryKey: ["matches"],
    queryFn: async () => {
      const res = await matchesApi.list();
      return res.data as Match[];
    },
  });
}

export function useMatchGroups() {
  return useQuery<Match[]>({
    queryKey: ["matches", "groups"],
    queryFn: async () => {
      const res = await matchesApi.groups();
      return res.data as Match[];
    },
  });
}

export function useMatchKnockout() {
  return useQuery<Match[]>({
    queryKey: ["matches", "knockout"],
    queryFn: async () => {
      const res = await matchesApi.knockout();
      return res.data as Match[];
    },
  });
}

export function useMatchDetail(id: number) {
  return useQuery<Match>({
    queryKey: ["matches", id],
    queryFn: async () => {
      const res = await matchesApi.detail(id);
      return res.data as Match;
    },
    enabled: !!id,
  });
}