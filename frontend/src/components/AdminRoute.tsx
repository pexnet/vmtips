import { Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) return null;
  if (!user) return <Navigate to="/login" replace />;
  // Check admin status — backend enforces via ADMIN_USER_ID
  // For now, we check if user ID matches the backend admin check
  // The backend /admin endpoints will reject non-admins anyway
  if (!user.is_admin && user.id !== 1) {
    return <Navigate to="/leaderboard" replace />;
  }

  return <>{children}</>;
}