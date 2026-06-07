import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Paper, Box, Typography, Button, TextField, CircularProgress, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Autocomplete, Select, MenuItem, FormControl } from "@mui/material";
import { adminApi } from "../../api/client";
import type { Match, Team } from "../../types/api";
import { getErrorDetail } from "../../types/api";
type Notify = (kind: "error" | "success", message: string) => void;

export default function KnockoutAdvancementsTab({
  matches,
  notify,
  queryClient,
}: {
  matches: Match[];
  notify: Notify;
  queryClient: import("@tanstack/react-query").QueryClient;
}) {
  const { t } = useTranslation();
  const [advancements, setAdvancements] = useState<{ id: number; team_id: number; team_name: string; team_code: string; round: string; match_number: number | null }[]>([]);
  const [advancementLoading, setAdvancementLoading] = useState(false);
  const [advancementDrafts, setAdvancementDrafts] = useState<Record<number, { team_id: number | null; round: string }>>(
    () => Object.fromEntries(matches.map((m) => [m.id, { team_id: null, round: nextAdvancementRound(m.round) }])),
  );
  const [resolving, setResolving] = useState(false);

  useEffect(() => {
    adminApi.getAdvancements().then((res) => {
      const payload = res.data as { advancements?: typeof advancements };
      setAdvancements(payload.advancements ?? []);
    }).catch(() => setAdvancements([]));
  }, []);

  function handleAdvancementDraftChange(matchId: number, teamId: number | null, round: string) {
    setAdvancementDrafts((prev) => ({ ...prev, [matchId]: { team_id: teamId, round } }));
  }

  function handleSetAdvancement(match: Match) {
    const draft = advancementDrafts[match.id];
    if (!draft?.team_id) return;
    setAdvancementLoading(true);
    adminApi.setAdvancement({
      team_id: draft.team_id,
      round: draft.round,
      match_number: match.match_number,
    })
      .then(() => { notify("success", t("admin.advancement_set")); adminApi.getAdvancements().then((res) => {
        const payload = res.data as { advancements?: typeof advancements };
        setAdvancements(payload.advancements ?? []);
      }); })
      .catch((err: unknown) => notify("error", getErrorDetail(err)))
      .finally(() => setAdvancementLoading(false));
  }

  function handleResolveKnockout() {
    setResolving(true);
    adminApi.resolveKnockoutTeams()
      .then(() => { notify("success", t("admin.knockout_resolved")); queryClient.invalidateQueries({ queryKey: ["matches"] }); })
      .catch((err: unknown) => notify("error", getErrorDetail(err)))
      .finally(() => setResolving(false));
  }

  const knockoutMatches = [...matches].filter((m) => m.round !== "group").sort((a, b) => a.match_number - b.match_number);

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 2, mb: 2 }}>
        <Typography variant="h6">{t("admin.knockout_advancements")}</Typography>
        <Button variant="outlined" onClick={handleResolveKnockout} disabled={resolving}>
          {resolving ? <CircularProgress size={20} /> : t("admin.resolve_knockout")}
        </Button>
      </Box>
      <TableContainer sx={{ mb: 3 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>#</TableCell>
              <TableCell>{t("matches.round")}</TableCell>
              <TableCell>{t("matches.home")}</TableCell>
              <TableCell>{t("matches.away")}</TableCell>
              <TableCell sx={{ minWidth: 220 }}>Advanced team</TableCell>
              <TableCell sx={{ minWidth: 180 }}>Advances to</TableCell>
              <TableCell align="right">{t("common.actions")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {knockoutMatches.map((match) => {
              const homeName = match.home_team?.name ?? match.home_team_placeholder ?? "?";
              const awayName = match.away_team?.name ?? match.away_team_placeholder ?? "?";
              const teamOptions = [match.home_team, match.away_team].filter((team): team is Team => Boolean(team));
              const defaultRound = nextAdvancementRound(match.round);
              const draft = advancementDrafts[match.id] ?? { team_id: null, round: defaultRound };
              const selectedTeam = teamOptions.find((team) => team.id === draft.team_id) ?? null;

              return (
                <TableRow key={match.id} hover>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>{match.match_number}</TableCell>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>{t(`matches.${match.round}`)}</TableCell>
                  <TableCell>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                      <Typography component="span">{match.home_team?.flag_emoji ?? ""}</Typography>
                      <Typography variant="body2">{homeName}</Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                      <Typography component="span">{match.away_team?.flag_emoji ?? ""}</Typography>
                      <Typography variant="body2">{awayName}</Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Autocomplete
                      size="small"
                      options={teamOptions}
                      getOptionLabel={(o) => `${o.flag_emoji ?? ""} ${o.name}`}
                      value={selectedTeam}
                      onChange={(_, value) => handleAdvancementDraftChange(match.id, value?.id ?? null, draft.round)}
                      renderInput={(params) => <TextField {...params} placeholder="Select team" />}
                    />
                  </TableCell>
                  <TableCell>
                    <FormControl size="small" fullWidth>
                      <Select
                        value={draft.round}
                        onChange={(e) => handleAdvancementDraftChange(match.id, draft.team_id, e.target.value)}
                      >
                        <MenuItem value="round_of_16">Round of 16</MenuItem>
                        <MenuItem value="quarter_final">Quarter-final</MenuItem>
                        <MenuItem value="semi_final">Semi-final</MenuItem>
                        <MenuItem value="final">Final</MenuItem>
                        <MenuItem value="match_for_third_place">3rd Place</MenuItem>
                        <MenuItem value="world_champion">World Champion</MenuItem>
                      </Select>
                    </FormControl>
                  </TableCell>
                  <TableCell align="right">
                    <Button
                      size="small"
                      variant="contained"
                      onClick={() => handleSetAdvancement(match)}
                      disabled={!draft.team_id || advancementLoading}
                    >
                      {advancementLoading ? <CircularProgress size={18} /> : t("admin.set_advancement")}
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
      {advancements.length > 0 && (
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>Saved advancements</Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Team</TableCell>
                  <TableCell>Round</TableCell>
                  <TableCell>Match #</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {advancements.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell>{a.team_code} {a.team_name}</TableCell>
                    <TableCell>{a.round}</TableCell>
                    <TableCell>{a.match_number ?? "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}
    </Paper>
  );
}

function nextAdvancementRound(round: string) {
  const map: Record<string, string> = {
    round_of_32: "round_of_16",
    round_of_16: "quarter_final",
    quarter_final: "semi_final",
    semi_final: "final",
    final: "world_champion",
    match_for_third_place: "match_for_third_place",
  };
  return map[round] ?? round;
}
