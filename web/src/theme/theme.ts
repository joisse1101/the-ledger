import { useCallback, useSyncExternalStore } from "react";

export type Theme = "light" | "dark";

export const THEME_STORAGE_KEY = "ledger-theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";

/** This device's saved choice, or null. Storage can be missing or throw (private
 *  windows, blocked site data), so every access is guarded and the app still works. */
export function readStoredTheme(): Theme | null {
  try {
    const value = window.localStorage.getItem(THEME_STORAGE_KEY);
    return value === "light" || value === "dark" ? value : null;
  } catch {
    return null;
  }
}

function writeStoredTheme(theme: Theme): void {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Not remembered, but the toggle still works for this visit.
  }
}

export function systemTheme(): Theme {
  return typeof window.matchMedia === "function" && window.matchMedia(DARK_QUERY).matches
    ? "dark"
    : "light";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
}

// One module-level store rather than per-component state: useTheme() is called both by the
// toggle button and by every chart that needs to know when to recolor itself (TokensChart, and
// the Overview page's three charts), and with a component-local useState per call site, toggling
// in one of them would never notify the others. A shared store (read via useSyncExternalStore,
// the same pattern useViewportClass uses) keeps every mounted instance in agreement instead.
let storedTheme: Theme | null = readStoredTheme();
let systemPreference: Theme = systemTheme();
const listeners = new Set<() => void>();

function currentTheme(): Theme {
  return storedTheme ?? systemPreference;
}

function notify(): void {
  applyTheme(currentTheme());
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

let mediaListenerAttached = false;
function ensureMediaListener(): void {
  if (mediaListenerAttached || typeof window.matchMedia !== "function") return;
  mediaListenerAttached = true;
  window.matchMedia(DARK_QUERY).addEventListener("change", (event) => {
    systemPreference = event.matches ? "dark" : "light";
    notify();
  });
}

applyTheme(currentTheme()); // seed <html data-theme> before the first component even mounts

/** The active theme and a toggle, shared across every call site (see the store comment above).
 *  With no saved choice it follows the device's own setting (live, if that changes); once
 *  toggled, the choice is this device's alone. */
export function useTheme(): { theme: Theme; toggle: () => void } {
  ensureMediaListener();
  const theme = useSyncExternalStore(subscribe, currentTheme, (): Theme => "light");

  const toggle = useCallback(() => {
    const next: Theme = currentTheme() === "dark" ? "light" : "dark";
    writeStoredTheme(next);
    storedTheme = next;
    notify();
  }, []);

  return { theme, toggle };
}
