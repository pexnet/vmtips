import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  Container,
  Typography,
  Tabs,
  Tab,
  Box,
  Paper,
  TextField,
  Button,
  Chip,
  Alert,
  CircularProgress,
  Autocomplete,
} from "@mui/material";
import { matchesApi, predictionsApi } from "../api/client";

interface Match {
  id: number;
  match_number: number;
  round: string;
  group?: string;
  home_team: { name: string; flag_emoji: string };
  away_team: { name: string; flag_emoji: string };
  match_date: string;
  status: string;
  home_goals: number | null;
  away_goals: number | null;
}

interface Team {
  id: number;
  name: string;
  flag_emoji: string;
}

function MatchCard({
  match,
  predictions,
  onChange,
}: {
  match: Match;
  predictions: Record<number, { home: string; away: string }>;
  onChange: (id: number, side: "home" | "away", val: string) => void;
}) {
  const { t, i18n } = useTranslation();
  const home = match.home_team;
  const away = match.away_team;
  const pred = predictions[match.id] || { home: "", away: "" };
  const isFinished = match.status === "finished";
  const isLocked = new Date(match.match_date) <= new Date();
  const disabled = isFinished || isLocked;

  const kickoff = new Date(match.match_date).toLocaleString(i18n.language, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <Paper
      elevation={1}
      sx={{
        p: 1.5,
        display: "flex",
        flexDirection: "column",
        gap: 1,
        minHeight: 120,
      }}
    >
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Typography variant="caption" color="text.secondary">
          {match.group || match.round.toUpperCase()} · {kickoff}
        </Typography>
        {isFinished ? (
          <Chip size="small" label={t("matches.result")} color="success" />
        ) : isLocked ? (
          <Chip size="small" label={t("matches.locked")} color="error" />
        ) : null}
      </Box>

      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Typography variant="body2" sx={{ fontSize: "1.1rem" }}>{home.flag_emoji}</Typography>
        <Typography variant="body2" sx={{ fontWeight: 500, flex: 1 }} noWrap>
          {home.name}
        </Typography>
        <TextField
          size="small"
          type="text"
          placeholder="-"
          value={pred.home}
          onChange={(e) => {
            const val = e.target.value;
            if (val === "" || (/^\d*$/.test(val) && Number(val) <= 15)) {
              onChange(match.id, "home", val);
            }
          }}
          disabled={disabled}
          sx={{ width: 60, '& input::-webkit-outer-spin-button, & input::-webkit-inner-spin-button': { WebkitAppearance: 'none' } }}
        />
      </Box>

      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Typography variant="body2" sx={{ fontSize: "1.1rem" }}>{away.flag_emoji}</Typography>
        <Typography variant="body2" sx={{ fontWeight: 500, flex: 1 }} noWrap>
          {away.name}
        </Typography>
        <TextField
          size="small"
          type="text"
          placeholder="-"
          value={pred.away}
          onChange={(e) => {
            const val = e.target.value;
            if (val === "" || (/^\d*$/.test(val) && Number(val) <= 15)) {
              onChange(match.id, "away", val);
            }
          }}
          disabled={disabled}
          sx={{ width: 60, '& input::-webkit-outer-spin-button, & input::-webkit-inner-spin-button': { WebkitAppearance: 'none' } }}
        />
      </Box>

      {isFinished && match.home_goals !== null && (
        <Typography variant="caption" color="text.secondary" align="center">
          {t("matches.result")}: {match.home_goals} - {match.away_goals}
        </Typography>
      )}
    </Paper>
  );
}

function BonusTab() {
  const { t } = useTranslation();
  const [teams, setTeams] = useState<Team[]>([]);
  const [bonuses, setBonuses] = useState({
    winner_team_id: null as number | null,
    top_scorer_name: "",
    top_assist_name: "",
    total_goals: "",
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    predictionsApi.tournament().then((res) => {
      const b = res.data || {};
      setBonuses({
        winner_team_id: b.winner_team_id || null,
        top_scorer_name: b.top_scorer_name || "",
        top_assist_name: b.top_assist_name || "",
        total_goals: b.total_goals != null ? String(b.total_goals) : "",
      });
    });
    matchesApi.list().then((res) => {
      const all = res.data;
      const teamMap = new Map<number, Team>();
      all.forEach((m: any) => {
        if (m.home_team?.id) teamMap.set(m.home_team.id, m.home_team);
        if (m.away_team?.id) teamMap.set(m.away_team.id, m.away_team);
      });
      setTeams(Array.from(teamMap.values()));
    });
  }, []);

  const handleSave = () => {
    predictionsApi
      .saveTournament({
        winner_team_id: bonuses.winner_team_id || undefined,
        top_scorer_name: bonuses.top_scorer_name || undefined,
        top_assist_name: bonuses.top_assist_name || undefined,
        total_goals: bonuses.total_goals ? Number(bonuses.total_goals) : undefined,
      })
      .then(() => setSaved(true))
      .catch(() => setSaved(false));
  };

  return (
    <Box sx={{ maxWidth: 600, mx: "auto", mt: 2 }}>
      <Typography variant="h6" gutterBottom>
        {t("predictions.bonus_questions")}
      </Typography>

      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <Autocomplete
          options={teams}
          getOptionLabel={(o) => `${o.flag_emoji} ${o.name}`}
          value={teams.find((t) => t.id === bonuses.winner_team_id) || null}
          onChange={(_, v) => setBonuses((b) => ({ ...b, winner_team_id: v?.id || null }))}
          renderInput={(params) => (
            <TextField {...params} label={t("predictions.winner")} />
          )}
        />

        <TextField
          label={t("predictions.top_scorer")}
          value={bonuses.top_scorer_name}
          onChange={(e) => setBonuses((b) => ({ ...b, top_scorer_name: e.target.value }))}
        />

        <TextField
          label={t("predictions.top_assist")}
          value={bonuses.top_assist_name}
          onChange={(e) => setBonuses((b) => ({ ...b, top_assist_name: e.target.value }))}
        />

        <TextField
          label={t("predictions.total_goals")}
          type="number"
          value={bonuses.total_goals}
          onChange={(e) => {
            const val = e.target.value;
            if (val === "" || Number(val) >= 0) setBonuses((b) => ({ ...b, total_goals: val }));
          }}
          slotProps={{ htmlInput: { min: 0 } }}
        />

        <Button variant="contained" onClick={handleSave}>
          {t("matches.save_predictions")}
        </Button>

        {saved && <Alert severity="success">{t("common.saved")}</Alert>}
      </Box>
    </Box>
  );
}

