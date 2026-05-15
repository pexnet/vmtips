import { useState } from "react";
import { useTranslation } from "react-i18next";
import Grid from "@mui/material/Grid";
import {
  Container,
  Typography,
  Tabs,
  Tab,
  Box,
  Paper,
  TextField,
  Button,
  Autocomplete,
  Chip,
  Alert,
  CircularProgress,
} from "@mui/material";
import { predictionsApi } from "../api/client";
import { usePredictions, useTournamentBonuses, useTeamsFromMatches } from "../hooks/usePredictions";
import type { Team } from "../types/api";

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

export default function PredictionsPage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState(0);
  const [bonuses, setBonuses] = useState({
    winner_team_id: null as number | null,
    top_scorer_name: "",
    top_assist_name: "",
    total_goals: "",
  });
  const [saveMsg, setSaveMsg] = useState("");
  const [localError, setLocalError] = useState("");

  const { data: rawPredictions = [], isLoading: predictionsLoading, error: predictionsError } = usePredictions();
  const predictions = rawPredictions as unknown as PredictionWithMatch[];
  const { data: teams = [] } = useTeamsFromMatches();
  const { data: bonusesData } = useTournamentBonuses();

  // Populate bonuses form when tournament bonuses are loaded
  if (bonusesData && !bonuses.top_scorer_name && !bonuses.top_assist_name && !bonuses.total_goals && bonuses.winner_team_id === null) {
    const b = bonusesData;
    setBonuses({
      winner_team_id: b.winner_team_id || null,
      top_scorer_name: b.top_scorer_name || "",
      top_assist_name: b.top_assist_name || "",
      total_goals: b.total_goals ? String(b.total_goals) : "",
    });
  }

  const saveBonuses = () => {
    setSaveMsg("");
    predictionsApi
      .saveTournament({
        winner_team_id: bonuses.winner_team_id || undefined,
        top_scorer_name: bonuses.top_scorer_name || undefined,
        top_assist_name: bonuses.top_assist_name || undefined,
        total_goals: bonuses.total_goals ? Number(bonuses.total_goals) : undefined,
      })
      .then(() => setSaveMsg(t("predictions.save_success")))
      .catch(() => setLocalError(t("common.error")));
  };

  const selectedTeam = teams.find((tm: Team) => tm.id === bonuses.winner_team_id) || null;

  const error = localError || (predictionsError ? t("common.error") : "");

  if (predictionsLoading) {
    return (
      <Container sx={{ mt: 8, textAlign: "center" }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 4, mb: 8 }}>
      <Typography variant="h4" gutterBottom>{t("predictions.title")}</Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {saveMsg && <Alert severity="success" sx={{ mb: 2 }}>{saveMsg}</Alert>}

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label={t("predictions.title")} />
        <Tab label={t("predictions.tournament_bonuses")} />
      </Tabs>

      {tab === 0 && (
        <Box>
          {predictions.length === 0 ? (
            <Alert severity="info">{t("predictions.no_predictions")}</Alert>
          ) : (
            predictions.map((p: PredictionWithMatch) => (
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

      {tab === 1 && (
        <Paper elevation={2} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>{t("predictions.tournament_bonuses")}</Typography>

          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <Autocomplete
              options={teams}
              getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
              value={selectedTeam}
              onChange={(_, v) => setBonuses((b) => ({ ...b, winner_team_id: v?.id || null }))}
              renderInput={(params) => (
                <TextField {...params} label={t("predictions.winner")} />
              )}
            />

            <TextField
              label={t("predictions.top_scorer")}
              value={bonuses.top_scorer_name}
              onChange={(e) => setBonuses((b) => ({ ...b, top_scorer_name: e.target.value }))}
              fullWidth
            />

            <TextField
              label={t("predictions.top_assist")}
              value={bonuses.top_assist_name}
              onChange={(e) => setBonuses((b) => ({ ...b, top_assist_name: e.target.value }))}
              fullWidth
            />

            <TextField
              label={t("predictions.total_goals")}
              type="text"
              value={bonuses.total_goals}
              onChange={(e) => {
                const val = e.target.value;
                if (val === "" || (/^\d*$/.test(val) && Number(val) <= 999)) setBonuses((b) => ({ ...b, total_goals: val }));
              }}
              fullWidth
            />

            <Button variant="contained" onClick={saveBonuses}>
              {t("common.save")}
            </Button>
          </Box>
        </Paper>
      )}
    </Container>
  );
}