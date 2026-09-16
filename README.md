# Claude Manager

## Setup

Create and activate a virtual environment (Windows PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Run

```powershell
streamlit run app.py
```

The app will open at http://localhost:8501.

## Dark mode

Toggle "Dark mode" in the sidebar to switch themes; the choice is remembered
across restarts in a local, gitignored `.streamlit/theme_pref.json`:

```json
{"dark": true}
```

Delete that file (or set `"dark": false`) to fall back to the `base` theme in
`.streamlit/config.toml`.
