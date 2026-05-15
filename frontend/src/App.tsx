import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppThemeProvider } from "./contexts/ThemeContext";
import { AuthProvider } from "./contexts/AuthContext";
import Navbar from "./components/Navbar";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import MatchesPage from "./pages/MatchesPage";
import PredictionsPage from "./pages/PredictionsPage";
import LeaderboardPage from "./pages/LeaderboardPage";
import LeaguesPage from "./pages/LeaguesPage";
import AdminPage from "./pages/AdminPage";

import "./i18n";

export default function App() {
  return (
    <BrowserRouter>
      <AppThemeProvider>
        <AuthProvider>
          <Navbar />
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/matches" element={<MatchesPage />} />
            <Route path="/predictions" element={<PredictionsPage />} />
            <Route path="/leaderboard" element={<LeaderboardPage />} />
            <Route path="/leagues" element={<LeaguesPage />} />
            <Route path="/admin" element={<AdminPage />} />
          </Routes>
        </AuthProvider>
      </AppThemeProvider>
    </BrowserRouter>
  );
}
