import type { Match, Team } from "../types/api";

export interface StandingTeam {
  team_id: number;
  name: string;
  code: string;
  flag_emoji: string | null;
  group: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd: number;
  points: number;
}

interface PredictedScore {
  home: string;
  away: string;
}

interface MatchScore {
  homeTeamId: number;
  awayTeamId: number;
  homeGoals: number;
  awayGoals: number;
}

function cloneTeam(team: Team): StandingTeam {
  return {
    team_id: team.id,
    name: team.name,
    code: team.code,
    flag_emoji: team.flag_emoji,
    group: team.group,
    played: 0,
    won: 0,
    drawn: 0,
    lost: 0,
    gf: 0,
    ga: 0,
    gd: 0,
    points: 0,
  };
}

function h2hStats(teamIds: Set<number>, matches: MatchScore[]) {
  const stats = new Map<number, { points: number; gf: number; ga: number; gd: number }>();
  teamIds.forEach((id) => stats.set(id, { points: 0, gf: 0, ga: 0, gd: 0 }));

  matches.forEach((match) => {
    if (!teamIds.has(match.homeTeamId) || !teamIds.has(match.awayTeamId)) return;
    const home = stats.get(match.homeTeamId);
    const away = stats.get(match.awayTeamId);
    if (!home || !away) return;

    home.gf += match.homeGoals;
    home.ga += match.awayGoals;
    away.gf += match.awayGoals;
    away.ga += match.homeGoals;

    if (match.homeGoals > match.awayGoals) home.points += 3;
    else if (match.homeGoals < match.awayGoals) away.points += 3;
    else {
      home.points += 1;
      away.points += 1;
    }
    home.gd = home.gf - home.ga;
    away.gd = away.gf - away.ga;
  });

  return stats;
}

function partitionBy<T>(items: T[], value: (item: T) => number, descending = true): T[][] {
  const sorted = [...items].sort((a, b) => descending ? value(b) - value(a) : value(a) - value(b));
  const groups: T[][] = [];
  sorted.forEach((item) => {
    const last = groups[groups.length - 1];
    if (!last || value(last[0]) !== value(item)) groups.push([item]);
    else last.push(item);
  });
  return groups;
}

function appFallback(teams: StandingTeam[]) {
  return [...teams].sort((a, b) => a.team_id - b.team_id || a.name.localeCompare(b.name));
}

function rankByOverall(teams: StandingTeam[]): StandingTeam[] {
  for (const value of [(t: StandingTeam) => t.gd, (t: StandingTeam) => t.gf]) {
    const groups = partitionBy(teams, value);
    if (groups.length > 1) {
      return groups.flatMap((group) => group.length > 1 ? rankByOverall(group) : group);
    }
  }
  return appFallback(teams);
}

function rankPointsTie(teams: StandingTeam[], matches: MatchScore[]): StandingTeam[] {
  if (teams.length <= 1) return teams;

  const stats = h2hStats(new Set(teams.map((team) => team.team_id)), matches);
  for (const value of [
    (t: StandingTeam) => stats.get(t.team_id)?.points ?? 0,
    (t: StandingTeam) => stats.get(t.team_id)?.gd ?? 0,
    (t: StandingTeam) => stats.get(t.team_id)?.gf ?? 0,
  ]) {
    const groups = partitionBy(teams, value);
    if (groups.length > 1) {
      return groups.flatMap((group) => group.length > 1 ? rankPointsTie(group, matches) : group);
    }
  }

  return rankByOverall(teams);
}

export function sortGroupTeams(teams: StandingTeam[], matches: MatchScore[]) {
  const byPoints = new Map<number, StandingTeam[]>();
  teams.forEach((team) => byPoints.set(team.points, [...(byPoints.get(team.points) ?? []), team]));
  return [...byPoints.keys()]
    .sort((a, b) => b - a)
    .flatMap((points) => {
      const tied = byPoints.get(points) ?? [];
      return tied.length > 1 ? rankPointsTie(tied, matches) : tied;
    });
}

export function computePredictedStandings(
  matches: Match[],
  predictions: Record<number, PredictedScore>,
) {
  const teamsByGroup = new Map<string, Map<number, StandingTeam>>();
  const matchScoresByGroup = new Map<string, MatchScore[]>();

  matches.filter((match) => match.round === "group").forEach((match) => {
    if (!match.home_team || !match.away_team || !match.group) return;
    const groupTeams = teamsByGroup.get(match.group) ?? new Map<number, StandingTeam>();
    if (!groupTeams.has(match.home_team.id)) groupTeams.set(match.home_team.id, cloneTeam(match.home_team));
    if (!groupTeams.has(match.away_team.id)) groupTeams.set(match.away_team.id, cloneTeam(match.away_team));
    teamsByGroup.set(match.group, groupTeams);

    const score = predictions[match.id];
    if (!score || score.home === "" || score.away === "") return;

    const homeGoals = Number(score.home);
    const awayGoals = Number(score.away);
    if (!Number.isFinite(homeGoals) || !Number.isFinite(awayGoals)) return;

    const home = groupTeams.get(match.home_team.id);
    const away = groupTeams.get(match.away_team.id);
    if (!home || !away) return;

    home.played += 1;
    away.played += 1;
    home.gf += homeGoals;
    home.ga += awayGoals;
    away.gf += awayGoals;
    away.ga += homeGoals;
    home.gd = home.gf - home.ga;
    away.gd = away.gf - away.ga;

    if (homeGoals > awayGoals) {
      home.won += 1;
      away.lost += 1;
      home.points += 3;
    } else if (homeGoals < awayGoals) {
      away.won += 1;
      home.lost += 1;
      away.points += 3;
    } else {
      home.drawn += 1;
      away.drawn += 1;
      home.points += 1;
      away.points += 1;
    }

    const groupScores = matchScoresByGroup.get(match.group) ?? [];
    groupScores.push({
      homeTeamId: match.home_team.id,
      awayTeamId: match.away_team.id,
      homeGoals,
      awayGoals,
    });
    matchScoresByGroup.set(match.group, groupScores);
  });

  const standings: Record<string, StandingTeam[]> = {};
  [...teamsByGroup.keys()].sort().forEach((group) => {
    standings[group] = sortGroupTeams(
      [...(teamsByGroup.get(group)?.values() ?? [])],
      matchScoresByGroup.get(group) ?? [],
    );
  });
  return standings;
}

export function computeThirdPlaceRanking(standings: Record<string, StandingTeam[]>) {
  return Object.entries(standings)
    .flatMap(([group, teams]) => teams[2] ? [{ ...teams[2], group }] : [])
    .sort((a, b) => (
      b.points - a.points ||
      b.gd - a.gd ||
      b.gf - a.gf ||
      a.team_id - b.team_id ||
      a.name.localeCompare(b.name)
    ));
}
