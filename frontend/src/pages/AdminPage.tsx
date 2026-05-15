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
} from "@mui/material";
import { adminApi } from "../api/client";
import { useMatches } from "../hooks/useMatches";
import { useTeams } from "../hooks/useTeams";
import { queryClient } from "../contexts/QueryClientProvider";
import type { Match, Team } from "../types/api";
import { getErrorDetail } from "../types/api";

export default function AdminPage() {
  const { t } = useTranslation();
  const [selectedMatch, setSelectedMatch] = useState<Match | null>(null);
  const [homeGoals, setHomeGoals] = useState("");
  const [awayGoals, setAwayGoals] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  // Tournament result state
  const [tournamentResult, setTournamentResult] = useState<{
    winner_team_id: number | null;
    top_scorer_name: string;
    top_assist_name: string;
    total_goals: string;
  }>({
    winner_team_id: null,
    top_scorer_name: "",
    top_assist_name: "",
    total_goals: "",
  });
  const [tournamentLoading, setTournamentLoading] = useState(false);

  // Sync config state
  const [syncConfig, setSyncConfig] = useState<{
    source: string;
    auto_sync_enabled: boolean;
    auto_sync_interval_minutes: number;
  } | null>(null);
  const [syncConfigLoading, setSyncConfigLoading] = useState(false);

  const { data: matches = [] } = useMatches();
  const { data: teams = [] } = useTeams();

  // Fetch current tournament result + sync config on mount
  useEffect(() => {
    const fetchResult = async () => {
      try {
        const res = await adminApi.tournamentResult();
        const data = res.data as {
          winner_team_id: number | null;
          top_scorer_name: string | null;
          top_assist_name: string | null;
          total_goals: number | null;
        };
        setTournamentResult({
          winner_team_id: data.winner_team_id,
          top_scorer_name: data.top_scorer_name ?? "",
          top_assist_name: data.top_assist_name ?? "",
          total_goals: data.total_goals !== null ? String(data.total_goals) : "",
        });
      } catch {
        // Silently ignore — likely no result set yet
      }
    };
    const fetchSyncConfig = async () => {
      try {
        const res = await adminApi.syncConfig();
        setSyncConfig(res.data as { source: string; auto_sync_enabled: boolean; auto_sync_interval_minutes: number });
      } catch {
        // Silently ignore
      }
    };
    fetchResult();
    fetchSyncConfig();
  }, []);

  const handleSubmit = async () => {
    if (!selectedMatch) return;
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      await adminApi.setResult(selectedMatch.id, {
        home_goals: parseInt(homeGoals, 10),
        away_goals: parseInt(awayGoals, 10),
      });
      setSuccess(t("admin.result_updated"));
      setHomeGoals("");
      setAwayGoals("");
      setSelectedMatch(null);
      queryClient.invalidateQueries({ queryKey: ["matches"] });
    } catch (err: unknown) {
      setError(getErrorDetail(err) || t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setLoading(true);
    setError("");
    try {
      await adminApi.sync();
      setSuccess(t("admin.results_synced"));
      queryClient.invalidateQueries({ queryKey: ["matches"] });
    } catch (err: unknown) {
      setError(getErrorDetail(err) || t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  const handleRecalc = async () => {
    setLoading(true);
    setError("");
    try {
      await adminApi.recalc();
      setSuccess(t("admin.scores_recalculated"));
      queryClient.invalidateQueries({ queryKey: ["leaderboard"] });
    } catch (err: unknown) {
      setError(getErrorDetail(err) || t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  const handleSyncConfigSave = async () => {
    if (!syncConfig) return;
    setSyncConfigLoading(true);
    setError("");
    setSuccess("");
    try {
      await adminApi.updateSyncConfig({
        source: syncConfig.source,
        auto_sync_enabled: syncConfig.auto_sync_enabled,
        auto_sync_interval_minutes: syncConfig.auto_sync_interval_minutes,
      });
      setSuccess(t("admin.sync_config_saved"));
    } catch (err: unknown) {
      setError(getErrorDetail(err) || t("common.error"));
    } finally {
      setSyncConfigLoading(false);
    }
  };

  const handleTournamentResultSave = async () => {
    setTournamentLoading(true);
    setError("");
    setSuccess("");
    try {
      await adminApi.setTournamentResult({
        winner_team_id: tournamentResult.winner_team_id ?? undefined,
        top_scorer_name: tournamentResult.top_scorer_name || undefined,
        top_assist_name: tournamentResult.top_assist_name || undefined,
        total_goals: tournamentResult.total_goals !== "" ? parseInt(tournamentResult.total_goals, 10) : undefined,
      });
      setSuccess(t("admin.result_updated"));
    } catch (err: unknown) {
      setError(getErrorDetail(err) || t("common.error"));
    } finally {
      setTournamentLoading(false);
    }
  };

  const selectedWinner = teams.find((t) => t.id === tournamentResult.winner_team_id) ?? null;

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        {t("admin.title")}
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}

      {/* ── Match result entry ─────────────────────────────────────── */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          {t("admin.enter_result")}
        </Typography>
        <Autocomplete
          options={matches}
          getOptionLabel={(m) =>
            `#${m.match_number} ${m.home_team?.flag_emoji ?? ""} ${m.home_team?.name ?? ""} vs ${m.away_team?.flag_emoji ?? ""} ${m.away_team?.name ?? ""}`
          }
          value={selectedMatch}
          onChange={(_, value) => setSelectedMatch(value)}
          renderInput={(params) => (
            <TextField {...params} label={t("admin.select_match")} fullWidth margin="normal" />
          )}
        />
        {selectedMatch && selectedMatch.home_team && selectedMatch.away_team && (
          <Box sx={{ display: "flex", gap: 2, mt: 2, flexWrap: "wrap", alignItems: "flex-end" }}>
            <TextField
              label={`${selectedMatch.home_team.name} ${t("admin.goals")}`}
              type="text"
              value={homeGoals}
              onChange={(e) => {
                const val = e.target.value;
                if (val === "" || (/^\d*$/.test(val) && Number(val) <= 30)) setHomeGoals(val);
              }}
              sx={{ width: 160 }}
            />
            <TextField
              label={`${selectedMatch.away_team.name} ${t("admin.goals")}`}
              type="text"
              value={awayGoals}
              onChange={(e) => {
                const val = e.target.value;
                if (val === "" || (/^\d*$/.test(val) && Number(val) <= 30)) setAwayGoals(val);
              }}
              sx={{ width: 160 }}
            />
            <Button
              variant="contained"
              onClick={handleSubmit}
              disabled={loading || homeGoals === "" || awayGoals === ""}
            >
              {loading ? <CircularProgress size={24} /> : t("admin.save_result")}
            </Button>
          </Box>
        )}
      </Paper>

      {/* ── Tournament results ────────────────────────────────────── */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          {t("admin.tournament_result")}
        </Typography>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, maxWidth: 480 }}>
          <Autocomplete
            options={teams}
            getOptionLabel={(team: Team) => `${team.flag_emoji ?? ""} ${team.name}`}
            value={selectedWinner}
            onChange={(_, value) =>
              setTournamentResult((prev) => ({ ...prev, winner_team_id: value?.id ?? null }))
            }
            renderInput={(params) => (
              <TextField {...params} label={t("admin.winner")} fullWidth />
            )}
          />
          <TextField
            label={t("admin.top_scorer")}
            value={tournamentResult.top_scorer_name}
            onChange={(e) =>
              setTournamentResult((prev) => ({ ...prev, top_scorer_name: e.target.value }))
            }
            fullWidth
          />
          <TextField
            label={t("admin.top_assist")}
            value={tournamentResult.top_assist_name}
            onChange={(e) =>
              setTournamentResult((prev) => ({ ...prev, top_assist_name: e.target.value }))
            }
            fullWidth
          />
          <TextField
            label={t("admin.total_goals")}
            type="text"
            value={tournamentResult.total_goals}
            onChange={(e) => {
              const val = e.target.value;
              if (val === "" || /^\d*$/.test(val)) {
                setTournamentResult((prev) => ({ ...prev, total_goals: val }));
              }
            }}
            fullWidth
          />
          <Box>
            <Button
              variant="contained"
              onClick={handleTournamentResultSave}
              disabled={tournamentLoading}
            >
              {tournamentLoading ? <CircularProgress size={24} /> : t("admin.update_result")}
            </Button>
          </Box>
        </Box>
      </Paper>

      {/* ── Score management ────────────────────────────────────── */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          {t("admin.score_management")}
        </Typography>
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          <Button variant="outlined" onClick={handleSync} disabled={loading}>
            {t("admin.sync_results")}
          </Button>
          <Button variant="outlined" onClick={handleRecalc} disabled={loading}>
            {t("admin.recalculate_scores")}
          </Button>
        </Box>
      </Paper>

      {/* ── Sync configuration ────────────────────────────────────── */}
      {syncConfig && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            {t("admin.sync_config")}
          </Typography>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2, maxWidth: 480 }}>
            <Autocomplete
              options={["worldcupjson", "openfootball"]}
              value={syncConfig.source}
              onChange={(_, value) =>
                setSyncConfig((prev) => (prev ? { ...prev, source: value ?? "worldcupjson" } : prev))
              }
              renderInput={(params) => (
                <TextField {...params} label={t("admin.sync_source")} fullWidth />
              )}
            />
            <Autocomplete
              options={[
                { label: t("admin.auto_sync_off"), value: false },
                { label: t("admin.auto_sync_on"), value: true },
              ]}
              getOptionLabel={(o) => o.label}
              value={
                syncConfig.auto_sync_enabled
                  ? { label: t("admin.auto_sync_on"), value: true }
                  : { label: t("admin.auto_sync_off"), value: false }
              }
              onChange={(_, value) =>
                setSyncConfig((prev) =>
                  prev ? { ...prev, auto_sync_enabled: value?.value ?? false } : prev
                )
              }
              renderInput={(params) => (
                <TextField {...params} label={t("admin.auto_sync")} fullWidth />
              )}
            />
            <TextField
              label={t("admin.sync_interval")}
              type="text"
              value={String(syncConfig.auto_sync_interval_minutes)}
              onChange={(e) => {
                const val = e.target.value;
                if (val === "" || /^\d*$/.test(val)) {
                  setSyncConfig((prev) =>
                    prev ? { ...prev, auto_sync_interval_minutes: parseInt(val, 10) || 1 } : prev
                  );
                }
              }}
              fullWidth
            />
            <Box>
              <Button
                variant="contained"
                onClick={handleSyncConfigSave}
                disabled={syncConfigLoading}
              >
                {syncConfigLoading ? <CircularProgress size={24} /> : t("admin.save_sync_config")}
              </Button>
            </Box>
          </Box>
        </Paper>
      )}
    </Container>
  );
}
