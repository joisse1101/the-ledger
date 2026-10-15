import { describe, expect, it } from "vitest";
import type { TooltipContent } from "../../lib/contextBreakdown";
import { breakdownTooltipHtml } from "./TokensChart";

const escape = (value: string) => value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const content: TooltipContent = {
  title: "Response 2: 28,300 tokens",
  lines: [
    { name: "Everything else", value: "15,800 (56%)" },
    { name: "Skills", value: "~6,700 (24%)" },
  ],
  estimateNote: "~ estimated from the transcript",
};

describe("breakdownTooltipHtml", () => {
  it("lists the title, each category with its figure, and the estimate note", () => {
    const html = breakdownTooltipHtml(content, escape);

    expect(html).toContain("<h2>Response 2: 28,300 tokens</h2>");
    expect(html).toContain("Skills:</td><td class=\"value\">~6,700 (24%)</td>");
    expect(html).toContain("~ estimated from the transcript");
  });

  it("omits the estimate note when there is none", () => {
    expect(breakdownTooltipHtml({ ...content, estimateNote: null }, escape)).not.toContain("estimated");
  });

  it("escapes names that come from the transcript", () => {
    const html = breakdownTooltipHtml({ ...content, lines: [{ name: "<img src=x onerror=alert(1)>", value: "1 (1%)" }] }, escape);

    expect(html).not.toContain("<img");
    expect(html).toContain("&lt;img");
  });
});
