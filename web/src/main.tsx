import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import { consumeTokenFromUrl } from "./api/token";
import { createQueryClient } from "./api/queryClient";
import "./theme/tokens.css";
import "./styles/app.css";
import "./styles/sessions.css";
import "./styles/overview.css";

// Before anything renders: a printed link's `?token=` signs this device in and is
// then stripped from the address bar (network-access spec).
consumeTokenFromUrl();

const queryClient = createQueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