// Flexbox wrapper: 2 per rad på sm+
function TwoColumnGrid({ children }: { children: React.ReactNode }) {
  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5 }}>
      {Array.isArray(children)
        ? children.map((child, i) => (
            <Box
              key={i}
              sx={{
                flexBasis: { xs: "100%", sm: "calc(50% - 8px)" },
                flexGrow: 1,
              }}
            >
              {child}
            </Box>
          ))
        : children}
    </Box>
  );
}

export default function MatchesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [tab, setTab] = useState(0);
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [predictions, setPredictions] = useState(
    {} as Record<number, { home: string; away: string }>
  );

  useEffect(() => {
    matchesApi
      .list()
      .then((res) => setMatches(res.data))
      .catch(() => setError(t("common.error")))
      .finally(() => setLoading(false));
  }, [t]);

  const handleChange = (id: number, side: "home" | "away", val: string) => {
    setPredictions((prev) => ({
      ...prev,
      [id]: { ...prev[id], [side]: val },
    }));
  };

  const handleSave = () => {
    const batch = Object.entries(predictions)
      .filter(([, v]) => v.home !== "" && v.away !== "")
      .map(([id, v]) => ({
        match_id: Number(id),
        home_goals: Number(v.home),
        away_goals: Number(v.away),
      }));

    if (batch.length === 0) return;

    const token = localStorage.getItem("token");
    if (!token) {
      navigate("/login");
      return;
    }

    fetch("/api/predictions/batch", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ predictions: batch }),
    })
      .then((r) => {
        if (r.status === 401) navigate("/login");
        else if (r.ok) setPredictions({});
      })
      .catch(() => setError(t("common.error")));
  };

  const groupMatches = matches.filter((m) => m.round === "group");
  const knockoutMatches = matches.filter((m) => m.round !== "group");
  const groups = [...new Set(groupMatches.map((m) => m.group).filter(Boolean))].sort();

  if (loading) {
    return (
      <Container sx={{ mt: 8, textAlign: "center" }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 2, mb: 8, maxWidth: "lg" }}>
      <Typography variant="h4" gutterBottom>
        {t("matches.title")}
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label={t("matches.group_stage")} />
        <Tab label={t("matches.knockout")} />
        <Tab label={t("predictions.bonus_questions")} />
      </Tabs>

      {/* GROUP STAGE */}
      {tab === 0 && (
        <Box>
          {groups.map((group) => (
            <Box key={group} sx={{ mb: 3 }}>
              <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>
                {group}
              </Typography>
              <TwoColumnGrid>
                {groupMatches
                  .filter((m) => m.group === group)
                  .map((m) => (
                    <MatchCard
                      key={m.id}
                      match={m}
                      predictions={predictions}
                      onChange={handleChange}
                    />
                  ))}
              </TwoColumnGrid>
            </Box>
          ))}
        </Box>
      )}

      {/* KNOCKOUT */}
      {tab === 1 && (
        <Box>
          {["ro32", "ro16", "qf", "sf", "3p", "final"].map((round) => {
            const roundMatches = knockoutMatches.filter((m) => m.round === round);
            if (roundMatches.length === 0) return null;
            return (
              <Box key={round} sx={{ mb: 3 }}>
                <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>
                  {round === "ro32" ? "Round of 32" : round === "ro16" ? "Round of 16" : round === "qf" ? "Quarter-finals" : round === "sf" ? "Semi-finals" : round === "3p" ? "3rd Place" : "Final"}
                </Typography>
                <TwoColumnGrid>
                  {roundMatches.map((m) => (
                    <MatchCard
                      key={m.id}
                      match={m}
                      predictions={predictions}
                      onChange={handleChange}
                    />
                  ))}
                </TwoColumnGrid>
              </Box>
            );
          })}
        </Box>
      )}

      {/* BONUS */}
      {tab === 2 && <BonusTab />}

      {/* Save button */}
      {tab !== 2 && (
        <Box sx={{ position: "sticky", bottom: 16, textAlign: "center", bgcolor: "background.default", p: 1 }}>
          <Button
            variant="contained"
            size="large"
            onClick={() => {
              const token = localStorage.getItem("token");
              if (!token) navigate("/login");
              else handleSave();
            }}
            disabled={Object.keys(predictions).length === 0}
          >
            {t("matches.save_predictions")}
          </Button>
        </Box>
      )}
    </Container>
  );
}
