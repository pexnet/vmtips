import { useState, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  Container,
  Typography,
  Tabs,
  Tab,
  Box,
  Paper,
  TextField,
  Button,
  Chip,
  Alert,
  CircularProgress,
  Autocomplete,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
} from "@mui/material";
import { predictionsApi } from "../api/client";
import { useMatches } from "../hooks/useMatches";
import { usePredictions, useTournamentBonuses, useTeamsFromMatches } from "../hooks/usePredictions";
import { usePhase, isGroupOpen } from "../hooks/usePhase";
import { useLeague } from "../contexts/LeagueContext";
import BracketViewTab from "../components/BracketViewTab";

import type { Match, Team } from "../types/api";

/** Shape returned by the predictions list endpoint (includes nested match info). */
interface PredictionWithMatch {
  match_id: number;
  home_goals: number;
  away_goals: number;
  match: {
    match_number: number;
    round: string;
    group?: string;
    home_team: { name: string; flag_emoji: string | null };
    away_team: { name: string; flag_emoji: string | null };
  };
}

/** Compute points for a single match (same logic as backend scoring). */
function calcMatchPoints(
  predHome: number,
  predAway: number,
  actualHome: number,
  actualAway: number
): { points: number; outcome: boolean; homeCorrect: boolean; awayCorrect: boolean; perfect: boolean } {
  const predOutcome = predHome > predAway ? "home" : predHome < predAway ? "away" : "draw";
  const actualOutcome = actualHome > actualAway ? "home" : actualHome < actualAway ? "away" : "draw";
  const outcomeCorrect = predOutcome === actualOutcome;
  const homeCorrect = predHome === actualHome;
  const awayCorrect = predAway === actualAway;
  const perfect = outcomeCorrect && homeCorrect && awayCorrect;
  let points = 0;
  if (outcomeCorrect) points += 3;
  if (homeCorrect) points += 2;
  if (awayCorrect) points += 2;
  return { points, outcome: outcomeCorrect, homeCorrect, awayCorrect, perfect };
}

// ── MatchCard ─────────────────────────────────────────────

