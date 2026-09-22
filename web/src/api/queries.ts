import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiFetch, withQuery } from "./client";
import type {
  LiveResponse,
  Meta,
  OverviewResponse,
  ProjectsResponse,
  SessionResponse,
  TimeRange,
  TranscriptQuery,
  TranscriptsResponse,
} from "./types";

export const LIVE_POLL_MS = 2000;
const META_POLL_MS = 60_000; // the server rescans on its own every 10 minutes
export const PAGE_SIZE = 50;

export const keys = {
  meta: ["meta"] as const,
  live: ["live"] as const,
  transcripts: ["transcripts"] as const,
  session: (id: string) => ["session", id] as const,
  overview: (range: TimeRange) => ["overview", range] as const,
  projects: ["projects"] as const,
};

export function useMeta() {
  return useQuery({
    queryKey: keys.meta,
    queryFn: () => apiFetch<Meta>("/api/meta"),
    refetchInterval: META_POLL_MS,
    refetchIntervalInBackground: false,
  });
}

/** Rescan Claude Code's files now, then reload everything derived from them. */
export function useRefresh() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<Meta>("/api/refresh", { method: "POST" }),
    onSuccess: (meta) => {
      client.setQueryData(keys.meta, meta);
      // Not "live": the registry isn't part of the scan.
      for (const key of [keys.transcripts, ["session"], ["overview"], keys.projects]) {
        void client.invalidateQueries({ queryKey: key });
      }
    },
  });
}

/** The Live list. `auto: false` stops the polling but keeps the last rows. */
export function useLive({ auto }: { auto: boolean }) {
  return useQuery({
    queryKey: keys.live,
    queryFn: () => apiFetch<LiveResponse>("/api/live"),
    refetchInterval: auto ? LIVE_POLL_MS : false,
    refetchIntervalInBackground: false, // nothing polls while the tab is hidden
    // Coming back to the tab refetches at once, but only while auto-refresh is on.
    refetchOnWindowFocus: auto ? "always" : false,
  });
}

/** The All list, one page at a time: `fetchNextPage` is "Load more". */
export function useTranscripts(query: TranscriptQuery) {
  const limit = query.limit ?? PAGE_SIZE;
  return useInfiniteQuery({
    queryKey: [...keys.transcripts, query],
    queryFn: ({ pageParam }) =>
      apiFetch<TranscriptsResponse>(
        withQuery("/api/transcripts", {
          q: query.q,
          project: query.project,
          version: query.version,
          branch: query.branch,
          sort: query.sort,
          dir: query.dir,
          limit,
          offset: pageParam,
        }),
      ),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((sum, page) => sum + page.items.length, 0);
      return loaded < last.total ? loaded : undefined;
    },
    placeholderData: keepPreviousData, // typing in the search box doesn't blank the list
  });
}

/** One session's recap and token history. Pass `refetchMs` while it is live. */
export function useSession(id: string | null, { refetchMs }: { refetchMs?: number } = {}) {
  return useQuery({
    queryKey: keys.session(id ?? ""),
    queryFn: () => apiFetch<SessionResponse>(`/api/sessions/${encodeURIComponent(id ?? "")}`),
    enabled: id !== null,
    refetchInterval: refetchMs ?? false,
    refetchIntervalInBackground: false,
  });
}

export function useOverview(range: TimeRange) {
  return useQuery({
    queryKey: keys.overview(range),
    queryFn: () => apiFetch<OverviewResponse>(withQuery("/api/overview", { range })),
    placeholderData: keepPreviousData,
  });
}

export function useProjects() {
  return useQuery({
    queryKey: keys.projects,
    queryFn: () => apiFetch<ProjectsResponse>("/api/projects"),
  });
}

/** Rejects with an ApiError carrying the server's message (409 when the session is live). */
export function useDeleteSession() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<{ deleted: string }>(`/api/sessions/${encodeURIComponent(id)}`, { method: "DELETE" }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: keys.transcripts });
      void client.invalidateQueries({ queryKey: ["overview"] });
    },
  });
}

export function useDeleteProject() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (path: string) =>
      apiFetch<{ deleted: string }>(withQuery("/api/projects", { path }), { method: "DELETE" }),
    onSuccess: () => {
      for (const key of [keys.projects, keys.transcripts, ["overview"]]) {
        void client.invalidateQueries({ queryKey: key });
      }
    },
  });
}
