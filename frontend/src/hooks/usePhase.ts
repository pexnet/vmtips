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
    refetchInterval: (query) => {
      const phase = query.state.data;
      const now = Date.now();
      const boundaries = [
        phase?.group_deadline,
        phase?.knockout_opens_at,
        phase?.knockout_deadline,
      ]
        .filter((value): value is string => Boolean(value))
        .map((value) => new Date(value).getTime())
        .filter((value) => Number.isFinite(value) && value > now);
      if (boundaries.length === 0) return 30_000;
      return Math.max(250, Math.min(30_000, Math.min(...boundaries) - now + 50));
    },
  });
}

/** Convenience: is the group stage open for predictions? */
export function isGroupOpen(phase: PhaseInfo | undefined): boolean {
  if (phase?.phase !== "group_open") return false;
  if (!phase.group_deadline) return true;
  const deadline = new Date(phase.group_deadline);
  return !Number.isNaN(deadline.getTime()) && deadline > new Date();
}

/** Convenience: is the knockout stage open for predictions? */
export function isKnockoutOpen(phase: PhaseInfo | undefined): boolean {
  if (!phase) return false;
  const now = new Date();
  if (phase.knockout_deadline) {
    const deadline = new Date(phase.knockout_deadline);
    if (Number.isNaN(deadline.getTime()) || deadline <= now) return false;
  }
  if (phase.phase === "knockout_open") return true;
  if (phase.phase !== "group_closed" || !phase.knockout_opens_at) return false;
  const opensAt = new Date(phase.knockout_opens_at);
  return !Number.isNaN(opensAt.getTime()) && opensAt <= now;
}

/** Convenience: is the group stage closed (no more group predictions)? */
export function isGroupClosed(phase: PhaseInfo | undefined): boolean {
  return !isGroupOpen(phase);
}

/** Convenience: is the tournament fully closed? */
export function isTournamentClosed(phase: PhaseInfo | undefined): boolean {
  return phase?.phase === "knockout_closed";
}
