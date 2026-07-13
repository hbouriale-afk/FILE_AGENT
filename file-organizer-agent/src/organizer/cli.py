"""Command-line interface.

Usage:
    organizer scan  /path/to/folder
    organizer clean /path/to/folder                # dry run (default, safe)
    organizer clean /path/to/folder --apply         # actually move files
    organizer undo  /path/to/folder/undo_log.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .archives import find_archives
from .classifier import summarize
from .duplicates import find_duplicates
from .executor import apply_plan, undo as undo_actions
from .planner import build_plan
from .scanner import scan_directory


def _format_bytes(n: int) -> str:
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def _run_scan(path: str) -> tuple[list, list]:
    files = scan_directory(path)
    dup_groups = find_duplicates(files)
    archives = find_archives(files)
    return dup_groups, archives


def _print_report(dup_groups, archives) -> None:
    total_wasted = sum(g.wasted_bytes for g in dup_groups)
    print(f"\n=== Duplicate files: {len(dup_groups)} group(s), "
          f"{_format_bytes(total_wasted)} reclaimable ===")
    for g in dup_groups[:20]:
        print(f"  [{_format_bytes(g.files[0].size)} each] keep: {g.files[0].path}")
        for dup in g.files[1:]:
            print(f"      -> duplicate: {dup.path}")
    if len(dup_groups) > 20:
        print(f"  ... and {len(dup_groups) - 20} more group(s)")

    print(f"\n=== Archives found: {len(archives)} ===")
    for a in archives[:20]:
        entries = f"{a.entry_count} entries" if a.entry_count is not None else "unknown format"
        print(f"  {a.file.path}  ({entries})")
    if len(archives) > 20:
        print(f"  ... and {len(archives) - 20} more")

    ai_summary = summarize(dup_groups, archives)
    print("\n=== Summary ===")
    if ai_summary:
        print(ai_summary)
    else:
        print(
            "(Set GEMINI_API_KEY for an AI-generated summary. "
            "Raw stats printed above.)"
        )


def cmd_scan(args: argparse.Namespace) -> None:
    dup_groups, archives = _run_scan(args.path)
    _print_report(dup_groups, archives)


def cmd_clean(args: argparse.Namespace) -> None:
    root = Path(args.path).expanduser().resolve()
    dup_groups, archives = _run_scan(str(root))
    _print_report(dup_groups, archives)

    plan = build_plan(root, dup_groups, archives)
    if not plan:
        print("\nNothing to do -- no duplicates or archives found.")
        return

    print(f"\n=== Plan: {len(plan)} action(s) ===")
    for action in plan[:20]:
        print(f"  [{action.type}] {action.src} -> {action.dest}")
    if len(plan) > 20:
        print(f"  ... and {len(plan) - 20} more")

    if not args.apply:
        log_path = apply_plan(plan, root, dry_run=True)
        print(f"\nDRY RUN -- nothing was moved. Plan written to {log_path}")
        print("Re-run with --apply to execute it.")
        return

    confirm = input(f"\nApply {len(plan)} action(s)? Files will be moved "
                     f"into '_organizer_review/' (not deleted). [y/N] ")
    if confirm.strip().lower() != "y":
        print("Cancelled.")
        return

    log_path = apply_plan(plan, root, dry_run=False)
    print(f"\nDone. {len(plan)} file(s) moved. Undo log: {log_path}")
    print(f"Run 'organizer undo {log_path}' to reverse this.")


def cmd_undo(args: argparse.Namespace) -> None:
    restored = undo_actions(Path(args.log_path))
    print(f"Restored {restored} file(s) to their original location.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="organizer",
        description="Find duplicate files and archives, and safely clean them up.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_scan = subparsers.add_parser("scan", help="Scan and report findings only.")
    p_scan.add_argument("path")
    p_scan.set_defaults(func=cmd_scan)

    p_clean = subparsers.add_parser("clean", help="Scan and build a cleanup plan.")
    p_clean.add_argument("path")
    p_clean.add_argument("--apply", action="store_true",
                          help="Actually move files (default is dry-run).")
    p_clean.set_defaults(func=cmd_clean)

    p_undo = subparsers.add_parser("undo", help="Reverse a previous 'clean --apply' run.")
    p_undo.add_argument("log_path")
    p_undo.set_defaults(func=cmd_undo)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (FileNotFoundError, NotADirectoryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
