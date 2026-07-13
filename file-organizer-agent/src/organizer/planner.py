"""Turns duplicate/archive findings into a concrete, reviewable action plan.

Design principle: never propose permanent deletion. Duplicates are proposed
to be moved into a `_duplicates_review/` folder (grouped by hash) so a human
can glance at them and delete for real. This is slower but much safer --
false positives in duplicate detection (however rare) shouldn't be able to
destroy data.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .archives import ArchiveInfo
from .duplicates import DuplicateGroup

ActionType = Literal["quarantine_duplicate", "quarantine_archive"]


@dataclass
class Action:
    type: ActionType
    src: Path
    dest: Path
    reason: str


def build_plan(
    root: Path,
    duplicate_groups: list[DuplicateGroup],
    archives: list[ArchiveInfo],
    quarantine_dirname: str = "_organizer_review",
) -> list[Action]:
    root = Path(root)
    quarantine_root = root / quarantine_dirname
    actions: list[Action] = []

    # Duplicates: keep the oldest file in place, quarantine the rest.
    for group in duplicate_groups:
        keeper, *rest = group.files
        for dup in rest:
            dest = quarantine_root / "duplicates" / group.file_hash[:10] / dup.path.name
            actions.append(Action(
                type="quarantine_duplicate",
                src=dup.path,
                dest=dest,
                reason=f"Duplicate of {keeper.path} (kept, older by mtime)",
            ))

    # Archives: flag zips that contain many files and look "unextracted".
    for arch in archives:
        if arch.entry_count is not None and arch.entry_count > 0:
            dest = quarantine_root / "archives" / arch.file.path.name
            actions.append(Action(
                type="quarantine_archive",
                src=arch.file.path,
                dest=dest,
                reason=f"Archive containing {arch.entry_count} file(s) -- review before extracting/deleting",
            ))

    return actions
