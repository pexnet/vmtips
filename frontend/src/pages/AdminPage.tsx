import { useState } from "react";
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
import { queryClient } from "../contexts/QueryClientProvider";
import type { Match } from "../types/api";
import { getErrorDetail } from "../types/api";

export default function AdminPage() {
  const { t } = useTranslation();
  const [selectedMatch, setSelectedMatch] = useState<Match | null>(null);
  const [homeGoals, setHomeGoals] = useState("");
  const [awayGoals, setAwayGoals] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const { data: matches = [] } = useMatches();

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
      // Invalidate matches cache so data stays fresh
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
          <Box sx={{ display: "flex", gap: 2, mt: 2 }}>
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

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          {t("admin.score_management")}
        </Typography>
        <Box sx={{ display: "flex", gap: 2 }}>
          <Button variant="outlined" onClick={handleSync} disabled={loading}>
            {t("admin.sync_results")}
          </Button>
          <Button variant="outlined" onClick={handleRecalc} disabled={loading}>
            {t("admin.recalculate_scores")}
          </Button>
        </Box>
      </Paper>
    </Container>
  );
}