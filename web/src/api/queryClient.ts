import { QueryClient } from "@tanstack/react-query";
import { ApiError, NetworkError } from "./client";

/** Retry a dropped connection once; anything the server actually answered is final. */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError) return false;
  return error instanceof NetworkError && failureCount < 1;
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      // A failed refetch keeps the last data (TanStack's default); the server banner
      // reads the error state to say that data may be out of date.
      queries: { retry: shouldRetry, retryDelay: 500, refetchOnWindowFocus: true, staleTime: 0 },
      mutations: { retry: false },
    },
  });
}
