import { useEffect, useState } from "react";
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
} from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import { leaguesApi } from "../api/client";

interface League {
  id: number;
  name: string;
  invite_code: string;
  admin_user_id: number;
  is_admin?: boolean;
}

export default function LeaguesPage() {
  const { t } = useTranslation();
  const [leagues, setLeagues] = useState<League[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [joinOpen, setJoinOpen] = useState(false);
  const [newLeagueName, setNewLeagueName] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [joinLeagueId, setJoinLeagueId] = useState<number | null>(null);
  const [detailLeague, setDetailLeague] = useState<any>(null);

  const refresh = () => {
    setLoading(true);
    leaguesApi
      .list()
      .then((res) => setLeagues(res.data.leagues || []))
      .catch(() => setError(t("common.error")))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refresh();
  }, [t]);

  const handleCreate = () => {
    if (!newLeagueName.trim()) return;
    leaguesApi
      .create(newLeagueName)
      .then(() => {
        setCreateOpen(false);
        setNewLeagueName("");
        refresh();
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
        refresh();
      })
      .catch((err: any) => {
        setError(err.response?.data?.detail || t("common.error"));
      });
  };

  const openJoin = (league: League) => {
    setJoinLeagueId(league.id);
    setJoinOpen(true);
  };

  const viewDetail = (id: number) => {
    leaguesApi
      .detail(id)
      .then((res) => setDetailLeague(res.data))
      .catch(() => setError(t("common.error")));
  };

  if (loading) {
    return (
      <Container sx={{ mt: 8, textAlign: "center" }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 4, mb: 8 }}>
      <Typography variant="h4" gutterBottom>{t("leagues.title")}</Typography>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Box sx={{ display: "flex", gap: 2, mb: 3 }}>
        <Button variant="contained" onClick={() => setCreateOpen(true)}>{t("leagues.create")}</Button>
      </Box>

      {leagues.length === 0 ? (
        <Alert severity="info">Du ar inte med i nagon liga an. Skapa en eller be om en inbjudningskod!</Alert>
      ) : (
        <List>
          {leagues.map((l) => (
            <Paper key={l.id} elevation={2} sx={{ mb: 2 }}>
              <ListItem
                secondaryAction={
                  l.is_admin ? (
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Chip size="small" label={t("leagues.admin")} color="primary" />
                      <IconButton
                        size="small"
                        onClick={() => navigator.clipboard.writeText(l.invite_code)}
                        title="Kopiera inbjudningskod"
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
                  secondary={l.is_admin ? `Kod: ${l.invite_code}` : ""}
                />
              </ListItem>
            </Paper>
          ))}
        </List>
      )}

      {/* Create dialog */}
      <Dialog open={createOpen} onClose={() => setCreateOpen(false)}>
        <DialogTitle>{t("leagues.create")}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Liganamn"
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
      <Dialog open={!!detailLeague} onClose={() => setDetailLeague(null)} maxWidth="sm" fullWidth>
        <DialogTitle>{detailLeague?.name}</DialogTitle>
        <DialogContent>
          <Typography variant="subtitle1" gutterBottom>{t("leagues.members")}:</Typography>
          <List>
            {detailLeague?.members?.map((m: any) => (
              <ListItem key={m.id}>
                <ListItemText primary={m.display_name || m.email} />
              </ListItem>
            )) || <Typography color="text.secondary">Inga medlemmar</Typography>}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailLeague(null)}>{t("common.close")}</Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
