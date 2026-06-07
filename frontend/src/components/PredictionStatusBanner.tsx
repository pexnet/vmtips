import { Alert } from "@mui/material";
import { useTranslation } from "react-i18next";

import { usePredictionStatus } from "../hooks/usePredictionStatus";

export default function PredictionStatusBanner({ leagueId }: { leagueId: number | null }) {
  const { t } = useTranslation();
  const status = usePredictionStatus(leagueId);

  if (!leagueId || status.round === "closed") {
    return <Alert severity="info" sx={{ mb: 2 }}>{t("predictionStatus.closed")}</Alert>;
  }
  if (status.missing === 0) {
    return (
      <Alert severity="success" sx={{ mb: 2 }}>
        {t(`predictionStatus.${status.round}Complete`, status)}
      </Alert>
    );
  }
  return (
    <Alert severity="warning" sx={{ mb: 2 }}>
      {t(`predictionStatus.${status.round}Remaining`, status)}
    </Alert>
  );
}
