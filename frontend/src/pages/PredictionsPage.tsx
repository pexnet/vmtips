import { useEffect, useState } from "react";
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
import { predictionsApi, matchesApi } from "../api/client";

interface Prediction {
  match_id: number;
  home_goals: number;
  away_goals: number;
  match: {
    match_number: number;
    round: string;
    group?: string;
    home_team: { name: string; flag: string };
    away_team: { name: string; flag: string };
  };
}

interface Team {
  id: number;
  name: string;
  flag: string;
}

export default function PredictionsPage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState(0);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [bonuses, setBonuses] = useState({
    winner_team_id: null as number | null,
    top_scorer_name: "",
    top_assist_name: "",
    total_goals: "",
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saveMsg, setSaveMsg] = useState("");

  useEffect(() => {
    Promise.all([
      predictionsApi
        .list()
        .then((res) => setPredictions(res.data))
        .catch(() => setError(t("common.error"))),
      matchesApi
        .list()
        .then((res) => {
          // Extract unique teams from matches
          const seen = new Set();
          const allTeams: Team[] = [];
          res.data.forEach((m: any) => {
            if (m.home_team?.id && !seen.has(m.home_team.id)) {
              seen.add(m.home_team.id);
              allTeams.push(m.home_team);
            }
            if (m.away_team?.id && !seen.has(m.away_team.id)) {
              seen.add(m.away_team.id);
              allTeams.push(m.away_team);
            }
          });
          setTeams(allTeams.sort((a, b) => a.name.localeCompare(b.name)));
        })
        .catch(() => {}),
      predictionsApi
        .tournament()
        .then((res) => {
          if (res.data) {
            setBonuses({
              winner_team_id: res.data.winner_team_id || null,
              top_scorer_name: res.data.top_scorer_name || "",
              top_assist_name: res.data.top_assist_name || "",
              total_goals: res.data.total_goals ? String(res.data.total_goals) : "",
            });
          }
        })
        .catch(() => {}),
    ]).finally(() => setLoading(false));
  }, [t]);

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
      .catch(() => setError(t("common.error")));
  };

  const selectedTeam = teams.find((t) => t.id === bonuses.winner_team_id) || null;

  if (loading) {
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
            <Alert severity="info">{`Inga tips sparade annu. Ga till "Matcher" for att tippa!`}</Alert>
          ) : (
            predictions.map((p) => (
              <Paper key={p.match_id} elevation={2} sx={{ p: 2, mb: 2 }}>
                <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    {p.match.group ? `${p.match.group} · ` : ""}
                    {p.match.match_number}
                  </Typography>
                  <Chip size="small" label={p.match.round} />
                </Box>
                <Grid container sx={{ alignItems: 'center' }} spacing={2}>
                  <Grid size={{ xs: 4 }}><Typography align="right">{p.match.home_team.flag} {p.match.home_team.name}</Typography></Grid>
                  <Grid size={{ xs: 4 }}><Typography align="center" variant="h6">{p.home_goals} - {p.away_goals}</Typography></Grid>
                  <Grid size={{ xs: 4 }}><Typography>{p.match.away_team.name} {p.match.away_team.flag}</Typography></Grid>
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
              getOptionLabel={(o) => `${o.flag} ${o.name}`}
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
              type="number"
              value={bonuses.total_goals}
              onChange={(e) => setBonuses((b) => ({ ...b, total_goals: e.target.value }))}
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
