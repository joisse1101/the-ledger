import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import "@testing-library/jest-dom/vitest";

// jsdom has no ResizeObserver, and it never lays anything out, so a stub that never fires is
// enough: components that observe size do their initial measurement synchronously anyway.
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// jsdom doesn't implement <dialog>'s showModal()/close(). These stand-ins do the two things the
// components rely on: toggle `open`, and fire `close` when an open dialog closes. They can't model
// the real browser's focus trap, inert background or Esc handling.
HTMLDialogElement.prototype.showModal ??= function showModal(this: HTMLDialogElement) {
  this.setAttribute("open", "");
};
HTMLDialogElement.prototype.close ??= function close(this: HTMLDialogElement) {
  if (!this.hasAttribute("open")) return;
  this.removeAttribute("open");
  this.dispatchEvent(new Event("close"));
};

// Unmounts whatever the previous test rendered so DOM queries in the next test
// (screen.getByText etc.) only ever see that test's own output.
afterEach(cleanup);
