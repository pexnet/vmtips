import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Container,
  Typography,
  Paper,
  Box,
  TextField,
  Button,
  Alert,
  Autocomplete,
  CircularProgress,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Switch,
  FormControlLabel,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
} from "@mui/material";
import { adminApi, phaseApi } from "../api/client";
import { useMatches } from "../hooks/useMatches";
import { useTeams } from "../hooks/useTeams";
import { queryClient } from "../contexts/QueryClientProvider";
import type { Match, Team, GroupStanding, ScoringOverviewEntry, PhaseInfo } from "../types/api";
import { getErrorDetail } from "../types/api";

export default function AdminPage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  // ── Match result state ──
  const [resultDrafts, setResultDrafts] = useState<Record<number, { home: string; away: string }>>({});
  const [savingMatchId, setSavingMatchId] = useState<number | null>(null);

  // ── Tournament result state (new fields) ──
  const [tournamentResult, setTournamentResult] = useState({
    winner_team_id: null as number | null,
    top_scorer_name: "",
    bronze_winner_team_id: null as number | null,
    most_goals_team_id: null as number | null,
    most_conceded_team_id: null as number | null,
    custom_bonus_1_answer: "",
    custom_bonus_2_answer: "",
  });
  const [tournamentLoading, setTournamentLoading] = useState(false);

  // ── Phase state ──
  const [phase, setPhaseState] = useState<PhaseInfo | null>(null);
  const [phaseLoading, setPhaseLoading] = useState(false);
  const [phaseForm, setPhaseForm] = useState({
    phase: "group_open",
    group_deadline: "",
    knockout_opens_at: "",
    knockout_deadline: "",
  });

  // ── Group standings state ──
  const [standings, setStandings] = useState<GroupStanding[]>([]);
  const [standingsLoading, setStandingsLoading] = useState(false);

  // ── Knockout advancement state ──
  const [advancements, setAdvancements] = useState<{ id: number; team_id: number; team_name: string; team_code: string; round: string; match_number: number | null }[]>([]);
  const [advancementLoading, setAdvancementLoading] = useState(false);
  const [advancementDrafts, setAdvancementDrafts] = useState<Record<number, { team_id: number | null; round: string }>>({});

  // ── Scoring overview state ──
  const [scoringOverview, setScoringOverview] = useState<ScoringOverviewEntry[]>([]);

  // ── All predictions state ──
  const [allPredictions, setAllPredictions] = useState<{
    users: {
      user_id: number;
      display_name: string;
      match_predictions: { match_id: number; match_number: number; group: string; round: string; home_team: string; home_flag: string; away_team: string; away_flag: string; home_goals: number | null; away_goals: number | null }[];
      bracket_predictions: { team_id: number; team_name: string; team_flag: string; round: string; points: number }[];
      tournament_bonuses: { winner_team_id: number | null; winner_team_name: string | null; winner_team_flag: string | null; top_scorer_name: string | null; bronze_winner_team_id: number | null; bronze_winner_team_name: string | null; most_goals_team_id: number | null; most_goals_team_name: string | null; most_conceded_team_id: number | null; most_conceded_team_name: string | null; custom_bonus_1: string | null; custom_bonus_2: string | null } | null;
    }[];
  } | null>(null);
  const [allPredictionsLoading, setAllPredictionsLoading] = useState(false);
  const [selectedPredUserId, setSelectedPredUserId] = useState<number | null>(null);

  // ── Sync config state ──
  const [syncConfig, setSyncConfig] = useState<{
    source: string;
    auto_sync_enabled: boolean;
    auto_sync_interval_minutes: number;
  } | null>(null);
  const [syncConfigLoading, setSyncConfigLoading] = useState(false);

  // ── League management state ──
  const [leagues, setLeagues] = useState<{
    id: number;
    name: string;
    invite_code: string;
    is_public: boolean;
    admin_user_id: number;
    member_count: number;
    created_at: string;
  }[]>([]);
  const [leaguesLoading, setLeaguesLoading] = useState(false);
  const [editingLeague, setEditingLeague] = useState<number | null>(null);
  const [editLeagueForm, setEditLeagueForm] = useState({ name: "", is_public: false });
  const [deleteConfirmLeagueId, setDeleteConfirmLeagueId] = useState<number | null>(null);

  const { data: matches = [], isLoading: matchesLoading } = useMatches();
  const { data: teams = [] } = useTeams();

  // Load initial data
  useEffect(() => { loadTournamentResult(); }, []);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadPhase(); loadStandings(); loadAdvancements(); loadScoringOverview(); }, []);

  function clearMessages() {
    setError("");
    setSuccess("");
  }

  useEffect(() => {
    setResultDrafts((prev) => {
      const next = { ...prev };
      matches.forEach((match) => {
        if (next[match.id]) return;
        next[match.id] = {
          home: match.home_goals === null ? "" : String(match.home_goals),
          away: match.away_goals === null ? "" : String(match.away_goals),
        };
      });
      return next;
    });
  }, [matches]);

  // ── Match result handlers ──
  function handleResultDraftChange(matchId: number, side: "home" | "away", value: string) {
    if (value !== "" && !/^\d+$/.test(value)) return;
    setResultDrafts((prev) => ({
      ...prev,
      [matchId]: {
        home: prev[matchId]?.home ?? "",
        away: prev[matchId]?.away ?? "",
        [side]: value,
      },
    }));
  }

  function handleSaveResult(match: Match) {
    const draft = resultDrafts[match.id];
    if (!draft || draft.home === "" || draft.away === "") return;
    clearMessages();
    setSavingMatchId(match.id);
    adminApi.setResult(match.id, { home_goals: Number(draft.home), away_goals: Number(draft.away) })
      .then(() => {
        setSuccess(t("admin.result_updated"));
        queryClient.invalidateQueries({ queryKey: ["matches"] });
        if (match.round === "group") {
          return adminApi.computeStandings().then(() => loadStandings());
        }
      })
      .catch((err: unknown) => setError(getErrorDetail(err)))
      .finally(() => setSavingMatchId(null));
  }

  // ── Tournament result handlers ──
  function loadTournamentResult() {
    adminApi.tournamentResult().then((res) => {
      const d = res.data as Record<string, unknown>;
      setTournamentResult({
        winner_team_id: (d.winner_team_id as number) || null,
        top_scorer_name: (d.top_scorer_name as string) || "",
        bronze_winner_team_id: (d.bronze_winner_team_id as number) || null,
        most_goals_team_id: (d.most_goals_team_id as number) || null,
        most_conceded_team_id: (d.most_conceded_team_id as number) || null,
        custom_bonus_1_answer: (d.custom_bonus_1_answer as string) || "",
        custom_bonus_2_answer: (d.custom_bonus_2_answer as string) || "",
      });
    }).catch(() => { /* no result yet */ });
  }

  function handleSaveTournamentResult() {
    clearMessages();
    setTournamentLoading(true);
    adminApi.setTournamentResult({
      winner_team_id: tournamentResult.winner_team_id || undefined,
      top_scorer_name: tournamentResult.top_scorer_name || undefined,
      bronze_winner_team_id: tournamentResult.bronze_winner_team_id || undefined,
      most_goals_team_id: tournamentResult.most_goals_team_id || undefined,
      most_conceded_team_id: tournamentResult.most_conceded_team_id || undefined,
      custom_bonus_1_answer: tournamentResult.custom_bonus_1_answer || undefined,
      custom_bonus_2_answer: tournamentResult.custom_bonus_2_answer || undefined,
    })
      .then(() => setSuccess(t("admin.result_updated")))
      .catch((err: unknown) => setError(getErrorDetail(err)))
      .finally(() => setTournamentLoading(false));
  }

  // ── Sync & Score handlers ──
  function handleSync() {
    clearMessages();
    setLoading(true);
    adminApi.sync().then(() => { setSuccess(t("admin.results_synced")); queryClient.invalidateQueries({ queryKey: ["matches"] }); })
      .catch((err: unknown) => setError(getErrorDetail(err)))
      .finally(() => setLoading(false));
  }

  function handleRecalc() {
    clearMessages();
    setLoading(true);
    adminApi.recalc().then(() => { setSuccess(t("admin.scores_recalculated")); queryClient.invalidateQueries({ queryKey: ["leaderboard"] }); })
      .catch((err: unknown) => setError(getErrorDetail(err)))
      .finally(() => setLoading(false));
  }

  // ── Phase handlers ──
  function loadPhase() {
    phaseApi.get()
      .then((data) => {
        const p = data.data as PhaseInfo;
        setPhaseState(p);
        setPhaseForm({
          phase: p.phase || "group_open",
          group_deadline: p.group_deadline?.slice(0, 16) || "",
          knockout_opens_at: p.knockout_opens_at?.slice(0, 16) || "",
          knockout_deadline: p.knockout_deadline?.slice(0, 16) || "",
        });
      })
      .catch(() => { /* phase endpoint not yet available */ });
  }

  function handleSavePhase() {
    clearMessages();
    setPhaseLoading(true);
    adminApi.updatePhase({
      phase: phaseForm.phase,
      group_deadline: phaseForm.group_deadline || undefined,
      knockout_opens_at: phaseForm.knockout_opens_at || undefined,
      knockout_deadline: phaseForm.knockout_deadline || undefined,
    })
      .then(() => { setSuccess(t("admin.phase_updated")); queryClient.invalidateQueries({ queryKey: ["phase"] }); })
      .catch((err: unknown) => setError(getErrorDetail(err)))
      .finally(() => setPhaseLoading(false));
  }

  // ── Group standings handlers ──
  function loadStandings() {
    adminApi.getStandings().then((res) => {
      const payload = res.data as { standings?: GroupStanding[] };
      setStandings(payload.standings ?? []);
    })
      .catch(() => setStandings([]));
  }

  function handleComputeStandings() {
    clearMessages();
    setStandingsLoading(true);
    adminApi.computeStandings().then(() => { setSuccess(t("admin.standings_computed")); loadStandings(); })
      .catch((err: unknown) => setError(getErrorDetail(err)))
      .finally(() => setStandingsLoading(false));
  }

  // ── Knockout advancement handlers ──
  function loadAdvancements() {
    adminApi.getAdvancements().then((res) => {
      const payload = res.data as { advancements?: typeof advancements };
      setAdvancements(payload.advancements ?? []);
    })
      .catch(() => setAdvancements([]));
  }

  function handleAdvancementDraftChange(matchId: number, teamId: number | null, round: string) {
    setAdvancementDrafts((prev) => ({
      ...prev,
      [matchId]: { team_id: teamId, round },
    }));
  }

  function handleSetAdvancement(match: Match) {
    const draft = advancementDrafts[match.id];
    if (!draft?.team_id) return;
    clearMessages();
    setAdvancementLoading(true);
    adminApi.setAdvancement({
      team_id: draft.team_id,
      round: draft.round,
      match_number: match.match_number,
    })
      .then(() => { setSuccess(t("admin.advancement_set")); loadAdvancements(); })
      .catch((err: unknown) => setError(getErrorDetail(err)))
      .finally(() => setAdvancementLoading(false));
  }

  function handleResolveKnockout() {
    clearMessages();
    setLoading(true);
    adminApi.resolveKnockoutTeams().then(() => { setSuccess(t("admin.knockout_resolved")); queryClient.invalidateQueries({ queryKey: ["matches"] }); })
      .catch((err: unknown) => setError(getErrorDetail(err)))
      .finally(() => setLoading(false));
  }

  // ── Scoring overview ──
  function loadScoringOverview() {
    adminApi.scoringOverview().then((res) => {
      const payload = res.data as { scores?: ScoringOverviewEntry[] };
      setScoringOverview(payload.scores ?? []);
    })
      .catch(() => setScoringOverview([]));
  }

  // ── Load all predictions ──
  useEffect(() => {
    setAllPredictionsLoading(true);
    adminApi.allPredictions()
      .then((res) => {
        const payload = res.data as { users?: NonNullable<typeof allPredictions>["users"] };
        if (payload.users) {
          setAllPredictions({ users: payload.users });
          setSelectedPredUserId((current) => current ?? payload.users?.[0]?.user_id ?? null);
        } else {
          setAllPredictions(null);
        }
      })
      .catch(() => { setAllPredictions(null); })
      .finally(() => setAllPredictionsLoading(false));
  }, []);

  // ── Sync config ──
  useEffect(() => {
    adminApi.syncConfig().then((res) => { setSyncConfig(res.data as typeof syncConfig); })
      .catch(() => { /* no config yet */ });
  }, []);

  function handleSaveSyncConfig() {
    if (!syncConfig) return;
    clearMessages();
    setSyncConfigLoading(true);
    adminApi.updateSyncConfig(syncConfig).then(() => setSuccess(t("admin.sync_config_saved")))
      .catch((err: unknown) => setError(getErrorDetail(err)))
      .finally(() => setSyncConfigLoading(false));
  }

  // ── League management ──
  function loadLeagues() {
    setLeaguesLoading(true);
    adminApi.listLeagues()
      .then((res) => {
        const data = res.data as typeof leagues;
        setLeagues(data);
      })
      .catch((err: unknown) => setError(getErrorDetail(err)))
      .finally(() => setLeaguesLoading(false));
  }

  function handleSaveLeagueEdit() {
    if (editingLeague === null) return;
    clearMessages();
    adminApi.updateLeague(editingLeague, {
      name: editLeagueForm.name,
      is_public: editLeagueForm.is_public,
    })
      .then(() => {
        setSuccess(t("common.saved"));
        setEditingLeague(null);
        loadLeagues();
      })
      .catch((err: unknown) => setError(getErrorDetail(err)));
  }

  function handleDeleteLeague() {
    if (deleteConfirmLeagueId === null) return;
    clearMessages();
    adminApi.deleteLeague(deleteConfirmLeagueId)
      .then(() => {
        setSuccess(t("common.success"));
        setDeleteConfirmLeagueId(null);
        loadLeagues();
      })
      .catch((err: unknown) => setError(getErrorDetail(err)));
  }

  // ── Helpers ──
  const selectedWinnerTeam = teams.find((tm: Team) => tm.id === tournamentResult.winner_team_id) || null;
  const selectedBronzeWinner = teams.find((tm: Team) => tm.id === tournamentResult.bronze_winner_team_id) || null;
  const selectedMostGoals = teams.find((tm: Team) => tm.id === tournamentResult.most_goals_team_id) || null;
  const selectedMostConceded = teams.find((tm: Team) => tm.id === tournamentResult.most_conceded_team_id) || null;
  const orderedMatches = [...matches].sort((a, b) => a.match_number - b.match_number);
  const knockoutMatches = orderedMatches.filter((m) => m.round !== "group");
  const groupLetters = [...new Set(standings.map((s) => s.group))].sort();

  function nextAdvancementRound(round: string) {
    const map: Record<string, string> = {
      round_of_32: "round_of_16",
      round_of_16: "quarter_final",
      quarter_final: "semi_final",
      semi_final: "final",
      final: "world_champion",
      match_for_third_place: "match_for_third_place",
    };
    return map[round] ?? round;
  }

  if (matchesLoading) {
    return <Container sx={{ mt: 8, textAlign: "center" }}><CircularProgress /></Container>;
  }

  return (
    <Container sx={{ mt: 2, mb: 8, maxWidth: "lg" }}>
      <Typography variant="h4" gutterBottom>{t("admin.title")}</Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }} variant="scrollable" scrollButtons="auto">
        <Tab label={t("admin.enter_result")} />
        <Tab label={t("admin.group_standings")} />
        <Tab label={t("admin.tournament_result")} />
        <Tab label={t("admin.phase_management")} />
        <Tab label={t("admin.knockout_advancements")} />
        <Tab label={t("admin.scoring_overview")} />
        <Tab label={t("admin.score_management")} />
        <Tab label={t("admin.all_predictions")} />
        <Tab label={t("admin.league_management")} />
      </Tabs>

      {/* ═══ TAB 0: MATCH RESULTS ═══ */}
      {tab === 0 && (
        <Paper elevation={2} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>{t("admin.enter_result")}</Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>#</TableCell>
                  <TableCell>{t("matches.round")}</TableCell>
                  <TableCell>{t("matches.home")}</TableCell>
                  <TableCell align="center">{t("admin.enter_result")}</TableCell>
                  <TableCell>{t("matches.away")}</TableCell>
                  <TableCell align="center">Status</TableCell>
                  <TableCell align="right">{t("common.actions")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {orderedMatches.map((match) => {
                  const draft = resultDrafts[match.id] ?? { home: "", away: "" };
                  const homeName = match.home_team?.name ?? match.home_team_placeholder ?? "?";
                  const awayName = match.away_team?.name ?? match.away_team_placeholder ?? "?";
                  const canSave = draft.home !== "" && draft.away !== "";

                  return (
                    <TableRow key={match.id} hover>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>{match.match_number}</TableCell>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>
                        {match.round === "group" ? `${t("matches.group")} ${match.group ?? ""}` : t(`matches.${match.round}`)}
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                          <Typography component="span">{match.home_team?.flag_emoji ?? ""}</Typography>
                          <Typography variant="body2">{homeName}</Typography>
                        </Box>
                      </TableCell>
                      <TableCell align="center">
                        <Box sx={{ display: "inline-flex", alignItems: "center", gap: 1 }}>
                          <TextField
                            size="small"
                            value={draft.home}
                            onChange={(e) => handleResultDraftChange(match.id, "home", e.target.value)}
                            sx={{ width: 58, "& input": { textAlign: "center" } }}
                            slotProps={{ input: { inputMode: "numeric" } }}
                          />
                          <Typography color="text.secondary">-</Typography>
                          <TextField
                            size="small"
                            value={draft.away}
                            onChange={(e) => handleResultDraftChange(match.id, "away", e.target.value)}
                            sx={{ width: 58, "& input": { textAlign: "center" } }}
                            slotProps={{ input: { inputMode: "numeric" } }}
                          />
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                          <Typography component="span">{match.away_team?.flag_emoji ?? ""}</Typography>
                          <Typography variant="body2">{awayName}</Typography>
                        </Box>
                      </TableCell>
                      <TableCell align="center">{match.status}</TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          variant="contained"
                          onClick={() => handleSaveResult(match)}
                          disabled={!canSave || savingMatchId === match.id}
                        >
                          {savingMatchId === match.id ? <CircularProgress size={18} /> : t("admin.save_result")}
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      {/* ═══ TAB 1: GROUP STANDINGS ═══ */}
      {tab === 1 && (
        <Paper elevation={2} sx={{ p: 3 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
            <Typography variant="h6">{t("admin.group_standings")}</Typography>
            <Button variant="outlined" onClick={handleComputeStandings} disabled={standingsLoading}>
              {standingsLoading ? <CircularProgress size={20} /> : t("admin.compute_standings")}
            </Button>
          </Box>
          {groupLetters.length === 0 ? (
            <Alert severity="info">No standings computed yet. Click &quot;{t("admin.compute_standings")}&quot; to generate.</Alert>
          ) : (
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" }, gap: 2 }}>
              {groupLetters.map((group) => (
                <Paper
                  key={group}
                  elevation={0}
                  sx={{
                    p: 1.5,
                    border: 1,
                    borderColor: "divider",
                    bgcolor: "background.default",
                  }}
                >
                  <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 1 }}>
                    Group {group}
                  </Typography>
                  <TableContainer>
                    <Table size="small" sx={{ tableLayout: "fixed" }}>
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ width: 40 }}>#</TableCell>
                          <TableCell>Team</TableCell>
                          <TableCell align="right" sx={{ width: 38 }}>P</TableCell>
                          <TableCell align="right" sx={{ width: 44 }}>GD</TableCell>
                          <TableCell align="right" sx={{ width: 44 }}>Pts</TableCell>
                          <TableCell align="right" sx={{ width: 72 }}>W-D-L</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {standings.filter((s) => s.group === group).sort((a, b) => (a.position ?? 99) - (b.position ?? 99)).map((s, idx) => (
                          <TableRow
                            key={s.team_id}
                            sx={{
                              "& td": {
                                py: 0.75,
                                borderBottomColor: "divider",
                              },
                              "& td:first-of-type": {
                                borderLeft: 3,
                                borderLeftColor: idx < 2
                                  ? "success.main"
                                  : idx === 2
                                    ? "warning.main"
                                    : "transparent",
                              },
                            }}
                          >
                            <TableCell sx={{ fontWeight: 700 }}>{s.position ?? "-"}</TableCell>
                            <TableCell sx={{ minWidth: 0 }}>
                              <Typography variant="body2" noWrap sx={{ fontWeight: 600 }}>
                                {s.team_code} {s.team_name}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                GF {s.goals_for} · GA {s.goals_against}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">{s.played}</TableCell>
                            <TableCell align="right">{s.goal_difference}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 800 }}>{s.points}</TableCell>
                            <TableCell align="right" sx={{ color: "text.secondary" }}>
                              {s.won}-{s.drawn}-{s.lost}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Paper>
              ))}
            </Box>
          )}
        </Paper>
      )}

      {/* ═══ TAB 2: TOURNAMENT RESULT ═══ */}
      {tab === 2 && (
        <Paper elevation={2} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>{t("admin.tournament_result")}</Typography>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <Autocomplete options={teams} getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
              value={selectedWinnerTeam} onChange={(_, v) => setTournamentResult((r) => ({ ...r, winner_team_id: v?.id || null }))}
              renderInput={(params) => <TextField {...params} label={`${t("admin.winner")} (20p)`} />} />
            <TextField label={`${t("admin.top_scorer")} (20p)`} value={tournamentResult.top_scorer_name}
              onChange={(e) => setTournamentResult((r) => ({ ...r, top_scorer_name: e.target.value }))} fullWidth />
            <Autocomplete options={teams} getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
              value={selectedBronzeWinner} onChange={(_, v) => setTournamentResult((r) => ({ ...r, bronze_winner_team_id: v?.id || null }))}
              renderInput={(params) => <TextField {...params} label={`${t("admin.bronze_winner")} (20p)`} />} />
            <Autocomplete options={teams} getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
              value={selectedMostGoals} onChange={(_, v) => setTournamentResult((r) => ({ ...r, most_goals_team_id: v?.id || null }))}
              renderInput={(params) => <TextField {...params} label={`${t("admin.most_goals_team")} (10p)`} />} />
            <Autocomplete options={teams} getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
              value={selectedMostConceded} onChange={(_, v) => setTournamentResult((r) => ({ ...r, most_conceded_team_id: v?.id || null }))}
              renderInput={(params) => <TextField {...params} label={`${t("admin.most_conceded_team")} (10p)`} />} />
            <TextField label={`${t("admin.custom_bonus_1")} (10p)`} value={tournamentResult.custom_bonus_1_answer}
              onChange={(e) => setTournamentResult((r) => ({ ...r, custom_bonus_1_answer: e.target.value }))} fullWidth />
            <TextField label={`${t("admin.custom_bonus_2")} (10p)`} value={tournamentResult.custom_bonus_2_answer}
              onChange={(e) => setTournamentResult((r) => ({ ...r, custom_bonus_2_answer: e.target.value }))} fullWidth />
            <Button variant="contained" onClick={handleSaveTournamentResult} disabled={tournamentLoading}>
              {tournamentLoading ? <CircularProgress size={20} /> : t("admin.update_result")}
            </Button>
          </Box>
        </Paper>
      )}

      {/* ═══ TAB 3: PHASE MANAGEMENT ═══ */}
      {tab === 3 && (
        <Paper elevation={2} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>{t("admin.phase_management")}</Typography>
          {phase && (
            <Alert severity="info" sx={{ mb: 2 }}>
              {t("admin.current_phase")}: {t(`phase.${phase.phase}`)}
            </Alert>
          )}
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <FormControl fullWidth>
              <InputLabel>{t("admin.set_phase")}</InputLabel>
              <Select value={phaseForm.phase} label={t("admin.set_phase")}
                onChange={(e) => setPhaseForm((f) => ({ ...f, phase: e.target.value }))}>
                <MenuItem value="group_open">{t("admin.phase_group_open")}</MenuItem>
                <MenuItem value="group_closed">{t("admin.phase_group_closed")}</MenuItem>
                <MenuItem value="knockout_open">{t("admin.phase_knockout_open")}</MenuItem>
                <MenuItem value="knockout_closed">{t("admin.phase_knockout_closed")}</MenuItem>
              </Select>
            </FormControl>
            <TextField label={t("admin.group_deadline")} type="datetime-local" value={phaseForm.group_deadline}
              onChange={(e) => setPhaseForm((f) => ({ ...f, group_deadline: e.target.value }))} slotProps={{ inputLabel: { shrink: true } }} fullWidth />
            <TextField label={t("admin.knockout_opens")} type="datetime-local" value={phaseForm.knockout_opens_at}
              onChange={(e) => setPhaseForm((f) => ({ ...f, knockout_opens_at: e.target.value }))} slotProps={{ inputLabel: { shrink: true } }} fullWidth />
            <TextField label={t("admin.knockout_deadline")} type="datetime-local" value={phaseForm.knockout_deadline}
              onChange={(e) => setPhaseForm((f) => ({ ...f, knockout_deadline: e.target.value }))} slotProps={{ inputLabel: { shrink: true } }} fullWidth />
            <Button variant="contained" onClick={handleSavePhase} disabled={phaseLoading}>
              {phaseLoading ? <CircularProgress size={20} /> : t("common.save")}
            </Button>
          </Box>
        </Paper>
      )}

      {/* ═══ TAB 4: KNOCKOUT ADVANCEMENTS ═══ */}
      {tab === 4 && (
        <Paper elevation={2} sx={{ p: 3 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 2, mb: 2 }}>
            <Typography variant="h6">{t("admin.knockout_advancements")}</Typography>
            <Button variant="outlined" onClick={handleResolveKnockout} disabled={loading}>
              {loading ? <CircularProgress size={20} /> : t("admin.resolve_knockout")}
            </Button>
          </Box>
          <TableContainer sx={{ mb: 3 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>#</TableCell>
                  <TableCell>{t("matches.round")}</TableCell>
                  <TableCell>{t("matches.home")}</TableCell>
                  <TableCell>{t("matches.away")}</TableCell>
                  <TableCell sx={{ minWidth: 220 }}>Advanced team</TableCell>
                  <TableCell sx={{ minWidth: 180 }}>Advances to</TableCell>
                  <TableCell align="right">{t("common.actions")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {knockoutMatches.map((match) => {
                  const homeName = match.home_team?.name ?? match.home_team_placeholder ?? "?";
                  const awayName = match.away_team?.name ?? match.away_team_placeholder ?? "?";
                  const teamOptions = [match.home_team, match.away_team].filter((team): team is Team => Boolean(team));
                  const defaultRound = nextAdvancementRound(match.round);
                  const draft = advancementDrafts[match.id] ?? { team_id: null, round: defaultRound };
                  const selectedTeam = teamOptions.find((team) => team.id === draft.team_id) ?? null;

                  return (
                    <TableRow key={match.id} hover>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>{match.match_number}</TableCell>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>{t(`matches.${match.round}`)}</TableCell>
                      <TableCell>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                          <Typography component="span">{match.home_team?.flag_emoji ?? ""}</Typography>
                          <Typography variant="body2">{homeName}</Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                          <Typography component="span">{match.away_team?.flag_emoji ?? ""}</Typography>
                          <Typography variant="body2">{awayName}</Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Autocomplete
                          size="small"
                          options={teamOptions}
                          getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
                          value={selectedTeam}
                          onChange={(_, value) => handleAdvancementDraftChange(match.id, value?.id ?? null, draft.round)}
                          renderInput={(params) => <TextField {...params} placeholder="Select team" />}
                        />
                      </TableCell>
                      <TableCell>
                        <FormControl size="small" fullWidth>
                          <Select
                            value={draft.round}
                            onChange={(e) => handleAdvancementDraftChange(match.id, draft.team_id, e.target.value)}
                          >
                            <MenuItem value="round_of_16">Round of 16</MenuItem>
                            <MenuItem value="quarter_final">Quarter-final</MenuItem>
                            <MenuItem value="semi_final">Semi-final</MenuItem>
                            <MenuItem value="final">Final</MenuItem>
                            <MenuItem value="match_for_third_place">3rd Place</MenuItem>
                            <MenuItem value="world_champion">World Champion</MenuItem>
                          </Select>
                        </FormControl>
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          variant="contained"
                          onClick={() => handleSetAdvancement(match)}
                          disabled={!draft.team_id || advancementLoading}
                        >
                          {advancementLoading ? <CircularProgress size={18} /> : t("admin.set_advancement")}
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
          {advancements.length > 0 && (
            <Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>Saved advancements</Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Team</TableCell>
                      <TableCell>Round</TableCell>
                      <TableCell>Match #</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {advancements.map((a) => (
                      <TableRow key={a.id}>
                        <TableCell>{a.team_code} {a.team_name}</TableCell>
                        <TableCell>{a.round}</TableCell>
                        <TableCell>{a.match_number ?? "-"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          )}
        </Paper>
      )}

      {/* ═══ TAB 5: SCORING OVERVIEW ═══ */}
      {tab === 5 && (
        <Paper elevation={2} sx={{ p: 3 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
            <Typography variant="h6">{t("admin.scoring_overview")}</Typography>
            <Button variant="outlined" onClick={() => { loadScoringOverview(); }}>{t("admin.refresh_overview")}</Button>
          </Box>
          {scoringOverview.length === 0 ? (
            <Alert severity="info">No scoring data yet. Recalculate scores first.</Alert>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{t("admin.user")}</TableCell>
                    <TableCell align="right">{t("admin.match_pts")}</TableCell>
                    <TableCell align="right">{t("admin.bracket_pts")}</TableCell>
                    <TableCell align="right">{t("admin.bonus_pts")}</TableCell>
                    <TableCell align="right">{t("admin.league_pts")}</TableCell>
                    <TableCell align="right">{t("admin.total_pts")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {scoringOverview.map((row) => (
                    <TableRow key={row.user_id}>
                      <TableCell>{row.display_name}</TableCell>
                      <TableCell align="right">{row.match_points}</TableCell>
                      <TableCell align="right">{row.bracket_points}</TableCell>
                      <TableCell align="right">{row.tournament_bonus_points}</TableCell>
                      <TableCell align="right">{row.league_bonus_points}</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700 }}>{row.total_points}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      )}

      {/* ═══ TAB 6: SCORE MANAGEMENT ═══ */}
      {tab === 6 && (
        <Paper elevation={2} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>{t("admin.score_management")}</Typography>
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
            <Button variant="contained" onClick={handleSync} disabled={loading}>
              {loading ? <CircularProgress size={20} /> : t("admin.sync_results")}
            </Button>
            <Button variant="contained" onClick={handleRecalc} disabled={loading}>
              {loading ? <CircularProgress size={20} /> : t("admin.recalculate_scores")}
            </Button>
          </Box>
          {syncConfig && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="subtitle1" sx={{ mb: 1 }}>{t("admin.sync_config")}</Typography>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <TextField label={t("admin.sync_source")} value={syncConfig.source}
                  onChange={(e) => setSyncConfig((c) => c ? { ...c, source: e.target.value } : c)} fullWidth />
                <FormControlLabel control={<Switch checked={syncConfig.auto_sync_enabled}
                  onChange={(e) => setSyncConfig((c) => c ? { ...c, auto_sync_enabled: e.target.checked } : c)} />}
                  label={`${t("admin.auto_sync")}: ${syncConfig.auto_sync_enabled ? t("admin.auto_sync_on") : t("admin.auto_sync_off")}`} />
                <TextField label={t("admin.sync_interval")} type="number" value={syncConfig.auto_sync_interval_minutes}
                  onChange={(e) => setSyncConfig((c) => c ? { ...c, auto_sync_interval_minutes: Number(e.target.value) } : c)} fullWidth />
                <Button variant="contained" onClick={handleSaveSyncConfig} disabled={syncConfigLoading}>
                  {syncConfigLoading ? <CircularProgress size={20} /> : t("admin.save_sync_config")}
                </Button>
              </Box>
            </Box>
          )}
        </Paper>
      )}

      {/* ═══ TAB 7: ALL PREDICTIONS ═══ */}
      {tab === 7 && (
        <Paper elevation={2} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>{t("admin.all_predictions")}</Typography>
          {allPredictionsLoading ? (
            <CircularProgress />
          ) : allPredictions && allPredictions.users.length > 0 ? (
            <>
              <Autocomplete
                options={allPredictions.users}
                getOptionLabel={(u) => u.display_name}
                value={allPredictions.users.find((u) => u.user_id === selectedPredUserId) || null}
                onChange={(_, v) => setSelectedPredUserId(v ? v.user_id : null)}
                renderInput={(params) => <TextField {...params} label={t("admin.select_user")} />}
                sx={{ mb: 3 }}
              />
              {selectedPredUserId && (() => {
                const user = allPredictions.users.find((u) => u.user_id === selectedPredUserId);
                if (!user) return null;
                const groupMatches = user.match_predictions.filter((m) => m.round === "group");
                const knockoutMatches = user.match_predictions.filter((m) => m.round !== "group");
                const bonuses = user.tournament_bonuses;
                return (
                  <Box>
                    {/* ── Group predictions ── */}
                    <Typography variant="subtitle1" sx={{ fontWeight: 700, mt: 2, mb: 1 }}>{t("admin.group_predictions")}</Typography>
                    {groupMatches.length > 0 ? (
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>#</TableCell>
                              <TableCell>{t("matches.group")}</TableCell>
                              <TableCell>{t("matches.home")}</TableCell>
                              <TableCell align="center">—</TableCell>
                              <TableCell>{t("matches.away")}</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {groupMatches.map((m) => (
                              <TableRow key={m.match_id}>
                                <TableCell>{m.match_number}</TableCell>
                                <TableCell>{m.group}</TableCell>
                                <TableCell>{m.home_flag} {m.home_team}</TableCell>
                                <TableCell align="center">{m.home_goals ?? "-"} – {m.away_goals ?? "-"}</TableCell>
                                <TableCell>{m.away_flag} {m.away_team}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    ) : (
                      <Alert severity="info" sx={{ mb: 2 }}>{t("admin.no_predictions")}</Alert>
                    )}

                    {/* ── Knockout match predictions (non-group, non-bracket) ── */}
                    {knockoutMatches.length > 0 && (
                      <>
                        <Typography variant="subtitle1" sx={{ fontWeight: 700, mt: 3, mb: 1 }}>{t("admin.knockout_advancements")}</Typography>
                        <TableContainer>
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell>#</TableCell>
                                <TableCell>{t("matches.round")}</TableCell>
                                <TableCell>{t("matches.home")}</TableCell>
                                <TableCell align="center">—</TableCell>
                                <TableCell>{t("matches.away")}</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {knockoutMatches.map((m) => (
                                <TableRow key={m.match_id}>
                                  <TableCell>{m.match_number}</TableCell>
                                  <TableCell>{m.round}</TableCell>
                                  <TableCell>{m.home_flag} {m.home_team}</TableCell>
                                  <TableCell align="center">{m.home_goals ?? "-"} – {m.away_goals ?? "-"}</TableCell>
                                  <TableCell>{m.away_flag} {m.away_team}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      </>
                    )}

                    {/* ── Bracket predictions ── */}
                    <Typography variant="subtitle1" sx={{ fontWeight: 700, mt: 3, mb: 1 }}>{t("admin.bracket_predictions")}</Typography>
                    {user.bracket_predictions.length > 0 ? (
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>{t("matches.round")}</TableCell>
                              <TableCell>Team</TableCell>
                              <TableCell align="right">{t("admin.bracket_pts")}</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {user.bracket_predictions.map((b, i) => (
                              <TableRow key={i}>
                                <TableCell>{b.round}</TableCell>
                                <TableCell>{b.team_flag} {b.team_name}</TableCell>
                                <TableCell align="right">{b.points}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    ) : (
                      <Alert severity="info" sx={{ mb: 2 }}>{t("admin.no_predictions")}</Alert>
                    )}

                    {/* ── Tournament bonuses ── */}
                    <Typography variant="subtitle1" sx={{ fontWeight: 700, mt: 3, mb: 1 }}>{t("admin.tournament_bonuses")}</Typography>
                    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 1 }}>
                      <Typography variant="body2"><strong>{t("admin.winner")}:</strong> {bonuses?.winner_team_flag ?? ""} {bonuses?.winner_team_name || t("admin.none")}</Typography>
                      <Typography variant="body2"><strong>{t("admin.top_scorer")}:</strong> {bonuses?.top_scorer_name || t("admin.none")}</Typography>
                      <Typography variant="body2"><strong>{t("admin.bronze_winner")}:</strong> {bonuses?.bronze_winner_team_id ? bonuses.bronze_winner_team_name : t("admin.none")}</Typography>
                      <Typography variant="body2"><strong>{t("admin.most_goals_team")}:</strong> {bonuses?.most_goals_team_id ? bonuses.most_goals_team_name : t("admin.none")}</Typography>
                      <Typography variant="body2"><strong>{t("admin.most_conceded_team")}:</strong> {bonuses?.most_conceded_team_id ? bonuses.most_conceded_team_name : t("admin.none")}</Typography>
                      {bonuses?.custom_bonus_1 && <Typography variant="body2"><strong>{t("admin.custom_bonus_1")}:</strong> {bonuses.custom_bonus_1}</Typography>}
                      {bonuses?.custom_bonus_2 && <Typography variant="body2"><strong>{t("admin.custom_bonus_2")}:</strong> {bonuses.custom_bonus_2}</Typography>}
                    </Box>
                  </Box>
                );
              })()}
            </>
          ) : (
            <Alert severity="info">{t("admin.no_predictions")}</Alert>
          )}
        </Paper>
      )}

      {/* ═══ TAB 8: LEAGUE MANAGEMENT ═══ */}
      {tab === 8 && (
        <Paper elevation={2} sx={{ p: 3 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
            <Typography variant="h6">{t("admin.league_management")}</Typography>
            <Button variant="outlined" onClick={() => loadLeagues()} disabled={leaguesLoading}>
              {leaguesLoading ? <CircularProgress size={20} /> : t("common.refresh")}
            </Button>
          </Box>

          {leagues.length === 0 ? (
            <Alert severity="info">{t("admin.no_predictions")}</Alert>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>{t("admin.league_name")}</TableCell>
                    <TableCell>{t("admin.invite_code")}</TableCell>
                    <TableCell align="center">{t("admin.league_visibility")}</TableCell>
                    <TableCell align="center">{t("admin.league_members")}</TableCell>
                    <TableCell align="right">{t("common.actions")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {leagues.map((l) => (
                    <TableRow key={l.id}>
                      <TableCell>{l.id}</TableCell>
                      <TableCell>{l.name}</TableCell>
                      <TableCell>{l.invite_code}</TableCell>
                      <TableCell align="center">
                        {l.is_public ? t("admin.league_public") : t("admin.league_private")}
                      </TableCell>
                      <TableCell align="center">{l.member_count}</TableCell>
                      <TableCell align="right">
                        <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end" }}>
                          {editingLeague === l.id ? (
                            <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                              <TextField
                                size="small"
                                value={editLeagueForm.name}
                                onChange={(e) => setEditLeagueForm((f) => ({ ...f, name: e.target.value }))}/>
                              <FormControlLabel
                                control={<Switch
                                  size="small"
                                  checked={editLeagueForm.is_public}
                                  onChange={(e) => setEditLeagueForm((f) => ({ ...f, is_public: e.target.checked }))}/>
                                }
                                label={editLeagueForm.is_public ? t("admin.league_public") : t("admin.league_private")}
                              />
                              <Button size="small" variant="contained" onClick={handleSaveLeagueEdit}>Save</Button>
                              <Button size="small" onClick={() => setEditingLeague(null)}>Cancel</Button>
                            </Box>
                          ) : (
                            <>
                              <Button
                                size="small"
                                variant="outlined"
                                onClick={() => {
                                  setEditingLeague(l.id);
                                  setEditLeagueForm({ name: l.name, is_public: l.is_public });
                                }}
                              >
                                {t("admin.edit_league")}
                              </Button>
                              <Button
                                size="small"
                                variant="outlined"
                                color="error"
                                disabled={l.name === "VM2026"}
                                onClick={() => setDeleteConfirmLeagueId(l.id)}
                              >
                                {l.name === "VM2026" ? t("admin.default_league_protected") : t("admin.delete_league")}
                              </Button>
                            </>
                          )}
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          <Dialog
            open={deleteConfirmLeagueId !== null}
            onClose={() => setDeleteConfirmLeagueId(null)}
          >
            <DialogTitle>{t("common.confirm")}</DialogTitle>
            <DialogContent>
              <Typography>{t("admin.delete_league_confirm")}</Typography>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDeleteConfirmLeagueId(null)}>{t("common.cancel")}</Button>
              <Button color="error" onClick={handleDeleteLeague}>{t("common.delete")}</Button>
            </DialogActions>
          </Dialog>
        </Paper>
      )}

    </Container>
  );
}
