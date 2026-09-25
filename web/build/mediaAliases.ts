import type { Plugin } from "postcss";

const ALIAS_IN_QUERY = /\((--[\w-]+)\)/g;

/** PostCSS plugin that swaps `@media (--name)` for the query `aliases` gives that name, so the
 *  stylesheets share their width boundaries with the TypeScript (see src/lib/breakpoints.ts).
 *  CSS can't do this itself: custom properties don't work inside a media condition. An unknown
 *  name fails the build rather than shipping a query the browser would silently never match. */
export function mediaAliases(aliases: Readonly<Record<string, string>>): Plugin {
  return {
    postcssPlugin: "ledger-media-aliases",
    AtRule: {
      media(atRule) {
        atRule.params = atRule.params.replace(ALIAS_IN_QUERY, (_match, name: string) => {
          const query = aliases[name];
          if (!query) throw atRule.error(`Unknown media alias ${name}`);
          return query;
        });
      },
    },
  };
}
