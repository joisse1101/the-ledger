import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { startDownload } from "../lib/download";
import { apiFetch, withQuery } from "./client";
import { uploadFile } from "./upload";
import type {
  DecisionAnswer,
  FilesResponse,
  LiveResponse,
  Meta,
  OverviewGroupBy,
  OverviewResponse,
  PendingDecisionResponse,
  ProjectReposResponse,
  ProjectsResponse,
  RemoteMode,
  RemoteQr,
  SessionResponse,
  Settings,
  TimeRange,
  TranscriptQuery,
  TranscriptsResponse,
} from "./types";

export const LIVE_POLL_MS = 2000;
export const DECISION_POLL_MS = 1500;
const META_POLL_MS = 60_000; // the server rescans on its own every 10 minutes
const REMOTE_STARTING_POLL_MS = 1000; // Remote mode takes a while to start; watch it closely
// Matches the server's cache (project_repo_service.CACHE_TTL_SECONDS): asking sooner only hits it.
export const PROJECT_REPOS_STALE_MS = 300_000;
export const PAGE_SIZE = 50;
// Matches the server's own default (overview_stats.BUCKET_MINUTES), so an unscoped cache key
// collides with one that named it explicitly.
const DEFAULT_BUCKET_MINUTES = 30;

export const keys = {
  meta: ["meta"] as const,
  live: ["live"] as const,
  transcripts: ["transcripts"] as const,
  session: (id: string) => ["session", id] as const,
  pendingDecision: (id: string) => ["pending-decision", id] as const,
  // Always starts ["overview", ...] so invalidating ["overview"] covers every scope and grouping.
  overview: (range: TimeRange, project?: string, groupBy?: OverviewGroupBy, bucketMinutes?: number) =>
    ["overview", range, project ?? null, groupBy ?? "project", bucketMinutes ?? DEFAULT_BUCKET_MINUTES] as const,
  projects: ["projects"] as const,
  projectRepos: ["project-repos"] as const,
  files: ["files"] as const,
  settings: ["settings"] as const,
};

export function useMeta() {
  return useQuery({
    queryKey: keys.meta,
    queryFn: () => apiFetch<Meta>("/api/meta"),
    refetchInterval: (query) =>
      query.state.data?.remote_mode.state === "starting" ? REMOTE_STARTING_POLL_MS : META_POLL_MS,
    refetchIntervalInBackground: false,
  });
}

