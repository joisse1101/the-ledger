// Shapes of the JSON the Python server sends. Dates are ISO strings; the client
// formats them, and shows `--` for anything missing.

export type RemoteState = "off" | "starting" | "ready" | "failed";

/** Whether the app is reachable from other devices, and whether they may see and answer a
 *  session's pending prompts. Turning it on starts Docker, the web interface and the gateway as
 *  needed, so it passes through `starting`. Only the machine running the app can change it; it
 *  turns itself off after 8 hours and on every backend restart. */
export interface RemoteMode {
  /** True only once `state` is `ready`. */
  enabled: boolean;
  /** ISO timestamp it turns itself off, or null while it is off. */
  expires_at: string | null;
  state: RemoteState;
  /** While `starting`: `docker`, `frontend` or `gateway`. */
  step: "docker" | "frontend" | "gateway" | null;
  /** While `failed`: why it could not start. */
  reason: string | null;
}

/** The gateway's sign-in code. Local requests only: the code contains the access token. */
export interface RemoteQr {
  /** An SVG of the code on an opaque white square. */
  svg: string;
  /** The gateway's address without the token, for showing under the code. */
  display_url: string;
  expires_at: string | null;
}

export interface Meta {
  refreshed_at: string | null;
  /** True only when this request comes from the machine running the app; the delete controls and
   *  the Remote mode switch key off it. */
  is_local: boolean;
  remote_mode: RemoteMode;
  /** True once any prompt has been relayed since the backend started; auto-approve is offered
   *  nowhere until then. */
  relay_hook_seen: boolean;
}

/** One file in the file-drop folder; `modified` is a local ISO timestamp. */
export interface FileEntry {
  name: string;
  size: number;
  modified: string;
}

export interface FilesResponse {
  files: FileEntry[];
}

/** One entry of the worktree-folder list: a path inside a repo, relative to its root. */
export interface WorktreeFolder {
  path: string;
  /** Claude Code's own folder: always listed, never removable. */
  built_in: boolean;
}

/** Local requests only; the server refuses any other device. */
export interface Settings {
  /** The built-in folder first, then the user's in the order they were added. */
  worktree_folders: WorktreeFolder[];
}

export interface LiveContext {
  size: number;
  growth: number | null;
  history: number[];
  /** Ready-made text such as `394k ▲ +2.1k ▁▂▃`, from the server's format_context(). */
  label: string;
}

/** A dialog a live session is blocked on (a tool-permission prompt, or `AskUserQuestion`), relayed
 *  by the optional PermissionRequest hook. `id` is the API's own, and names the prompt in answers. */
export interface PendingDecision {
  id: string;
  tool_name: string;
  tool_input: Record<string, unknown>;
}

export interface PendingDecisionResponse {
  pending_decision: PendingDecision | null;
}

/** The tool whose prompt is a question rather than a permission request. */
export const QUESTION_TOOL = "AskUserQuestion";

/** What the dashboard sends back: approve/deny a permission prompt, or answer a question by its
 *  text -> a label or free text (an array only for a multi-select question). */
export type DecisionAnswer =
  | { decision: "allow" }
  | { decision: "deny"; reason?: string }
  | { decision: "answer"; answers: Record<string, string | string[]> };

/** The latest prompt the app approved on a session's behalf. `at` is an ISO timestamp. */
export interface AutoApproved {
  tool_name: string;
  at: string;
}

/** How long ago a live session started or was last compacted: `ok` under 45 min, `should` up to
 *  55 min, `needs` beyond. `since` is the moment that time is measured from. */
export type CompactState = "ok" | "should" | "needs";

export interface CompactGrade {
  state: CompactState;
  since: string;
}

export interface LiveSession {
  session_id: string;
  pid: number;
  name: string;
  project: string;
  title: string;
  status: string;
  kind: string;
  started_at: string | null;
  updated_at: string | null;
  last_message: string;
  first_prompt: string;
  context: LiveContext | null;
  compact: CompactGrade | null;
  pending_decision: PendingDecision | null;
  auto_approve: boolean;
  last_auto_approved: AutoApproved | null;
}

