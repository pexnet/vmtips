import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Paper, Box, Typography, TextField, Button, Alert, CircularProgress, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Switch, FormControlLabel, Dialog, DialogActions, DialogContent, DialogTitle } from "@mui/material";
import { adminApi } from "../../api/client";
import { getErrorDetail } from "../../types/api";
type Notify = (kind: "error" | "success", message: string) => void;

type AdminLeague = {
  id: number;
  name: string;
  invite_code: string;
  is_public: boolean;
  admin_user_id: number;
  member_count: number;
  created_at: string;
};

export default function LeagueManagementTab({ notify }: { notify: Notify }) {
  const { t } = useTranslation();
  const [leagues, setLeagues] = useState<AdminLeague[]>([]);
  const [leaguesLoading, setLeaguesLoading] = useState(false);
  const [editingLeague, setEditingLeague] = useState<number | null>(null);
  const [editLeagueForm, setEditLeagueForm] = useState({ name: "", is_public: false });
  const [deleteConfirmLeagueId, setDeleteConfirmLeagueId] = useState<number | null>(null);

  function loadLeagues() {
    setLeaguesLoading(true);
    adminApi.listLeagues()
      .then((res) => { setLeagues(res.data as AdminLeague[]); })
      .catch((err: unknown) => notify("error", getErrorDetail(err)))
      .finally(() => setLeaguesLoading(false));
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadLeagues(); }, []);

  function handleSaveLeagueEdit() {
    if (editingLeague === null) return;
    adminApi.updateLeague(editingLeague, {
      name: editLeagueForm.name,
      is_public: editLeagueForm.is_public,
    })
      .then(() => {
        notify("success", t("common.saved"));
        setEditingLeague(null);
        loadLeagues();
      })
      .catch((err: unknown) => notify("error", getErrorDetail(err)));
  }

  function handleDeleteLeague() {
    if (deleteConfirmLeagueId === null) return;
    adminApi.deleteLeague(deleteConfirmLeagueId)
      .then(() => {
        notify("success", t("common.success"));
        setDeleteConfirmLeagueId(null);
        loadLeagues();
      })
      .catch((err: unknown) => notify("error", getErrorDetail(err)));
  }

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h6">{t("admin.league_management")}</Typography>
        <Button variant="outlined" onClick={() => loadLeagues()} disabled={leaguesLoading}>
          {leaguesLoading ? <CircularProgress size={20} /> : t("common.refresh")}
        </Button>
      </Box>

      {leagues.length === 0 ? (
        <Alert severity="info">{t("admin.no_predictions")}</Alert>
      ) : (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>{t("admin.league_name")}</TableCell>
                <TableCell>{t("admin.invite_code")}</TableCell>
                <TableCell align="center">{t("admin.league_visibility")}</TableCell>
                <TableCell align="center">{t("admin.league_members")}</TableCell>
                <TableCell align="right">{t("common.actions")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {leagues.map((l) => (
                <TableRow key={l.id}>
                  <TableCell>{l.id}</TableCell>
                  <TableCell>{l.name}</TableCell>
                  <TableCell>{l.invite_code}</TableCell>
                  <TableCell align="center">
                    {l.is_public ? t("admin.league_public") : t("admin.league_private")}
                  </TableCell>
                  <TableCell align="center">{l.member_count}</TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end" }}>
                      {editingLeague === l.id ? (
                        <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                          <TextField
                            size="small"
                            value={editLeagueForm.name}
                            onChange={(e) => setEditLeagueForm((f) => ({ ...f, name: e.target.value }))}/>
                          <FormControlLabel
                            control={<Switch
                              size="small"
                              checked={editLeagueForm.is_public}
                              onChange={(e) => setEditLeagueForm((f) => ({ ...f, is_public: e.target.checked }))}/>
                            }
                            label={editLeagueForm.is_public ? t("admin.league_public") : t("admin.league_private")}
                          />
                          <Button size="small" variant="contained" onClick={handleSaveLeagueEdit}>Save</Button>
                          <Button size="small" onClick={() => setEditingLeague(null)}>Cancel</Button>
                        </Box>
                      ) : (
                        <>
                          <Button
                            size="small"
                            variant="outlined"
                            onClick={() => {
                              setEditingLeague(l.id);
                              setEditLeagueForm({ name: l.name, is_public: l.is_public });
                            }}
                          >
                            {t("admin.edit_league")}
                          </Button>
                          <Button
                            size="small"
                            variant="outlined"
                            color="error"
                            disabled={l.name === "VM2026"}
                            onClick={() => setDeleteConfirmLeagueId(l.id)}
                          >
                            {l.name === "VM2026" ? t("admin.default_league_protected") : t("admin.delete_league")}
                          </Button>
                        </>
                      )}
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog
        open={deleteConfirmLeagueId !== null}
        onClose={() => setDeleteConfirmLeagueId(null)}
      >
        <DialogTitle>{t("common.confirm")}</DialogTitle>
        <DialogContent>
          <Typography>{t("admin.delete_league_confirm")}</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirmLeagueId(null)}>{t("common.cancel")}</Button>
          <Button color="error" onClick={handleDeleteLeague}>{t("common.delete")}</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
