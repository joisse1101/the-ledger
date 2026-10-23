import { describe, expect, it } from "vitest";
import { groupColorMap, groupNoun } from "./chartTheme";

describe("groupNoun", () => {
  it("words a worktree chart's rows as branch / worktree", () => {
    expect(groupNoun("worktree")).toBe("branch / worktree");
  });

  it("leaves the other labels as they are", () => {
    expect(groupNoun("project")).toBe("project");
    expect(groupNoun("branch")).toBe("branch");
  });
});

describe("groupColorMap", () => {
  it("gives a worktree entry and a branch entry of the same name different colours", () => {
    const colors = groupColorMap(["fix", "wt fix", "Other"], ["#111", "#222", "#333"], "#999");
    expect(colors.get("fix")).not.toBe(colors.get("wt fix"));
    expect(colors.get("Other")).toBe("#999");
  });
});
