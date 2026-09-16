# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Streamlit app for viewing your local Claude Code sessions and projects. Sidebar-navigated pages (Sessions, Projects); both are live.

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
- `.streamlit/config.toml` holds Streamlit config (theme, server settings). `.streamlit/secrets.toml`, if created, is gitignored — put secrets there, accessed via `st.secrets`.
- `requirements.txt` currently lists `streamlit` and `pandas` (unpinned — `st.fragment(run_every=...)` requires Streamlit ≥1.37).
