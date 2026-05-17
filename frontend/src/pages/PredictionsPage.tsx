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
import { useLeague } from "../contexts/LeagueContext";
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
  const { selectedLeagueId } = useLeague();
  const [tab, setTab] = useState(0);
  const [bonuses, setBonuses] = useState({
    winner_team_id: null as number | null,
    top_scorer_name: "",
    bronze_winner_team_id: null as number | null,
    most_goals_team_id: null as number | null,
    most_conceded_team_id: null as number | null,
    custom_bonus_1: "",
    custom_bonus_2: "",
  });
  const [saveMsg, setSaveMsg] = useState("");
  const [localError, setLocalError] = useState("");

  const { data: rawPredictions = [], isLoading: predictionsLoading, error: predictionsError } = usePredictions(selectedLeagueId ?? undefined);
  const predictions = rawPredictions as unknown as PredictionWithMatch[];
  const { data: teams = [] } = useTeamsFromMatches();
  const { data: bonusesData } = useTournamentBonuses(selectedLeagueId ?? undefined);

  // Populate bonuses form when tournament bonuses are loaded
  if (bonusesData && !bonuses.top_scorer_name && bonuses.winner_team_id === null && bonuses.bronze_winner_team_id === null) {
    const b = bonusesData;
    setBonuses({
      winner_team_id: b.winner_team_id || null,
      top_scorer_name: b.top_scorer_name || "",
      bronze_winner_team_id: b.bronze_winner_team_id || null,
      most_goals_team_id: b.most_goals_team_id || null,
      most_conceded_team_id: b.most_conceded_team_id || null,
      custom_bonus_1: b.custom_bonus_1 || "",
      custom_bonus_2: b.custom_bonus_2 || "",
    });
  }

  const saveBonuses = () => {
    setSaveMsg("");
    setLocalError("");
    if (!selectedLeagueId) {
      setLocalError(t("predictions.no_league_selected"));
      return;
    }
    predictionsApi
      .saveTournament(selectedLeagueId, {
        winner_team_id: bonuses.winner_team_id || undefined,
        top_scorer_name: bonuses.top_scorer_name || undefined,
        bronze_winner_team_id: bonuses.bronze_winner_team_id || undefined,
        most_goals_team_id: bonuses.most_goals_team_id || undefined,
        most_conceded_team_id: bonuses.most_conceded_team_id || undefined,
        custom_bonus_1: bonuses.custom_bonus_1 || undefined,
        custom_bonus_2: bonuses.custom_bonus_2 || undefined,
      })
      .then(() => setSaveMsg(t("predictions.save_success")))
      .catch(() => setLocalError(t("common.error")));
  };

  const selectedTeam = teams.find((tm: Team) => tm.id === bonuses.winner_team_id) || null;
  const selectedBronzeWinner = teams.find((tm: Team) => tm.id === bonuses.bronze_winner_team_id) || null;
  const selectedMostGoals = teams.find((tm: Team) => tm.id === bonuses.most_goals_team_id) || null;
  const selectedMostConceded = teams.find((tm: Team) => tm.id === bonuses.most_conceded_team_id) || null;

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

            <Autocomplete
              options={teams}
              getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
              value={selectedBronzeWinner}
              onChange={(_, v) => setBonuses((b) => ({ ...b, bronze_winner_team_id: v?.id || null }))}
              renderInput={(params) => (
                <TextField {...params} label={`${t("predictions.bronze_winner")} (20p)`} />
              )}
            />

            <Autocomplete
              options={teams}
              getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
              value={selectedMostGoals}
              onChange={(_, v) => setBonuses((b) => ({ ...b, most_goals_team_id: v?.id || null }))}
              renderInput={(params) => (
                <TextField {...params} label={`${t("predictions.most_goals_team")} (10p)`} />
              )}
            />

            <Autocomplete
              options={teams}
              getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
              value={selectedMostConceded}
              onChange={(_, v) => setBonuses((b) => ({ ...b, most_conceded_team_id: v?.id || null }))}
              renderInput={(params) => (
                <TextField {...params} label={`${t("predictions.most_conceded_team")} (10p)`} />
              )}
            />

            <TextField
              label={`${t("predictions.custom_bonus_1")} (10p)`}
              value={bonuses.custom_bonus_1}
              onChange={(e) => setBonuses((b) => ({ ...b, custom_bonus_1: e.target.value }))}
              fullWidth
            />

            <TextField
              label={`${t("predictions.custom_bonus_2")} (10p)`}
              value={bonuses.custom_bonus_2}
              onChange={(e) => setBonuses((b) => ({ ...b, custom_bonus_2: e.target.value }))}
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