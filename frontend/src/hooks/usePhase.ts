import { useQuery } from "@tanstack/react-query";
import { phaseApi } from "../api/client";
import type { PhaseInfo } from "../types/api";

/** Fetch the current tournament phase. */
export function usePhase() {
  return useQuery<PhaseInfo>({
    queryKey: ["phase"],
    queryFn: async () => {
      const res = await phaseApi.get();
      return res.data as PhaseInfo;
    },
    staleTime: 30_000, // cache for 30s — phase rarely changes
  });
}

/** Convenience: is the group stage open for predictions? */
export function isGroupOpen(phase: PhaseInfo | undefined): boolean {
  return phase?.phase === "group_open";
}

/** Convenience: is the knockout stage open for predictions? */
export function isKnockoutOpen(phase: PhaseInfo | undefined): boolean {
  if (!phase) return false;
  if (phase.phase === "knockout_open") return true;
  if (phase.phase !== "group_closed" || !phase.knockout_opens_at) return false;
  const opensAt = new Date(phase.knockout_opens_at);
  return !Number.isNaN(opensAt.getTime()) && opensAt <= new Date();
}

/** Convenience: is the group stage closed (no more group predictions)? */
export function isGroupClosed(phase: PhaseInfo | undefined): boolean {
  return phase?.phase !== "group_open";
}

/** Convenience: is the tournament fully closed? */
export function isTournamentClosed(phase: PhaseInfo | undefined): boolean {
  return phase?.phase === "knockout_closed";
}
