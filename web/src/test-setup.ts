import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import "@testing-library/jest-dom/vitest";

// Unmounts whatever the previous test rendered so DOM queries in the next test
// (screen.getByText etc.) only ever see that test's own output.
afterEach(cleanup);
