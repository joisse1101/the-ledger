import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Both `npm run dev` and `npm run preview` forward /api to the Python server, so the
// page is always same-origin with the API — the built app (and the gateway proxying to
// it) never needs to know the API's own port.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8501",
    },
  },
  preview: {
    proxy: {
      "/api": "http://127.0.0.1:8501",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
  },
});
