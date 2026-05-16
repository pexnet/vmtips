import { useTranslation } from "react-i18next";
import {
  Container,
  Typography,
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
  Divider,
  Avatar,
} from "@mui/material";
import PersonIcon from "@mui/icons-material/Person";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";
import { useAuth } from "../contexts/AuthContext";
import { usePersonalScore } from "../hooks/useLeaderboard";
import type { ScoreBreakdown, BracketDetail } from "../types/api";
import { useGlobalLeaderboard } from "../hooks/useLeaderboard";

/** Format a bracket round key into a human-readable label. */
function formatRound(round: string, t: (key: string) => string): string {
  const key = `matches.${round}`;
  const translated = t(key);
  // If i18n has no match, the key itself is returned — fall back to pretty-print
  if (translated === key) {
    return round
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }
  return translated;
}

export default function ProfilePage() {
  const { t } = useTranslation();
  const { user } = useAuth();

  const { data: personal, isLoading, error } = usePersonalScore();
  const { data: globalEntries } = useGlobalLeaderboard();

  // Derive the user's global rank from the global leaderboard
  const rank = globalEntries?.find(
    (entry) => entry.user_id === user?.id
  )?.rank;

  if (isLoading) {
    return (
      <Container sx={{ mt: 8, textAlign: "center" }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error) {
    return (
      <Container sx={{ mt: 4 }}>
        <Alert severity="error">{t("common.error")}</Alert>
      </Container>
    );
  }

  if (!personal) {
    return (
      <Container sx={{ mt: 4 }}>
        <Alert severity="info">{t("profile.login_required")}</Alert>
      </Container>
    );
  }

  const accuracy =
    personal.matches_scored > 0
      ? ((personal.perfect_predictions / personal.matches_scored) * 100).toFixed(1)
      : "0.0";

  return (
    <Container sx={{ mt: 4, mb: 8 }}>
      <Typography variant="h4" gutterBottom>
        {t("profile.title")}
      </Typography>

      {/* ── User info header ────────────────────────────────────── */}
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
          <Avatar sx={{ width: 56, height: 56 }}>
            <PersonIcon fontSize="large" />
          </Avatar>
          <Box>
            <Typography variant="h5">{personal.display_name}</Typography>
            {user?.email && (
              <Typography variant="body2" color="text.secondary">
                {user.email}
              </Typography>
            )}
          </Box>
        </Box>

        <Divider sx={{ my: 2 }} />

        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5 }}>
          <Chip
            icon={<EmojiEventsIcon />}
            label={`${t("profile.rank")}: ${rank ? `#${rank}` : "—"}`}
            color="primary"
            variant="outlined"
          />
          <Chip
            label={`${t("leaderboard.points")}: ${personal.total_points}`}
            color="primary"
          />
          <Chip
            label={`${t("profile.match_points")}: ${personal.match_points}`}
            variant="outlined"
          />
          <Chip
            label={`${t("profile.bracket_points")}: ${personal.bracket_points}`}
            variant="outlined"
          />
          <Chip
            label={`${t("leaderboard.predictions")}: ${personal.predictions_made}`}
          />
          <Chip
            label={`${t("leaderboard.perfect")}: ${personal.perfect_predictions}`}
            color="success"
          />
          <Chip
            label={`${t("profile.accuracy")}: ${accuracy}%`}
            variant="outlined"
          />
        </Box>
      </Paper>

      {/* ── Tournament bonus points ─────────────────────────────── */}
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          {t("profile.tournament_bonus_points")}
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5 }}>
          <Chip
            label={`${t("profile.tournament_bonus_points")}: ${personal.tournament_bonus_points ?? 0}`}
            color={personal.tournament_bonus_points && personal.tournament_bonus_points > 0 ? "success" : "default"}
          />
          {personal.tournament_bonus_details && (
            <>
              <Chip
                size="small"
                label={`${t("predictions.winner")} (20p): ${personal.tournament_bonus_details.winner_correct ? "✅" : "❌"}`}
                color={personal.tournament_bonus_details.winner_correct ? "success" : "default"}
                variant="outlined"
              />
              <Chip
                size="small"
                label={`${t("predictions.top_scorer")} (20p): ${personal.tournament_bonus_details.top_scorer_correct ? "✅" : "❌"}`}
                color={personal.tournament_bonus_details.top_scorer_correct ? "success" : "default"}
                variant="outlined"
              />
              <Chip
                size="small"
                label={`${t("predictions.bronze_winner")} (20p): ${personal.tournament_bonus_details.bronze_winner_correct ? "✅" : "❌"}`}
                color={personal.tournament_bonus_details.bronze_winner_correct ? "success" : "default"}
                variant="outlined"
              />
              <Chip
                size="small"
                label={`${t("predictions.most_goals_team")} (10p): ${personal.tournament_bonus_details.most_goals_team_correct ? "✅" : "❌"}`}
                color={personal.tournament_bonus_details.most_goals_team_correct ? "success" : "default"}
                variant="outlined"
              />
              <Chip
                size="small"
                label={`${t("predictions.most_conceded_team")}: ${personal.tournament_bonus_details.most_conceded_team_correct ? "✅" : "❌"}`}
                color={personal.tournament_bonus_details.most_conceded_team_correct ? "success" : "default"}
                variant="outlined"
              />
              <Chip
                size="small"
                label={`${t("predictions.custom_bonus_1")}: ${personal.tournament_bonus_details.custom_bonus_1_correct ? "✅" : "❌"}`}
                color={personal.tournament_bonus_details.custom_bonus_1_correct ? "success" : "default"}
                variant="outlined"
              />
              <Chip
                size="small"
                label={`${t("predictions.custom_bonus_2")}: ${personal.tournament_bonus_details.custom_bonus_2_correct ? "✅" : "❌"}`}
                color={personal.tournament_bonus_details.custom_bonus_2_correct ? "success" : "default"}
                variant="outlined"
              />
            </>
          )}
        </Box>
      </Paper>

      {/* ── Bracket points breakdown ─────────────────────────────── */}
      {personal.bracket_details && personal.bracket_details.length > 0 && (
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            {t("profile.bracket_points")}
          </Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("profile.team_id")}</TableCell>
                  <TableCell>{t("matches.round")}</TableCell>
                  <TableCell align="right">{t("leaderboard.match_points")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {personal.bracket_details.map(
                  (row: BracketDetail, i: number) => (
                    <TableRow key={i}>
                      <TableCell>#{row.team_id}</TableCell>
                      <TableCell>{formatRound(row.round, t)}</TableCell>
                      <TableCell align="right">
                        <Chip
                          size="small"
                          label={row.points}
                          color={row.points > 0 ? "success" : "default"}
                        />
                      </TableCell>
                    </TableRow>
                  )
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      {/* ── Match-by-match score breakdown ────────────────────────── */}
      <Paper elevation={2} sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          {t("profile.match_breakdown")}
        </Typography>

        {personal.breakdown && personal.breakdown.length > 0 ? (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("leaderboard.match")}</TableCell>
                  <TableCell>{t("matches.round")}</TableCell>
                  <TableCell align="center">
                    {t("leaderboard.predicted")}
                  </TableCell>
                  <TableCell align="center">
                    {t("leaderboard.actual")}
                  </TableCell>
                  <TableCell align="right">
                    {t("leaderboard.match_points")}
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {personal.breakdown.map(
                  (row: ScoreBreakdown, i: number) => (
                    <TableRow key={i}>
                      <TableCell>
                        {row.home_team} vs {row.away_team}
                      </TableCell>
                      <TableCell>
                        <Chip size="small" label={formatRound(row.round, t)} />
                      </TableCell>
                      <TableCell align="center">{row.predicted}</TableCell>
                      <TableCell align="center">{row.actual}</TableCell>
                      <TableCell align="right">
                        <Chip
                          size="small"
                          label={row.points}
                          color={row.perfect ? "success" : "default"}
                        />
                      </TableCell>
                    </TableRow>
                  )
                )}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Alert severity="info">{t("profile.no_breakdown")}</Alert>
        )}
      </Paper>
    </Container>
  );
}