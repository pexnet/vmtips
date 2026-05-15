import { AppBar, Toolbar, Typography, Button, IconButton, Box } from "@mui/material";
import LanguageIcon from "@mui/icons-material/Language";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import { useNavigate, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../contexts/AuthContext";
import { useAppTheme } from "../contexts/ThemeContext";

export default function Navbar() {
  const { t, i18n } = useTranslation();
  const { user, isLoggedIn, logout } = useAuth();
  const { isDark, toggle } = useAppTheme();
  const navigate = useNavigate();

  const changeLang = () => {
    const next = i18n.language === "sv" ? "en" : "sv";
    i18n.changeLanguage(next);
  };

  return (
    <AppBar position="static" elevation={2}>
      <Toolbar sx={{ display: "flex", justifyContent: "space-between" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Typography
            variant="h6"
            component={Link}
            to="/"
            sx={{ textDecoration: "none", color: "inherit", fontWeight: 700 }}
          >
            {t("brand")}
          </Typography>

          {isLoggedIn && (
            <>
              <Button color="inherit" component={Link} to="/matches">
                {t("nav.matches")}
              </Button>
              <Button color="inherit" component={Link} to="/predictions">
                {t("nav.predictions")}
              </Button>
              <Button color="inherit" component={Link} to="/knockout">
                {t("nav.knockout")}
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
            </>
          )}
        </Box>

        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
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
            <Button color="inherit" onClick={logout}>
              {t("nav.logout")} ({user?.display_name || user?.email})
            </Button>
          ) : (
            <Button color="inherit" onClick={() => navigate("/login")}>
              {t("nav.login")}
            </Button>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
}
