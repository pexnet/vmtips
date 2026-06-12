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
  upcoming: MatchdayGroup | null;
  memberOrder?: string[];
}

export default function NextMatchdaySection({ upcoming, memberOrder }: NextMatchdaySectionProps) {
  const { t } = useTranslation();

  return (
    <Accordion defaultExpanded>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography variant="h6">{t("leaderboard.next_matchday")}</Typography>
      </AccordionSummary>
      <AccordionDetails>
        {!upcoming || upcoming.matches.length === 0 ? (
          <Alert severity="info">{t("leaderboard.no_upcoming")}</Alert>
        ) : (
          <MatchdayGrid matchday={upcoming} memberOrder={memberOrder} />
        )}
      </AccordionDetails>
    </Accordion>
  );
}
