import { useState, useEffect, useCallback, useMemo } from "react";
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
import { useMatches } from "../hooks/useMatches";
import { usePredictions, useTournamentBonuses, useTeamsFromMatches } from "../hooks/usePredictions";
import {
  useBracketPredictions,
  useSaveBracketPredictions,
  BRACKET_ROUNDS,
  BRACKET_ROUND_POINTS,
  type BracketRound,
} from "../hooks/useBracket";
import { usePhase, isGroupOpen, isKnockoutOpen } from "../hooks/usePhase";

import type { Match, Team, BracketPredictionEntry } from "../types/api";

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
          ) : (
            <Chip size="small" label={t("matches.max_points_hint", { points: 7 })} variant="outlined" color="primary" />
          )}
        </Box>
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
            disabled={isDisabled}
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
            disabled={isDisabled}
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

// Flexbox wrapper: 2 per row on sm+
function TwoColumnGrid({ children }: { children: React.ReactNode }) {
  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5 }}>
      {Array.isArray(children)
        ? children.map((child, i) => (
            <Box
              key={i}
              sx={{
                flexBasis: { xs: "100%", sm: "calc(50% - 8px)" },
                flexGrow: 1,
              }}
            >
              {child}
            </Box>
          ))
        : children}
    </Box>
  );
}

// ── BracketRoundColumn ────────────────────────────────────

