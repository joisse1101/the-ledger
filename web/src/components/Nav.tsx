import { NavLink } from "react-router-dom";
import type { ViewportClass } from "../hooks/useViewportClass";
import { OverviewIcon, ProjectsIcon, SessionsIcon } from "./icons";

const PAGES = [
  { to: "/", label: "Sessions", icon: <SessionsIcon />, end: true },
  { to: "/overview", label: "Overview", icon: <OverviewIcon />, end: false },
  { to: "/projects", label: "Projects", icon: <ProjectsIcon />, end: false },
];

/** The same three links either way: inline in the top bar (medium, wide) or a tab
 *  bar fixed to the bottom of the screen where a thumb can reach it (narrow). */
export function Nav({ viewport }: { viewport: ViewportClass }) {
  const bottom = viewport === "narrow";
  return (
    <nav className={bottom ? "nav nav--bottom" : "nav nav--top"} aria-label="Pages">
      {PAGES.map(({ to, label, icon, end }) => (
        <NavLink key={to} to={to} end={end} className="nav-link">
          {bottom && icon}
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
