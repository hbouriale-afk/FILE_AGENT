"""Applies an action plan to disk.

Everything here is designed around one rule: it must always be possible to
undo. Nothing is ever deleted -- files are moved into a quarantine folder,
and every move is logged to `undo_log.json` with enough info to reverse it.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .planner import Action

UNDO_LOG_NAME = "undo_log.json"


def apply_plan(actions: list[Action], root: Path, dry_run: bool = True) -> Path:
    """Executes the plan. Returns the path to the undo log (written even in
    dry-run mode, but marked as such, so you can inspect what *would* happen).
    """
    root = Path(root)
    log_entries = []

    for action in actions:
        entry = {
            "type": action.type,
            "src": str(action.src),
            "dest": str(action.dest),
            "reason": action.reason,
            "applied": False,
        }

        if not dry_run:
            try:
                action.dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(action.src), str(action.dest))
                entry["applied"] = True
            except (OSError, PermissionError) as e:
                entry["error"] = str(e)

        log_entries.append(entry)

    log_path = root / UNDO_LOG_NAME
    log_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "actions": log_entries,
    }
    log_path.write_text(json.dumps(log_payload, indent=2))
    return log_path


def undo(log_path: Path) -> int:
    """Reverses every applied action in a given undo log. Returns count restored."""
    log_path = Path(log_path)
    payload = json.loads(log_path.read_text())
    restored = 0

    for entry in payload["actions"]:
        if not entry.get("applied"):
            continue
        dest, src = Path(entry["dest"]), Path(entry["src"])
        if dest.exists():
            src.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dest), str(src))
            restored += 1

    return restored
