// Shapes of the JSON the Python server sends. Dates are ISO strings; the client
// formats them, and shows `--` for anything missing.

export interface Meta {
  refreshed_at: string | null;
}

export interface LiveContext {
  size: number;
  growth: number | null;
  history: number[];
  /** Ready-made text such as `394k ▲ +2.1k ▁▂▃`, from the server's format_context(). */
  label: string;
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
}

export interface LiveResponse {
  sessions: LiveSession[];
}

export interface TranscriptItem {
  session_id: string;
  project: string;
  title: string;
  started_at: string | null;
  updated_at: string | null;
  message_count: number;
  cost: number;
  context: number | null;
  version: string;
  git_branch: string;
  live: boolean;
}

export interface FilterOptions {
  projects: string[];
  versions: string[];
  branches: string[];
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
  | "version"
  | "git_branch";

export type SortDirection = "asc" | "desc";

export interface TranscriptQuery {
  q?: string;
  project?: string[];
  version?: string[];
  branch?: string[];
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

export interface SessionDetail {
  turns: Turn[];
  compactions: Compaction[];
  attribution: {
    floor: number;
    current: number;
    by_tool: ToolGrowth[];
    largest: LargestIncrease[];
  };
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

/** Extremes also say which session they came from. */
export type WithSession<T> = T & { project: string | null; session_id: string | null };

export interface OverviewSummary {
  projects: number;
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
}

export interface ProjectTotals {
  project: string;
  sessions: number;
  messages: number;
  cost: number;
  share: number;
  messages_pct: number;
  cost_pct: number;
}

export interface HourlyBucket {
  hour: number;
  label: string;
  sessions: number;
  messages: number;
  sessions_pct: number;
  messages_pct: number;
}

export type OverviewResponse =
  | { range: string; empty: true }
  | {
      range: string;
      empty: false;
      summary: OverviewSummary;
      projects: ProjectTotals[];
      /** The one order every project chart uses; colors follow a project's index in it. */
      project_order: string[];
      hourly: HourlyBucket[];
    };
