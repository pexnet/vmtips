import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Suspense, lazy } from "react";
import { AppThemeProvider } from "./contexts/ThemeContext";
import { AuthProvider } from "./contexts/AuthContext";
import { AppQueryClientProvider } from "./contexts/QueryClientProvider";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminRoute from "./components/AdminRoute";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import MatchesPage from "./pages/MatchesPage";
import LeaderboardPage from "./pages/LeaderboardPage";
import LeaguesPage from "./pages/LeaguesPage";
import ProfilePage from "./pages/ProfilePage";
import LeagueBonusQuestionsPage from "./pages/LeagueBonusQuestionsPage";
import InfoPage from "./pages/InfoPage";

const AdminPage = lazy(() => import("./pages/AdminPage"));

import "./i18n";

export default function App() {
  return (
    <BrowserRouter>
      <AppThemeProvider>
        <AppQueryClientProvider>
          <AuthProvider>
            <Navbar />
            <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/leaderboard" element={<LeaderboardPage />} />
            <Route path="/info" element={<InfoPage />} />
            <Route
              path="/matches"
              element={
                <ProtectedRoute>
                  <MatchesPage />
                </ProtectedRoute>
              }
            />
            {/* Legacy /predictions and /knockout redirect to /matches */}
            <Route path="/predictions" element={<Navigate to="/matches" />} />
            <Route path="/knockout" element={<Navigate to="/matches" />} />
            <Route
              path="/leagues"
              element={
                <ProtectedRoute>
                  <LeaguesPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/leagues/:leagueId/bonus-questions"
              element={
                <ProtectedRoute>
                  <LeagueBonusQuestionsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <ProfilePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin"
              element={
                <AdminRoute>
                  <Suspense fallback={<div style={{padding: 40, textAlign: 'center'}}>Loading...</div>}>
                    <AdminPage />
                  </Suspense>
                </AdminRoute>
              }
            />
            <Route path="*" element={<LeaderboardPage />} />
          </Routes>
        </AuthProvider>
      </AppQueryClientProvider>
    </AppThemeProvider>
  </BrowserRouter>
  );
}