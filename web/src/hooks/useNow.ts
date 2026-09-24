import { useEffect, useState } from "react";

/** The current time in ms, refreshed every `intervalMs`, for countdown text that has to keep
 *  moving between data fetches. */
export function useNow(intervalMs: number): number {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);

  return now;
}
