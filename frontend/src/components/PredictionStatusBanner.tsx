import { Alert, Box } from "@mui/material";
import { useTranslation } from "react-i18next";

import { usePredictionStatus } from "../hooks/usePredictionStatus";

export default function PredictionStatusBanner({ leagueId }: { leagueId: number | null }) {
  const { t } = useTranslation();
  const status = usePredictionStatus(leagueId);

  if (!leagueId || status.round === "closed") {
    return <Alert severity="info" sx={{ mb: 2 }}>{t("predictionStatus.closed")}</Alert>;
  }

  const hasMissingMatchPredictions = status.missing > 0;
  const hasMissingBonuses = status.round === "group" && status.bonusMissing > 0;
  const severity = hasMissingMatchPredictions || hasMissingBonuses ? "warning" : "success";

  return (
    <Alert severity={severity} sx={{ mb: 2 }}>
      <Box component="span" sx={{ display: "block" }}>
        {t(
          `predictionStatus.${status.round}${hasMissingMatchPredictions ? "Remaining" : "Complete"}`,
          status,
        )}
      </Box>
      {status.round === "group" && (
        <Box component="span" sx={{ display: "block", mt: 0.5 }}>
          {t(
            `predictionStatus.${hasMissingBonuses ? "bonusRemaining" : "bonusComplete"}`,
            status,
          )}
        </Box>
      )}
    </Alert>
  );
}
