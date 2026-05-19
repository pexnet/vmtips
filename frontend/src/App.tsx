import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Suspense, lazy } from "react";
import { AppThemeProvider } from "./contexts/ThemeContext";
import { AuthProvider } from "./contexts/AuthContext";
import { LeagueProvider } from "./contexts/LeagueContext";
import { AppQueryClientProvider } from "./contexts/QueryClientProvider";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminRoute from "./components/AdminRoute";

const HomePage = lazy(() => import("./pages/HomePage"));
const LoginPage = lazy(() => import("./pages/LoginPage"));
const RegisterPage = lazy(() => import("./pages/RegisterPage"));
const MatchesPage = lazy(() => import("./pages/MatchesPage"));
const LeaderboardPage = lazy(() => import("./pages/LeaderboardPage"));
const LeaguesPage = lazy(() => import("./pages/LeaguesPage"));
const ProfilePage = lazy(() => import("./pages/ProfilePage"));
const LeagueBonusQuestionsPage = lazy(() => import("./pages/LeagueBonusQuestionsPage"));
const InfoPage = lazy(() => import("./pages/InfoPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));

import "./i18n";

export default function App() {
  return (
    <BrowserRouter>
      <AppThemeProvider>
        <AppQueryClientProvider>
          <AuthProvider>
            <LeagueProvider>
              <Navbar />
              <Suspense fallback={<div style={{ padding: 40, textAlign: "center" }}>Loading...</div>}>
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
                  {/* Legacy /predictions redirect to /matches */}
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
                        <AdminPage />
                      </AdminRoute>
                    }
                  />
                  <Route path="*" element={<LeaderboardPage />} />
                </Routes>
              </Suspense>
            </LeagueProvider>
          </AuthProvider>
        </AppQueryClientProvider>
      </AppThemeProvider>
    </BrowserRouter>
  );
}