export interface LiveResponse {
  sessions: LiveSession[];
}

/** Whether a session's cost is Claude Code's own reported figure, or this app's best-effort
 *  estimate (computed only from recognized models and the session's own main-thread turns). */
export type CostSource = "exact" | "estimated";

export interface TranscriptItem {
  session_id: string;
  project: string;
  title: string;
  started_at: string | null;
  updated_at: string | null;
  message_count: number;
  cost: number;
  cost_source: CostSource;
  /** Model ids this app's own pricing table didn't recognize while estimating; empty when every
   *  turn's model was priced (always empty on an `exact` session). */
  unpriced_models: string[];
  /** True only when Claude Code's own `cost-state` line flagged this session as unpriced; false on
   *  an `estimated` session that instead simply has no `cost-state` line yet (still in progress, or
   *  from a build too old to write one) - always false on an `exact` session. */
  cost_state_flagged: boolean;
  context: number | null;
  /** The model with the most main-thread responses in the session; empty if it had none. */
  model: string;
  /** True if the session ran an OpenSpec (`/opsx:*`) command or skill. */
  used_openspec: boolean;
  version: string;
  git_branch: string;
  /** The Claude Code worktree the session ran in; empty when it did not run in one. */
  worktree: string;
  live: boolean;
}

export interface FilterOptions {
  projects: string[];
  versions: string[];
  branches: string[];
  worktrees: string[];
}

export interface TranscriptsResponse {
  items: TranscriptItem[];
  /** Sessions matching the filters, not just this page. */
  total: number;
  options: FilterOptions;
}

export type SortField =
  | "project"
  | "title"
  | "session_id"
  | "started_at"
  | "updated_at"
  | "message_count"
  | "cost"
  | "context"
  | "model"
  | "used_openspec"
  | "version"
  | "git_branch"
  | "worktree";

export type SortDirection = "asc" | "desc";

export interface TranscriptQuery {
  q?: string;
  project?: string[];
  version?: string[];
  branch?: string[];
  worktree?: string[];
  sort?: SortField;
  dir?: SortDirection;
  limit?: number;
}

export interface SessionRecap {
  title: string;
  last_message: string;
  first_prompt: string;
  started_at: string | null;
  updated_at: string | null;
  message_count: number | null;
  cost: number | null;
  cost_source: CostSource | null;
  unpriced_models: string[];
  cost_state_flagged: boolean;
  context: number | null;
  avg_tokens_per_message: number | null;
}

export interface ToolRef {
  name: string;
  hint: string;
}

export interface Turn {
  message_id: string;
  timestamp: string | null;
  new: number;
  cache_read: number;
  cache_written: number;
  output: number;
  context: number;
  tools: ToolRef[];
  cache_miss: boolean;
}

export interface Compaction {
  position: number;
  trigger: string;
  pre_tokens: number | null;
}

export interface ToolGrowth {
  tool: string;
  tokens: number;
  uses: number;
}

export interface LargestIncrease {
  index: number;
  tokens: number;
  tool: string;
  hint: string;
}

export interface BreakdownItem {
  label: string;
  tokens: number;
}

/** An estimated startup category (memory files, skills, custom agents, MCP instructions). */
export interface BreakdownCategory {
  name: string;
  tokens: number;
  items: BreakdownItem[];
}

/** The estimated startup content from response index `position` until the next snapshot. */
export interface BreakdownSnapshot {
  position: number;
  categories: BreakdownCategory[];
}

export interface BreakdownGrowth {
  tool: string;
  tokens: number;
}

/** One response's rows: its snapshot's categories + exact growth by tool + remainder = its context. */
export interface BreakdownTurn {
  snapshot: number;
  growth: BreakdownGrowth[];
  remainder: number;
}

export interface ContextBreakdown {
  snapshots: BreakdownSnapshot[];
  turns: BreakdownTurn[];
}

