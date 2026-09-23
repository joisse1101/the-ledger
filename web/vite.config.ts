import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Both `npm run dev` and `npm run preview` forward /api to the Python server, so the
// page is always same-origin with the API — the built app (and the gateway proxying to
// it) never needs to know the API's own port. The target reads BACKEND_PORT from the
// environment (not baked into the client bundle, unlike the removed VITE_API_PORT) so
// direct (non-gateway) frontend access keeps working when BACKEND_PORT is customized.
const backendTarget = `http://127.0.0.1:${process.env.BACKEND_PORT ?? 8501}`;

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    proxy: {
      "/api": backendTarget,
    },
  },
  preview: {
    host: "127.0.0.1",
    proxy: {
      "/api": backendTarget,
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
  },
});
