import { useMatches } from "./useMatches";
import { usePredictions, useTournamentBonuses } from "./usePredictions";
import { isGroupOpen, isKnockoutOpen, usePhase } from "./usePhase";

function hasText(value: string | null | undefined) {
  return Boolean(value?.trim());
}

export function usePredictionStatus(leagueId: number | null) {
  const { data: matches = [] } = useMatches();
  const { data: predictions = [] } = usePredictions(leagueId ?? undefined);
  const { data: tournamentBonuses } = useTournamentBonuses(leagueId ?? undefined);
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

  const bonusTotal = round === "group" ? 4 : 0;
  const bonusSaved = bonusTotal === 0 ? 0 : [
    tournamentBonuses?.winner_team_id,
    tournamentBonuses?.runner_up_team_id,
    tournamentBonuses?.bronze_winner_team_id,
    hasText(tournamentBonuses?.top_scorer_name) ? 1 : null,
  ].filter(Boolean).length;

  return {
    saved: savedIds.size,
    total: relevantMatches.length,
    missing: Math.max(0, relevantMatches.length - savedIds.size),
    bonusSaved,
    bonusTotal,
    bonusMissing: Math.max(0, bonusTotal - bonusSaved),
    round,
  };
}