function MatchCard({
  match,
  predictions,
  onChange,
  disabled,
}: {
  match: Match;
  predictions: Record<number, { home: string; away: string }>;
  onChange: (id: number, side: "home" | "away", val: string) => void;
  disabled?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const home = match.home_team;
  const away = match.away_team;
  const pred = predictions[match.id] || { home: "", away: "" };
  const isFinished = match.status === "finished";
  const isLocked = new Date(match.match_date) <= new Date();
  const isDisabled = disabled || isFinished || isLocked;

  const kickoff = new Date(match.match_date).toLocaleString(i18n.language, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  // Points if result is known
  const pointsData = useMemo(() => {
    if (isFinished && match.home_goals !== null && match.away_goals !== null && pred.home !== "" && pred.away !== "") {
      return calcMatchPoints(Number(pred.home), Number(pred.away), match.home_goals, match.away_goals);
    }
    return null;
  }, [isFinished, match.home_goals, match.away_goals, pred.home, pred.away]);

  return (
    <Paper
      elevation={1}
      sx={{
        p: 1.5,
        display: "flex",
        flexDirection: "column",
        gap: 1,
        minHeight: 120,
      }}
    >
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Typography variant="caption" color="text.secondary">
          {match.group || match.round.toUpperCase()} · {kickoff}
        </Typography>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          {isFinished ? (
            <Chip size="small" label={t("matches.result")} color="success" />
          ) : isLocked ? (
            <Chip size="small" label={t("matches.locked")} color="error" />
          ) : null}
        </Box>
      </Box>

      {/* Header row: predicted | actual | points */}
      <Box sx={{ display: "flex", alignItems: "center" }}>
        <Box sx={{ flex: 1 }} />
        <Box sx={{ display: "grid", gridTemplateColumns: "56px 56px 56px", gap: 1, width: 184, flexShrink: 0 }}>
          <Typography variant="caption" color="text.secondary" sx={{ textAlign: "center" }}>
            {t("matches.predicted")}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ textAlign: "center" }}>
            {t("matches.result")}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ textAlign: "center" }}>
            {t("matches.points")}
          </Typography>
        </Box>
      </Box>

      {/* Home team row */}
      {home && (
        <Box sx={{ display: "flex", alignItems: "center" }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, flex: 1, minWidth: 0 }}>
            <Typography variant="body2" sx={{ fontSize: "1.1rem", flexShrink: 0 }}>{home.flag_emoji ?? ""}</Typography>
            <Typography variant="body2" sx={{ fontWeight: 500 }} noWrap>{home.name}</Typography>
          </Box>
          <Box sx={{ display: "grid", gridTemplateColumns: "56px 56px 56px", gap: 1, width: 184, flexShrink: 0 }}>
            <TextField
              size="small"
              type="text"
              placeholder="-"
              value={pred.home}
              onChange={(e) => {
                const val = e.target.value;
                if (val === "" || (/^\d*$/.test(val) && Number(val) <= 15)) {
                  onChange(match.id, "home", val);
                }
              }}
              disabled={isDisabled}
              sx={{ width: 56, textAlign: "center", '& input': { textAlign: 'center' }, '& input::-webkit-outer-spin-button, & input::-webkit-inner-spin-button': { WebkitAppearance: 'none' } }}
            />
            <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center" }}>
              {isFinished && match.home_goals !== null ? (
                <Typography variant="body2" sx={{ fontWeight: 700, color: pointsData?.homeCorrect ? "success.main" : "text.primary" }}>
                  {match.home_goals}
                </Typography>
              ) : (
                <Typography variant="body2" color="text.secondary">-</Typography>
              )}
            </Box>
            <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center" }}>
              {pointsData && (
                <Chip
                  size="small"
                  color={pointsData.homeCorrect ? "success" : "default"}
                  label={pointsData.homeCorrect ? "+2" : "0"}
                  sx={{ height: 20, fontSize: "0.7rem", width: 56, justifyContent: "center" }}
                />
              )}
            </Box>
          </Box>
        </Box>
      )}

      {/* Away team row */}
      {away && (
        <Box sx={{ display: "flex", alignItems: "center" }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, flex: 1, minWidth: 0 }}>
            <Typography variant="body2" sx={{ fontSize: "1.1rem", flexShrink: 0 }}>{away.flag_emoji ?? ""}</Typography>
            <Typography variant="body2" sx={{ fontWeight: 500 }} noWrap>{away.name}</Typography>
          </Box>
          <Box sx={{ display: "grid", gridTemplateColumns: "56px 56px 56px", gap: 1, width: 184, flexShrink: 0 }}>
            <TextField
              size="small"
              type="text"
              placeholder="-"
              value={pred.away}
              onChange={(e) => {
                const val = e.target.value;
                if (val === "" || (/^\d*$/.test(val) && Number(val) <= 15)) {
                  onChange(match.id, "away", val);
                }
              }}
              disabled={isDisabled}
              sx={{ width: 56, textAlign: "center", '& input': { textAlign: 'center' }, '& input::-webkit-outer-spin-button, & input::-webkit-inner-spin-button': { WebkitAppearance: 'none' } }}
            />
            <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center" }}>
              {isFinished && match.away_goals !== null ? (
                <Typography variant="body2" sx={{ fontWeight: 700, color: pointsData?.awayCorrect ? "success.main" : "text.primary" }}>
                  {match.away_goals}
                </Typography>
              ) : (
                <Typography variant="body2" color="text.secondary">-</Typography>
              )}
            </Box>
            <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center" }}>
              {pointsData && (
                <Chip
                  size="small"
                  color={pointsData.awayCorrect ? "success" : "default"}
                  label={pointsData.awayCorrect ? "+2" : "0"}
                  sx={{ height: 20, fontSize: "0.7rem", width: 56, justifyContent: "center" }}
                />
              )}
            </Box>
          </Box>
        </Box>
      )}

      {/* Total points row */}
      {pointsData && (
        <Box sx={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 1, mt: 0.5 }}>
          <Typography variant="caption" color="text.secondary">
            {pointsData.perfect
              ? t("matches.perfect")
              : `${pointsData.outcome ? "✓ " + t("matches.outcome") : ""}${pointsData.homeCorrect ? " ✓ " + t("matches.home_goals") : ""}${pointsData.awayCorrect ? " ✓ " + t("matches.away_goals") : ""}`}
          </Typography>
          <Chip
            size="small"
            color={pointsData.perfect ? "success" : pointsData.points > 0 ? "primary" : "default"}
            label={`${pointsData.points}p`}
            sx={{ height: 20, fontSize: "0.7rem", width: 56, justifyContent: "center" }}
          />
        </Box>
      )}
      {isLocked && !pointsData && (
        <Typography variant="caption" color="text.secondary" align="center">
          {t("matches.no_prediction")}
        </Typography>
      )}
    </Paper>
  );
}

