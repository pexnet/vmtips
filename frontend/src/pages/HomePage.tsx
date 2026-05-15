import { Typography, Container, Paper, Box } from "@mui/material";
import { useTranslation } from "react-i18next";

export default function HomePage() {
  const { t } = useTranslation();

  return (
    <Container maxWidth="md" sx={{ mt: 6 }}>
      <Paper elevation={3} sx={{ p: 4, textAlign: "center" }}>
        <Box sx={{ fontSize: 64 }}>⚽</Box>
        <Typography variant="h3" gutterBottom>
          VMTips
        </Typography>
        <Typography variant="h6" color="text.secondary" gutterBottom>
          FIFA World Cup 2026
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
          {t("wc2026.dates")} &middot; {t("wc2026.location")}
        </Typography>
      </Paper>
    </Container>
  );
}
