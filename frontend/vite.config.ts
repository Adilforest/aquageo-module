import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Dev server proxies /api to the Django backend (docker-compose web on :8000).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
