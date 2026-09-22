import type { Theme } from "../theme/theme";
import { MoonIcon, SunIcon } from "./icons";

export function ThemeToggle({ theme, onToggle }: { theme: Theme; onToggle: () => void }) {
  const dark = theme === "dark";
  return (
    <button
      type="button"
      className="icon-button"
      role="switch"
      aria-checked={dark}
      aria-label="Dark mode"
      title={dark ? "Switch to light mode" : "Switch to dark mode"}
      onClick={onToggle}
    >
      {dark ? <MoonIcon /> : <SunIcon />}
    </button>
  );
}
