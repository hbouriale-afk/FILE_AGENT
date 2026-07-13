from organizer.archives import find_archives
from organizer.duplicates import find_duplicates
from organizer.executor import apply_plan, undo
from organizer.planner import build_plan
from organizer.scanner import scan_directory


def test_dry_run_does_not_move_files(tmp_path):
    (tmp_path / "a.txt").write_text("dupe content")
    (tmp_path / "b.txt").write_text("dupe content")

    files = scan_directory(tmp_path)
    dup_groups = find_duplicates(files)
    archives = find_archives(files)
    plan = build_plan(tmp_path, dup_groups, archives)

    apply_plan(plan, tmp_path, dry_run=True)

    assert (tmp_path / "a.txt").exists()
    assert (tmp_path / "b.txt").exists()


def test_apply_and_undo_round_trip(tmp_path):
    (tmp_path / "a.txt").write_text("dupe content")
    (tmp_path / "b.txt").write_text("dupe content")

    files = scan_directory(tmp_path)
    dup_groups = find_duplicates(files)
    archives = find_archives(files)
    plan = build_plan(tmp_path, dup_groups, archives)
    assert len(plan) == 1  # one file kept, one quarantined

    log_path = apply_plan(plan, tmp_path, dry_run=False)

    # One of the two original files should have moved into quarantine.
    originals_remaining = sum(
        1 for name in ("a.txt", "b.txt") if (tmp_path / name).exists()
    )
    assert originals_remaining == 1

    restored = undo(log_path)
    assert restored == 1
    assert (tmp_path / "a.txt").exists()
    assert (tmp_path / "b.txt").exists()
