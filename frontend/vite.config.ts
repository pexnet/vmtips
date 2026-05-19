import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return;
          if (id.includes("/react") || id.includes("react-router-dom")) return "react";
          if (id.includes("@mui") || id.includes("@emotion")) return "mui";
          if (id.includes("@tanstack/react-query")) return "query";
          if (id.includes("i18next") || id.includes("react-i18next")) return "i18n";
          if (id.includes("axios")) return "axios";
          return "vendor";
        },
      },
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        // Note: do NOT rewrite /api away — backend routers now use prefix="/api"
      },
    },
  },
});
