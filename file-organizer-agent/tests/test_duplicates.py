from organizer.duplicates import find_duplicates
from organizer.scanner import scan_directory


def test_finds_exact_duplicates(tmp_path):
    (tmp_path / "a.txt").write_text("hello world")
    (tmp_path / "b.txt").write_text("hello world")
    (tmp_path / "c.txt").write_text("something else")

    files = scan_directory(tmp_path)
    groups = find_duplicates(files)

    assert len(groups) == 1
    assert len(groups[0].files) == 2
    names = {f.path.name for f in groups[0].files}
    assert names == {"a.txt", "b.txt"}


def test_no_duplicates_when_content_differs(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("world")

    files = scan_directory(tmp_path)
    groups = find_duplicates(files)

    assert groups == []


def test_empty_files_are_ignored(tmp_path):
    (tmp_path / "a.txt").write_text("")
    (tmp_path / "b.txt").write_text("")

    files = scan_directory(tmp_path)
    groups = find_duplicates(files)

    assert groups == []


def test_wasted_bytes_calculation(tmp_path):
    (tmp_path / "a.txt").write_text("x" * 100)
    (tmp_path / "b.txt").write_text("x" * 100)
    (tmp_path / "c.txt").write_text("x" * 100)

    files = scan_directory(tmp_path)
    groups = find_duplicates(files)

    assert len(groups) == 1
    assert groups[0].wasted_bytes == 200  # keep 1, reclaim 2 copies
