import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Container, Typography, Tabs, Tab, Alert, Box, CircularProgress } from "@mui/material";
import { useMatches } from "../hooks/useMatches";
import { useTeams } from "../hooks/useTeams";
import { queryClient } from "../contexts/QueryClientProvider";

import MatchResultsTab from "./admin/MatchResultsTab";
import GroupStandingsTab from "./admin/GroupStandingsTab";
import TournamentResultTab from "./admin/TournamentResultTab";
import PhaseTab from "./admin/PhaseTab";
import KnockoutAdvancementsTab from "./admin/KnockoutAdvancementsTab";
import ScoringOverviewTab from "./admin/ScoringOverviewTab";
import ScoreManagementTab from "./admin/ScoreManagementTab";
import AllPredictionsTab from "./admin/AllPredictionsTab";
import LeagueManagementTab from "./admin/LeagueManagementTab";
import UsersTab from "./admin/UsersTab";

export default function AdminPage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  // Bumped after actions that should refresh cached data on the standings tab
  // (e.g. group result save → recompute). Other tabs fetch on mount and
  // are not affected.
  const [standingsReloadKey, setStandingsReloadKey] = useState(0);

  const { data: matches = [], isLoading: matchesLoading } = useMatches();
  const { data: teams = [] } = useTeams();

  const notify = useCallback(
    (kind: "error" | "success", message: string) => {
      if (kind === "error") {
        setError(message);
        setSuccess("");
      } else {
        setSuccess(message);
        setError("");
      }
      // Bump reload key for any tab that watches data we might have invalidated
      setStandingsReloadKey((k) => k + 1);
    },
    [],
  );

  if (matchesLoading) {
    return (
      <Container sx={{ mt: 8, textAlign: "center" }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 2, mb: 8, maxWidth: "lg" }}>
      <Typography variant="h4" gutterBottom>
        {t("admin.title")}
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess("")}>
          {success}
        </Alert>
      )}

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ mb: 2 }}
        variant="scrollable"
        scrollButtons="auto"
      >
        <Tab label={t("admin.enter_result")} />
        <Tab label={t("admin.group_standings")} />
        <Tab label={t("admin.tournament_result")} />
        <Tab label={t("admin.phase_management")} />
        <Tab label={t("admin.knockout_advancements")} />
        <Tab label={t("admin.scoring_overview")} />
        <Tab label={t("admin.score_management")} />
        <Tab label={t("admin.all_predictions")} />
        <Tab label={t("admin.league_management")} />
        <Tab label={t("admin.user_management")} />
      </Tabs>

      <Box>
        {tab === 0 && (
          <MatchResultsTab matches={matches} notify={notify} queryClient={queryClient} />
        )}
        {tab === 1 && <GroupStandingsTab notify={notify} reloadKey={standingsReloadKey} />}
        {tab === 2 && <TournamentResultTab teams={teams} notify={notify} />}
        {tab === 3 && <PhaseTab notify={notify} queryClient={queryClient} />}
        {tab === 4 && (
          <KnockoutAdvancementsTab matches={matches} notify={notify} queryClient={queryClient} />
        )}
        {tab === 5 && <ScoringOverviewTab />}
        {tab === 6 && <ScoreManagementTab notify={notify} queryClient={queryClient} />}
        {tab === 7 && <AllPredictionsTab />}
        {tab === 8 && <LeagueManagementTab notify={notify} />}
        {tab === 9 && <UsersTab notify={notify} />}
      </Box>
    </Container>
  );
}