// ── GroupStandingsTable ─────────────────────────────────────

interface StandingRow {
  team_id: number;
  name: string;
  flag_emoji: string | null;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goals_for: number;
  goals_against: number;
  points: number;
}

/** Initialise a standings map with every team in the group set to 0. */
function initTeamMap(groupMatches: Match[]): Map<number, StandingRow> {
  const map = new Map<number, StandingRow>();
  for (const m of groupMatches) {
    for (const tm of [m.home_team, m.away_team]) {
      if (!tm || map.has(tm.id)) continue;
      map.set(tm.id, {
        team_id: tm.id,
        name: tm.name,
        flag_emoji: tm.flag_emoji,
        played: 0, won: 0, drawn: 0, lost: 0,
        goals_for: 0, goals_against: 0, points: 0,
      });
    }
  }
  return map;
}

function buildPredictedStandings(
  groupMatches: Match[],
  predictions: Record<number, { home: string; away: string }>
): StandingRow[] {
  const map = initTeamMap(groupMatches);

  for (const m of groupMatches) {
    const home = m.home_team;
    const away = m.away_team;
    if (!home || !away) continue;

    let hg: number | null = null;
    let ag: number | null = null;
    if (m.status === "finished" && m.home_goals !== null && m.away_goals !== null) {
      hg = m.home_goals;
      ag = m.away_goals;
    } else {
      const pred = predictions[m.id];
      if (pred && pred.home !== "" && pred.away !== "") {
        hg = Number(pred.home);
        ag = Number(pred.away);
      }
    }
    if (hg === null || ag === null) continue;

    const h = map.get(home.id)!;
    const a = map.get(away.id)!;
    h.played += 1;
    a.played += 1;
    h.goals_for += hg;
    h.goals_against += ag;
    a.goals_for += ag;
    a.goals_against += hg;

    if (hg > ag) {
      h.won += 1; h.points += 3;
      a.lost += 1;
    } else if (hg === ag) {
      h.drawn += 1; h.points += 1;
      a.drawn += 1; a.points += 1;
    } else {
      h.lost += 1;
      a.won += 1; a.points += 3;
    }
  }

  return Array.from(map.values()).sort(
    (a, b) => b.points - a.points || (b.goals_for - b.goals_against) - (a.goals_for - a.goals_against) || b.goals_for - a.goals_for
  );
}

function buildActualStandings(groupMatches: Match[]): StandingRow[] {
  const map = initTeamMap(groupMatches);

  for (const m of groupMatches) {
    if (m.status !== "finished" || m.home_goals === null || m.away_goals === null) continue;
    const home = m.home_team;
    const away = m.away_team;
    if (!home || !away) continue;

    const hg = m.home_goals;
    const ag = m.away_goals;

    const h = map.get(home.id)!;
    const a = map.get(away.id)!;
    h.played += 1;
    a.played += 1;
    h.goals_for += hg;
    h.goals_against += ag;
    a.goals_for += ag;
    a.goals_against += hg;

    if (hg > ag) {
      h.won += 1; h.points += 3;
      a.lost += 1;
    } else if (hg === ag) {
      h.drawn += 1; h.points += 1;
      a.drawn += 1; a.points += 1;
    } else {
      h.lost += 1;
      a.won += 1; a.points += 3;
    }
  }

  return Array.from(map.values()).sort(
    (a, b) => b.points - a.points || (b.goals_for - b.goals_against) - (a.goals_for - a.goals_against) || b.goals_for - a.goals_for
  );
}

