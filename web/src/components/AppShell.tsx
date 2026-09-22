import { Outlet } from "react-router-dom";
import { useServerProblem } from "../api/serverStatus";
import { useViewportClass } from "../hooks/useViewportClass";
import { useTheme } from "../theme/theme";
import { Nav } from "./Nav";
import { RefreshControl } from "./RefreshControl";
import { ServerBanner, SignInNeeded } from "./ServerBanner";
import { ThemeToggle } from "./ThemeToggle";

/** Header, navigation and the page. The navigation is a top bar on medium and wide
 *  screens and a bottom tab bar on narrow ones; the refresh control and theme toggle
 *  stay in the header in both. */
export function AppShell() {
  const viewport = useViewportClass();
  const { theme, toggle } = useTheme();
  const { problem, retry } = useServerProblem();

  return (
    <div className="app" data-viewport={viewport}>
      <header className="topbar">
        <span className="brand">The Ledger</span>
        {viewport !== "narrow" && <Nav viewport={viewport} />}
        <span className="spacer" />
        <RefreshControl />
        <ThemeToggle theme={theme} onToggle={toggle} />
      </header>
      <ServerBanner problem={problem} onRetry={retry} />
      <main className="content">{problem === "unauthorized" ? <SignInNeeded /> : <Outlet />}</main>
      {viewport === "narrow" && <Nav viewport={viewport} />}
    </div>
  );
}
