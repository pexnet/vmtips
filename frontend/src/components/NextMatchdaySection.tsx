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

interface NextMatchdaySectionProps {
  upcoming: MatchdayGroup[];
  memberOrder?: string[];
}

export default function NextMatchdaySection({ upcoming, memberOrder }: NextMatchdaySectionProps) {
  const { t } = useTranslation();

  return (
    <Accordion defaultExpanded>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography variant="h6">{t("leaderboard.upcoming_matches")}</Typography>
      </AccordionSummary>
      <AccordionDetails>
        {upcoming.length === 0 ? (
          <Alert severity="info">{t("leaderboard.no_upcoming")}</Alert>
        ) : (
          upcoming.map((matchday) => (
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
