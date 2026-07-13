import zipfile

from organizer.archives import find_archives
from organizer.scanner import scan_directory


def test_detects_zip_by_extension_and_counts_entries(tmp_path):
    zip_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("one.txt", "content one")
        zf.writestr("two.txt", "content two")

    files = scan_directory(tmp_path)
    archives = find_archives(files)

    assert len(archives) == 1
    assert archives[0].file.path.name == "bundle.zip"
    assert archives[0].entry_count == 2


def test_non_archive_files_are_not_flagged(tmp_path):
    (tmp_path / "notes.txt").write_text("just some notes")

    files = scan_directory(tmp_path)
    archives = find_archives(files)

    assert archives == []


def test_renamed_zip_without_extension_is_still_detected(tmp_path):
    real_zip = tmp_path / "bundle.zip"
    with zipfile.ZipFile(real_zip, "w") as zf:
        zf.writestr("one.txt", "content")

    renamed = tmp_path / "mystery_file"
    renamed.write_bytes(real_zip.read_bytes())
    real_zip.unlink()

    files = scan_directory(tmp_path)
    archives = find_archives(files)

    assert len(archives) == 1
    assert archives[0].file.path.name == "mystery_file"
