import { useTranslation } from "react-i18next";
import {
  Box,
  Paper,
  Typography,
  Chip,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Divider,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import { useBracketView } from "../hooks/useBracketView";
import { useLeague } from "../contexts/LeagueContext";

function roundLabel(t: (k: string) => string, round: string) {
  const map: Record<string, string> = {
    round_of_32: "matches.round_of_32",
    round_of_16: "matches.round_of_16",
    quarter_final: "matches.quarter_final",
    semi_final: "matches.semi_final",
    match_for_third_place: "matches.match_for_third_place",
    final: "matches.final",
  };
  return t(map[round] || round);
}

export default function BracketViewTab() {
  const { t } = useTranslation();
  const { selectedLeagueId } = useLeague();
  const { data, isLoading, error } = useBracketView(selectedLeagueId ?? undefined);

  if (isLoading) {
    return (
      <Box sx={{ textAlign: "center", mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !data) {
    return (
      <Alert severity="info" sx={{ mt: 2 }}>
        {t("bracket.no_data")}
      </Alert>
    );
  }

  const { group_standings, third_places, knockout_matches } = data;

  return (
    <Box>
      {/* Group Standings */}
      <Typography variant="h6" gutterBottom>
        {t("bracket.predicted_standings")}
      </Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        {Object.entries(group_standings).sort(([a], [b]) => a.localeCompare(b)).map(([group, teams]) => (
          <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={group}>
            <Paper elevation={1} sx={{ p: 1.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                {t("matches.group")} {group}
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ width: 28, p: 0.5 }}>#</TableCell>
                    <TableCell sx={{ p: 0.5 }}>{t("matches.team")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {teams.map((tm, idx) => (
                    <TableRow key={tm.team_id} hover>
                      <TableCell
                        sx={{
                          fontWeight: 700,
                          p: 0.5,
                          color: idx < 2 ? "success.main" : idx === 2 ? "warning.main" : "text.secondary",
                        }}
                      >
                        {idx + 1}
                      </TableCell>
                      <TableCell sx={{ p: 0.5 }}>
                        {tm.flag_emoji} {tm.name}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {/* Third Places */}
      <Paper elevation={1} sx={{ p: 2, mb: 3 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
          {t("bracket.third_places")}
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
          {third_places.map((tp) => (
            <Chip
              key={tp.team_id}
              label={`${tp.rank}. ${tp.flag_emoji ?? ""} ${tp.name} (${tp.group})`}
              color={tp.rank <= 8 ? "success" : "default"}
              variant={tp.rank <= 8 ? "filled" : "outlined"}
              size="small"
            />
          ))}
        </Box>
      </Paper>

      <Divider sx={{ my: 3 }}>
        <Typography variant="body2" color="text.secondary">
          {t("bracket.knockout_matches")}
        </Typography>
      </Divider>

      {/* Knockout Matches */}
      {["round_of_32", "round_of_16", "quarter_final", "semi_final", "match_for_third_place", "final"].map((round) => {
        const matches = knockout_matches.filter((m) => m.round === round);
        if (matches.length === 0) return null;

        return (
          <Box key={round} sx={{ mb: 3 }}>
            <Typography
              variant="subtitle1"
              sx={{ mb: 1, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}
            >
              {roundLabel(t, round)}
            </Typography>

            <Grid container spacing={1.5}>
              {matches.map((m) => {
                const pred = m.predicted;
                const act = m.actual;
                const hasActualTeams = act.home_team_id !== null;
                const hasResult = act.status === "finished";

                return (
                  <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={m.match_number}>
                    <Paper
                      elevation={2}
                      sx={{
                        p: 1.5,
                        borderLeft: hasResult ? 4 : 0,
                        borderColor: hasResult ? "success.main" : "transparent",
                      }}
                    >
                      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          #{m.match_number}
                        </Typography>
                        {hasResult && (
                          <Chip size="small" label={t("matches.result")} color="success" />
                        )}
                      </Box>

                      {/* Predicted teams */}
                      <Box sx={{ mb: 0.5 }}>
                        <Typography variant="caption" color="primary" sx={{ fontWeight: 600 }}>
                          {t("bracket.predicted")}:
                        </Typography>
                      </Box>
                      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 28px", rowGap: 0.5, mb: 1 }}>
                        <Typography variant="body2">
                          {pred.home_team_flag ?? ""} {pred.home_team_name ?? "?"}
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 700, textAlign: "right" }}>
                          {pred.home_goals !== null ? pred.home_goals : "-"}
                        </Typography>
                        <Typography variant="body2">
                          {pred.away_team_flag ?? ""} {pred.away_team_name ?? "?"}
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 700, textAlign: "right" }}>
                          {pred.away_goals !== null ? pred.away_goals : "-"}
                        </Typography>
                      </Box>

                      {/* Actual teams */}
                      {hasActualTeams && (
                        <>
                          <Divider sx={{ my: 1 }}>
                            <Typography variant="caption" color="text.secondary">
                              {t("bracket.actual")}
                            </Typography>
                          </Divider>
                          {(() => {
                            const ahg = act.home_goals ?? 0;
                            const aag = act.away_goals ?? 0;
                            return (
                              <Box sx={{ display: "grid", gridTemplateColumns: "1fr 28px", rowGap: 0.5 }}>
                                <Typography variant="body2" sx={{ color: hasResult && ahg > aag ? "success.main" : "text.primary" }}>
                                  {act.home_team_flag ?? ""} {act.home_team_name ?? "?"}
                                </Typography>
                                <Typography variant="body2" sx={{ fontWeight: 700, textAlign: "right" }}>
                                  {act.home_goals !== null ? act.home_goals : "-"}
                                </Typography>
                                <Typography variant="body2" sx={{ color: hasResult && aag > ahg ? "success.main" : "text.primary" }}>
                                  {act.away_team_flag ?? ""} {act.away_team_name ?? "?"}
                                </Typography>
                                <Typography variant="body2" sx={{ fontWeight: 700, textAlign: "right" }}>
                                  {act.away_goals !== null ? act.away_goals : "-"}
                                </Typography>
                              </Box>
                            );
                          })()}
                        </>
                      )}
                    </Paper>
                  </Grid>
                );
              })}
            </Grid>
          </Box>
        );
      })}
    </Box>
  );
}
