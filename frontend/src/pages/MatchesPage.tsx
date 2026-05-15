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
} from "@mui/material";
import { matchesApi } from "../api/client";

interface Match {
  id: number;
  match_number: number;
  round: string;
  group?: string;
  home_team: { name: string; flag: string };
  away_team: { name: string; flag: string };
  match_date: string;
  status: string;
  home_goals: number | null;
  away_goals: number | null;
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
    <Paper elevation={2} sx={{ p: 2, mb: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
        <Typography variant="caption" color="text.secondary">
          {match.group ? `${match.group} · ` : ""}
          {match.match_number} · {kickoff}
        </Typography>
        <Chip
          size="small"
          label={isFinished ? t("matches.result") : isLocked ? t("matches.locked") : match.status}
          color={isFinished ? "success" : isLocked ? "error" : "default"}
        />
      </Box>

      <Box sx={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
        <Box sx={{ flex: "1 1 auto", textAlign: "right" }}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {(home.flag?.length || 0) <= 6 ? home.flag : "🌍"} {home.name}
          </Typography>
        </Box>
        <Box sx={{ width: 80 }}>
          <TextField
            size="small"
            type="number"
            placeholder="-"
            value={pred.home}
            onChange={(e) => onChange(match.id, "home", e.target.value)}
            disabled={disabled}
            fullWidth
          />
        </Box>
        <Box sx={{ width: 80 }}>
          <TextField
            size="small"
            type="number"
            placeholder="-"
            value={pred.away}
            onChange={(e) => onChange(match.id, "away", e.target.value)}
            disabled={disabled}
            fullWidth
          />
        </Box>
        <Box sx={{ flex: "1 1 auto", textAlign: "left" }}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {away.name} {(away.flag?.length || 0) <= 6 ? away.flag : "🌍"}
          </Typography>
        </Box>
      </Box>

      {isFinished && match.home_goals !== null && (
        <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1 }}>
          {t("matches.result")}: {match.home_goals} - {match.away_goals}
        </Typography>
      )}
    </Paper>
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
    <Container sx={{ mt: 4, mb: 8 }}>
      <Typography variant="h4" gutterBottom>{t("matches.title")}</Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label={t("matches.group_stage")} />
        <Tab label={t("matches.knockout")} />
      </Tabs>

      {tab === 0 && (
        <Box>
          {groups.map((group) => (
            <Box key={group} sx={{ mb: 3 }}>
              <Typography variant="h6" sx={{ mb: 1 }}>{group}</Typography>
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
            </Box>
          ))}
        </Box>
      )}

      {tab === 1 && (
        <Box>
          {knockoutMatches.map((m) => (
            <MatchCard
              key={m.id}
              match={m}
              predictions={predictions}
              onChange={handleChange}
            />
          ))}
        </Box>
      )}

      <Box sx={{ position: "sticky", bottom: 16, textAlign: "center" }}>
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
    </Container>
  );
}
