# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Streamlit app, currently a minimal starting-point scaffold (single-page app with a sidebar name input).

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

- `app.py` is the entire app (single-file Streamlit script, run top-to-bottom on every interaction).
- `.streamlit/config.toml` holds Streamlit config (theme, server settings). `.streamlit/secrets.toml`, if created, is gitignored — put secrets there, accessed via `st.secrets`.
- `requirements.txt` currently lists `streamlit` and `pandas`.
