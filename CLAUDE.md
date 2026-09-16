# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Streamlit app for viewing your local Claude Code sessions and projects. Sidebar-navigated pages (Sessions, Projects). The Sessions page has two tables: "Live" (auto-polling, from the live process registry) and "All" (every session ever run, from on-disk transcripts, manual refresh).

## Setup & Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

The app opens at http://localhost:8501. `.streamlit/config.toml` sets `runOnSave = true`, so the app auto-reloads on file changes while `streamlit run` is active.

There are no lint, test, or build commands configured yet.

## Architecture

- `app.py` is the Streamlit entry point (run top-to-bottom on every interaction), with sidebar nav switching between pages via `st.session_state.page`.
- `claude_sessions.py` parses Claude Code's live session registry at `~/.claude/sessions/<pid>.json` (one file per Claude process; see a live example by reading any file in that directory). `load_sessions()` returns `ClaudeSession` dataclasses sorted by `updated_at` descending, with a module-level cache keyed by each file's mtime — unchanged files are served from cache instead of being re-read/re-parsed. Note: dead PIDs' files may linger, so entries aren't guaranteed to reflect live processes.
- The Sessions page (`render_sessions_table` in `app.py`) is an `@st.fragment(run_every="2s")`, so it polls and redraws independently of the rest of the page. It has an "Auto-refresh" toggle (`st.session_state.auto_refresh`) and a "Last refreshed" caption laid out side by side in an `st.container(horizontal=True, vertical_alignment="center")` — when auto-refresh is off, the fragment still ticks on schedule but skips re-reading sessions and just redisplays the cached `st.session_state.sessions_df`.
- `claude_projects.py` parses Claude Code's global config at `~/.claude.json`, specifically its top-level `projects` map (one entry per directory Claude Code has been run/trusted in). `load_projects()` returns `ClaudeProject` dataclasses sorted by `last_start_time` descending, with a module-level cache keyed by the config file's mtime. Each entry reflects only that project's *last* session (no historical/cumulative data): trust status, last session ID, CLI version, cost, start time, lines added/removed, and any project-scoped MCP servers.
- The Projects page (`render_projects_table` in `app.py`) is a plain (non-fragment) render that caches its dataframe in `st.session_state.projects_df` and only re-reads `~/.claude.json` on first load or when the "⟳" reload button (paired with the "Last refreshed" caption in the same `st.container(horizontal=True, ...)` row) is clicked — no polling, unlike Sessions.
- `claude_transcripts.py` parses every on-disk session transcript at `~/.claude/projects/<sanitized-cwd>/<session-id>.jsonl` (one project folder per cwd, non-alphanumeric characters replaced with `-`; one `.jsonl` per session, one JSON object per line). Unlike the live registry, this covers every session that has ever run, including exited ones. `load_transcripts()` returns `ClaudeTranscript` dataclasses sorted by `updated_at` descending, with a module-level cache keyed by each file's mtime. Each transcript is built from a full line-by-line scan: `started_at`/`updated_at` are the min/max `timestamp` across all lines, `message_count` counts non-meta `user`/`assistant` lines, and `cost` sums per-turn token usage (`message.usage` on `type: "assistant"` lines) priced via the `_MODEL_PRICING` table in that file — a multi-block turn (e.g. thinking + tool_use) repeats the same `message.id` and its usage across several lines, so usage is counted once per unique `message.id`. This is an *estimate*: Claude Code doesn't write a dollar figure into the transcript anywhere (only `~/.claude.json`'s `lastCost` has one, and only for each project's most recent session), and an unrecognized model in `_MODEL_PRICING` is silently skipped rather than raising, so cost can undercount for sessions run on models missing from that table.
- The "All" sessions table (`render_transcripts_table` in `app.py`, under the Sessions page below "Live") follows the same manual-refresh pattern as Projects (caches in `st.session_state.transcripts_df`, "⟳" button, no polling) rather than the Sessions fragment's auto-poll — a full transcript scan is too expensive to run every 2s.
- `.streamlit/config.toml` holds Streamlit config (theme, server settings). `.streamlit/secrets.toml`, if created, is gitignored — put secrets there, accessed via `st.secrets`.
- `requirements.txt` currently lists `streamlit` and `pandas` (unpinned — `st.fragment(run_every=...)` requires Streamlit ≥1.37).
