import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Alert,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import type { MatchdayGroup } from "../types/api";
import MatchdayGrid from "./MatchdayGrid";

interface PreviousMatchesSectionProps {
  past: MatchdayGroup[];
  memberOrder?: string[];
}

export default function PreviousMatchesSection({ past, memberOrder }: PreviousMatchesSectionProps) {
  const { t } = useTranslation();

  // Sort matches within each day once — latest kickoffs first.
  const sortedPast = useMemo(
    () =>
      past.map((matchday) => ({
        ...matchday,
        matches: [...matchday.matches].sort(
          (a, b) => new Date(b.kickoff).getTime() - new Date(a.kickoff).getTime()
        ),
      })),
    [past]
  );

  return (
    <Accordion defaultExpanded>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography variant="h6">{t("leaderboard.previous_matches")}</Typography>
      </AccordionSummary>
      <AccordionDetails>
        {sortedPast.length === 0 ? (
          <Alert severity="info">{t("leaderboard.no_past")}</Alert>
        ) : (
          sortedPast.map((matchday) => (
            <MatchdayGrid
              key={matchday.date}
              matchday={matchday}
              memberOrder={memberOrder}
            />
          ))
        )}
      </AccordionDetails>
    </Accordion>
  );
}
