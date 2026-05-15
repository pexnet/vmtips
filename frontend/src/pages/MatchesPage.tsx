import { useState } from "react";
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
import { predictionsApi } from "../api/client";
import { useMatches } from "../hooks/useMatches";

import type { Match } from "../types/api";

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

      {home && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Typography variant="body2" sx={{ fontSize: "1.1rem" }}>{home.flag_emoji ?? ""}</Typography>
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
      )}

      {away && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Typography variant="body2" sx={{ fontSize: "1.1rem" }}>{away.flag_emoji ?? ""}</Typography>
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
      )}

      {isFinished && match.home_goals !== null && (
        <Typography variant="caption" color="text.secondary" align="center">
          {t("matches.result")}: {match.home_goals} - {match.away_goals}
        </Typography>
      )}
    </Paper>
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
  const [error, setError] = useState("");
  const [predictions, setPredictions] = useState(
    {} as Record<number, { home: string; away: string }>
  );

  const { data: matches = [], isLoading } = useMatches();

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

    predictionsApi
      .batch(batch)
      .then(() => setPredictions({}))
      .catch((err: unknown) => {
        const axiosErr = err as { response?: { status?: number } };
        if (axiosErr.response?.status === 401) navigate("/login");
        else setError(t("common.error"));
      });
  };

  const groupMatches = matches.filter((m) => m.round === "group");
  const knockoutMatches = matches.filter((m) => m.round !== "group");
  const groups = [...new Set(groupMatches.map((m) => m.group).filter(Boolean))].sort();

  if (isLoading) {
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
          {["round_of_32","round_of_16","quarter_final","semi_final","match_for_third_place","final"].map((round) => {
            const roundMatches = knockoutMatches.filter((m) => m.round === round);
            if (roundMatches.length === 0) return null;
            return (
              <Box key={round} sx={{ mb: 3 }}>
                <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>
                  {round === "round_of_32" ? "Round of 32" : round === "round_of_16" ? "Round of 16" : round === "quarter_final" ? "Quarter-finals" : round === "semi_final" ? "Semi-finals" : round === "match_for_third_place" ? "3rd Place" : "Final"}
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


      {/* Save button */}
      <Box sx={{ position: "sticky", bottom: 16, textAlign: "center", bgcolor: "background.default", p: 1 }}>
          <Button
            variant="contained"
            size="large"
            onClick={() => {
            const token = localStorage.getItem("token");
            if (!token) {
              navigate("/login");
              return;
            }
            handleSave();
            }}
            disabled={Object.keys(predictions).length === 0}
          >
            {t("matches.save_predictions")}
          </Button>
        </Box>
    </Container>
  );
}