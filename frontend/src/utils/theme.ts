import { createTheme, type ThemeOptions } from "@mui/material/styles";

const commonOptions: ThemeOptions = {
  typography: {
    fontFamily: "'Roboto', 'Helvetica Neue', Arial, sans-serif",
    h4: { fontWeight: 700 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
  },
  shape: {
    borderRadius: 8,
  },
};

export const lightTheme = createTheme({
  ...commonOptions,
  palette: {
    mode: "light",
    primary: { main: "#1976d2" },
    secondary: { main: "#dc004e" },
    background: {
      default: "#f5f5f5",
      paper: "#ffffff",
    },
    text: {
      primary: "#212121",
      secondary: "#757575",
    },
  },
});

export const darkTheme = createTheme({
  ...commonOptions,
  palette: {
    mode: "dark",
    primary: { main: "#90caf9" },
    secondary: { main: "#f48fb1" },
    background: {
      default: "#121212",
      paper: "#1e1e1e",
    },
    text: {
      primary: "#e0e0e0",
      secondary: "#9e9e9e",
    },
  },
});
