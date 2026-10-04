import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // Local dev: forward /api to the FastAPI backend so no CORS setup is needed.
    proxy: { "/api": "http://localhost:8000" },
  },
});
