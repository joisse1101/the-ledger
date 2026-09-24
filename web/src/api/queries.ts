import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiFetch, withQuery } from "./client";
import type {
  DecisionAnswer,
  LiveResponse,
  Meta,
  OverviewResponse,
  PendingDecisionResponse,
  ProjectsResponse,
  RemoteMode,
  SessionResponse,
  TimeRange,
  TranscriptQuery,
  TranscriptsResponse,
} from "./types";

export const LIVE_POLL_MS = 2000;
export const DECISION_POLL_MS = 1500;
const META_POLL_MS = 60_000; // the server rescans on its own every 10 minutes
export const PAGE_SIZE = 50;

export const keys = {
  meta: ["meta"] as const,
  live: ["live"] as const,
  transcripts: ["transcripts"] as const,
  session: (id: string) => ["session", id] as const,
  pendingDecision: (id: string) => ["pending-decision", id] as const,
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

/** The Live list. `auto: false` stops the polling but keeps the last rows; `enabled: false`
 *  (default true) skips the query entirely. */
export function useLive({ auto, enabled = true }: { auto: boolean; enabled?: boolean }) {
  return useQuery({
    queryKey: keys.live,
    enabled,
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

/** A live session's oldest pending prompt (null when none, or when this device may not see it -
 *  another device while Remote mode is off). Pass a null `id` to not poll. */
export function usePendingDecision(id: string | null) {
  return useQuery({
    queryKey: keys.pendingDecision(id ?? ""),
    queryFn: () =>
      apiFetch<PendingDecisionResponse>(`/api/sessions/${encodeURIComponent(id ?? "")}/pending-decision`),
    enabled: id !== null,
    refetchInterval: DECISION_POLL_MS,
    refetchIntervalInBackground: false,
  });
}

/** Answers one prompt, named by `promptId`, so two open at once can't be answered for each other.
 *  Rejects with an ApiError: 409 the prompt is gone (the session already moved on), 403 Remote mode
 *  is off for this device. */
export function useAnswerDecision(sessionId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ promptId, answer }: { promptId: string; answer: DecisionAnswer }) =>
      apiFetch<{ answered: string }>(
        `/api/sessions/${encodeURIComponent(sessionId)}/decisions/${encodeURIComponent(promptId)}/answer`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(answer),
        },
      ),
    // Answered or too late, that prompt is gone either way.
    onSettled: () => {
      void client.invalidateQueries({ queryKey: keys.pendingDecision(sessionId) });
      void client.invalidateQueries({ queryKey: keys.live });
    },
  });
}

/** Turns Remote mode on or off. Only the machine running the app may; anything else gets a 403. */
export function useSetRemoteMode() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (enabled: boolean) =>
      apiFetch<RemoteMode>("/api/remote-mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      }),
    onSuccess: (remoteMode) => {
      client.setQueryData<Meta>(keys.meta, (meta) => (meta ? { ...meta, remote_mode: remoteMode } : meta));
    },
  });
}

/** Opens the session's repo in the editor on the machine running the app. */
export function useOpenRepo(id: string) {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ opened: string }>(`/api/sessions/${encodeURIComponent(id)}/open-repo`, { method: "POST" }),
  });
}
