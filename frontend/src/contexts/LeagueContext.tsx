import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import { useLeagues } from "../hooks/useLeagues";

interface LeagueContextType {
  selectedLeagueId: number | null;
  setSelectedLeagueId: (id: number | null) => void;
}

const LeagueContext = createContext<LeagueContextType | undefined>(undefined);

export function LeagueProvider({ children }: { children: ReactNode }) {
  const [selectedLeagueId, setSelectedLeagueId] = useState<number | null>(() => {
    const saved = localStorage.getItem("selected_league_id");
    return saved ? Number(saved) : null;
  });

  const { data: leagues = [] } = useLeagues();

  // Auto-select the first available league when none is selected, and clear
  // stale selections left in localStorage when switching between accounts.
  useEffect(() => {
    if (leagues.length === 0) {
      if (selectedLeagueId) {
        setSelectedLeagueId(null);
        localStorage.removeItem("selected_league_id");
      }
      return;
    }

    const selectedIsAvailable = leagues.some((league) => league.id === selectedLeagueId);
    if (!selectedLeagueId || !selectedIsAvailable) {
      const first = leagues[0].id;
      setSelectedLeagueId(first);
      localStorage.setItem("selected_league_id", String(first));
    }
  }, [selectedLeagueId, leagues]);

  const handleSet = (id: number | null) => {
    setSelectedLeagueId(id);
    if (id) {
      localStorage.setItem("selected_league_id", String(id));
    } else {
      localStorage.removeItem("selected_league_id");
    }
  };

  return (
    <LeagueContext.Provider value={{ selectedLeagueId, setSelectedLeagueId: handleSet }}>
      {children}
    </LeagueContext.Provider>
  );
}

export function useLeague() {
  const ctx = useContext(LeagueContext);
  if (!ctx) throw new Error("useLeague must be used within LeagueProvider");
  return ctx;
}
