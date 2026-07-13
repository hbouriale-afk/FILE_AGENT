"""Duplicate file detection.

Strategy (fast -> slow, to avoid hashing every file on disk):
  1. Group files by size. Files with a unique size can't have a duplicate.
  2. Within each size group, hash file contents (SHA-256, streamed in chunks)
     and group by hash.
  3. Any hash group with more than one file is a set of duplicates.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass

from .scanner import FileInfo

CHUNK_SIZE = 1024 * 1024  # 1 MB


def _hash_file(path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            hasher.update(chunk)
    return hasher.hexdigest()


@dataclass
class DuplicateGroup:
    file_hash: str
    files: list[FileInfo]

    @property
    def wasted_bytes(self) -> int:
        """Bytes that could be reclaimed by keeping only one copy."""
        return self.files[0].size * (len(self.files) - 1)


def find_duplicates(files: list[FileInfo]) -> list[DuplicateGroup]:
    by_size: dict[int, list[FileInfo]] = defaultdict(list)
    for f in files:
        if f.size > 0:  # ignore empty files, they're trivially "duplicate"
            by_size[f.size].append(f)

    by_hash: dict[str, list[FileInfo]] = defaultdict(list)
    for size, candidates in by_size.items():
        if len(candidates) < 2:
            continue
        for f in candidates:
            try:
                h = _hash_file(f.path)
            except (OSError, PermissionError):
                continue
            by_hash[h].append(f)

    groups = [
        DuplicateGroup(file_hash=h, files=sorted(group, key=lambda fi: fi.mtime))
        for h, group in by_hash.items()
        if len(group) > 1
    ]
    groups.sort(key=lambda g: g.wasted_bytes, reverse=True)
    return groups
