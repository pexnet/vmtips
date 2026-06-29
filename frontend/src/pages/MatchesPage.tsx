import { useState, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
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
import PredictionStatusBanner from "../components/PredictionStatusBanner";
import { computePredictedStandings } from "../utils/standings";

import type { Match, Team } from "../types/api";
import type { StandingTeam } from "../utils/standings";

/** Shape returned by the predictions list endpoint (includes nested match info). */
interface PredictionWithMatch {
  match_id: number;
  home_goals: number;
  away_goals: number;
  knockout_winner_side: "home" | "away" | null;
  knockout_resolution: "extra_time" | "penalties" | null;
  match: {
    match_number: number;
    round: string;
    group?: string;
    home_team: { name: string; flag_emoji: string | null };
    away_team: { name: string; flag_emoji: string | null };
  };
}

// ── MatchCard ─────────────────────────────────────────────

// IMPORTANT: This function MUST stay in sync with
// backend/scoring.py:calculate_match_points. The backend is the source
// of truth and is exercised by tests/test_scoring.py; this copy exists
// so the UI can show predicted/earned points instantly without a
// roundtrip. If the rules change (e.g. +1 for correct goal difference),
// update both files in the same commit.
function calculateMatchPoints(
  predHome: string,
  predAway: string,
  actualHome: number | null,
  actualAway: number | null,
  knockoutWinnerSide?: "home" | "away" | null,
) {
  if (predHome === "" || predAway === "" || actualHome === null || actualAway === null) {
    return null;
  }

  const predictedHome = Number(predHome);
  const predictedAway = Number(predAway);
  let predictedOutcome = Math.sign(predictedHome - predictedAway);
  // In knockout, a draw prediction with a winner side uses the winner as the outcome
  if (predictedOutcome === 0 && knockoutWinnerSide) {
    predictedOutcome = knockoutWinnerSide === "home" ? 1 : -1;
  }
  const actualOutcome = Math.sign(actualHome - actualAway);

  let points = 0;
  if (predictedOutcome === actualOutcome) points += 3;
  if (predictedHome === actualHome) points += 2;
  if (predictedAway === actualAway) points += 2;

  return points;
}

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
  const points = isFinished
    ? calculateMatchPoints(pred.home, pred.away, match.home_goals, match.away_goals)
    : null;

  const kickoff = new Date(match.match_date).toLocaleString(i18n.language, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

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
          {isLocked && !isFinished ? (
            <Chip size="small" label={t("matches.locked")} color="error" />
          ) : null}
        </Box>
      </Box>

      {/* Header row: predicted | actual | points */}
      <Box sx={{ display: "flex", alignItems: "center" }}>
        <Box sx={{ flex: 1 }} />
        <Box sx={{ display: "grid", gridTemplateColumns: "56px 56px", gap: 1, width: 120, flexShrink: 0 }}>
          <Typography variant="caption" color="text.secondary" sx={{ textAlign: "center" }}>
            {t("matches.predicted")}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ textAlign: "center" }}>
            {t("matches.result")}
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
          <Box sx={{ display: "grid", gridTemplateColumns: "56px 56px", gap: 1, width: 120, flexShrink: 0 }}>
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
                <Typography variant="body2" sx={{ fontWeight: 700 }}>
                  {match.home_goals}
                </Typography>
              ) : (
                <Typography variant="body2" color="text.secondary">-</Typography>
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
          <Box sx={{ display: "grid", gridTemplateColumns: "56px 56px", gap: 1, width: 120, flexShrink: 0 }}>
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
                <Typography variant="body2" sx={{ fontWeight: 700 }}>
                  {match.away_goals}
                </Typography>
              ) : (
                <Typography variant="body2" color="text.secondary">-</Typography>
              )}
            </Box>
          </Box>
        </Box>
      )}

      {points !== null && (
        <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
          <Chip
            size="small"
            label={t("matches.points_earned", { points })}
            color={points > 0 ? "primary" : "default"}
            variant="outlined"
            sx={{ minWidth: 48 }}
          />
        </Box>
      )}

      {isLocked && (
        <Typography variant="caption" color="text.secondary" align="center">
          {t("matches.no_prediction")}
        </Typography>
      )}
    </Paper>
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

