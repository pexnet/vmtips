import { useEffect, useState } from "react";

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
  useMediaQuery,
  useTheme,
} from "@mui/material";

import {
  usePersonalScore,
  useLeagueLeaderboard,
  useMatchdays,
} from "../hooks/useLeaderboard";
import { useLeagues } from "../hooks/useLeagues";
import { useAuth } from "../contexts/AuthContext";
import { useLeague } from "../contexts/LeagueContext";
import UserAvatar from "../components/UserAvatar";
import NextMatchdaySection from "../components/NextMatchdaySection";
import PreviousMatchesSection from "../components/PreviousMatchesSection";
import type { LeaderboardEntry, ScoreBreakdown, League } from "../types/api";

function LeagueLeaderboardSection() {
  const { t } = useTranslation();
  const { data: leagues = [] } = useLeagues();
  const { selectedLeagueId, setSelectedLeagueId } = useLeague();
  const { data: leagueData, isLoading } = useLeagueLeaderboard(selectedLeagueId);
  const { data: matchdaysData, isLoading: matchdaysLoading } = useMatchdays(
    selectedLeagueId,
    5,
    !!selectedLeagueId
  );

  useEffect(() => {
    if (!selectedLeagueId && leagues.length > 0) {
      setSelectedLeagueId(leagues[0].id);
    }
  }, [leagues, selectedLeagueId, setSelectedLeagueId]);

  const memberOrder = leagueData?.leaderboard.map((e) => e.display_name) ?? [];

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
          {matchdaysLoading ? (
            <CircularProgress sx={{ mt: 2 }} />
          ) : matchdaysData ? (
            <Box sx={{ mt: 2 }}>
              <NextMatchdaySection
                upcoming={matchdaysData.upcoming}
                memberOrder={memberOrder}
              />
              <PreviousMatchesSection
                past={matchdaysData.past}
                memberOrder={memberOrder}
              />
            </Box>
          ) : null}
        </Box>
      ) : null}
    </Box>
  );
}

function LeaderTable({ data }: { data: LeaderboardEntry[] }) {
  const { t } = useTranslation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

  if (isMobile) {
    return (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 1.25 }}>
        {data.map((row) => (
          <Paper
            key={row.rank}
            variant="outlined"
            sx={{
              p: 1.5,
              borderRadius: 2,
              display: "grid",
              gridTemplateColumns: "auto 1fr auto",
              gap: 1.25,
              alignItems: "center",
            }}
          >
            <Typography variant="h6" component="div" sx={{ fontWeight: 800, minWidth: 42 }}>
              #{row.rank}
            </Typography>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 0 }}>
              <UserAvatar
                displayName={row.display_name}
                firstName={row.first_name}
                lastName={row.last_name}
                avatarUrl={row.avatar_url}
                sx={{ width: 40, height: 40, fontSize: "0.85rem", flexShrink: 0 }}
              />
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="body1" sx={{ fontWeight: 700 }} noWrap>
                  {row.display_name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {row.predictions_made} {t("leaderboard.predictions_short")} · {row.perfect_predictions} {t("leaderboard.perfect_short")}
                </Typography>
              </Box>
            </Box>
            <Box sx={{ textAlign: "right" }}>
              <Typography variant="h6" sx={{ fontWeight: 900, lineHeight: 1 }}>
                {row.total_points}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("leaderboard.points")}
              </Typography>
              {row.bracket_points > 0 && (
                <Typography variant="caption" sx={{ display: "block", color: "primary.light", fontWeight: 700 }}>
                  +{row.bracket_points} {t("leaderboard.bracket")}
                </Typography>
              )}
            </Box>
          </Paper>
        ))}
        {data.length === 0 && (
          <Alert severity="info">{t("leaderboard.no_data")}</Alert>
        )}
      </Box>
    );
  }

  return (
    <TableContainer component={Paper}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>{t("leaderboard.rank")}</TableCell>
            <TableCell>{t("leaderboard.player")}</TableCell>
            <TableCell align="right">{t("leaderboard.points")}</TableCell>
            <TableCell align="right">{t("leaderboard.bracket")}</TableCell>
            <TableCell align="right">{t("leaderboard.predictions")}</TableCell>
            <TableCell align="right">{t("leaderboard.perfect")}</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data.map((row) => (
            <TableRow key={row.rank}>
              <TableCell><strong>#{row.rank}</strong></TableCell>
              <TableCell>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <UserAvatar
                    displayName={row.display_name}
                    firstName={row.first_name}
                    lastName={row.last_name}
                    avatarUrl={row.avatar_url}
                    sx={{ width: 30, height: 30, fontSize: "0.75rem" }}
                  />
                  {row.display_name}
                </Box>
              </TableCell>
              <TableCell align="right"><strong>{row.total_points}</strong></TableCell>
              <TableCell align="right">{row.bracket_points > 0 ? <Chip size="small" label={row.bracket_points} color="primary" variant="outlined" /> : 0}</TableCell>
              <TableCell align="right">{row.predictions_made}</TableCell>
              <TableCell align="right"><Chip size="small" label={row.perfect_predictions} color="success" /></TableCell>
            </TableRow>
          ))}
          {data.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} align="center">{t("leaderboard.no_data")}</TableCell>
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
  const { isLoggedIn } = useAuth();
  const { selectedLeagueId } = useLeague();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

  // Only fetch personal score when the profile tab is active — avoids
  // an unnecessary API call on initial page load.
  const { data: personal, isLoading: personalLoading } = usePersonalScore(
    isLoggedIn && tab === 1,
    selectedLeagueId
  );

  if (personalLoading && tab === 1) {
    return (
      <Container sx={{ mt: 8, textAlign: "center" }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container sx={{ mt: { xs: 2, sm: 4 }, mb: 8, px: { xs: 2, sm: 3 } }}>
      <Typography
        variant="h4"
        gutterBottom
        sx={{ fontSize: { xs: "2rem", sm: "2.125rem" }, fontWeight: 800 }}
      >
        {t("leaderboard.title")}
      </Typography>

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ mb: 2 }}
        variant={isMobile ? "fullWidth" : "standard"}
      >
        <Tab label={t("leaderboard.league")} />
        <Tab label={t("nav.profile")} />
      </Tabs>

      {tab === 0 && (
        <LeagueLeaderboardSection />
      )}

      {tab === 1 && personal && (
        <Box>
          <Paper elevation={2} sx={{ p: 3, mb: 2 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
              <UserAvatar
                displayName={personal.display_name}
                firstName={personal.first_name}
                lastName={personal.last_name}
                avatarUrl={personal.avatar_url}
                sx={{ width: 42, height: 42 }}
              />
              <Typography variant="h6">{personal.display_name}</Typography>
            </Box>
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
