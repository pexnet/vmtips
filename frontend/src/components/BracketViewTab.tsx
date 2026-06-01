import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Paper,
  Typography,
  Chip,
  Alert,
  CircularProgress,
  Divider,
  TextField,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import Grid from "@mui/material/Grid";
import { useBracketView } from "../hooks/useBracketView";
import { BRACKET_ROUND_POINTS } from "../hooks/useBracket";
import { useLeague } from "../contexts/LeagueContext";
import { predictionsApi } from "../api/client";
import { usePhase, isKnockoutOpen, isGroupClosed, isTournamentClosed } from "../hooks/usePhase";

function roundLabel(t: (k: string) => string, round: string) {
  const map: Record<string, string> = {
    round_of_32: "matches.round_of_32",
    round_of_16: "matches.round_of_16",
    quarter_final: "matches.quarter_final",
    semi_final: "matches.semi_final",
    match_for_third_place: "matches.match_for_third_place",
    final: "matches.final",
  };
  return t(map[round] || round);
}

interface PredictionPointData {
  points: number;
  outcome: boolean;
  homeCorrect: boolean;
  awayCorrect: boolean;
  perfect: boolean;
}

type KnockoutMatchPrediction = {
  home: string;
  away: string;
  knockout_winner_side?: "home" | "away";
  knockout_resolution?: "extra_time" | "penalties";
};

