import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Paper, Box, Typography, TextField, Button, CircularProgress, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from "@mui/material";
import { adminApi } from "../../api/client";
import type { Match } from "../../types/api";
import { getErrorDetail } from "../../types/api";
type Notify = (kind: "error" | "success", message: string) => void;

export default function MatchResultsTab({
  matches,
  notify,
  queryClient,
}: {
  matches: Match[];
  notify: Notify;
  queryClient: import("@tanstack/react-query").QueryClient;
}) {
  const { t } = useTranslation();
  const [resultDrafts, setResultDrafts] = useState<Record<number, { home: string; away: string }>>(
    () => Object.fromEntries(matches.map((m) => [m.id, { home: m.home_goals === null ? "" : String(m.home_goals), away: m.away_goals === null ? "" : String(m.away_goals) }])),
  );
  const [savingMatchId, setSavingMatchId] = useState<number | null>(null);

  // Seed drafts for any matches that didn't have an entry yet
  useEffect(() => {
    setResultDrafts((prev) => {
      const next = { ...prev };
      matches.forEach((match) => {
        if (next[match.id]) return;
        next[match.id] = {
          home: match.home_goals === null ? "" : String(match.home_goals),
          away: match.away_goals === null ? "" : String(match.away_goals),
        };
      });
      return next;
    });
  }, [matches]);

  function handleResultDraftChange(matchId: number, side: "home" | "away", value: string) {
    if (value !== "" && !/^\d+$/.test(value)) return;
    setResultDrafts((prev) => ({
      ...prev,
      [matchId]: {
        home: prev[matchId]?.home ?? "",
        away: prev[matchId]?.away ?? "",
        [side]: value,
      },
    }));
  }

  function handleSaveResult(match: Match) {
    const draft = resultDrafts[match.id];
    if (!draft || draft.home === "" || draft.away === "") return;
    setSavingMatchId(match.id);
    adminApi.setResult(match.id, { home_goals: Number(draft.home), away_goals: Number(draft.away) })
      .then(async () => {
        notify("success", t("admin.result_updated"));
        queryClient.invalidateQueries({ queryKey: ["matches"] });
        if (match.round === "group") {
          await adminApi.computeStandings();
        }
      })
      .catch((err: unknown) => notify("error", getErrorDetail(err)))
      .finally(() => setSavingMatchId(null));
  }

  const orderedMatches = [...matches].sort((a, b) => a.match_number - b.match_number);

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>{t("admin.enter_result")}</Typography>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>#</TableCell>
              <TableCell>{t("matches.round")}</TableCell>
              <TableCell>{t("matches.home")}</TableCell>
              <TableCell align="center">{t("admin.enter_result")}</TableCell>
              <TableCell>{t("matches.away")}</TableCell>
              <TableCell align="center">Status</TableCell>
              <TableCell align="right">{t("common.actions")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {orderedMatches.map((match) => {
              const draft = resultDrafts[match.id] ?? { home: "", away: "" };
              const homeName = match.home_team?.name ?? match.home_team_placeholder ?? "?";
              const awayName = match.away_team?.name ?? match.away_team_placeholder ?? "?";
              const canSave = draft.home !== "" && draft.away !== "";

              return (
                <TableRow key={match.id} hover>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>{match.match_number}</TableCell>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>
                    {match.round === "group" ? `${t("matches.group")} ${match.group ?? ""}` : t(`matches.${match.round}`)}
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                      <Typography component="span">{match.home_team?.flag_emoji ?? ""}</Typography>
                      <Typography variant="body2">{homeName}</Typography>
                    </Box>
                  </TableCell>
                  <TableCell align="center">
                    <Box sx={{ display: "inline-flex", alignItems: "center", gap: 1 }}>
                      <TextField
                        size="small"
                        value={draft.home}
                        onChange={(e) => handleResultDraftChange(match.id, "home", e.target.value)}
                        sx={{ width: 58, "& input": { textAlign: "center" } }}
                        slotProps={{ input: { inputMode: "numeric" } }}
                      />
                      <Typography color="text.secondary">-</Typography>
                      <TextField
                        size="small"
                        value={draft.away}
                        onChange={(e) => handleResultDraftChange(match.id, "away", e.target.value)}
                        sx={{ width: 58, "& input": { textAlign: "center" } }}
                        slotProps={{ input: { inputMode: "numeric" } }}
                      />
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                      <Typography component="span">{match.away_team?.flag_emoji ?? ""}</Typography>
                      <Typography variant="body2">{awayName}</Typography>
                    </Box>
                  </TableCell>
                  <TableCell align="center">{match.status}</TableCell>
                  <TableCell align="right">
                    <Button
                      size="small"
                      variant="contained"
                      onClick={() => handleSaveResult(match)}
                      disabled={!canSave || savingMatchId === match.id}
                    >
                      {savingMatchId === match.id ? <CircularProgress size={18} /> : t("admin.save_result")}
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
}
