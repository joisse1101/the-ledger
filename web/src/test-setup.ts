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

// Unmounts whatever the previous test rendered so DOM queries in the next test
// (screen.getByText etc.) only ever see that test's own output.
afterEach(cleanup);
