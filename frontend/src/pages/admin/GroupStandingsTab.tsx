import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Paper, Box, Typography, Button, Alert, CircularProgress, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from "@mui/material";
import { adminApi } from "../../api/client";
import type { GroupStanding } from "../../types/api";
import { getErrorDetail } from "../../types/api";
type Notify = (kind: "error" | "success", message: string) => void;

export default function GroupStandingsTab({ notify, reloadKey = 0 }: { notify: Notify; reloadKey?: number }) {
  const { t } = useTranslation();
  const [standings, setStandings] = useState<GroupStanding[]>([]);
  const [standingsLoading, setStandingsLoading] = useState(false);

  function loadStandings() {
    adminApi.getStandings().then((res) => {
      const payload = res.data as { standings?: GroupStanding[] };
      setStandings(payload.standings ?? []);
    }).catch(() => setStandings([]));
  }

  useEffect(() => { loadStandings(); }, [reloadKey]);

  function handleComputeStandings() {
    setStandingsLoading(true);
    adminApi.computeStandings()
      .then(() => { notify("success", t("admin.standings_computed")); loadStandings(); })
      .catch((err: unknown) => notify("error", getErrorDetail(err)))
      .finally(() => setStandingsLoading(false));
  }

  const groupLetters = [...new Set(standings.map((s) => s.group))].sort();

  return (
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
  );
}
