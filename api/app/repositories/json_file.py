"""Writing a JSON file so a crash or a failed write never leaves half of it on disk."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def write_json_atomic(path: Path, data: Any) -> None:
    """Write `data` as indented JSON to a temp file beside `path`, then swap it in.

    The swap is a single rename, so readers see either the old file or the new one. On a failed
    write the temp file is removed, `path` is untouched and the error propagates.
    """
    temp = path.with_name(f"{path.name}.tmp")
    try:
        temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(temp, path)
    except OSError:
        temp.unlink(missing_ok=True)
        raise
