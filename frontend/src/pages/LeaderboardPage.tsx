import { useState } from "react";

import { useTranslation } from "react-i18next";
import {
  Container,
  Typography,
  Tabs,
  Tab,
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  CircularProgress,
  Chip,
} from "@mui/material";

import { useGlobalLeaderboard, usePersonalScore, useLeagueLeaderboard } from "../hooks/useLeaderboard";
import { useLeagues } from "../hooks/useLeagues";
import type { LeaderboardEntry, ScoreBreakdown, League } from "../types/api";

function LeagueLeaderboardSection() {
  const { t } = useTranslation();
  const { data: leagues = [] } = useLeagues();
  const [selectedLeagueId, setSelectedLeagueId] = useState<number | null>(null);
  const { data: leagueData, isLoading } = useLeagueLeaderboard(selectedLeagueId);

  return (
    <Box>
      <Box sx={{ display: "flex", gap: 2, mb: 2, flexWrap: "wrap" }}>
        {leagues.map((l: League) => (
          <Chip
            key={l.id}
            label={l.name}
            onClick={() => setSelectedLeagueId(l.id)}
            color={selectedLeagueId === l.id ? "primary" : "default"}
            clickable
          />
        ))}
        {leagues.length === 0 && (
          <Alert severity="info">{t("leagues.no_leagues")}</Alert>
        )}
      </Box>
      {selectedLeagueId && isLoading ? (
        <CircularProgress />
      ) : selectedLeagueId && leagueData && leagueData.leaderboard ? (
        <Box>
          <Typography variant="h6" gutterBottom>{leagueData.league_name}</Typography>
          <LeaderTable data={leagueData.leaderboard} />
        </Box>
      ) : null}
    </Box>
  );
}

function LeaderTable({ data }: { data: LeaderboardEntry[] }) {
  const { t } = useTranslation();
  return (
    <TableContainer component={Paper}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>{t("leaderboard.rank")}</TableCell>
            <TableCell>{t("leaderboard.player")}</TableCell>
            <TableCell align="right">{t("leaderboard.points")}</TableCell>
            <TableCell align="right">{t("leaderboard.predictions")}</TableCell>
            <TableCell align="right">{t("leaderboard.perfect")}</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data.map((row) => (
            <TableRow key={row.rank}>
              <TableCell><strong>#{row.rank}</strong></TableCell>
              <TableCell>{row.display_name}</TableCell>
              <TableCell align="right"><strong>{row.total_points}</strong></TableCell>
              <TableCell align="right">{row.predictions_made}</TableCell>
              <TableCell align="right"><Chip size="small" label={row.perfect_predictions} color="success" /></TableCell>
            </TableRow>
          ))}
          {data.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} align="center">{t("leaderboard.no_data")}</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

export default function LeaderboardPage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState(0);

  const { data: global = [], isLoading: globalLoading, error: globalError } = useGlobalLeaderboard();
  const { data: personal } = usePersonalScore();

  if (globalLoading) {
    return (
      <Container sx={{ mt: 8, textAlign: "center" }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 4, mb: 8 }}>
      <Typography variant="h4" gutterBottom>{t("leaderboard.title")}</Typography>
      {globalError && <Alert severity="error" sx={{ mb: 2 }}>{t("common.error")}</Alert>}

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label={t("leaderboard.global")} />
        <Tab label={t("leaderboard.league")} />
        <Tab label={t("nav.profile")} />
      </Tabs>

      {tab === 0 && <LeaderTable data={global} />}

      {tab === 1 && (
        <LeagueLeaderboardSection />
      )}

      {tab === 2 && personal && (
        <Box>
          <Paper elevation={2} sx={{ p: 3, mb: 2 }}>
            <Typography variant="h6">{personal.display_name}</Typography>
            <Box sx={{ display: "flex", gap: 2, mt: 1 }}>
              <Chip label={`${t("leaderboard.points")}: ${personal.total_points}`} color="primary" />
              <Chip label={`${t("leaderboard.predictions")}: ${personal.predictions_made}`} />
            </Box>
          </Paper>

          {personal.breakdown?.length > 0 && (
            <TableContainer component={Paper}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{t("leaderboard.match")}</TableCell>
                    <TableCell align="center">{t("leaderboard.predicted")}</TableCell>
                    <TableCell align="center">{t("leaderboard.actual")}</TableCell>
                    <TableCell align="right">{t("leaderboard.match_points")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {personal.breakdown.map((row: ScoreBreakdown, i: number) => (
                    <TableRow key={i}>
                      <TableCell>{row.home_team} vs {row.away_team}</TableCell>
                      <TableCell align="center">{row.predicted}</TableCell>
                      <TableCell align="center">{row.actual}</TableCell>
                      <TableCell align="right"><Chip
                        size="small"
                        label={row.points}
                        color={row.perfect ? "success" : "default"}
                      /></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Box>
      )}
    </Container>
  );
}