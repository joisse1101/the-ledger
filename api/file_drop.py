"""The file-drop folder: list, save, read and delete files in one fixed directory.

Pure file logic with no web-framework imports. Every operation takes the folder as an argument and
accepts a bare file name only, so a caller can never reach outside the folder. Uploads are written to
an `.incoming/` subfolder first and linked into place, so a half-written file is never listed and an
existing file is never overwritten.
"""

from __future__ import annotations

import asyncio
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterable, Iterable, Mapping

DEFAULT_DIR = Path(__file__).resolve().parent / ".ledger" / "transfer"
INCOMING_DIR = ".incoming"
MAX_NAME_LENGTH = 200
FALLBACK_NAME = "file"

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{n}" for n in range(1, 10)),
    *(f"LPT{n}" for n in range(1, 10)),
}


class FileDropError(Exception):
    """A request the folder can't honour (bad name, missing file)."""


@dataclass(frozen=True)
class FileEntry:
    name: str
    size: int
    modified: float  # POSIX timestamp


def drop_dir(environ: Mapping[str, str]) -> Path:
    """The folder from `LEDGER_TRANSFER_DIR`, else the default under `api/.ledger/`."""
    configured = environ.get("LEDGER_TRANSFER_DIR")
    return Path(configured) if configured else DEFAULT_DIR


def list_files(folder: Path) -> list[FileEntry]:
    """Regular files directly inside `folder`, newest first. Creates the folder when missing."""
    folder.mkdir(parents=True, exist_ok=True)
    entries = [
        FileEntry(name=item.name, size=stat.st_size, modified=stat.st_mtime)
        for item in folder.iterdir()
        if item.is_file() and not item.is_symlink()
        for stat in [item.stat()]
    ]
    return sorted(entries, key=lambda entry: (entry.modified, entry.name), reverse=True)


def sanitize_name(raw: str) -> str:
    """A safe file name for Windows: no directory part, no invalid characters, no reserved name."""
    name = re.split(r"[\\/]", raw)[-1]
    name = _INVALID_CHARS.sub("_", name).rstrip(". ")
    if name.upper().split(".")[0] in _RESERVED_NAMES:
        name = f"_{name}"
    if len(name) > MAX_NAME_LENGTH:
        stem, dot, extension = name.rpartition(".")
        keep = MAX_NAME_LENGTH - (len(extension) + 1 if dot else 0)
        name = f"{stem[:keep]}.{extension}" if dot else name[:MAX_NAME_LENGTH]
    return name.strip() or FALLBACK_NAME


def _unique_names(name: str) -> Iterable[str]:
    yield name
    stem, dot, extension = name.rpartition(".")
    if not dot or not stem:
        stem, extension = name, ""
    suffix = f".{extension}" if extension else ""
    counter = 1
    while True:
        yield f"{stem} ({counter}){suffix}"
        counter += 1


def save_stream(folder: Path, raw_name: str, chunks: Iterable[bytes]) -> FileEntry:
    """Write `chunks` as a new file named after `raw_name`; a name in use gets ` (1)`, ` (2)`...

    Raises OSError (for example disk full) after removing the partial file, and re-raises whatever the
    chunk iterator raises (a dropped connection) the same way."""
    temp = _new_temp(folder)
    try:
        with temp.open("wb") as handle:
            for chunk in chunks:
                handle.write(chunk)
        return _place(folder, temp, raw_name)
    finally:
        temp.unlink(missing_ok=True)


async def save_async_stream(folder: Path, raw_name: str, chunks: AsyncIterable[bytes]) -> FileEntry:
    """`save_stream` for an async chunk source (a request body); disk writes run off the event loop."""
    temp = _new_temp(folder)
    try:
        with temp.open("wb") as handle:
            async for chunk in chunks:
                await asyncio.to_thread(handle.write, chunk)
        return await asyncio.to_thread(_place, folder, temp, raw_name)
    finally:
        temp.unlink(missing_ok=True)


def _new_temp(folder: Path) -> Path:
    incoming = folder / INCOMING_DIR
    incoming.mkdir(parents=True, exist_ok=True)
    return incoming / uuid.uuid4().hex


def _place(folder: Path, temp: Path, raw_name: str) -> FileEntry:
    for candidate in _unique_names(sanitize_name(raw_name)):
        target = folder / candidate
        try:
            os.link(temp, target)  # fails if the name exists, so nothing is overwritten
        except FileExistsError:
            continue
        stat = target.stat()
        return FileEntry(name=candidate, size=stat.st_size, modified=stat.st_mtime)
    raise AssertionError("unreachable: _unique_names never ends")  # pragma: no cover


def resolve_existing(folder: Path, name: str) -> Path:
    """The path of the regular file `name` inside `folder`, or FileDropError."""
    if not name or name != Path(name).name or name in {".", ".."} or "\\" in name:
        raise FileDropError("invalid file name")
    path = folder / name
    if path.is_symlink() or not path.is_file():
        raise FileDropError("no such file")
    return path


def delete_file(folder: Path, name: str) -> None:
    resolve_existing(folder, name).unlink()
