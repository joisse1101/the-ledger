import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useSyncExternalStore } from "react";
import { NetworkError, UnauthorizedError } from "./client";

/** What, if anything, is wrong with the server, judged from the queries on screen.
 *  A query whose refetch failed keeps its last data, so the page can carry on showing
 *  it under a banner; this is what tells the banner to appear, and to go away again
 *  when polling reaches the server. */
export type ServerProblem = "none" | "unauthorized" | "unreachable" | "error";

export function useServerProblem(): { problem: ServerProblem; retry: () => void } {
  const client = useQueryClient();
  const cache = client.getQueryCache();

  const problem = useSyncExternalStore(
    useCallback((onChange) => cache.subscribe(onChange), [cache]),
    (): ServerProblem => {
      let sawNetworkError = false;
      let sawOtherError = false;
      for (const query of cache.getAll()) {
        // Only queries something is showing: a page the user left can't be out of date.
        if (query.state.status !== "error" || query.getObserversCount() === 0) continue;
        const error = query.state.error;
        if (error instanceof UnauthorizedError) return "unauthorized";
        if (error instanceof NetworkError) sawNetworkError = true;
        else sawOtherError = true;
      }
      // A real error from the server outranks "can't reach it" so the banner names
      // the more specific problem when both kinds of query are failing at once.
      if (sawOtherError) return "error";
      if (sawNetworkError) return "unreachable";
      return "none";
    },
  );

  const retry = useCallback(() => {
    void client.refetchQueries({
      predicate: (query) => query.state.status === "error" && query.getObserversCount() > 0,
    });
  }, [client]);

  return { problem, retry };
}
