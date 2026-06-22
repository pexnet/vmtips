import { useMemo, memo } from "react";
import { useTranslation } from "react-i18next";
import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Box,
  Chip,
  Tooltip,
  Divider,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import type { MatchdayGroup, MatchdayPredictionEntry } from "../types/api";

interface MatchdayGridProps {
  matchday: MatchdayGroup;
  memberOrder?: string[];
}

function formatKickoff(kickoff: string) {
  return new Date(kickoff).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

function MatchdayGridBase({ matchday, memberOrder }: MatchdayGridProps) {
  const { t } = useTranslation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

  // Gather unique member display names across all matches in this day
  const members = useMemo(() => {
    if (memberOrder?.length) return memberOrder;
    const memberSet = new Set<string>();
    matchday.matches.forEach((m) =>
      m.predictions.forEach((p) => memberSet.add(p.display_name))
    );
    return Array.from(memberSet);
  }, [matchday.matches, memberOrder]);

  // Pre-build prediction lookup maps per match — avoids rebuilding
  // a new Map on every render of each row.
  const predMapsByMatch = useMemo(() => {
    const maps = new Map<number, Map<string, MatchdayPredictionEntry>>();
    for (const m of matchday.matches) {
      maps.set(m.id, new Map(m.predictions.map((p) => [p.display_name, p])));
    }
    return maps;
  }, [matchday.matches]);

  if (isMobile) {
    return (
      <Box sx={{ mb: 2 }}>
        <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
          {t("leaderboard.matchday_header", { date: matchday.date })} ·{" "}
          {matchday.matches.length === 1
            ? t("leaderboard.match_count", { count: matchday.matches.length })
            : t("leaderboard.match_count_plural", { count: matchday.matches.length })}
        </Typography>

        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.25 }}>
          {matchday.matches.map((m) => {
            const predMap = predMapsByMatch.get(m.id)!;
            return (
              <Paper key={m.id} variant="outlined" sx={{ p: 1.5, borderRadius: 2 }}>
                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 1 }}>
                  <Box sx={{ minWidth: 0 }}>
                    <Typography variant="body1" sx={{ fontWeight: 800 }}>
                      {m.home_team.flag_emoji} {m.home_team.code} vs {m.away_team.code} {m.away_team.flag_emoji}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {formatKickoff(m.kickoff)}
                    </Typography>
                  </Box>
                  {m.actual && <Chip size="small" label={m.actual} color="success" />}
                </Box>

                <Divider sx={{ my: 1.25 }} />

                <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
                  {members.map((name) => {
                    const p = predMap.get(name);
                    const showPoints = p?.points !== undefined;
                    return (
                      <Box
                        key={name}
                        sx={{
                          display: "grid",
                          gridTemplateColumns: showPoints ? "1fr auto auto" : "1fr auto",
                          gap: 1,
                          alignItems: "center",
                        }}
                      >
                        <Typography variant="body2" noWrap sx={{ minWidth: 0 }}>
                          {name}
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: p ? 700 : 400 }}>
                          {p?.predicted ?? "—"}
                        </Typography>
                        {showPoints && (
                          <Chip
                            size="small"
                            label={t("leaderboard.points_short", { points: p.points })}
                            color={p.points === 7 ? "success" : "default"}
                            sx={{ height: 22 }}
                          />
                        )}
                      </Box>
                    );
                  })}
                </Box>
              </Paper>
            );
          })}
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ mb: 2 }}>
      <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
        {t("leaderboard.matchday_header", { date: matchday.date })} ·{" "}
        {matchday.matches.length === 1
          ? t("leaderboard.match_count", { count: matchday.matches.length })
          : t("leaderboard.match_count_plural", { count: matchday.matches.length })}
      </Typography>
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t("leaderboard.match")}</TableCell>
              {members.map((name) => (
                <TableCell key={name} align="center" sx={{ minWidth: 80 }}>
                  {name}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {matchday.matches.map((m) => {
              const predMap = predMapsByMatch.get(m.id)!;
              return (
                <TableRow key={m.id}>
                  <TableCell>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, flexWrap: "wrap" }}>
                      <span>{m.home_team.flag_emoji}</span>
                      <span>{m.home_team.code}</span>
                      <span>vs</span>
                      <span>{m.away_team.code}</span>
                      <span>{m.away_team.flag_emoji}</span>
                      {m.actual && (
                        <Chip size="small" label={m.actual} color="success" sx={{ ml: 0.5 }} />
                      )}
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {formatKickoff(m.kickoff)}
                    </Typography>
                  </TableCell>
                  {members.map((name) => {
                    const p = predMap.get(name);
                    if (!p) {
                      return (
                        <TableCell key={name} align="center">
                          {t("leaderboard.no_prediction")}
                        </TableCell>
                      );
                    }
                    const showPoints = p.points !== undefined;
                    return (
                      <TableCell key={name} align="center">
                        <Tooltip
                          title={
                            showPoints
                              ? t("leaderboard.points_short", { points: p.points })
                              : p.predicted
                          }
                        >
                          <Box>
                            <Typography
                              variant="body2"
                              sx={{ fontWeight: showPoints ? 700 : 400 }}
                            >
                              {p.predicted}
                            </Typography>
                            {showPoints && (
                              <Typography variant="caption" color="text.secondary">
                                {t("leaderboard.points_short", { points: p.points })}
                              </Typography>
                            )}
                          </Box>
                        </Tooltip>
                      </TableCell>
                    );
                  })}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

const MatchdayGrid = memo(MatchdayGridBase);
export default MatchdayGrid;
