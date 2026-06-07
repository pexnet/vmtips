import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Paper, Box, Typography, TextField, Alert, CircularProgress, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Autocomplete } from "@mui/material";
import { adminApi } from "../../api/client";
type AllPredictionsResponse = {
  users: {
    user_id: number;
    display_name: string;
    match_predictions: {
      match_id: number; match_number: number; group: string; round: string;
      home_team: string; home_flag: string; away_team: string; away_flag: string;
      home_goals: number | null; away_goals: number | null;
    }[];
    bracket_predictions: {
      team_id: number; team_name: string; team_flag: string; round: string; points: number;
    }[];
    tournament_bonuses: {
      winner_team_id: number | null; winner_team_name: string | null; winner_team_flag: string | null;
      top_scorer_name: string | null;
      bronze_winner_team_id: number | null; bronze_winner_team_name: string | null;
      most_goals_team_id: number | null; most_goals_team_name: string | null;
      most_conceded_team_id: number | null; most_conceded_team_name: string | null;
      custom_bonus_1: string | null; custom_bonus_2: string | null;
    } | null;
  }[];
};

export default function AllPredictionsTab() {
  const { t } = useTranslation();
  const [allPredictions, setAllPredictions] = useState<AllPredictionsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedPredUserId, setSelectedPredUserId] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    adminApi.allPredictions()
      .then((res) => {
        const payload = res.data as AllPredictionsResponse;
        if (payload.users) {
          setAllPredictions(payload);
          setSelectedPredUserId((current) => current ?? payload.users[0]?.user_id ?? null);
        } else {
          setAllPredictions(null);
        }
      })
      .catch(() => setAllPredictions(null))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>{t("admin.all_predictions")}</Typography>
      {loading ? (
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
  );
}
