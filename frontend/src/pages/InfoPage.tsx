import { Container, Typography, Paper, Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip, Divider } from "@mui/material";
import { useTranslation } from "react-i18next";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";
import SportsSoccerIcon from "@mui/icons-material/SportsSoccer";
import MilitaryTechIcon from "@mui/icons-material/MilitaryTech";
import CalculateIcon from "@mui/icons-material/Calculate";
import BarChartIcon from "@mui/icons-material/BarChart";
import { BRACKET_ROUND_POINTS } from "../hooks/useBracket";

export default function InfoPage() {
  const { t } = useTranslation();

  const matchRows = [
    { label: t("info.match.outcome"), points: 3 },
    { label: t("info.match.home_goals"), points: 2 },
    { label: t("info.match.away_goals"), points: 2 },
    { label: t("info.match.max"), points: 7, bold: true },
  ];

  const bracketRows = [
    { round: t("info.bracket.r32"), points: BRACKET_ROUND_POINTS.round_of_32 },
    { round: t("info.bracket.r16"), points: BRACKET_ROUND_POINTS.round_of_16 },
    { round: t("info.bracket.qf"), points: BRACKET_ROUND_POINTS.quarter_final },
    { round: t("info.bracket.sf"), points: BRACKET_ROUND_POINTS.semi_final },
    { round: t("info.bracket.third"), points: BRACKET_ROUND_POINTS.match_for_third_place },
    { round: t("info.bracket.final"), points: BRACKET_ROUND_POINTS.final },
    { round: t("info.bracket.champion"), points: BRACKET_ROUND_POINTS.world_champion, bold: true },
  ];

  const bonusRows = [
    { label: t("info.bonus.champion"), points: 20 },
    { label: t("info.bonus.runner_up"), points: 20 },
    { label: t("info.bonus.bronze_winner"), points: 20 },
    { label: t("info.bonus.top_scorer"), points: 20 },
  ];

  const bracketSlots = {
    round_of_32: 32,
    round_of_16: 16,
    quarter_final: 8,
    semi_final: 4,
    match_for_third_place: 2,
    final: 2,
    world_champion: 1,
  };
  const totalBracketPts = Object.entries(bracketSlots)
    .reduce((sum, [key, slots]) => sum + slots * BRACKET_ROUND_POINTS[key as keyof typeof BRACKET_ROUND_POINTS], 0);
  const totalBonusPts = 20 + 20 + 20 + 10 + 10 + 10 + 10; // = 100
  const totalMatchPts = 104 * 7; // 72 group + 32 knockout
  const grandTotal = totalMatchPts + totalBracketPts + totalBonusPts;

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 700 }}>
        {t("info.title")}
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        {t("info.intro")}
      </Typography>

      {/* ── Phase explanation ─────────────────────────── */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
          <SportsSoccerIcon color="primary" />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {t("info.phases_title")}
          </Typography>
        </Box>
        <Typography variant="body2" sx={{ mb: 1 }}>
          {t("info.phase1_desc")}
        </Typography>
        <Typography variant="body2">
          {t("info.phase2_desc")}
        </Typography>
      </Paper>

      {/* ── Match scoring ─────────────────────────────── */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
          <CalculateIcon color="primary" />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {t("info.match_title")}
          </Typography>
        </Box>
        <Typography variant="body2" sx={{ mb: 2 }}>
          {t("info.match_desc")}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {t("info.match_detail")}
        </Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>{t("info.column_rule")}</TableCell>
                <TableCell align="right" sx={{ fontWeight: 600 }}>{t("info.column_points")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {matchRows.map((row) => (
                <TableRow key={row.label}>
                  <TableCell>
                    {row.bold ? <strong>{row.label}</strong> : row.label}
                  </TableCell>
                  <TableCell align="right">
                    <Chip
                      label={row.points}
                      size="small"
                      color={row.bold ? "primary" : "default"}
                      variant={row.bold ? "filled" : "outlined"}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* ── Knockout bracket scoring ──────────────────── */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
          <MilitaryTechIcon color="primary" />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {t("info.bracket_title")}
          </Typography>
        </Box>
        <Typography variant="body2" sx={{ mb: 2 }}>
          {t("info.bracket_desc")}
        </Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>{t("info.column_round")}</TableCell>
                <TableCell align="right" sx={{ fontWeight: 600 }}>{t("info.column_points")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {bracketRows.map((row) => (
                <TableRow key={row.round}>
                  <TableCell>
                    {row.bold ? <strong>{row.round}</strong> : row.round}
                  </TableCell>
                  <TableCell align="right">
                    <Chip
                      label={row.points}
                      size="small"
                      color={row.bold ? "primary" : "default"}
                      variant={row.bold ? "filled" : "outlined"}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {t("info.bracket_per_team_note")}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {t("info.knockout_match_note")}
        </Typography>
      </Paper>

      {/* ── Bonus question scoring ────────────────────── */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
          <EmojiEventsIcon color="primary" />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {t("info.bonus_title")}
          </Typography>
        </Box>
        <Typography variant="body2" sx={{ mb: 2 }}>
          {t("info.bonus_desc")}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {t("info.bonus_matching_note")}
        </Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>{t("info.column_question")}</TableCell>
                <TableCell align="right" sx={{ fontWeight: 600 }}>{t("info.column_points")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {bonusRows.map((row) => (
                <TableRow key={row.label}>
                  <TableCell>{row.label}</TableCell>
                  <TableCell align="right">
                    <Chip
                      label={row.points}
                      size="small"
                      color={row.points >= 20 ? "primary" : "default"}
                      variant={row.points >= 20 ? "filled" : "outlined"}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* ── Total points overview ─────────────────────── */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
          <BarChartIcon color="primary" />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {t("info.total_title")}
          </Typography>
        </Box>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>{t("info.column_round")}</TableCell>
                <TableCell align="right" sx={{ fontWeight: 600 }}>{t("info.column_points")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>{t("info.total_match_results")}</TableCell>
                <TableCell align="right"><Chip label={totalMatchPts} size="small" variant="outlined" /></TableCell>
              </TableRow>
              <TableRow>
                <TableCell>{t("info.total_bracket")}</TableCell>
                <TableCell align="right"><Chip label={totalBracketPts} size="small" variant="outlined" /></TableCell>
              </TableRow>
              <TableRow>
                <TableCell>{t("info.total_bonuses")}</TableCell>
                <TableCell align="right"><Chip label={totalBonusPts} size="small" variant="outlined" /></TableCell>
              </TableRow>
              <TableRow>
                <TableCell><strong>{t("info.grand_total")}</strong></TableCell>
                <TableCell align="right"><Chip label={grandTotal} size="small" color="primary" /></TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      <Divider sx={{ my: 3 }} />

      <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center" }}>
        {t("info.phase_lock_note")}
      </Typography>
    </Container>
  );
}
