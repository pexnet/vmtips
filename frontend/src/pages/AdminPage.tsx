import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  Container,
  Typography,
  Paper,
  Box,
  TextField,
  Button,
  Alert,
  Autocomplete,
  CircularProgress,
} from "@mui/material";
import { adminApi, matchesApi } from "../api/client";
import { useAuth } from "../contexts/AuthContext";

interface Match {
  id: number;
  match_number: number;
  round: string;
  group?: string;
  home_team: { name: string; flag: string };
  away_team: { name: string; flag: string };
  status: string;
  home_goals: number | null;
  away_goals: number | null;
  match_date: string;
}

export default function AdminPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [matches, setMatches] = useState<Match[]>([]);
  const [selectedMatch, setSelectedMatch] = useState<Match | null>(null);
  const [homeGoals, setHomeGoals] = useState("");
  const [awayGoals, setAwayGoals] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!user) {
      navigate("/login");
      return;
    }
    matchesApi
      .list()
      .then((res) => setMatches(res.data))
      .catch(() => setError(t("common.error")));
  }, [user, navigate, t]);

  const handleSubmit = async () => {
    if (!selectedMatch) return;
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      await adminApi.setResult(selectedMatch.id, {
        home_goals: parseInt(homeGoals, 10),
        away_goals: parseInt(awayGoals, 10),
      });
      setSuccess("Result updated!");
      setHomeGoals("");
      setAwayGoals("");
      setSelectedMatch(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setLoading(true);
    setError("");
    try {
      await adminApi.sync();
      setSuccess("Results synced!");
    } catch (err: any) {
      setError(err.response?.data?.detail || t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  const handleRecalc = async () => {
    setLoading(true);
    setError("");
    try {
      await adminApi.recalc();
      setSuccess("Scores recalculated!");
    } catch (err: any) {
      setError(err.response?.data?.detail || t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        Admin Panel
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Enter Match Result
        </Typography>
        <Autocomplete
          options={matches}
          getOptionLabel={(m) =>
            `#${m.match_number} ${m.home_team.name} ${m.home_team.flag} vs ${m.away_team.flag} ${m.away_team.name}`
          }
          value={selectedMatch}
          onChange={(_, value) => setSelectedMatch(value)}
          renderInput={(params) => (
            <TextField {...params} label="Select match" fullWidth margin="normal" />
          )}
        />
        {selectedMatch && (
          <Box sx={{ display: "flex", gap: 2, mt: 2 }}>
            <TextField
              label={`${selectedMatch.home_team.name} goals`}
              type="number"
              value={homeGoals}
              onChange={(e) => setHomeGoals(e.target.value)}
              slotProps={{ htmlInput: { min: 0 } }}
            />
            <TextField
              label={`${selectedMatch.away_team.name} goals`}
              type="number"
              value={awayGoals}
              onChange={(e) => setAwayGoals(e.target.value)}
              slotProps={{ htmlInput: { min: 0 } }}
            />
            <Button
              variant="contained"
              onClick={handleSubmit}
              disabled={loading || homeGoals === "" || awayGoals === ""}
            >
              {loading ? <CircularProgress size={24} /> : "Save Result"}
            </Button>
          </Box>
        )}
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Score Management
        </Typography>
        <Box sx={{ display: "flex", gap: 2 }}>
          <Button variant="outlined" onClick={handleSync} disabled={loading}>
            Sync Results
          </Button>
          <Button variant="outlined" onClick={handleRecalc} disabled={loading}>
            Recalculate Scores
          </Button>
        </Box>
      </Paper>
    </Container>
  );
}
