import { useState, useCallback, useMemo, useEffect } from "react";
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
} from "@mui/material";
import Grid from "@mui/material/Grid";
import { predictionsApi } from "../api/client";
import { useMatchKnockout } from "../hooks/useMatches";
import {
  useBracketPredictions,
  useSaveBracketPredictions,
  BRACKET_ROUNDS,
  BRACKET_ROUND_POINTS,
  type BracketRound,
} from "../hooks/useBracket";
import { useTeamsFromMatches } from "../hooks/usePredictions";
import type { Match, Team, BracketPredictionEntry } from "../types/api";

// ── Match prediction input card for knockout matches ────────

function KnockoutMatchCard({
  match,
  predictions,
  onChange,
}: {
  match: Match;
  predictions: Record<number, { home: string; away: string }>;
  onChange: (id: number, side: "home" | "away", val: string) => void;
}) {
  const { t, i18n } = useTranslation();
  const home = match.home_team;
  const away = match.away_team;
  const pred = predictions[match.id] || { home: "", away: "" };
  const isFinished = match.status === "finished";
  const isLocked = new Date(match.match_date) <= new Date();
  const disabled = isFinished || isLocked;

  const kickoff = new Date(match.match_date).toLocaleString(i18n.language, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  const roundLabel = (round: string) => {
    switch (round) {
      case "round_of_32": return t("matches.round_of_32");
      case "round_of_16": return t("matches.round_of_16");
      case "quarter_final": return t("matches.quarter_final");
      case "semi_final": return t("matches.semi_final");
      case "match_for_third_place": return t("matches.match_for_third_place");
      case "final": return t("matches.final");
      default: return round;
    }
  };

  return (
    <Paper elevation={1} sx={{ p: 1.5, display: "flex", flexDirection: "column", gap: 1, minHeight: 120 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Typography variant="caption" color="text.secondary">
          {roundLabel(match.round)} · {kickoff}
        </Typography>
        {isFinished ? (
          <Chip size="small" label={t("matches.result")} color="success" />
        ) : isLocked ? (
          <Chip size="small" label={t("matches.locked")} color="error" />
        ) : null}
      </Box>

      {home && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Typography variant="body2" sx={{ fontSize: "1.1rem" }}>{home.flag_emoji ?? ""}</Typography>
          <Typography variant="body2" sx={{ fontWeight: 500, flex: 1 }} noWrap>
            {home.name}
          </Typography>
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
            disabled={disabled}
            sx={{ width: 60, '& input::-webkit-outer-spin-button, & input::-webkit-inner-spin-button': { WebkitAppearance: 'none' } }}
          />
        </Box>
      )}

      {away && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Typography variant="body2" sx={{ fontSize: "1.1rem" }}>{away.flag_emoji ?? ""}</Typography>
          <Typography variant="body2" sx={{ fontWeight: 500, flex: 1 }} noWrap>
            {away.name}
          </Typography>
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
            disabled={disabled}
            sx={{ width: 60, '& input::-webkit-outer-spin-button, & input::-webkit-inner-spin-button': { WebkitAppearance: 'none' } }}
          />
        </Box>
      )}

      {isFinished && match.home_goals !== null && (
        <Typography variant="caption" color="text.secondary" align="center">
          {t("matches.result")}: {match.home_goals} - {match.away_goals}
        </Typography>
      )}
    </Paper>
  );
}

// ── Single bracket round column ────────────────────────────

function BracketRoundColumn({
  round,
  selectedTeamIds,
  allTeams,
  onChange,
  existingEntries,
}: {
  round: BracketRound;
  selectedTeamIds: number[];
  allTeams: Team[];
  onChange: (round: BracketRound, teamId: number | null, slotIndex: number) => void;
  existingEntries: BracketPredictionEntry[];
}) {
  const { t } = useTranslation();
  const roundLabel = t(`knockout.${round}`);
  const points = BRACKET_ROUND_POINTS[round];

  // Expected slots per round
  const slotsPerRound: Record<BracketRound, number> = {
    round_of_32: 32,
    round_of_16: 16,
    quarter_final: 8,
    semi_final: 4,
    match_for_third_place: 2,
    final: 2,
  };
  const slotCount = slotsPerRound[round];

  // Build slots: fill from existing entries then selected IDs
  const slots: (Team | null)[] = [];
  const usedTeamIds = new Set<number>();

  // First fill from existing saved predictions for this round
  for (const entry of existingEntries) {
    if (entry.round === round) {
      const team = allTeams.find((t) => t.id === entry.team_id);
      if (team) {
        slots.push(team);
        usedTeamIds.add(team.id);
      }
    }
  }

  // Then fill from locally selected IDs
  for (const tid of selectedTeamIds) {
    if (!usedTeamIds.has(tid)) {
      const team = allTeams.find((t) => t.id === tid);
      if (team) {
        slots.push(team);
        usedTeamIds.add(team.id);
      }
    }
  }

  // Pad with nulls
  while (slots.length < slotCount) {
    slots.push(null);
  }

  return (
    <Box sx={{ minWidth: 180, flex: "0 0 auto" }}>
      <Paper elevation={2} sx={{ p: 1.5, mb: 1, textAlign: "center", bgcolor: "primary.main", color: "primary.contrastText" }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
          {roundLabel}
        </Typography>
        <Typography variant="caption">
          {points} {t("knockout.points_value")}
        </Typography>
      </Paper>

      <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
        {slots.map((team, idx) => {
          // Filter out teams already used in OTHER slots of the same round
          const availableTeams = allTeams.filter(
            (t) => !usedTeamIds.has(t.id) || (team && t.id === team.id)
          );

          return (
            <Autocomplete
              key={`${round}-${idx}`}
              size="small"
              options={availableTeams}
              getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
              value={team}
              onChange={(_, v) => onChange(round, v?.id ?? null, idx)}
              renderInput={(params) => (
                <TextField
                  {...params}
                  placeholder={t("knockout.select_team")}
                  variant="outlined"
                  size="small"
                />
              )}
              sx={{
                "& .MuiAutocomplete-inputRoot": { fontSize: "0.85rem", py: 0.5 },
              }}
            />
          );
        })}
      </Box>
    </Box>
  );
}

// ── Main page ─────────────────────────────────────────────

export default function KnockoutPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [tab, setTab] = useState(0);
  const [error, setError] = useState("");
  const [saveMsg, setSaveMsg] = useState("");

  // Knockout matches & predictions
  const { data: knockoutMatches = [], isLoading: knockoutLoading } = useMatchKnockout();
  const [matchPredictions, setMatchPredictions] = useState(
    {} as Record<number, { home: string; away: string }>
  );
  const [matchSaveMsg, setMatchSaveMsg] = useState("");

  // Bracket predictions
  const { data: bracketEntries = [], isLoading: bracketLoading } = useBracketPredictions();
  const { data: allTeams = [] } = useTeamsFromMatches();
  const saveBracketMutation = useSaveBracketPredictions();

  // Local bracket state: round -> list of team IDs
  const [bracketSelections, setBracketSelections] = useState<Record<BracketRound, number[]>>({
    round_of_32: [],
    round_of_16: [],
    quarter_final: [],
    semi_final: [],
    final: [],
    match_for_third_place: [],
  });

  // Populate bracket selections from saved entries on first load
  const populated = useMemo(() => {
    const map: Record<BracketRound, number[]> = {
      round_of_32: [],
      round_of_16: [],
      quarter_final: [],
      semi_final: [],
      final: [],
      match_for_third_place: [],
    };
    for (const entry of bracketEntries) {
      const r = entry.round as BracketRound;
      if (map[r] && entry.team_id) {
        map[r].push(entry.team_id);
      }
    }
    return map;
  }, [bracketEntries]);

  useEffect(() => {
    // Only set if we have entries and the current selections are empty
    const hasEntries = bracketEntries.length > 0;
    const currentEmpty = Object.values(bracketSelections).every((arr) => arr.length === 0);
    if (hasEntries && currentEmpty) {
      setBracketSelections(populated);
    }
  }, [populated, bracketEntries.length, bracketSelections]);

  const handleBracketChange = useCallback(
    (round: BracketRound, teamId: number | null, slotIndex: number) => {
      setBracketSelections((prev) => {
        const current = [...(prev[round] || [])];
        if (teamId === null) {
          // Remove the slot
          current.splice(slotIndex, 1);
        } else if (slotIndex < current.length) {
          current[slotIndex] = teamId;
        } else {
          current.push(teamId);
        }
        return { ...prev, [round]: current };
      });
    },
    []
  );

  const handleSaveBracket = () => {
    setSaveMsg("");
    setError("");
    const entries: Array<{ team_id: number; round: string }> = [];
    for (const round of BRACKET_ROUNDS) {
      for (const teamId of bracketSelections[round]) {
        entries.push({ team_id: teamId, round });
      }
    }
    if (entries.length === 0) return;

    saveBracketMutation.mutate(entries, {
      onSuccess: () => {
        setSaveMsg(t("knockout.bracket_saved"));
      },
      onError: () => {
        setError(t("common.error"));
      },
    });
  };

  // Match prediction handlers
  const handleMatchChange = (id: number, side: "home" | "away", val: string) => {
    setMatchPredictions((prev) => ({
      ...prev,
      [id]: { ...prev[id], [side]: val },
    }));
  };

  const handleSaveMatches = () => {
    const batch = Object.entries(matchPredictions)
      .filter(([, v]) => v.home !== "" && v.away !== "")
      .map(([id, v]) => ({
        match_id: Number(id),
        home_goals: Number(v.home),
        away_goals: Number(v.away),
      }));

    if (batch.length === 0) return;

    predictionsApi
      .batch(batch)
      .then(() => {
        setMatchPredictions({});
        setMatchSaveMsg(t("predictions.save_success"));
      })
      .catch((err: unknown) => {
        const axiosErr = err as { response?: { status?: number } };
        if (axiosErr.response?.status === 401) navigate("/login");
        else setError(t("common.error"));
      });
  };

  const isLoading = knockoutLoading || bracketLoading;

  if (isLoading) {
    return (
      <Container sx={{ mt: 8, textAlign: "center" }}>
        <CircularProgress />
      </Container>
    );
  }

  // Group knockout matches by round
  const roundOrder = ["round_of_32", "round_of_16", "quarter_final", "semi_final", "match_for_third_place", "final"];
  const matchesByRound = roundOrder
    .map((round) => ({
      round,
      matches: knockoutMatches.filter((m) => m.round === round),
    }))
    .filter((r) => r.matches.length > 0);

  return (
    <Container sx={{ mt: 2, mb: 8, maxWidth: "lg" }}>
      <Typography variant="h4" gutterBottom>
        {t("knockout.title")}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("knockout.subtitle")}
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {saveMsg && <Alert severity="success" sx={{ mb: 2 }}>{saveMsg}</Alert>}
      {matchSaveMsg && <Alert severity="success" sx={{ mb: 2 }}>{matchSaveMsg}</Alert>}

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab label={t("knockout.matches_tab")} />
        <Tab label={t("knockout.bracket_tab")} />
      </Tabs>

      {/* ── Tab 1: Knockout Match Predictions ── */}
      {tab === 0 && (
        <Box>
          {matchesByRound.length === 0 ? (
            <Alert severity="info">{t("predictions.no_predictions")}</Alert>
          ) : (
            matchesByRound.map(({ round, matches }) => {
              const roundLabel =
                round === "ro32" ? t("matches.round_of_32") :
                round === "ro16" ? t("matches.round_of_16") :
                round === "qf" ? t("matches.quarter_final") :
                round === "sf" ? t("matches.semi_final") :
                round === "3p" ? t("matches.match_for_third_place") :
                t("matches.final");

              return (
                <Box key={round} sx={{ mb: 3 }}>
                  <Typography
                    variant="subtitle1"
                    sx={{ mb: 1, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}
                  >
                    {roundLabel}
                  </Typography>
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5 }}>
                    {matches.map((m) => (
                      <Box
                        key={m.id}
                        sx={{ flexBasis: { xs: "100%", sm: "calc(50% - 8px)" }, flexGrow: 1 }}
                      >
                        <KnockoutMatchCard
                          match={m}
                          predictions={matchPredictions}
                          onChange={handleMatchChange}
                        />
                      </Box>
                    ))}
                  </Box>
                </Box>
              );
            })
          )}

          {/* Save button for match predictions */}
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
                handleSaveMatches();
              }}
              disabled={Object.keys(matchPredictions).length === 0}
            >
              {t("matches.save_predictions")}
            </Button>
          </Box>
        </Box>
      )}

      {/* ── Tab 2: Bracket Predictions (visual bracket) ── */}
      {tab === 1 && (
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t("knockout.drag_or_select")}
          </Typography>

          {/* Horizontal scrolling bracket grid */}
          <Box
            sx={{
              display: "flex",
              gap: 2,
              overflowX: "auto",
              pb: 2,
              "&::-webkit-scrollbar": { height: 8 },
              "&::-webkit-scrollbar-thumb": { bgcolor: "grey.400", borderRadius: 4 },
            }}
          >
            {BRACKET_ROUNDS.map((round) => (
              <BracketRoundColumn
                key={round}
                round={round}
                selectedTeamIds={bracketSelections[round]}
                allTeams={allTeams}
                onChange={handleBracketChange}
                existingEntries={bracketEntries}
              />
            ))}
          </Box>

          {/* Connector lines between rounds (decorative) */}
          <Box sx={{ mt: 1, mb: 1 }}>
            <Grid container spacing={2}>
              {BRACKET_ROUNDS.map((round, idx) => {
                if (idx === 0) return <Grid key={round} size={{ xs: 12, sm: "grow" }} />;
                return (
                  <Grid key={round} size={{ xs: 12, sm: "grow" }}>
                    <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: 32 }}>
                      <Typography variant="caption" color="text.secondary">
                        →
                      </Typography>
                    </Box>
                  </Grid>
                );
              })}
            </Grid>
          </Box>

          {/* Save button for bracket */}
          <Box sx={{ mt: 3, textAlign: "center" }}>
            <Button
              variant="contained"
              size="large"
              onClick={handleSaveBracket}
              disabled={saveBracketMutation.isPending || Object.values(bracketSelections).every((arr) => arr.length === 0)}
            >
              {saveBracketMutation.isPending ? <CircularProgress size={24} color="inherit" /> : t("knockout.save_bracket")}
            </Button>
          </Box>
        </Box>
      )}
    </Container>
  );
}