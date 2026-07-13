"""Detects archive/compressed files and inspects zip contents.

Detection is extension-based first (cheap, covers the vast majority of
cases) with a magic-byte check for zip files so renamed/extensionless
archives still get caught.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass

from .scanner import FileInfo

ARCHIVE_EXTENSIONS = {".zip", ".tar", ".gz", ".tgz", ".rar", ".7z", ".bz2", ".xz"}

ZIP_MAGIC_BYTES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")


@dataclass
class ArchiveInfo:
    file: FileInfo
    entry_count: int | None = None  # None if we couldn't inspect it (not a real zip, or unsupported format)


def _looks_like_zip(path) -> bool:
    try:
        with open(path, "rb") as f:
            header = f.read(4)
        return any(header.startswith(magic[:len(header)]) for magic in ZIP_MAGIC_BYTES)
    except (OSError, PermissionError):
        return False


def find_archives(files: list[FileInfo]) -> list[ArchiveInfo]:
    results: list[ArchiveInfo] = []
    for f in files:
        is_archive_ext = f.extension in ARCHIVE_EXTENSIONS
        if not is_archive_ext and not _looks_like_zip(f.path):
            continue

        entry_count = None
        if f.extension == ".zip" or _looks_like_zip(f.path):
            try:
                with zipfile.ZipFile(f.path) as zf:
                    entry_count = len(zf.namelist())
            except (zipfile.BadZipFile, OSError, PermissionError):
                entry_count = None

        results.append(ArchiveInfo(file=f, entry_count=entry_count))

    return results
