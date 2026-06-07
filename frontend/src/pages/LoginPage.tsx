import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, Link } from "react-router-dom";
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
} from "@mui/material";
import { authApi } from "../api/client";
import { useAuth } from "../contexts/AuthContext";

export default function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const publicRegistrationEnabled =
    import.meta.env.VITE_ALLOW_PUBLIC_REGISTRATION === "true";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await authApi.login({ identifier, password });
      login(res.data.access_token);
      navigate("/leaderboard");
    } catch (err: unknown) {
      const detail = err instanceof Error && "response" in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      setError(detail || t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="sm" sx={{ mt: 8 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" align="center" gutterBottom>
          {t("auth.login")}
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <Box component="form" onSubmit={handleSubmit} sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <TextField
            label={t("auth.identifier")}
            placeholder={t("auth.identifier_placeholder")}
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            required
            fullWidth
          />
          <TextField
            label={t("auth.password")}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            fullWidth
          />
          <Button type="submit" variant="contained" size="large" disabled={loading}>
            {loading ? t("common.loading") : t("auth.login")}
          </Button>
        </Box>

        {publicRegistrationEnabled && (
          <Typography variant="body2" align="center" sx={{ mt: 2 }}>
            <Link to="/register">{t("auth.no_account")}</Link>
          </Typography>
        )}
      </Paper>
    </Container>
  );
}
