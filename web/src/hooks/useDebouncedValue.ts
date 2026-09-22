import { useEffect, useState } from "react";

/** `value`, but updated only after it has stopped changing for `delayMs`. Used for the search
 *  box so every keystroke doesn't fire a request. */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