/** Rescan Claude Code's files now, then reload everything derived from them. */
export function useRefresh() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<Pick<Meta, "refreshed_at">>("/api/refresh", { method: "POST" }),
    onSuccess: ({ refreshed_at }) => {
      // The reply is only the new timestamp; the rest of the cached meta (Remote mode, is_local)
      // stays as it was.
      client.setQueryData<Meta>(keys.meta, (meta) => (meta ? { ...meta, refreshed_at } : meta));
      // Not "live": the registry isn't part of the scan.
      for (const key of [keys.transcripts, ["session"], ["overview"], keys.projects]) {
        void client.invalidateQueries({ queryKey: key });
      }
      // The server dropped its repo cache, so this refetch re-reads issue and PR counts from gh.
      // Returned, so the refresh stays pending until it settles; it never rejects, so a gh failure
      // (null counts) doesn't fail the refresh. Only a mounted repos query is refetched.
      return client.invalidateQueries({ queryKey: keys.projectRepos });
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
          worktree: query.worktree,
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

/** Overview figures for `range`. `project` (a project path) scopes them to that one project;
 *  `groupBy` picks what the donut/bar rows are grouped by (the server defaults to "project");
 *  `bucketMinutes` (30 or 60, server default 30) is the block size of the time-of-day activity. */
export function useOverview(
  range: TimeRange,
  {
    project,
    groupBy,
    bucketMinutes,
  }: { project?: string; groupBy?: OverviewGroupBy; bucketMinutes?: number } = {},
) {
  return useQuery({
    queryKey: keys.overview(range, project, groupBy, bucketMinutes),
    queryFn: () =>
      apiFetch<OverviewResponse>(
        withQuery("/api/overview", { range, project, group_by: groupBy, bucket_minutes: bucketMinutes }),
      ),
    placeholderData: keepPreviousData,
  });
}

export function useProjects() {
  return useQuery({
    queryKey: keys.projects,
    queryFn: () => apiFetch<ProjectsResponse>("/api/projects"),
  });
}

/** Each project's repo link and open issue / PR counts. Slow on the server (it runs git and gh), so
 *  it is its own query: the projects table renders from `useProjects` without waiting on it. */
export function useProjectRepos() {
  return useQuery({
    queryKey: keys.projectRepos,
    queryFn: () => apiFetch<ProjectReposResponse>("/api/projects/repos"),
    staleTime: PROJECT_REPOS_STALE_MS,
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

/** Turns one session's auto-approve on or off. Only the machine running the app may; anything else
 *  gets a 403. The row in the cached Live list is updated at once so the switch doesn't flicker. */
export function useSetAutoApprove(sessionId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (enabled: boolean) =>
      apiFetch<{ auto_approve: boolean }>(`/api/sessions/${encodeURIComponent(sessionId)}/auto-approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      }),
    onSuccess: ({ auto_approve }) => {
      client.setQueryData<LiveResponse>(keys.live, (live) =>
        live
          ? { ...live, sessions: live.sessions.map((s) => (s.session_id === sessionId ? { ...s, auto_approve } : s)) }
          : live,
      );
    },
    // Approving what was already pending changes the rest of the row too.
    onSettled: () => void client.invalidateQueries({ queryKey: keys.live }),
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

/** The sign-in code for other devices. Fetched only while `enabled` (the dialog is open), and
 *  dropped from the cache the moment it closes: the code holds the access token. */
export function useRemoteQr(enabled: boolean) {
  return useQuery({
    queryKey: ["remote-qr"] as const,
    queryFn: () => apiFetch<RemoteQr>("/api/remote-mode/qr"),
    enabled,
    gcTime: 0,
    staleTime: 0,
    retry: false,
  });
}

/** Opens the session's repo in the editor on the machine running the app. */
export function useOpenRepo(id: string) {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ opened: string }>(`/api/sessions/${encodeURIComponent(id)}/open-repo`, { method: "POST" }),
  });
}

/** The file-drop folder. Only asked for while Remote mode is on: with it off the server refuses. */
export function useFiles(enabled: boolean) {
  return useQuery({
    queryKey: keys.files,
    queryFn: () => apiFetch<FilesResponse>("/api/files"),
    enabled,
    retry: false,
  });
}

/** Uploads one file, reporting progress as a 0-1 fraction; rejects with an ApiError (507 when the
 *  PC's disk is full, 403 when Remote mode has since turned off). */
export function useUploadFile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ file, onProgress }: { file: File; onProgress: (fraction: number) => void }) =>
      uploadFile(file, onProgress),
    onSettled: () => {
      void client.invalidateQueries({ queryKey: keys.files });
    },
  });
}

/** Local requests only; a remote device gets a 403. */
export function useDeleteFile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      apiFetch<{ deleted: string }>(`/api/files/${encodeURIComponent(name)}`, { method: "DELETE" }),
    onSettled: () => {
      void client.invalidateQueries({ queryKey: keys.files });
    },
  });
}

/** Asks for a single-use link to one file and hands it to the browser to save. The link needs no
 *  token but dies after one use or about a minute, so it is fetched at click time, never kept. */
export function useDownloadFile() {
  return useMutation({
    mutationFn: async (name: string) => {
      const { url } = await apiFetch<{ url: string }>(`/api/files/${encodeURIComponent(name)}/download-link`, {
        method: "POST",
      });
      startDownload(url);
    },
  });
}

/** The settings, for the machine running the app only: another device gets a 403, so ask only while
 *  `enabled` (this device is local). */
export function useSettings(enabled: boolean) {
  return useQuery({
    queryKey: keys.settings,
    queryFn: () => apiFetch<Settings>("/api/settings"),
    enabled,
    retry: false,
  });
}

/** Saves the user's worktree folders. The server re-files every session before it answers, so on
 *  success everything derived from sessions is reloaded. Rejects with an ApiError carrying the
 *  server's reason (422 for a folder it won't accept). */
export function useSaveSettings() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (worktreeFolders: string[]) =>
      apiFetch<Settings>("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ worktree_folders: worktreeFolders }),
      }),
    onSuccess: (settings) => {
      client.setQueryData(keys.settings, settings);
      // Transcripts also hold the filter options (projects, worktrees).
      for (const key of [keys.transcripts, ["session"], ["overview"], keys.projects, keys.live]) {
        void client.invalidateQueries({ queryKey: key });
      }
    },
  });
}

/** Saves how many projects the desktop widget lists. A display preference only: nothing derived from
 *  sessions changes, so nothing is reloaded. Rejects with an ApiError carrying the server's reason
 *  (422 for a number outside 1 to 10). */
export function useSaveWidgetMaxProjects() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (maxProjects: number) =>
      apiFetch<Settings>("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ widget: { max_projects: maxProjects } }),
      }),
    onSuccess: (settings) => client.setQueryData(keys.settings, settings),
  });
}
