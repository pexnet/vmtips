import { useState } from "react";
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Box,
  FormControl,
  Select,
  MenuItem,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import HomeIcon from "@mui/icons-material/Home";
import SportsSoccerIcon from "@mui/icons-material/SportsSoccer";
import LeaderboardIcon from "@mui/icons-material/Leaderboard";
import GroupsIcon from "@mui/icons-material/Groups";
import PersonIcon from "@mui/icons-material/Person";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import InfoIcon from "@mui/icons-material/Info";
import LoginIcon from "@mui/icons-material/Login";
import LogoutIcon from "@mui/icons-material/Logout";
import LanguageIcon from "@mui/icons-material/Language";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import { useNavigate, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../contexts/AuthContext";
import { useAppTheme } from "../contexts/ThemeContext";
import { useLeague } from "../contexts/LeagueContext";
import { useLeagues } from "../hooks/useLeagues";
import UserAvatar from "./UserAvatar";

export default function Navbar() {
  const { t, i18n } = useTranslation();
  const { user, isLoggedIn, logout } = useAuth();
  const { isDark, toggle } = useAppTheme();
  const navigate = useNavigate();
  const { selectedLeagueId, setSelectedLeagueId } = useLeague();
  const { data: leagues = [] } = useLeagues();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const closeDrawer = () => setDrawerOpen(false);

  const changeLang = () => {
    const next = i18n.language === "sv" ? "en" : "sv";
    i18n.changeLanguage(next);
  };

  const handleLogout = () => {
    closeDrawer();
    logout();
  };

  const goToLogin = () => {
    closeDrawer();
    navigate("/login");
  };

  const drawerNavItems = [
    { label: t("nav.home"), to: "/", icon: <HomeIcon /> },
    ...(isLoggedIn
      ? [
          { label: t("nav.matches"), to: "/matches", icon: <SportsSoccerIcon /> },
          { label: t("nav.leaderboard"), to: "/leaderboard", icon: <LeaderboardIcon /> },
          { label: t("nav.leagues"), to: "/leagues", icon: <GroupsIcon /> },
          { label: t("nav.profile"), to: "/profile", icon: <PersonIcon /> },
          ...(user?.is_admin
            ? [{ label: t("admin.title"), to: "/admin", icon: <AdminPanelSettingsIcon /> }]
            : []),
        ]
      : []),
    { label: t("nav.info"), to: "/info", icon: <InfoIcon /> },
  ];

  return (
    <AppBar position="static" elevation={2}>
      <Toolbar sx={{ display: "flex", justifyContent: "space-between", gap: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: { xs: 1, md: 2 }, minWidth: 0 }}>
          <Typography
            variant="h6"
            component={Link}
            to="/"
            sx={{
              textDecoration: "none",
              color: "inherit",
              fontWeight: 700,
              whiteSpace: "nowrap",
              fontSize: { xs: "1.1rem", sm: "1.25rem" },
            }}
          >
            {t("brand")}
          </Typography>

          <Box sx={{ display: { xs: "none", md: "flex" }, alignItems: "center", gap: 1 }}>
            {isLoggedIn && (
              <>
                <Button color="inherit" component={Link} to="/matches">
                  {t("nav.matches")}
                </Button>
                <Button color="inherit" component={Link} to="/leaderboard">
                  {t("nav.leaderboard")}
                </Button>
                <Button color="inherit" component={Link} to="/leagues">
                  {t("nav.leagues")}
                </Button>
                <Button color="inherit" component={Link} to="/profile">
                  {t("nav.profile")}
                </Button>
                {user?.is_admin && (
                  <Button color="inherit" component={Link} to="/admin">
                    {t("admin.title")}
                  </Button>
                )}
              </>
            )}
            <Button color="inherit" component={Link} to="/info">
              {t("nav.info")}
            </Button>
          </Box>
        </Box>

        <Box sx={{ display: { xs: "none", md: "flex" }, alignItems: "center", gap: 1 }}>
          {isLoggedIn && leagues.length > 0 && (
            <FormControl variant="standard" size="small" sx={{ minWidth: 120, mr: 1 }}>
              <Select
                value={selectedLeagueId ?? ""}
                onChange={(e) => setSelectedLeagueId(Number(e.target.value) || null)}
                displayEmpty
                sx={{
                  color: "inherit",
                  fontSize: "0.875rem",
                }}
              >
                {leagues.map((l) => (
                  <MenuItem key={l.id} value={l.id}>{l.name}</MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
          <IconButton color="inherit" onClick={changeLang} title={t("common.language")}>
            <LanguageIcon />
            <Typography variant="caption" sx={{ ml: 0.5 }}>
              {i18n.language.toUpperCase()}
            </Typography>
          </IconButton>
          <IconButton color="inherit" onClick={toggle} title={isDark ? t("common.light_mode") : t("common.dark_mode")}>
            {isDark ? <Brightness7Icon /> : <Brightness4Icon />}
          </IconButton>

          {isLoggedIn ? (
            <Button color="inherit" onClick={logout} sx={{ gap: 1 }}>
              <UserAvatar
                displayName={user?.display_name}
                firstName={user?.first_name}
                lastName={user?.last_name}
                email={user?.email}
                avatarUrl={user?.avatar_url}
                sx={{ width: 28, height: 28, fontSize: "0.75rem" }}
              />
              {t("nav.logout")}
            </Button>
          ) : (
            <Button color="inherit" onClick={() => navigate("/login")}>
              {t("nav.login")}
            </Button>
          )}
        </Box>

        <IconButton
          color="inherit"
          edge="end"
          onClick={() => setDrawerOpen(true)}
          aria-label={t("common.open_navigation_menu")}
          sx={{ display: { xs: "inline-flex", md: "none" } }}
        >
          <MenuIcon />
        </IconButton>
      </Toolbar>

      <Drawer anchor="right" open={drawerOpen} onClose={closeDrawer}>
        <Box sx={{ width: 300, maxWidth: "86vw", py: 1 }} role="presentation">
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.25, px: 2, py: 1.25 }}>
            {isLoggedIn && (
              <UserAvatar
                displayName={user?.display_name}
                firstName={user?.first_name}
                lastName={user?.last_name}
                email={user?.email}
                avatarUrl={user?.avatar_url}
                sx={{ width: 36, height: 36, fontSize: "0.8rem" }}
              />
            )}
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 800 }} noWrap>
                {t("brand")}
              </Typography>
              {isLoggedIn && (
                <Typography variant="caption" color="text.secondary" noWrap>
                  {user?.display_name || user?.email}
                </Typography>
              )}
            </Box>
          </Box>

          {isLoggedIn && leagues.length > 0 && (
            <Box sx={{ px: 2, pb: 1.5 }}>
              <FormControl fullWidth size="small">
                <Select
                  value={selectedLeagueId ?? ""}
                  onChange={(e) => setSelectedLeagueId(Number(e.target.value) || null)}
                  displayEmpty
                >
                  {leagues.map((l) => (
                    <MenuItem key={l.id} value={l.id}>{l.name}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
          )}

          <Divider />

          <List>
            {drawerNavItems.map((item) => (
              <ListItemButton key={item.to} component={Link} to={item.to} onClick={closeDrawer}>
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItemButton>
            ))}
          </List>

          <Divider />

          <List>
            <ListItemButton
              onClick={() => {
                changeLang();
                closeDrawer();
              }}
            >
              <ListItemIcon><LanguageIcon /></ListItemIcon>
              <ListItemText primary={t("common.language")} secondary={i18n.language.toUpperCase()} />
            </ListItemButton>
            <ListItemButton
              onClick={() => {
                toggle();
                closeDrawer();
              }}
            >
              <ListItemIcon>{isDark ? <Brightness7Icon /> : <Brightness4Icon />}</ListItemIcon>
              <ListItemText primary={isDark ? t("common.light_mode") : t("common.dark_mode")} />
            </ListItemButton>
            {isLoggedIn ? (
              <ListItemButton onClick={handleLogout}>
                <ListItemIcon><LogoutIcon /></ListItemIcon>
                <ListItemText primary={t("nav.logout")} />
              </ListItemButton>
            ) : (
              <ListItemButton onClick={goToLogin}>
                <ListItemIcon><LoginIcon /></ListItemIcon>
                <ListItemText primary={t("nav.login")} />
              </ListItemButton>
            )}
          </List>
        </Box>
      </Drawer>
    </AppBar>
  );
}
