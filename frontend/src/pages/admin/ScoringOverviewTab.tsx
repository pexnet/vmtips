import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Paper, Box, Typography, Button, Alert, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from "@mui/material";
import { adminApi } from "../../api/client";
import type { ScoringOverviewEntry } from "../../types/api";
export default function ScoringOverviewTab() {
  const { t } = useTranslation();
  const [scoringOverview, setScoringOverview] = useState<ScoringOverviewEntry[]>([]);

  function loadScoringOverview() {
    adminApi.scoringOverview().then((res) => {
      const payload = res.data as { scores?: ScoringOverviewEntry[] };
      setScoringOverview(payload.scores ?? []);
    }).catch(() => setScoringOverview([]));
  }

  useEffect(() => { loadScoringOverview(); }, []);

  return (
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
  );
}
