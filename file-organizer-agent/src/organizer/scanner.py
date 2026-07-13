"""Walks a directory tree and collects lightweight metadata for every file.

This is the only module that touches the filesystem for *reading* info,
so it's easy to test in isolation and easy to reason about performance
(no hashing happens here -- that's done lazily later, only for files
that are actually duplicate *candidates*).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileInfo:
    path: Path
    size: int
    mtime: float
    extension: str = field(init=False)

    def __post_init__(self) -> None:
        self.extension = self.path.suffix.lower()


DEFAULT_IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".idea", ".vscode", "$RECYCLE.BIN", "System Volume Information",
}


def scan_directory(root: str | Path, ignore_dirs: set[str] | None = None) -> list[FileInfo]:
    """Recursively collect FileInfo for every regular file under `root`.

    Symlinks are skipped to avoid double-counting or infinite loops.
    """
    root = Path(root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    ignore = ignore_dirs if ignore_dirs is not None else DEFAULT_IGNORE_DIRS
    results: list[FileInfo] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore]
        for name in filenames:
            path = Path(dirpath) / name
            try:
                if path.is_symlink():
                    continue
                stat = path.stat()
            except (OSError, PermissionError):
                continue
            results.append(FileInfo(path=path, size=stat.st_size, mtime=stat.st_mtime))

    return results
