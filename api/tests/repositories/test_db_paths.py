"""The snapshot and history stores stay in api/, whatever package the path helpers live in."""

from app.repositories.db import paths


def test_stores_live_under_api():
    api_dir = paths.db_path().parents[1]
    assert (api_dir / "app" / "repositories" / "db" / "paths.py").is_file()
    assert paths.db_path() == api_dir / ".ledger" / "ledger.db"
    assert paths.history_db_path() == api_dir / ".history" / "history.db"
