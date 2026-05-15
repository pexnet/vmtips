import { Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) return null;
  if (!user) return <Navigate to="/login" replace />;
  // Global admin flag from backend; backend admin endpoints enforce independently
  if (!user.is_admin) {
    return <Navigate to="/leaderboard" replace />;
  }

  return <>{children}</>;
}