function QualificationStandings({
  group,
  teams,
}: {
  group: string;
  teams: StandingTeam[];
}) {
  const { t } = useTranslation();

  return (
    <Paper
      elevation={0}
      sx={{
        p: 1.5,
        mt: 1.5,
        bgcolor: "background.default",
        border: 1,
        borderColor: "divider",
      }}
    >
      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 700, textTransform: "uppercase" }}>
        {group} · {t("matches.predicted_standings")}
      </Typography>
      <Table size="small" sx={{ tableLayout: "fixed" }}>
        <TableHead>
          <TableRow>
            <TableCell sx={{ width: 36 }}>#</TableCell>
            <TableCell>{t("matches.team")}</TableCell>
            <TableCell align="right" sx={{ width: 38 }}>{t("matches.played_short")}</TableCell>
            <TableCell align="right" sx={{ width: 44 }}>{t("matches.goal_diff_short")}</TableCell>
            <TableCell align="right" sx={{ width: 44 }}>{t("matches.points_short")}</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {teams.map((team, index) => {
            const direct = index < 2;
            return (
              <TableRow
                key={team.team_id}
                sx={{
                  "& td": {
                    py: 0.5,
                    bgcolor: "background.paper",
                    borderBottomColor: "divider",
                  },
                  "& td:first-of-type": {
                    borderLeft: 3,
                    borderLeftColor: direct
                      ? "primary.main"
                      : "transparent",
                    bgcolor: direct
                      ? "rgba(25, 118, 210, 0.08)"
                      : "background.paper",
                  },
                }}
              >
                <TableCell>{index + 1}</TableCell>
                <TableCell sx={{ minWidth: 0 }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, minWidth: 0 }}>
                    <Typography component="span" sx={{ flexShrink: 0 }}>{team.flag_emoji ?? ""}</Typography>
                    <Typography variant="body2" noWrap>{team.name}</Typography>
                  </Box>
                </TableCell>
                <TableCell align="right">{team.played}</TableCell>
                <TableCell align="right">{team.gd}</TableCell>
                <TableCell align="right" sx={{ fontWeight: 700 }}>{team.points}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </Paper>
  );
}

// ── Main page ─────────────────────────────────────────────

export default function MatchesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { selectedLeagueId } = useLeague();
  const [tab, setTab] = useState(0);
  const [error, setError] = useState("");
  const [saveMsg, setSaveMsg] = useState("");
  const [predictions, setPredictions] = useState(
    {} as Record<number, { home: string; away: string }>
  );
  const [dirtyMatchIds, setDirtyMatchIds] = useState<Set<number>>(() => new Set());

  // Phase gating
  const { data: phaseData } = usePhase();
  const groupLocked = !isGroupOpen(phaseData);

  // Tournament bonuses state
  const [bonuses, setBonuses] = useState({
    winner_team_id: null as number | null,
    runner_up_team_id: null as number | null,
    bronze_winner_team_id: null as number | null,
    top_scorer_name: "",
  });

  const { data: matches = [], isLoading: matchesLoading } = useMatches();
  const { data: rawPredictions = [], isLoading: predictionsLoading } = usePredictions(selectedLeagueId ?? undefined);
  const predictionsList = rawPredictions as unknown as PredictionWithMatch[];
  const { data: teams = [] } = useTeamsFromMatches();
  const { data: bonusesData } = useTournamentBonuses(selectedLeagueId ?? undefined);

  useEffect(() => {
    setPredictions({});
    setDirtyMatchIds(new Set());
  }, [selectedLeagueId]);

  // Populate bonuses form when tournament bonuses are loaded
  useEffect(() => {
    if (bonusesData) {
      const b = bonusesData as unknown as Record<string, unknown>;
      setBonuses((prev) => ({
        ...prev,
        winner_team_id: (b.winner_team_id as number) || null,
        runner_up_team_id: (b.runner_up_team_id as number) || null,
        bronze_winner_team_id: (b.bronze_winner_team_id as number) || null,
        top_scorer_name: (b.top_scorer_name as string) || "",
      }));
    }
  }, [bonusesData]);

  // Pre-fill predictions from saved ones
  useEffect(() => {
    const filled: Record<number, { home: string; away: string }> = {};
    predictionsList.forEach((p) => {
      filled[p.match_id] = {
        home: String(p.home_goals),
        away: String(p.away_goals),
      };
    });
    setPredictions((prev) => ({ ...filled, ...prev }));
  }, [predictionsList]);

  const handleChange = (id: number, side: "home" | "away", val: string) => {
    setPredictions((prev) => ({
      ...prev,
      [id]: { ...prev[id], [side]: val },
    }));
    setDirtyMatchIds((prev) => new Set(prev).add(id));
  };

  const handleSave = () => {
    const now = new Date();
    const editableGroupMatchIds = new Set(
      matches
        .filter((match) => (
          match.round === "group" &&
          match.status !== "finished" &&
          new Date(match.match_date) > now
        ))
        .map((match) => match.id),
    );
    const batch = Object.entries(predictions)
      .filter(([id, v]) => (
        dirtyMatchIds.has(Number(id)) &&
        editableGroupMatchIds.has(Number(id)) &&
        v.home !== "" &&
        v.away !== ""
      ))
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
        setDirtyMatchIds((prev) => {
          const next = new Set(prev);
          batch.forEach((prediction) => next.delete(prediction.match_id));
          return next;
        });
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
        winner_team_id: bonuses.winner_team_id || undefined,
        runner_up_team_id: bonuses.runner_up_team_id || undefined,
        bronze_winner_team_id: bonuses.bronze_winner_team_id || undefined,
        top_scorer_name: bonuses.top_scorer_name || undefined,
      })
      .then(() => {
        void queryClient.invalidateQueries({ queryKey: ["predictions", "tournament", selectedLeagueId] });
        setSaveMsg(t("predictions.save_success"));
      })
      .catch(() => setError(t("common.error")));
  };

  const selectedWinnerTeam = teams.find((tm: Team) => tm.id === bonuses.winner_team_id) || null;
  const selectedRunnerUpTeam = teams.find((tm: Team) => tm.id === bonuses.runner_up_team_id) || null;
  const selectedThirdPlaceTeam = teams.find((tm: Team) => tm.id === bonuses.bronze_winner_team_id) || null;

  const groupMatches = matches.filter((m) => m.round === "group");
  const groups = [...new Set(groupMatches.map((m) => m.group).filter((group): group is string => Boolean(group)))].sort();
  const predictedStandings = useMemo(
    () => computePredictedStandings(matches, predictions),
    [matches, predictions],
  );

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
      <PredictionStatusBanner leagueId={selectedLeagueId} />

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
              <Paper
                key={group}
                elevation={0}
                sx={{
                  p: { xs: 1.25, sm: 1.75 },
                  mb: 3,
                  border: 1,
                  borderColor: "divider",
                  borderLeft: 4,
                  borderLeftColor: "text.disabled",
                  bgcolor: "background.paper",
                }}
              >
                <Typography
                  variant="subtitle1"
                  sx={{ mb: 1.5, fontWeight: 800, textTransform: "uppercase", letterSpacing: 0.4 }}
                >
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
                <QualificationStandings
                  group={group}
                  teams={predictedStandings[group] ?? []}
                />
              </Paper>
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
            <Autocomplete
              options={teams}
              getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
              value={selectedWinnerTeam}
              onChange={(_, v) => setBonuses((b) => ({ ...b, winner_team_id: v?.id || null }))}
              disabled={groupLocked}
              renderInput={(params) => (
                <TextField {...params} label={`${t("predictions.winner")} (20p)`} />
              )}
            />

            <Autocomplete
              options={teams}
              getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
              value={selectedRunnerUpTeam}
              onChange={(_, v) => setBonuses((b) => ({ ...b, runner_up_team_id: v?.id || null }))}
              disabled={groupLocked}
              renderInput={(params) => (
                <TextField {...params} label={`${t("predictions.runner_up")} (20p)`} />
              )}
            />

            <Autocomplete
              options={teams}
              getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
              value={selectedThirdPlaceTeam}
              onChange={(_, v) => setBonuses((b) => ({ ...b, bronze_winner_team_id: v?.id || null }))}
              disabled={groupLocked}
              renderInput={(params) => (
                <TextField {...params} label={`${t("predictions.third_place")} (20p)`} />
              )}
            />

            <TextField
              label={`${t("predictions.top_scorer")} (20p)`}
              value={bonuses.top_scorer_name}
              onChange={(e) => setBonuses((b) => ({ ...b, top_scorer_name: e.target.value }))}
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
            disabled={groupLocked || dirtyMatchIds.size === 0}
          >
            {t("matches.save_predictions")}
          </Button>
        </Box>
      )}
    </Container>
  );
}
