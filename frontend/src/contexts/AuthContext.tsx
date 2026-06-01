import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "../api/client";
import type { User } from "../types/api";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isLoggedIn: boolean;
  login: (token: string) => void;
  logout: () => void;
  refreshUser: () => Promise<User | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setUser(null);
    navigate("/login");
  }, [navigate]);

  const refreshUser = useCallback(async () => {
    const res = await authApi.me();
    const nextUser = res.data as User;
    setUser(nextUser);
    return nextUser;
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      authApi
        .me()
        .then((res) => setUser(res.data as User))
        .catch(() => {
          localStorage.removeItem("token");
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }

    // Listen for 401 events from axios interceptor
    const handleAuth401 = () => {
      setUser(null);
      navigate("/login");
    };
    window.addEventListener("auth:401", handleAuth401);
    return () => window.removeEventListener("auth:401", handleAuth401);
  }, [navigate]);

  const login = (token: string) => {
    localStorage.setItem("token", token);
    refreshUser().then(() => {
      navigate("/leaderboard");
    });
  };

  return (
    <AuthContext.Provider
      value={{ user, isLoading, isLoggedIn: !!user, login, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
