import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Paper, Box, Typography, TextField, Button, CircularProgress, Switch, FormControlLabel } from "@mui/material";
import { adminApi } from "../../api/client";
import { getErrorDetail } from "../../types/api";
type Notify = (kind: "error" | "success", message: string) => void;

export default function ScoreManagementTab({
  notify,
  queryClient,
}: {
  notify: Notify;
  queryClient: import("@tanstack/react-query").QueryClient;
}) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [syncConfig, setSyncConfig] = useState<{
    source: string;
    auto_sync_enabled: boolean;
    auto_sync_interval_minutes: number;
  } | null>(null);
  const [syncConfigLoading, setSyncConfigLoading] = useState(false);

  useEffect(() => {
    adminApi.syncConfig().then((res) => { setSyncConfig(res.data as typeof syncConfig); }).catch(() => { /* no config yet */ });
  }, []);

  function handleSync() {
    setLoading(true);
    adminApi.sync()
      .then(() => { notify("success", t("admin.results_synced")); queryClient.invalidateQueries({ queryKey: ["matches"] }); })
      .catch((err: unknown) => notify("error", getErrorDetail(err)))
      .finally(() => setLoading(false));
  }

  function handleRecalc() {
    setLoading(true);
    adminApi.recalc()
      .then(() => { notify("success", t("admin.scores_recalculated")); queryClient.invalidateQueries({ queryKey: ["leaderboard"] }); })
      .catch((err: unknown) => notify("error", getErrorDetail(err)))
      .finally(() => setLoading(false));
  }

  function handleSaveSyncConfig() {
    if (!syncConfig) return;
    setSyncConfigLoading(true);
    adminApi.updateSyncConfig(syncConfig)
      .then(() => notify("success", t("admin.sync_config_saved")))
      .catch((err: unknown) => notify("error", getErrorDetail(err)))
      .finally(() => setSyncConfigLoading(false));
  }

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>{t("admin.score_management")}</Typography>
      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
        <Button variant="contained" onClick={handleSync} disabled={loading}>
          {loading ? <CircularProgress size={20} /> : t("admin.sync_results")}
        </Button>
        <Button variant="contained" onClick={handleRecalc} disabled={loading}>
          {loading ? <CircularProgress size={20} /> : t("admin.recalculate_scores")}
        </Button>
      </Box>
      {syncConfig && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>{t("admin.sync_config")}</Typography>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <TextField label={t("admin.sync_source")} value={syncConfig.source}
              onChange={(e) => setSyncConfig((c) => c ? { ...c, source: e.target.value } : c)} fullWidth />
            <FormControlLabel control={<Switch checked={syncConfig.auto_sync_enabled}
              onChange={(e) => setSyncConfig((c) => c ? { ...c, auto_sync_enabled: e.target.checked } : c)} />}
              label={`${t("admin.auto_sync")}: ${syncConfig.auto_sync_enabled ? t("admin.auto_sync_on") : t("admin.auto_sync_off")}`} />
            <TextField label={t("admin.sync_interval")} type="number" value={syncConfig.auto_sync_interval_minutes}
              onChange={(e) => setSyncConfig((c) => c ? { ...c, auto_sync_interval_minutes: Number(e.target.value) } : c)} fullWidth />
            <Button variant="contained" onClick={handleSaveSyncConfig} disabled={syncConfigLoading}>
              {syncConfigLoading ? <CircularProgress size={20} /> : t("admin.save_sync_config")}
            </Button>
          </Box>
        </Box>
      )}
    </Paper>
  );
}
