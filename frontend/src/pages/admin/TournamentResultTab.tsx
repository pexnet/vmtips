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
    runner_up_team_id: null as number | null,
    bronze_winner_team_id: null as number | null,
    top_scorer_name: "",
  });
  const [tournamentLoading, setTournamentLoading] = useState(false);

  useEffect(() => {
    adminApi.tournamentResult().then((res) => {
      const d = res.data as Record<string, unknown>;
      setTournamentResult({
        winner_team_id: (d.winner_team_id as number) || null,
        runner_up_team_id: (d.runner_up_team_id as number) || null,
        bronze_winner_team_id: (d.bronze_winner_team_id as number) || null,
        top_scorer_name: (d.top_scorer_name as string) || "",
      });
    }).catch(() => { /* no result yet */ });
  }, []);

  function handleSaveTournamentResult() {
    setTournamentLoading(true);
    adminApi.setTournamentResult({
      winner_team_id: tournamentResult.winner_team_id || undefined,
      runner_up_team_id: tournamentResult.runner_up_team_id || undefined,
      bronze_winner_team_id: tournamentResult.bronze_winner_team_id || undefined,
      top_scorer_name: tournamentResult.top_scorer_name || undefined,
    })
      .then(() => notify("success", t("admin.result_updated")))
      .catch((err: unknown) => notify("error", getErrorDetail(err)))
      .finally(() => setTournamentLoading(false));
  }

  const selectedWinnerTeam = teams.find((tm: Team) => tm.id === tournamentResult.winner_team_id) || null;
  const selectedRunnerUpTeam = teams.find((tm: Team) => tm.id === tournamentResult.runner_up_team_id) || null;
  const selectedBronzeWinner = teams.find((tm: Team) => tm.id === tournamentResult.bronze_winner_team_id) || null;

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>{t("admin.tournament_result")}</Typography>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        <Autocomplete options={teams} getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
          value={selectedWinnerTeam} onChange={(_, v) => setTournamentResult((r) => ({ ...r, winner_team_id: v?.id || null }))}
          renderInput={(params) => <TextField {...params} label={`${t("admin.winner")} (20p)`} />} />
        <Autocomplete options={teams} getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
          value={selectedRunnerUpTeam} onChange={(_, v) => setTournamentResult((r) => ({ ...r, runner_up_team_id: v?.id || null }))}
          renderInput={(params) => <TextField {...params} label={`${t("admin.runner_up")} (20p)`} />} />
        <Autocomplete options={teams} getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
          value={selectedBronzeWinner} onChange={(_, v) => setTournamentResult((r) => ({ ...r, bronze_winner_team_id: v?.id || null }))}
          renderInput={(params) => <TextField {...params} label={`${t("admin.third_place")} (20p)`} />} />
        <TextField label={`${t("admin.top_scorer")} (20p)`} value={tournamentResult.top_scorer_name}
          onChange={(e) => setTournamentResult((r) => ({ ...r, top_scorer_name: e.target.value }))} fullWidth />
        <Button variant="contained" onClick={handleSaveTournamentResult} disabled={tournamentLoading}>
          {tournamentLoading ? <CircularProgress size={20} /> : t("admin.update_result")}
        </Button>
      </Box>
    </Paper>
  );
}
