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
} from "@mui/material";
import type { MatchdayGroup } from "../../types/api";

interface MatchdayGridProps {
  matchday: MatchdayGroup;
  memberOrder?: string[];
}

export default function MatchdayGrid({ matchday, memberOrder }: MatchdayGridProps) {
  const { t } = useTranslation();

  // Gather unique member display names across all matches in this day
  const memberSet = new Set<string>();
  matchday.matches.forEach((m) =>
    m.predictions.forEach((p) => memberSet.add(p.display_name))
  );
  const members = memberOrder ?? Array.from(memberSet);

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
              const predMap = new Map(
                m.predictions.map((p) => [p.display_name, p])
              );
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
                      {new Date(m.kickoff).toLocaleTimeString(undefined, {
                        hour: "2-digit",
                        minute: "2-digit",
                        timeZoneName: "short",
                      })}
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
