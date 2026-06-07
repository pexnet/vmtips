import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Paper, Box, Typography, TextField, Button, Alert, CircularProgress, Select, MenuItem, FormControl, InputLabel } from "@mui/material";
import { adminApi, phaseApi } from "../../api/client";
import type { PhaseInfo } from "../../types/api";
import { getErrorDetail } from "../../types/api";
type Notify = (kind: "error" | "success", message: string) => void;

export default function PhaseTab({ notify, queryClient }: { notify: Notify; queryClient: import("@tanstack/react-query").QueryClient }) {
  const { t } = useTranslation();
  const [phase, setPhase] = useState<PhaseInfo | null>(null);
  const [phaseLoading, setPhaseLoading] = useState(false);
  const [phaseForm, setPhaseForm] = useState({
    phase: "group_open",
    group_deadline: "",
    knockout_opens_at: "",
    knockout_deadline: "",
  });

  useEffect(() => {
    phaseApi.get().then((data) => {
      const p = data.data as PhaseInfo;
      setPhase(p);
      setPhaseForm({
        phase: p.phase || "group_open",
        group_deadline: p.group_deadline?.slice(0, 16) || "",
        knockout_opens_at: p.knockout_opens_at?.slice(0, 16) || "",
        knockout_deadline: p.knockout_deadline?.slice(0, 16) || "",
      });
    }).catch(() => { /* phase endpoint not yet available */ });
  }, []);

  function handleSavePhase() {
    setPhaseLoading(true);
    adminApi.updatePhase({
      phase: phaseForm.phase,
      group_deadline: phaseForm.group_deadline || undefined,
      knockout_opens_at: phaseForm.knockout_opens_at || undefined,
      knockout_deadline: phaseForm.knockout_deadline || undefined,
    })
      .then(() => {
        notify("success", t("admin.phase_updated"));
        queryClient.invalidateQueries({ queryKey: ["phase"] });
      })
      .catch((err: unknown) => notify("error", getErrorDetail(err)))
      .finally(() => setPhaseLoading(false));
  }

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>{t("admin.phase_management")}</Typography>
      {phase && (
        <Alert severity="info" sx={{ mb: 2 }}>
          {t("admin.current_phase")}: {t(`phase.${phase.phase}`)}
        </Alert>
      )}
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        <FormControl fullWidth>
          <InputLabel>{t("admin.set_phase")}</InputLabel>
          <Select value={phaseForm.phase} label={t("admin.set_phase")}
            onChange={(e) => setPhaseForm((f) => ({ ...f, phase: e.target.value }))}>
            <MenuItem value="group_open">{t("admin.phase_group_open")}</MenuItem>
            <MenuItem value="group_closed">{t("admin.phase_group_closed")}</MenuItem>
            <MenuItem value="knockout_open">{t("admin.phase_knockout_open")}</MenuItem>
            <MenuItem value="knockout_closed">{t("admin.phase_knockout_closed")}</MenuItem>
          </Select>
        </FormControl>
        <TextField label={t("admin.group_deadline")} type="datetime-local" value={phaseForm.group_deadline}
          onChange={(e) => setPhaseForm((f) => ({ ...f, group_deadline: e.target.value }))} slotProps={{ inputLabel: { shrink: true } }} fullWidth />
        <TextField label={t("admin.knockout_opens")} type="datetime-local" value={phaseForm.knockout_opens_at}
          onChange={(e) => setPhaseForm((f) => ({ ...f, knockout_opens_at: e.target.value }))} slotProps={{ inputLabel: { shrink: true } }} fullWidth />
        <TextField label={t("admin.knockout_deadline")} type="datetime-local" value={phaseForm.knockout_deadline}
          onChange={(e) => setPhaseForm((f) => ({ ...f, knockout_deadline: e.target.value }))} slotProps={{ inputLabel: { shrink: true } }} fullWidth />
        <Button variant="contained" onClick={handleSavePhase} disabled={phaseLoading}>
          {phaseLoading ? <CircularProgress size={20} /> : t("common.save")}
        </Button>
      </Box>
    </Paper>
  );
}
