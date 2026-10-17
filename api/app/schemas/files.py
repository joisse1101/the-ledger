"""The JSON shape of a drop-folder file."""

from __future__ import annotations

from datetime import datetime

from app.infra import file_drop

def file_json(entry: file_drop.FileEntry) -> dict:
    return {"name": entry.name, "size": entry.size, "modified": datetime.fromtimestamp(entry.modified).isoformat()}
