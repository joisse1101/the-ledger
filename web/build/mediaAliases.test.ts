import postcss from "postcss";
import { describe, expect, it } from "vitest";
import { MEDIA_ALIASES } from "../src/lib/breakpoints";
import { mediaAliases } from "./mediaAliases";

const aliases = { "--small": "(max-width: 10px)", "--big": "(min-width: 20px)" };

function run(css: string, map: Record<string, string> = aliases): Promise<string> {
  return postcss([mediaAliases(map)])
    .process(css, { from: undefined })
    .then((result) => result.css);
}

describe("mediaAliases", () => {
  it("replaces an alias with its query", async () => {
    expect(await run("@media (--small) { a { color: red } }")).toBe(
      "@media (max-width: 10px) { a { color: red } }",
    );
  });

  it("replaces an alias inside a compound query and leaves ordinary conditions alone", async () => {
    expect(await run("@media (--big) and (hover: hover) { a { color: red } }")).toBe(
      "@media (min-width: 20px) and (hover: hover) { a { color: red } }",
    );
  });

  it("fails the build on an unknown alias", async () => {
    await expect(run("@media (--nope) { a { color: red } }")).rejects.toThrow(
      /Unknown media alias --nope/,
    );
  });

  it("knows every alias the stylesheets use", async () => {
    for (const name of Object.keys(MEDIA_ALIASES)) {
      const css = await run(`@media (${name}) { a { color: red } }`, MEDIA_ALIASES);
      expect(css).not.toContain("--");
    }
  });
});
