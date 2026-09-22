import { describe, expect, it } from "vitest";
import { classForWidth } from "./useViewportClass";

describe("classForWidth", () => {
  it("is narrow below 640", () => {
    expect(classForWidth(320)).toBe("narrow");
    expect(classForWidth(639)).toBe("narrow");
  });

  it("is medium from 640 up to 1023", () => {
    expect(classForWidth(640)).toBe("medium");
    expect(classForWidth(1023)).toBe("medium");
  });

  it("is wide from 1024 up", () => {
    expect(classForWidth(1024)).toBe("wide");
    expect(classForWidth(1920)).toBe("wide");
  });
});
