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

  return (
    <Accordion defaultExpanded>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography variant="h6">{t("leaderboard.previous_matches")}</Typography>
      </AccordionSummary>
      <AccordionDetails>
        {past.length === 0 ? (
          <Alert severity="info">{t("leaderboard.no_past")}</Alert>
        ) : (
          past.map((matchday) => {
            // Sort matches within each day so latest kickoffs appear first
            const sortedMatches = [...matchday.matches].sort(
              (a, b) => new Date(b.kickoff).getTime() - new Date(a.kickoff).getTime()
            );
            return (
              <MatchdayGrid
                key={matchday.date}
                matchday={{ ...matchday, matches: sortedMatches }}
                memberOrder={memberOrder}
              />
            );
          })
        )}
      </AccordionDetails>
    </Accordion>
  );
}
