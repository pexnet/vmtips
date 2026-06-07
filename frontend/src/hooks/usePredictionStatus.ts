import { useMatches } from "./useMatches";
import { usePredictions } from "./usePredictions";
import { isGroupOpen, isKnockoutOpen, usePhase } from "./usePhase";

export function usePredictionStatus(leagueId: number | null) {
  const { data: matches = [] } = useMatches();
  const { data: predictions = [] } = usePredictions(leagueId ?? undefined);
  const { data: phase } = usePhase();

  const round = isGroupOpen(phase)
    ? "group"
    : isKnockoutOpen(phase)
      ? "knockout"
      : "closed";
  const relevantMatches = round === "group"
    ? matches.filter((match) => match.round === "group")
    : round === "knockout"
      ? matches.filter((match) => match.round !== "group")
      : [];
  const relevantIds = new Set(relevantMatches.map((match) => match.id));
  const savedIds = new Set(
    predictions
      .map((prediction) => prediction.match_id)
      .filter((matchId) => relevantIds.has(matchId)),
  );

  return {
    saved: savedIds.size,
    total: relevantMatches.length,
    missing: Math.max(0, relevantMatches.length - savedIds.size),
    round,
  };
}
