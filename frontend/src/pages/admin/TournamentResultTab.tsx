import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Paper, Box, Typography, TextField, Button, CircularProgress, Autocomplete } from "@mui/material";
import { adminApi } from "../../api/client";
import type { Team } from "../../types/api";
import { getErrorDetail } from "../../types/api";
type Notify = (kind: "error" | "success", message: string) => void;

export default function TournamentResultTab({ teams, notify }: { teams: Team[]; notify: Notify }) {
  const { t } = useTranslation();
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

  useEffect(() => {
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
  }, []);

  function handleSaveTournamentResult() {
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
      .then(() => notify("success", t("admin.result_updated")))
      .catch((err: unknown) => notify("error", getErrorDetail(err)))
      .finally(() => setTournamentLoading(false));
  }

  const selectedWinnerTeam = teams.find((tm: Team) => tm.id === tournamentResult.winner_team_id) || null;
  const selectedBronzeWinner = teams.find((tm: Team) => tm.id === tournamentResult.bronze_winner_team_id) || null;
  const selectedMostGoals = teams.find((tm: Team) => tm.id === tournamentResult.most_goals_team_id) || null;
  const selectedMostConceded = teams.find((tm: Team) => tm.id === tournamentResult.most_conceded_team_id) || null;

  return (
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
  );
}
