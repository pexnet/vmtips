import { Container, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

export default function MatchesPage() {
  const { t } = useTranslation();
  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4">{t("matches.title")}</Typography>
    </Container>
  );
}