export interface SessionDetail {
  turns: Turn[];
  compactions: Compaction[];
  attribution: {
    floor: number;
    current: number;
    by_tool: ToolGrowth[];
    largest: LargestIncrease[];
  };
  /** null when the server could not build it. */
  breakdown: ContextBreakdown | null;
}

export interface SessionResponse {
  session_id: string;
  live: boolean;
  recap: SessionRecap | null;
  readable: boolean;
  detail: SessionDetail | null;
}

export interface Project {
  path: string;
  name: string;
  trust_accepted: boolean;
  last_session_id: string | null;
  last_version: string;
  last_cost: number | null;
  last_start_time: string | null;
  last_duration_ms: number | null;
  lines_added: number | null;
  lines_removed: number | null;
  mcp_servers: string[];
}

export interface ProjectsResponse {
  projects: Project[];
}

/** A project's repo on its host. Everything but `path` is null when unknown: no remote, a host other
 *  than GitHub (no counts), or the GitHub CLI missing or signed out. */
export interface ProjectRepo {
  path: string;
  host: string | null;
  url: string | null;
  issues: number | null;
  prs: number | null;
}

export interface ProjectReposResponse {
  repos: ProjectRepo[];
}

export const TIME_RANGES = [
  "All time",
  "Today",
  "Yesterday",
  "Past week",
  "Past month",
  "Past quarter",
  "Past year",
] as const;

export type TimeRange = (typeof TIME_RANGES)[number];

export interface DurationFigure {
  seconds: number;
  label: string;
}

export interface MoneyFigure {
  amount: number;
  label: string;
}

/** A raw token count - unlike DurationFigure/MoneyFigure, not pre-formatted server-side; the
 *  frontend humanises it the same way as the Context column/detail figures (`formatContext`). */
export interface TokenFigure {
  amount: number;
}

/** Extremes also say which session they came from, and that session's cost source (present even
 *  for a non-cost extreme, e.g. longest session, since the server attaches it uniformly). */
export type WithSession<T> = T & {
  project: string | null;
  session_id: string | null;
  cost_source: CostSource | null;
  unpriced_models: string[];
  cost_state_flagged: boolean;
};

export interface OverviewSummary {
  projects: number;
  /** Distinct git branches among these transcripts (the same key `group_by: "branch"` uses). */
  branches: number;
  /** Distinct Claude Code worktrees among these transcripts. */
  worktrees: number;
  sessions: number;
  messages: number;
  avg_messages_per_session: number | null;
  duration: {
    average: DurationFigure;
    longest: WithSession<DurationFigure>;
    shortest: WithSession<DurationFigure>;
    total: DurationFigure;
  };
  cost: {
    average: MoneyFigure;
    most_expensive: WithSession<MoneyFigure>;
    cheapest: WithSession<MoneyFigure>;
    total: MoneyFigure;
  };
  tokens: {
    total: number;
    average: number;
    most: WithSession<TokenFigure>;
    least: WithSession<TokenFigure>;
  };
}

/** One donut/bar row: a project on Overview, a work stream (`wt <name>` for a worktree, else the git branch) on a project's own charts. */
export interface GroupTotals {
  group: string;
  sessions: number;
  messages: number;
  cost: number;
  tokens: number;
  share: number;
  messages_pct: number;
  cost_pct: number;
}

/** One 30-minute block of the local day; `minute` is its start, in minutes after midnight. */
export interface ActivityBucket {
  minute: number;
  label: string;
  sessions: number;
  messages: number;
}

export type OverviewGroupBy = "project" | "branch" | "worktree";

export type OverviewResponse =
  | { range: string; empty: true; available_ranges: string[] }
  | {
      range: string;
      empty: false;
      /** The time ranges that contain at least one session (within the project, when scoped to one). */
      available_ranges: string[];
      summary: OverviewSummary;
      groups: GroupTotals[];
      /** The one order every grouped chart uses; colors follow a group's index in it. */
      group_order: string[];
      activity: ActivityBucket[];
    };
