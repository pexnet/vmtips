import { useEffect, useState } from "react";
import {
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";

import { adminApi } from "../../api/client";
import { getErrorDetail, type AdminUser } from "../../types/api";

type Notify = (kind: "error" | "success", message: string) => void;
type AdminLeague = { id: number; name: string };
type UserForm = {
  email: string;
  password: string;
  display_name: string;
  first_name: string;
  last_name: string;
  is_admin: boolean;
  is_active: boolean;
  league_ids: number[];
};

const emptyForm: UserForm = {
  email: "",
  password: "",
  display_name: "",
  first_name: "",
  last_name: "",
  is_admin: false,
  is_active: true,
  league_ids: [],
};

export default function UsersTab({ notify }: { notify: Notify }) {
  const { t } = useTranslation();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [leagues, setLeagues] = useState<AdminLeague[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<UserForm>(emptyForm);

  function loadData() {
    setLoading(true);
    Promise.all([adminApi.listUsers(), adminApi.listLeagues()])
      .then(([usersResponse, leaguesResponse]) => {
        setUsers(usersResponse.data as AdminUser[]);
        setLeagues(leaguesResponse.data as AdminLeague[]);
      })
      .catch((error: unknown) => notify("error", getErrorDetail(error)))
      .finally(() => setLoading(false));
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadData(); }, []);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setDialogOpen(true);
  }

  function openEdit(user: AdminUser) {
    setEditing(user);
    setForm({
      email: user.email,
      password: "",
      display_name: user.display_name || "",
      first_name: user.first_name || "",
      last_name: user.last_name || "",
      is_admin: user.is_admin,
      is_active: user.is_active,
      league_ids: user.league_ids,
    });
    setDialogOpen(true);
  }

  function saveUser() {
    const payload = {
      email: form.email.trim(),
      display_name: form.display_name.trim(),
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      is_admin: form.is_admin,
      is_active: form.is_active,
      league_ids: form.league_ids,
      ...(form.password ? { password: form.password } : {}),
    };
    const request = editing
      ? adminApi.updateUser(editing.id, payload)
      : adminApi.createUser({ ...payload, password: form.password });
    request
      .then(() => {
        notify("success", t("admin.user_saved"));
        setDialogOpen(false);
        loadData();
      })
      .catch((error: unknown) => notify("error", getErrorDetail(error)));
  }

  function toggleActive(user: AdminUser) {
    if (!window.confirm(t(user.is_active ? "admin.disable_user_confirm" : "admin.enable_user_confirm"))) return;
    adminApi.updateUser(user.id, { is_active: !user.is_active })
      .then(() => {
        notify("success", t("admin.user_saved"));
        loadData();
      })
      .catch((error: unknown) => notify("error", getErrorDetail(error)));
  }

  const valid = Boolean(
    form.email.trim() &&
    form.display_name.trim() &&
    (editing || form.password.length >= 6),
  );

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h6">{t("admin.user_management")}</Typography>
        <Button variant="contained" onClick={openCreate}>{t("admin.create_user")}</Button>
      </Box>
      {loading ? <CircularProgress /> : (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t("admin.user")}</TableCell>
                <TableCell>{t("profile.email")}</TableCell>
                <TableCell>{t("admin.league_members")}</TableCell>
                <TableCell>{t("admin.status")}</TableCell>
                <TableCell>{t("admin.last_login")}</TableCell>
                <TableCell align="right">{t("common.actions")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id} sx={{ opacity: user.is_active ? 1 : 0.55 }}>
                  <TableCell>
                    {user.display_name}
                    {user.is_admin && <Chip size="small" label={t("admin.admin_role")} sx={{ ml: 1 }} />}
                  </TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>
                    {user.league_ids.map((id) => (
                      <Chip key={id} size="small" label={leagues.find((league) => league.id === id)?.name || id} sx={{ mr: 0.5 }} />
                    ))}
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      color={user.is_active ? "success" : "default"}
                      label={t(user.is_active ? "admin.active" : "admin.disabled")}
                    />
                  </TableCell>
                  <TableCell>
                    {user.last_login_at
                      ? new Date(user.last_login_at).toLocaleString()
                      : t("admin.never")}
                  </TableCell>
                  <TableCell align="right">
                    <Button size="small" onClick={() => openEdit(user)}>{t("common.edit")}</Button>
                    <Button size="small" color={user.is_active ? "error" : "success"} onClick={() => toggleActive(user)}>
                      {t(user.is_active ? "admin.disable" : "admin.enable")}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{t(editing ? "admin.edit_user" : "admin.create_user")}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "12px !important" }}>
          <TextField label={t("profile.email")} value={form.email} onChange={(event) => setForm((value) => ({ ...value, email: event.target.value }))} />
          <TextField label={t("profile.nickname")} value={form.display_name} onChange={(event) => setForm((value) => ({ ...value, display_name: event.target.value }))} />
          <TextField label={t("profile.first_name")} value={form.first_name} onChange={(event) => setForm((value) => ({ ...value, first_name: event.target.value }))} />
          <TextField label={t("profile.last_name")} value={form.last_name} onChange={(event) => setForm((value) => ({ ...value, last_name: event.target.value }))} />
          <TextField
            label={t(editing ? "admin.new_password" : "auth.password")}
            type="password"
            value={form.password}
            onChange={(event) => setForm((value) => ({ ...value, password: event.target.value }))}
            required={!editing}
          />
          <FormControl>
            <InputLabel>{t("admin.league_members")}</InputLabel>
            <Select
              multiple
              value={form.league_ids}
              label={t("admin.league_members")}
              onChange={(event) => setForm((value) => ({ ...value, league_ids: event.target.value as number[] }))}
            >
              {leagues.map((league) => <MenuItem key={league.id} value={league.id}>{league.name}</MenuItem>)}
            </Select>
          </FormControl>
          <Box>
            <FormControlLabel control={<Checkbox checked={form.is_admin} onChange={(event) => setForm((value) => ({ ...value, is_admin: event.target.checked }))} />} label={t("admin.admin_role")} />
            <FormControlLabel control={<Checkbox checked={form.is_active} onChange={(event) => setForm((value) => ({ ...value, is_active: event.target.checked }))} />} label={t("admin.active")} />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>{t("common.cancel")}</Button>
          <Button variant="contained" disabled={!valid} onClick={saveUser}>{t("common.save")}</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