function GroupStandingsTables({ matches, predictions }: { matches: Match[]; predictions: Record<number, { home: string; away: string }> }) {
  const { t } = useTranslation();
  const predicted = useMemo(() => buildPredictedStandings(matches, predictions), [matches, predictions]);
  const actual = useMemo(() => buildActualStandings(matches), [matches]);

  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5, mt: 1.5, mb: 1.5 }}>
      {/* Predicted */}
      <Paper
        elevation={0}
        sx={{
          flex: 1,
          minWidth: 280,
          overflow: "hidden",
          border: (theme) => `1px solid ${theme.palette.divider}`,
        }}
      >
        <Box sx={{ px: 1.5, py: 0.75, bgcolor: "action.hover" }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, fontSize: "0.8rem" }}>
            {t("matches.predicted_standings")}
          </Typography>
        </Box>
        <Table size="small" sx={{ '& td, & th': { px: 1, py: 0.5, fontSize: '0.75rem' } }}>
          <TableHead>
            <TableRow>
              <TableCell sx={{ width: 28 }}>#</TableCell>
              <TableCell>{t("matches.team")}</TableCell>
              <TableCell align="center" sx={{ width: 32 }}>{t("matches.played_short")}</TableCell>
              <TableCell align="center" sx={{ width: 32 }}>{t("matches.goal_diff_short")}</TableCell>
              <TableCell align="center" sx={{ width: 36, fontWeight: 700 }}>{t("matches.points_short")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {predicted.map((s, idx) => (
              <TableRow key={s.team_id} hover>
                <TableCell sx={{ fontWeight: 700, color: idx < 2 ? "success.main" : "text.secondary" }}>{idx + 1}</TableCell>
                <TableCell>{s.flag_emoji} {s.name}</TableCell>
                <TableCell align="center">{s.played}</TableCell>
                <TableCell align="center">{s.goals_for - s.goals_against}</TableCell>
                <TableCell align="center" sx={{ fontWeight: 700 }}>{s.points}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>

      {/* Actual */}
      <Paper
        elevation={0}
        sx={{
          flex: 1,
          minWidth: 280,
          overflow: "hidden",
          border: (theme) => `1px solid ${theme.palette.divider}`,
        }}
      >
        <Box sx={{ px: 1.5, py: 0.75, bgcolor: "action.hover" }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, fontSize: "0.8rem" }}>
            {t("matches.actual_standings")}
          </Typography>
        </Box>
        <Table size="small" sx={{ '& td, & th': { px: 1, py: 0.5, fontSize: '0.75rem' } }}>
          <TableHead>
            <TableRow>
              <TableCell sx={{ width: 28 }}>#</TableCell>
              <TableCell>{t("matches.team")}</TableCell>
              <TableCell align="center" sx={{ width: 32 }}>{t("matches.played_short")}</TableCell>
              <TableCell align="center" sx={{ width: 32 }}>{t("matches.goal_diff_short")}</TableCell>
              <TableCell align="center" sx={{ width: 36, fontWeight: 700 }}>{t("matches.points_short")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {actual.map((s, idx) => (
              <TableRow key={s.team_id} hover>
                <TableCell sx={{ fontWeight: 700, color: idx < 2 ? "success.main" : "text.secondary" }}>{idx + 1}</TableCell>
                <TableCell>{s.flag_emoji} {s.name}</TableCell>
                <TableCell align="center">{s.played}</TableCell>
                <TableCell align="center">{s.goals_for - s.goals_against}</TableCell>
                <TableCell align="center" sx={{ fontWeight: 700 }}>{s.points}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </Box>
  );
}

// Flexbox wrapper: 2 per row on sm+
function TwoColumnGrid({ children }: { children: React.ReactNode }) {
  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5 }}>
      {Array.isArray(children)
        ? children.map((child, i) => (
            <Box
              key={i}
              sx={{
                flex: "1 1 calc(50% - 6px)",
                minWidth: 280,
              }}
            >
              {child}
            </Box>
          ))
        : children}
    </Box>
  );
}

// ── Main page ─────────────────────────────────────────────

export default function MatchesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { selectedLeagueId } = useLeague();
  const [tab, setTab] = useState(0);
  const [error, setError] = useState("");
  const [saveMsg, setSaveMsg] = useState("");
  const [predictions, setPredictions] = useState(
    {} as Record<number, { home: string; away: string }>
  );

  // Phase gating
  const { data: phaseData } = usePhase();
  const groupLocked = !isGroupOpen(phaseData);

  // Tournament bonuses state
  const [bonuses, setBonuses] = useState({
    top_scorer_name: "",
    most_goals_team_id: null as number | null,
    most_conceded_team_id: null as number | null,
    custom_bonus_1: "",
    custom_bonus_2: "",
  });

  const { data: matches = [], isLoading: matchesLoading } = useMatches();
  const { data: rawPredictions = [], isLoading: predictionsLoading } = usePredictions(selectedLeagueId ?? undefined);
  const predictionsList = rawPredictions as unknown as PredictionWithMatch[];
  const { data: teams = [] } = useTeamsFromMatches();
  const { data: bonusesData } = useTournamentBonuses(selectedLeagueId ?? undefined);

  // Populate bonuses form when tournament bonuses are loaded
  useEffect(() => {
    if (bonusesData) {
      const b = bonusesData as unknown as Record<string, unknown>;
      setBonuses((prev) => ({
        ...prev,
        top_scorer_name: (b.top_scorer_name as string) || "",
        most_goals_team_id: (b.most_goals_team_id as number) || null,
        most_conceded_team_id: (b.most_conceded_team_id as number) || null,
        custom_bonus_1: (b.custom_bonus_1 as string) || "",
        custom_bonus_2: (b.custom_bonus_2 as string) || "",
      }));
    }
  }, [bonusesData]);

  // Pre-fill predictions from saved ones
  useEffect(() => {
    if (predictionsList.length > 0) {
      const filled: Record<number, { home: string; away: string }> = {};
      predictionsList.forEach((p) => {
        filled[p.match_id] = {
          home: String(p.home_goals),
          away: String(p.away_goals),
        };
      });
      setPredictions((prev) => ({ ...prev, ...filled }));
    }
  }, [predictionsList]);

  const handleChange = (id: number, side: "home" | "away", val: string) => {
    setPredictions((prev) => ({
      ...prev,
      [id]: { ...prev[id], [side]: val },
    }));
  };

  const handleSave = () => {
    const batch = Object.entries(predictions)
      .filter(([, v]) => v.home !== "" && v.away !== "")
      .map(([id, v]) => ({
        match_id: Number(id),
        home_goals: Number(v.home),
        away_goals: Number(v.away),
      }));

    if (batch.length === 0) {
      setError(t("predictions.no_predictions"));
      return;
    }

    if (!selectedLeagueId) {
      setError(t("predictions.no_league_selected"));
      return;
    }

    setError("");
    setSaveMsg("");

    predictionsApi
      .batch(selectedLeagueId, batch)
      .then(() => {
        setSaveMsg(t("predictions.save_success"));
      })
      .catch((err: unknown) => {
        const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } };
        if (axiosErr.response?.status === 401) navigate("/login");
        else setError(axiosErr.response?.data?.detail || t("common.error"));
      });
  };

  const saveBonuses = () => {
    setSaveMsg("");
    setError("");
    if (!selectedLeagueId) {
      setError(t("predictions.no_league_selected"));
      return;
    }
    predictionsApi
      .saveTournament(selectedLeagueId, {
        top_scorer_name: bonuses.top_scorer_name || undefined,
        most_goals_team_id: bonuses.most_goals_team_id || undefined,
        most_conceded_team_id: bonuses.most_conceded_team_id || undefined,
        custom_bonus_1: bonuses.custom_bonus_1 || undefined,
        custom_bonus_2: bonuses.custom_bonus_2 || undefined,
      })
      .then(() => setSaveMsg(t("predictions.save_success")))
      .catch(() => setError(t("common.error")));
  };

  const selectedMostGoals = teams.find((tm: Team) => tm.id === bonuses.most_goals_team_id) || null;
  const selectedMostConceded = teams.find((tm: Team) => tm.id === bonuses.most_conceded_team_id) || null;

  const groupMatches = matches.filter((m) => m.round === "group");
  const groups = [...new Set(groupMatches.map((m) => m.group).filter(Boolean))].sort();

  const isLoading = matchesLoading || predictionsLoading;

  const tabs = [
    t("matches.group_stage"),
    t("matches.knockout"),
    t("predictions.tournament_bonuses"),
  ];

  // Reset tab if out of bounds
  useEffect(() => {
    if (tab >= tabs.length) setTab(Math.max(0, tabs.length - 1));
  }, [tabs.length, tab]);

  if (isLoading) {
    return (
      <Container sx={{ mt: 8, textAlign: "center" }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 2, mb: 8, maxWidth: "lg" }}>
      <Typography variant="h4" gutterBottom>
        {t("matches.title")}
      </Typography>

      {/* Phase info banner */}
      {phaseData && (
        <Alert
          severity={groupLocked ? "info" : "success"}
          sx={{ mb: 2 }}
        >
          {t(`phase.${phaseData.phase}`)}
          {phaseData.group_deadline && ` — ${t("phase.group_deadline")}: ${new Date(phaseData.group_deadline).toLocaleString()}`}
          {phaseData.knockout_deadline && ` — ${t("phase.knockout_deadline")}: ${new Date(phaseData.knockout_deadline).toLocaleString()}`}
        </Alert>
      )}

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {saveMsg && <Alert severity="success" sx={{ mb: 2 }}>{saveMsg}</Alert>}

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        {tabs.map((label, idx) => (
          <Tab key={idx} label={label} />
        ))}
      </Tabs>

      {/* GROUP STAGE TAB */}
      {tab === 0 && (
        <Box>
          {groups.map((group) => {
            const grpMatches = groupMatches.filter((m) => m.group === group);
            return (
              <Box key={group} sx={{ mb: 3 }}>
                <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>
                  {group}
                </Typography>
                <TwoColumnGrid>
                  {grpMatches.map((m) => (
                    <MatchCard
                      key={m.id}
                      match={m}
                      predictions={predictions}
                      onChange={handleChange}
                      disabled={groupLocked}
                    />
                  ))}
                </TwoColumnGrid>
                <GroupStandingsTables matches={grpMatches} predictions={predictions} />
              </Box>
            );
          })}
        </Box>
      )}

      {/* KNOCKOUT / SLUTSPEL TAB — BracketViewTab with predicted vs actual + score input */}
      {tab === 1 && (
        <BracketViewTab />
      )}

      {/* TOURNAMENT BONUSES TAB */}
      {tab === 2 && (
        <Paper elevation={2} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>{t("predictions.tournament_bonuses")}</Typography>

          {groupLocked && (
            <Alert severity="info" sx={{ mb: 2 }}>{t("phase.group_closed_msg")}</Alert>
          )}

          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <TextField
              label={`${t("predictions.top_scorer")} (20p)`}
              value={bonuses.top_scorer_name}
              onChange={(e) => setBonuses((b) => ({ ...b, top_scorer_name: e.target.value }))}
              disabled={groupLocked}
              fullWidth
            />

            <Autocomplete
              options={teams}
              getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
              value={selectedMostGoals}
              onChange={(_, v) => setBonuses((b) => ({ ...b, most_goals_team_id: v?.id || null }))}
              disabled={groupLocked}
              renderInput={(params) => (
                <TextField {...params} label={`${t("predictions.most_goals_team")} (10p)`} />
              )}
            />

            <Autocomplete
              options={teams}
              getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
              value={selectedMostConceded}
              onChange={(_, v) => setBonuses((b) => ({ ...b, most_conceded_team_id: v?.id || null }))}
              disabled={groupLocked}
              renderInput={(params) => (
                <TextField {...params} label={`${t("predictions.most_conceded_team")} (10p)`} />
              )}
            />

            <TextField
              label={`${t("predictions.custom_bonus_1")} (10p)`}
              value={bonuses.custom_bonus_1}
              onChange={(e) => setBonuses((b) => ({ ...b, custom_bonus_1: e.target.value }))}
              disabled={groupLocked}
              fullWidth
            />

            <TextField
              label={`${t("predictions.custom_bonus_2")} (10p)`}
              value={bonuses.custom_bonus_2}
              onChange={(e) => setBonuses((b) => ({ ...b, custom_bonus_2: e.target.value }))}
              disabled={groupLocked}
              fullWidth
            />

            <Button variant="contained" onClick={saveBonuses} disabled={groupLocked}>
              {t("common.save")}
            </Button>
          </Box>
        </Paper>
      )}

      {/* Save button — visible on group stage tab only */}
      {tab === 0 && (
        <Box sx={{ position: "sticky", bottom: 16, textAlign: "center", bgcolor: "background.default", p: 1 }}>
          <Button
            variant="contained"
            size="large"
            onClick={() => {
              const token = localStorage.getItem("token");
              if (!token) {
                navigate("/login");
                return;
              }
              handleSave();
            }}
            disabled={Object.keys(predictions).length === 0}
          >
            {t("matches.save_predictions")}
          </Button>
        </Box>
      )}
    </Container>
  );
}