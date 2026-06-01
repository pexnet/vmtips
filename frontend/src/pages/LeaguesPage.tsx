import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Container,
  Typography,
  Paper,
  Box,
  TextField,
  Button,
  List,
  ListItem,
  ListItemText,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  Chip,
  IconButton,
  Tabs,
  Tab,
} from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import { leaguesApi } from "../api/client";
import { useLeagues, useLeagueDetail, useInvalidateLeagues, usePublicLeagues } from "../hooks/useLeagues";
import type { League } from "../types/api";
import { getErrorDetail } from "../types/api";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import UserAvatar from "../components/UserAvatar";

export default function LeaguesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [joinOpen, setJoinOpen] = useState(false);
  const [newLeagueName, setNewLeagueName] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [joinLeagueId, setJoinLeagueId] = useState<number | null>(null);
  const [detailLeagueId, setDetailLeagueId] = useState<number | null>(null);
  const [tab, setTab] = useState(0);

  const { data: leagues = [], isLoading, error: queryError } = useLeagues();
  const { data: publicLeagues = [], isLoading: publicLoading } = usePublicLeagues();
  const { data: detailLeague } = useLeagueDetail(detailLeagueId);
  const invalidateLeagues = useInvalidateLeagues();

  const handleCreate = () => {
    if (!newLeagueName.trim()) return;
    leaguesApi
      .create(newLeagueName)
      .then(() => {
        setCreateOpen(false);
        setNewLeagueName("");
        invalidateLeagues();
      })
      .catch(() => setError(t("common.error")));
  };

  const handleJoin = () => {
    if (!joinLeagueId || !joinCode.trim()) return;
    leaguesApi
      .join(joinLeagueId, joinCode)
      .then(() => {
        setJoinOpen(false);
        setJoinCode("");
        invalidateLeagues();
      })
      .catch((err: unknown) => {
        setError(getErrorDetail(err) || t("common.error"));
      });
  };

  const openJoin = (league: League) => {
    setJoinLeagueId(league.id);
    setJoinOpen(true);
  };

  const viewDetail = (id: number) => {
    setDetailLeagueId(id);
  };

  const combinedError = error || (queryError ? t("common.error") : "");

  if (isLoading) {
    return (
      <Container sx={{ mt: 8, textAlign: "center" }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 4, mb: 8 }}>
      <Typography variant="h4" gutterBottom>{t("leagues.title")}</Typography>
      {combinedError && <Alert severity="error" sx={{ mb: 2 }}>{combinedError}</Alert>}

      <Box sx={{ display: "flex", gap: 2, mb: 3 }}>
        <Button variant="contained" onClick={() => setCreateOpen(true)}>{t("leagues.create")}</Button>
      </Box>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label={t("leagues.my_leagues")} />
        <Tab label={t("leagues.public_leagues")} />
      </Tabs>
      {tab === 0 && (
<>

      {leagues.length === 0 ? (
        <Alert severity="info">{t("leagues.no_leagues")}</Alert>
      ) : (
        <List>
          {leagues.map((l) => (
            <Paper key={l.id} elevation={2} sx={{ mb: 2 }}>
              <ListItem
                secondaryAction={
                  user?.id === l.admin_user_id ? (
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Chip size="small" label={t("leagues.admin")} color="primary" />
                      <IconButton
                        size="small"
                        onClick={() => navigator.clipboard.writeText(l.invite_code || "")}
                        title={t("leagues.copy_invite_code")}
                      >
                        <ContentCopyIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  ) : (
                    <Button size="small" variant="outlined" onClick={() => openJoin(l)}>
                      {t("leagues.join")}
                    </Button>
                  )
                }
              >
                <ListItemText
                  primary={
                    <Typography variant="h6">
                      <Button color="inherit" onClick={() => viewDetail(l.id)} sx={{ p: 0, justifyContent: "flex-start" }}>
                        {l.name}
                      </Button>
                    </Typography>
                  }
                  secondary={`${t("leagues.code_label")}: ${l.invite_code || "—"}`}
                />
              </ListItem>
            </Paper>
          ))}
        </List>
      )}

      </>
      )}
      {tab === 1 && (
        <Box>
          {publicLoading ? (
            <CircularProgress />
          ) : publicLeagues.length === 0 ? (
            <Alert severity="info">{t("leagues.no_public_leagues")}</Alert>
          ) : (
            <List>
              {publicLeagues.map((l) => (
                <Paper key={l.id} elevation={2} sx={{ mb: 2 }}>
                  <ListItem>
                    <ListItemText
                      primary={l.name}
                      secondary={`${t("leagues.member_count")}: ${l.member_count}`}
                    />
                  </ListItem>
                </Paper>
              ))}
            </List>
          )}
        </Box>
      )}
      {/* Create dialog */}
      <Dialog open={createOpen} onClose={() => setCreateOpen(false)}>
        <DialogTitle>{t("leagues.create")}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label={t("leagues.league_name")}
            fullWidth
            value={newLeagueName}
            onChange={(e) => setNewLeagueName(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>{t("common.cancel")}</Button>
          <Button onClick={handleCreate} disabled={!newLeagueName.trim()}>{t("common.save")}</Button>
        </DialogActions>
      </Dialog>

      {/* Join dialog */}
      <Dialog open={joinOpen} onClose={() => setJoinOpen(false)}>
        <DialogTitle>{t("leagues.join")}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label={t("leagues.invite_code")}
            fullWidth
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setJoinOpen(false)}>{t("common.cancel")}</Button>
          <Button onClick={handleJoin} disabled={!joinCode.trim()}>{t("leagues.join")}</Button>
        </DialogActions>
      </Dialog>

      {/* Detail dialog */}
      <Dialog open={!!detailLeagueId} onClose={() => setDetailLeagueId(null)} maxWidth="sm" fullWidth>
        <DialogTitle>{detailLeague?.name}</DialogTitle>
        <DialogContent>
          <Typography variant="subtitle1" gutterBottom>{t("leagues.members")}:</Typography>
          <List>
            {detailLeague?.members?.map((m) => (
              <ListItem key={m.id}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                  <UserAvatar
                    displayName={m.display_name}
                    avatarUrl={m.avatar_url}
                    sx={{ width: 34, height: 34, fontSize: "0.8rem" }}
                  />
                  <ListItemText primary={m.display_name} />
                </Box>
              </ListItem>
            )) || <Typography color="text.secondary">{t("leagues.no_members")}</Typography>}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setDetailLeagueId(null); navigate(`/leagues/${detailLeagueId}/bonus-questions`); }}>{t("leagues.bonus_questions")}</Button>
          <Button onClick={() => setDetailLeagueId(null)}>{t("common.close")}</Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