function BracketRoundColumn({
  round,
  selectedTeamIds,
  allTeams,
  onChange,
  existingEntries,
  disabled,
}: {
  round: BracketRound;
  selectedTeamIds: number[];
  allTeams: Team[];
  onChange: (round: BracketRound, teamId: number | null, slotIndex: number) => void;
  existingEntries: BracketPredictionEntry[];
  disabled?: boolean;
}) {
  const { t } = useTranslation();
  const roundLabel = t(`knockout.${round}`);
  const points = BRACKET_ROUND_POINTS[round];

  const slotsPerRound: Record<BracketRound, number> = {
    round_of_32: 32,
    round_of_16: 16,
    quarter_final: 8,
    semi_final: 4,
    match_for_third_place: 2,
    final: 2,
    world_champion: 1,
  };
  const slotCount = slotsPerRound[round];

  const slots: (Team | null)[] = [];
  const usedTeamIds = new Set<number>();

  for (const entry of existingEntries) {
    if (entry.round === round) {
      const team = allTeams.find((t) => t.id === entry.team_id);
      if (team) {
        slots.push(team);
        usedTeamIds.add(team.id);
      }
    }
  }

  for (const tid of selectedTeamIds) {
    if (!usedTeamIds.has(tid)) {
      const team = allTeams.find((t) => t.id === tid);
      if (team) {
        slots.push(team);
        usedTeamIds.add(team.id);
      }
    }
  }

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
              disabled={disabled}
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

export default function MatchesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [tab, setTab] = useState(0);
  const [error, setError] = useState("");
  const [saveMsg, setSaveMsg] = useState("");
  const [predictions, setPredictions] = useState(
    {} as Record<number, { home: string; away: string }>
  );

  // Phase gating
  const { data: phaseData } = usePhase();
  const groupLocked = !isGroupOpen(phaseData);
  const knockoutLocked = !isKnockoutOpen(phaseData);

  // Tournament bonuses state (new fields)
  const [bonuses, setBonuses] = useState({
    winner_team_id: null as number | null,
    top_scorer_name: "",
    bronze_winner_team_id: null as number | null,
    most_goals_team_id: null as number | null,
    most_conceded_team_id: null as number | null,
    custom_bonus_1: "",
    custom_bonus_2: "",
  });

  // Bracket state
  const [bracketSelections, setBracketSelections] = useState<Record<BracketRound, number[]>>({
    round_of_32: [],
    round_of_16: [],
    quarter_final: [],
    semi_final: [],
    final: [],
    match_for_third_place: [],
    world_champion: [],
  });

  const { data: matches = [], isLoading: matchesLoading } = useMatches();
  const { data: rawPredictions = [], isLoading: predictionsLoading } = usePredictions();
  const predictionsList = rawPredictions as unknown as PredictionWithMatch[];
  const { data: teams = [] } = useTeamsFromMatches();
  const { data: bonusesData } = useTournamentBonuses();

  // Bracket data
  const { data: bracketEntries = [], isLoading: bracketLoading } = useBracketPredictions();
  const saveBracketMutation = useSaveBracketPredictions();

  // Populate bracket selections from saved entries
  const populated = useMemo(() => {
    const map: Record<BracketRound, number[]> = {
      round_of_32: [],
      round_of_16: [],
      quarter_final: [],
      semi_final: [],
      final: [],
      match_for_third_place: [],
      world_champion: [],
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

  // Populate bonuses form when tournament bonuses are loaded
  useEffect(() => {
    if (bonusesData) {
      const b = bonusesData as unknown as Record<string, unknown>;
      setBonuses((prev) => ({
        ...prev,
        winner_team_id: (b.winner_team_id as number) || null,
        top_scorer_name: (b.top_scorer_name as string) || "",
        bronze_winner_team_id: (b.bronze_winner_team_id as number) || null,
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
      const existing: Record<number, { home: string; away: string }> = {};
      predictionsList.forEach((p) => {
        existing[p.match_id] = {
          home: String(p.home_goals),
          away: String(p.away_goals),
        };
      });
      setPredictions((prev) => ({ ...existing, ...prev }));
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

    setError("");
    setSaveMsg("");

    predictionsApi
      .batch(batch)
      .then(() => {
        setSaveMsg(t("predictions.save_success"));
      })
      .catch((err: unknown) => {
        const axiosErr = err as { response?: { status?: number } };
        if (axiosErr.response?.status === 401) navigate("/login");
        else setError(t("common.error"));
      });
  };

  const saveBonuses = () => {
    setSaveMsg("");
    setError("");
    predictionsApi
      .saveTournament({
        winner_team_id: bonuses.winner_team_id || undefined,
        top_scorer_name: bonuses.top_scorer_name || undefined,
        bronze_winner_team_id: bonuses.bronze_winner_team_id || undefined,
        most_goals_team_id: bonuses.most_goals_team_id || undefined,
        most_conceded_team_id: bonuses.most_conceded_team_id || undefined,
        custom_bonus_1: bonuses.custom_bonus_1 || undefined,
        custom_bonus_2: bonuses.custom_bonus_2 || undefined,
      })
      .then(() => setSaveMsg(t("predictions.save_success")))
      .catch(() => setError(t("common.error")));
  };

  const selectedWinner = teams.find((tm: Team) => tm.id === bonuses.winner_team_id) || null;
  const selectedBronzeWinner = teams.find((tm: Team) => tm.id === bonuses.bronze_winner_team_id) || null;
  const selectedMostGoals = teams.find((tm: Team) => tm.id === bonuses.most_goals_team_id) || null;
  const selectedMostConceded = teams.find((tm: Team) => tm.id === bonuses.most_conceded_team_id) || null;

  const groupMatches = matches.filter((m) => m.round === "group");
  const knockoutMatches = matches.filter((m) => m.round !== "group");
  const groups = [...new Set(groupMatches.map((m) => m.group).filter(Boolean))].sort();

  const isLoading = matchesLoading || predictionsLoading || bracketLoading;

  // Determine visible tabs based on phase
  type TabItem = { label: string; always: boolean; show?: () => boolean };
  const allTabs: TabItem[] = [
    { label: t("matches.group_stage"), always: true },
    { label: t("matches.knockout"), always: true },
    { label: t("predictions.title"), always: true },
    { label: t("knockout.bracket_tab"), always: false, show: () => isKnockoutOpen(phaseData) },
    { label: t("predictions.tournament_bonuses"), always: true },
  ];
  const tabs = allTabs.filter((tab) => tab.always || (tab.show ? tab.show() : false));

  // Reset tab if out of bounds after tab list changes
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

  // Map tab indices to content sections
  // 0 = group, 1 = knockout, 2 = predictions, 3 = bracket (maybe), 4 = bonuses (maybe)
  const bracketTabIndex = allTabs.findIndex((tabItem) => tabItem.label === t("knockout.bracket_tab"));

  return (
    <Container sx={{ mt: 2, mb: 8, maxWidth: "lg" }}>
      <Typography variant="h4" gutterBottom>
        {t("matches.title")}
      </Typography>

      {/* Phase info banner */}
      {phaseData && (
        <Alert
          severity={groupLocked && !knockoutLocked ? "info" : knockoutLocked ? "warning" : "success"}
          sx={{ mb: 2 }}
        >
          {t(`phase.${phaseData.phase}`)}
          {phaseData.group_deadline && ` — ${t("phase.group_deadline")}: ${new Date(phaseData.group_deadline).toLocaleString()}`}
          {phaseData.knockout_deadline && ` — ${t("phase.knockout_deadline")}: ${new Date(phaseData.knockout_deadline).toLocaleString()}`}
        </Alert>
      )}

      {groupLocked && !knockoutLocked && tab <= 1 && (
        <Alert severity="info" sx={{ mb: 2 }}>{t("phase.group_closed_msg")}</Alert>
      )}
      {!knockoutLocked === false && bracketTabIndex >= 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>{t("phase.knockout_not_open_msg")}</Alert>
      )}

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {saveMsg && <Alert severity="success" sx={{ mb: 2 }}>{saveMsg}</Alert>}

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        {tabs.map((tabItem, idx) => (
          <Tab key={idx} label={tabItem.label} />
        ))}
      </Tabs>

      {/* GROUP STAGE */}
      {tab === 0 && (
        <Box>
          {groups.map((group) => (
            <Box key={group} sx={{ mb: 3 }}>
              <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>
                {group}
              </Typography>
              <TwoColumnGrid>
                {groupMatches
                  .filter((m) => m.group === group)
                  .map((m) => (
                    <MatchCard
                      key={m.id}
                      match={m}
                      predictions={predictions}
                      onChange={handleChange}
                      disabled={groupLocked}
                    />
                  ))}
              </TwoColumnGrid>
            </Box>
          ))}
        </Box>
      )}

      {/* KNOCKOUT MATCHES */}
      {tab === 1 && (
        <Box>
          {["round_of_32","round_of_16","quarter_final","semi_final","match_for_third_place","final"].map((round) => {
            const roundMatches = knockoutMatches.filter((m) => m.round === round);
            if (roundMatches.length === 0) return null;
            return (
              <Box key={round} sx={{ mb: 3 }}>
                <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>
                  {t(`matches.${round}`)}
                </Typography>
                <TwoColumnGrid>
                  {roundMatches.map((m) => (
                    <MatchCard
                      key={m.id}
                      match={m}
                      predictions={predictions}
                      onChange={handleChange}
                    />
                  ))}
                </TwoColumnGrid>
              </Box>
            );
          })}
        </Box>
      )}

      {/* MY PREDICTIONS OVERVIEW */}
      {tab === 2 && (
        <Box>
          {predictionsList.length === 0 ? (
            <Alert severity="info">{t("predictions.no_predictions")}</Alert>
          ) : (
            predictionsList.map((p: PredictionWithMatch) => (
              <Paper key={p.match_id} elevation={2} sx={{ p: 2, mb: 2 }}>
                <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    {p.match.group ? `${p.match.group} · ` : ""}
                    {p.match.match_number}
                  </Typography>
                  <Chip size="small" label={p.match.round} />
                </Box>
                <Grid container sx={{ alignItems: 'center' }} spacing={2}>
                  <Grid size={{ xs: 4 }}><Typography align="right">{p.match.home_team.flag_emoji ?? ""} {p.match.home_team.name}</Typography></Grid>
                  <Grid size={{ xs: 4 }}><Typography align="center" variant="h6">{p.home_goals} - {p.away_goals}</Typography></Grid>
                  <Grid size={{ xs: 4 }}><Typography>{p.match.away_team.name} {p.match.away_team.flag_emoji ?? ""}</Typography></Grid>
                </Grid>
              </Paper>
            ))
          )}
        </Box>
      )}

      {/* BRACKET PREDICTIONS */}
      {tab === bracketTabIndex && bracketTabIndex >= 0 && (
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t("knockout.subtitle")}
          </Typography>

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
                allTeams={teams}
                onChange={handleBracketChange}
                existingEntries={bracketEntries}
                disabled={knockoutLocked}
              />
            ))}
          </Box>

          <Box sx={{ mt: 3, textAlign: "center" }}>
            <Button
              variant="contained"
              size="large"
              onClick={handleSaveBracket}
              disabled={saveBracketMutation.isPending || knockoutLocked || Object.values(bracketSelections).every((arr) => arr.length === 0)}
            >
              {saveBracketMutation.isPending ? <CircularProgress size={24} color="inherit" /> : t("knockout.save_bracket")}
            </Button>
          </Box>
        </Box>
      )}

      {/* TOURNAMENT BONUSES */}
      {tab === tabs.length - 1 && (
        <Paper elevation={2} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>{t("predictions.tournament_bonuses")}</Typography>

          {groupLocked && (
            <Alert severity="info" sx={{ mb: 2 }}>{t("phase.group_closed_msg")}</Alert>
          )}

          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <Autocomplete
              options={teams}
              getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
              value={selectedWinner}
              onChange={(_, v) => setBonuses((b) => ({ ...b, winner_team_id: v?.id || null }))}
              disabled={groupLocked}
              renderInput={(params) => (
                <TextField {...params} label={`${t("predictions.winner")} (20p)`} />
              )}
            />

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
              value={selectedBronzeWinner}
              onChange={(_, v) => setBonuses((b) => ({ ...b, bronze_winner_team_id: v?.id || null }))}
              disabled={groupLocked}
              renderInput={(params) => (
                <TextField {...params} label={`${t("predictions.bronze_winner")} (20p)`} />
              )}
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

      {/* Save button — visible on match tabs only */}
      {(tab === 0 || tab === 1) && (
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