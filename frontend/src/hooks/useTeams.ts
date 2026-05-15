import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Team } from "../types/api";

export function useTeams() {
  return useQuery<Team[]>({
    queryKey: ["teams"],
    queryFn: async () => {
      const res = await api.get("/teams");
      return res.data as Team[];
    },
  });
}