function calcMatchPoints(
  predHome: number,
  predAway: number,
  actualHome: number,
  actualAway: number
): PredictionPointData {
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

function calcBracketCardPoints(
  round: string,
  predictedTeamIds: Array<number | null>,
  actualTeamIds: Array<number | null>,
): number {
  const roundPoints = BRACKET_ROUND_POINTS[round as keyof typeof BRACKET_ROUND_POINTS] ?? 0;
  if (roundPoints === 0) return 0;

  const actualSet = new Set(actualTeamIds.filter((teamId): teamId is number => teamId !== null));
  return predictedTeamIds.reduce<number>((total, teamId) => {
    if (teamId === null || !actualSet.has(teamId)) return total;
    return total + roundPoints;
  }, 0);
}

function hasResolvedActualTeams(actualTeamIds: Array<number | null>): boolean {
  return actualTeamIds.some((teamId) => teamId !== null);
}

function predictedWinnerSide(prediction: KnockoutMatchPrediction): "home" | "away" | null {
  if (prediction.home === "" || prediction.away === "") return null;

  const homeGoals = Number(prediction.home);
  const awayGoals = Number(prediction.away);
  if (homeGoals > awayGoals) return "home";
  if (homeGoals < awayGoals) return "away";
  return prediction.knockout_winner_side ?? null;
}

/** Check if a specific knockout match is locked based on phase + kickoff + status. */
function isMatchLocked(
  matchDate: string | null,
  status: string,
  phase: string | undefined,
  matchRound: string
): boolean {
  // Finished matches are always locked
  if (status === "finished") return true;

  // If the tournament is fully closed, everything is locked
  if (phase === "knockout_closed") return true;

  // If match has already kicked off, it's locked
  if (matchDate) {
    const kickoff = new Date(matchDate);
    if (!isNaN(kickoff.getTime()) && kickoff <= new Date()) return true;
  }

  // If we're still in group_open, early knockout rounds are locked
  // (Users can only predict knockouts after group stage closes or during knockout_open)
  if (phase === "group_open" && matchRound !== "group") return true;

  return false;
}

export default function BracketViewTab() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { selectedLeagueId } = useLeague();
  const { data, isLoading, error } = useBracketView(selectedLeagueId ?? undefined);
  const { data: phaseData } = usePhase();
  const [errorMsg, setErrorMsg] = useState("");
  const [saveMsg, setSaveMsg] = useState("");
  const [matchPredictions, setMatchPredictions] = useState(
    {} as Record<number, KnockoutMatchPrediction>
  );

  // Pre-fill from existing predictions whenever data loads
  useEffect(() => {
    if (data?.knockout_matches) {
      const prefill: Record<number, KnockoutMatchPrediction> = {};
      for (const m of data.knockout_matches) {
        if (m.predicted.home_goals !== null && m.predicted.away_goals !== null) {
          prefill[m.match_id] = {
            home: String(m.predicted.home_goals),
            away: String(m.predicted.away_goals),
            knockout_winner_side: m.predicted.knockout_winner_side ?? undefined,
            knockout_resolution: m.predicted.knockout_resolution ?? undefined,
          };
        }
      }
      setMatchPredictions((prev) => ({ ...prefill, ...prev }));
    }
  }, [data]);

  if (isLoading) {
    return (
      <Box sx={{ textAlign: "center", mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !data) {
    return (
      <Alert severity="info" sx={{ mt: 2 }}>
        {t("bracket.no_data")}
      </Alert>
    );
  }

  const { group_standings, third_places } = data;
  // Get knockout matches in order
  const knockout_matches = data.knockout_matches;

  const handleChange = (id: number, side: "home" | "away", val: string) => {
    setMatchPredictions((prev) => ({
      ...prev,
      [id]: { ...prev[id], [side]: val },
    }));
  };

  const handleKnockoutMetaChange = (
    id: number,
    field: "knockout_winner_side" | "knockout_resolution",
    val: "home" | "away" | "extra_time" | "penalties",
  ) => {
    setMatchPredictions((prev) => ({
      ...prev,
      [id]: { ...prev[id], [field]: val },
    }));
  };

  const handleSave = () => {
    const batch = Object.entries(matchPredictions)
      .filter(([, v]) => v.home !== "" && v.away !== "")
      .map(([id, v]) => ({
        match_id: Number(id),
        home_goals: Number(v.home),
        away_goals: Number(v.away),
        knockout_winner_side: v.home === v.away ? v.knockout_winner_side : undefined,
        knockout_resolution: v.home === v.away ? v.knockout_resolution : undefined,
      }));

    if (batch.length === 0) return;
    if (!selectedLeagueId) {
      setErrorMsg(t("predictions.no_league_selected"));
      return;
    }
    if (batch.some((pred) => pred.home_goals === pred.away_goals && (!pred.knockout_winner_side || !pred.knockout_resolution))) {
      setErrorMsg(t("knockout.winner_required"));
      return;
    }

    predictionsApi
      .batch(selectedLeagueId, batch)
      .then(() => {
        setSaveMsg(t("predictions.save_success"));
        setErrorMsg("");
      })
      .catch((err: unknown) => {
        const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } };
        if (axiosErr.response?.status === 401) navigate("/login");
        else setErrorMsg(axiosErr.response?.data?.detail || t("common.error"));
      });
  };

  // Group matches by round
  const roundOrder = ["round_of_32", "round_of_16", "quarter_final", "semi_final", "match_for_third_place", "final"];
  const matchesByRound = roundOrder
    .map((round) => ({
      round,
      matches: knockout_matches.filter((m) => m.round === round),
    }))
    .filter((r) => r.matches.length > 0);

  const groupClosed = isGroupClosed(phaseData);
  const tournamentClosed = isTournamentClosed(phaseData);
  const knockoutEditable = groupClosed && !tournamentClosed;
  const knockoutOpen = isKnockoutOpen(phaseData);

  return (
    <Box>
      {errorMsg && <Alert severity="error" sx={{ mb: 2 }}>{errorMsg}</Alert>}
      {saveMsg && <Alert severity="success" sx={{ mb: 2 }}>{saveMsg}</Alert>}

      {/* Phase gating info */}
      {phaseData && (
        <Alert
          severity={tournamentClosed ? "error" : knockoutOpen ? "success" : "info"}
          sx={{ mb: 2 }}
        >
          {t(`phase.${phaseData.phase}`)}
          {tournamentClosed
            ? ` — ${t("phase.knockout_closed_msg")}`
            : !groupClosed
            ? ` — ${t("phase.group_closed_msg")}`
            : ""}
        </Alert>
      )}

      {/* ── Predicted Group Standings ── */}
      {Object.keys(group_standings).length > 0 && (
        <>
          <Typography variant="h6" gutterBottom>
            {t("bracket.predicted_standings")}
          </Typography>

          <Grid container spacing={2} sx={{ mb: 3 }}>
            {Object.entries(group_standings).sort(([a], [b]) => a.localeCompare(b)).map(([group, teams]) => (
              <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={group}>
                <Paper elevation={1} sx={{ p: 1.5 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                    {t("matches.group")} {group}
                  </Typography>
                  <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
                    {teams.map((tm, idx) => (
                      <Box
                        key={tm.team_id}
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 1,
                        }}
                      >
                        <Typography
                          variant="body2"
                          sx={{
                            fontWeight: 700,
                            width: 20,
                            color: idx < 2
                              ? "success.main"
                              : idx === 2
                                ? third_places.some((tp) => tp.team_id === tm.team_id && tp.qualified)
                                  ? "warning.main"
                                  : "text.disabled"
                                : "text.secondary",
                          }}
                        >
                          {idx + 1}
                        </Typography>
                        <Typography variant="body2" sx={{ fontSize: "1.1rem" }}>{tm.flag_emoji ?? ""}</Typography>
                        <Typography variant="body2">{tm.name}</Typography>
                      </Box>
                    ))}
                  </Box>
                </Paper>
              </Grid>
            ))}
          </Grid>
        </>
      )}

      {/* ── Third Places ── */}
      {third_places.length > 0 && (
        <Paper elevation={1} sx={{ p: 2, mb: 3 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
            {t("bracket.third_places")}
          </Typography>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
            {third_places.map((tp) => (
              <Chip
                key={tp.team_id}
                label={`${tp.rank}. ${tp.flag_emoji ?? ""} ${tp.name} (${tp.group})`}
                color={tp.rank <= 8 ? "success" : "default"}
                variant={tp.rank <= 8 ? "filled" : "outlined"}
                size="small"
              />
            ))}
          </Box>
        </Paper>
      )}

      <Divider sx={{ my: 3 }}>
        <Typography variant="body2" color="text.secondary">
          {t("bracket.knockout_matches")}
        </Typography>
      </Divider>

      {/* ── Knockout Match Cards ── */}
      {matchesByRound.map(({ round, matches }) => (
        <Box key={round} sx={{ mb: 3 }}>
          <Typography
            variant="subtitle1"
            sx={{ mb: 1, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}
          >
            {roundLabel(t, round)}
          </Typography>

          <Grid container spacing={1.5}>
            {matches.map((m) => {
              const pred = m.predicted;
              const act = m.actual;
              const predFilled = pred.home_goals !== null && pred.away_goals !== null;
              const matchPred = matchPredictions[m.match_id] || { home: "", away: "" };
              const isDrawPrediction = matchPred.home !== "" && matchPred.home === matchPred.away;
              const drawMetaMissing = isDrawPrediction && (!matchPred.knockout_winner_side || !matchPred.knockout_resolution);
              const winnerSide = predictedWinnerSide(matchPred);

              const isFinished = act.status === "finished";
              const isLocked = isMatchLocked(m.match_date, act.status, phaseData?.phase, m.round);
              const isDisabled = isLocked || !knockoutEditable;

              const kickoff = m.match_date
                ? new Date(m.match_date).toLocaleString(i18n.language, {
                    weekday: "short",
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                : "";

              // Points calculation if finished and predicted
              const pointsData: PredictionPointData | null = (() => {
                if (isFinished && predFilled && act.home_goals !== null && act.away_goals !== null) {
                  return calcMatchPoints(
                    pred.home_goals ?? 0,
                    pred.away_goals ?? 0,
                    act.home_goals,
                    act.away_goals
                  );
                }
                return null;
              })();
              const bracketPoints = calcBracketCardPoints(
                m.round,
                [pred.home_team_id, pred.away_team_id],
                [act.home_team_id, act.away_team_id],
              );
              const totalCardPoints = bracketPoints + (pointsData?.points ?? 0);
              const showPointsPill = pointsData !== null || hasResolvedActualTeams([act.home_team_id, act.away_team_id]);

              // Helper to get actual team display
              const actualHomeName = act.home_team_name ?? act.home_team_placeholder ?? t("matches.round");
              const actualAwayName = act.away_team_name ?? act.away_team_placeholder ?? t("matches.round");

              return (
                <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={m.match_number}>
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
                        #{m.match_number}
                        {kickoff ? ` · ${kickoff}` : ""}
                      </Typography>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                        {isLocked && !isFinished ? (
                          <Chip size="small" label={t("matches.locked")} color="error" />
                        ) : null}
                      </Box>
                    </Box>

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

                    <Box sx={{ display: "flex", alignItems: "center" }}>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, flex: 1, minWidth: 0 }}>
                        <Typography variant="body2" sx={{ fontSize: "1.1rem", flexShrink: 0 }}>
                          {act.home_team_flag ?? "🏳️"}
                        </Typography>
                        <Typography
                          variant="body2"
                          sx={{ fontWeight: 500, lineHeight: 1.25, whiteSpace: "normal", overflowWrap: "anywhere" }}
                        >
                          {actualHomeName}
                        </Typography>
                        {winnerSide === "home" && (
                          <CheckCircleIcon color="success" sx={{ fontSize: 16, flexShrink: 0 }} />
                        )}
                      </Box>
                      <Box sx={{ display: "grid", gridTemplateColumns: "56px 56px", gap: 1, width: 120, flexShrink: 0 }}>
                        <TextField
                          size="small"
                          type="text"
                          placeholder="-"
                          value={matchPred.home}
                          error={drawMetaMissing}
                          onChange={(e) => {
                            const val = e.target.value;
                            if (val === "" || (/^\d*$/.test(val) && Number(val) <= 15)) {
                              handleChange(m.match_id, "home", val);
                            }
                          }}
                          disabled={isDisabled}
                          sx={{
                            width: 56,
                            textAlign: "center",
                            "& input": { textAlign: "center" },
                            "& input::-webkit-outer-spin-button, & input::-webkit-inner-spin-button": { WebkitAppearance: "none" },
                          }}
                        />
                        <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center" }}>
                          {isFinished && act.home_goals !== null ? (
                            <Typography variant="body2" sx={{ fontWeight: 700 }}>
                              {act.home_goals}
                            </Typography>
                          ) : (
                            <Typography variant="body2" color="text.secondary">-</Typography>
                          )}
                        </Box>
                      </Box>
                    </Box>

                    <Box sx={{ display: "flex", alignItems: "center" }}>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, flex: 1, minWidth: 0 }}>
                        <Typography variant="body2" sx={{ fontSize: "1.1rem", flexShrink: 0 }}>
                          {act.away_team_flag ?? "🏳️"}
                        </Typography>
                        <Typography
                          variant="body2"
                          sx={{ fontWeight: 500, lineHeight: 1.25, whiteSpace: "normal", overflowWrap: "anywhere" }}
                        >
                          {actualAwayName}
                        </Typography>
                        {winnerSide === "away" && (
                          <CheckCircleIcon color="success" sx={{ fontSize: 16, flexShrink: 0 }} />
                        )}
                      </Box>
                      <Box sx={{ display: "grid", gridTemplateColumns: "56px 56px", gap: 1, width: 120, flexShrink: 0 }}>
                        <TextField
                          size="small"
                          type="text"
                          placeholder="-"
                          value={matchPred.away}
                          error={drawMetaMissing}
                          onChange={(e) => {
                            const val = e.target.value;
                            if (val === "" || (/^\d*$/.test(val) && Number(val) <= 15)) {
                              handleChange(m.match_id, "away", val);
                            }
                          }}
                          disabled={isDisabled}
                          sx={{
                            width: 56,
                            textAlign: "center",
                            "& input": { textAlign: "center" },
                            "& input::-webkit-outer-spin-button, & input::-webkit-inner-spin-button": { WebkitAppearance: "none" },
                          }}
                        />
                        <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center" }}>
                          {isFinished && act.away_goals !== null ? (
                            <Typography variant="body2" sx={{ fontWeight: 700 }}>
                              {act.away_goals}
                            </Typography>
                          ) : (
                            <Typography variant="body2" color="text.secondary">-</Typography>
                          )}
                        </Box>
                      </Box>
                    </Box>

                    {isDrawPrediction && (
                      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, mt: 1 }}>
                        <FormControl size="small" error={!matchPred.knockout_winner_side} disabled={isDisabled}>
                          <InputLabel>{t("knockout.winner")}</InputLabel>
                          <Select
                            label={t("knockout.winner")}
                            value={matchPred.knockout_winner_side ?? ""}
                            onChange={(e) => handleKnockoutMetaChange(m.match_id, "knockout_winner_side", e.target.value as "home" | "away")}
                          >
                            <MenuItem value="home">{actualHomeName}</MenuItem>
                            <MenuItem value="away">{actualAwayName}</MenuItem>
                          </Select>
                        </FormControl>
                        <FormControl size="small" error={!matchPred.knockout_resolution} disabled={isDisabled}>
                          <InputLabel>{t("knockout.resolution")}</InputLabel>
                          <Select
                            label={t("knockout.resolution")}
                            value={matchPred.knockout_resolution ?? ""}
                            onChange={(e) => handleKnockoutMetaChange(m.match_id, "knockout_resolution", e.target.value as "extra_time" | "penalties")}
                          >
                            <MenuItem value="extra_time">{t("knockout.extra_time")}</MenuItem>
                            <MenuItem value="penalties">{t("knockout.penalties")}</MenuItem>
                          </Select>
                        </FormControl>
                      </Box>
                    )}

                    {showPointsPill && (
                      <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
                        <Chip
                          size="small"
                          label={t("matches.points_earned", { points: totalCardPoints })}
                          color={totalCardPoints > 0 ? "primary" : "default"}
                          variant="outlined"
                          sx={{ minWidth: 48 }}
                        />
                      </Box>
                    )}

                    {/* ── PREDICTED TEAMS (bracket_engine) shown as info ── */}
                    {(pred.home_team_id !== null || pred.away_team_id !== null) && (
                      <>
                        <Divider sx={{ my: 0.25 }}>
                          <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.65rem" }}>
                            {t("bracket.predicted")}
                          </Typography>
                        </Divider>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                          <Typography variant="body2" sx={{ fontSize: "1.1rem", flexShrink: 0 }}>
                            {pred.home_team_flag ?? ""}
                          </Typography>
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{ flex: 1, lineHeight: 1.25, whiteSpace: "normal", overflowWrap: "anywhere" }}
                          >
                            {pred.home_team_name ?? pred.home_team_placeholder ?? "?"}
                          </Typography>
                        </Box>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                          <Typography variant="body2" sx={{ fontSize: "1.1rem", flexShrink: 0 }}>
                            {pred.away_team_flag ?? ""}
                          </Typography>
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{ flex: 1, lineHeight: 1.25, whiteSpace: "normal", overflowWrap: "anywhere" }}
                          >
                            {pred.away_team_name ?? pred.away_team_placeholder ?? "?"}
                          </Typography>
                        </Box>
                      </>
                    )}

                    {isLocked && !isFinished && (
                      <Typography variant="caption" color="text.secondary" align="center">
                        {t("matches.no_prediction")}
                      </Typography>
                    )}
                  </Paper>
                </Grid>
              );
            })}
          </Grid>
        </Box>
      ))}

      {/* Save button */}
      <Box sx={{ position: "sticky", bottom: 16, textAlign: "center", bgcolor: "background.default", p: 1, zIndex: 10 }}>
        <Button
          variant="contained"
          size="large"
          onClick={handleSave}
          disabled={!knockoutEditable || Object.keys(matchPredictions).length === 0}
        >
          {t("matches.save_predictions")}
        </Button>
      </Box>
    </Box>
  );
}
