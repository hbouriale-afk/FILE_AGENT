# File Organizer Agent

A command-line tool that scans a folder, finds duplicate files and unextracted
archives, and safely cleans them up — with an optional AI-generated summary of
what it found.

Built to be *actually usable*, not just a demo: nothing is ever permanently
deleted, every action is logged, and every action can be undone.

## Why

Everyone's Downloads folder is a graveyard of duplicate PDFs, old zip files,
and screenshots named `IMG_final_v2_FINAL.png`. This tool finds the mess and
proposes a cleanup plan you can review before anything happens.

## How it works

```
scan folder ──▶ find duplicates (hash-based) ──▶ find archives ──▶
                                                                    │
                                              build action plan ◀──┘
                                                    │
                              dry-run report  or  --apply (with confirmation)
                                                    │
                                          _organizer_review/ + undo_log.json
```

- **Duplicate detection**: files are first grouped by size (cheap), then
  SHA-256 hashed within each size group — no unnecessary hashing of files
  that obviously can't match.
- **Archive detection**: catches `.zip`, `.tar`, `.rar`, `.7z`, etc. by
  extension, plus zip files renamed without an extension (via magic-byte
  sniffing), and reports how many entries are inside.
- **Safety first**: nothing is deleted. Files are moved into
  `_organizer_review/` grouped by what triggered the move, and every move is
  written to `undo_log.json` so it can be fully reversed with `organizer undo`.
- **AI layer (optional)**: if `GEMINI_API_KEY` is set, Gemini turns the raw
  stats into a short plain-English summary and recommendation. Without a key,
  you still get the full report and full cleanup functionality — the AI adds
  polish, not a hard dependency.

## Quick start

```bash
git clone https://github.com/<your-username>/file-organizer-agent.git
cd file-organizer-agent
pip install -e .

# optional, for the AI summary:
cp .env.example .env   # then add your key
export GEMINI_API_KEY="..."

# report only, touches nothing:
organizer scan ~/Downloads

# build a cleanup plan (dry run by default):
organizer clean ~/Downloads

# actually move duplicates/archives into _organizer_review/:
organizer clean ~/Downloads --apply

# change your mind:
organizer undo ~/Downloads/undo_log.json
```

## Example output

```
=== Duplicate files: 2 group(s), 14.3MB reclaimable ===
  [7.1MB each] keep: /Downloads/vacation_photo.jpg
      -> duplicate: /Downloads/vacation_photo (1).jpg
  [128.0KB each] keep: /Downloads/resume.pdf
      -> duplicate: /Downloads/resume_copy.pdf

=== Archives found: 1 ===
  /Downloads/old_project.zip  (47 entries)

=== Summary ===
Your Downloads folder has about 14.3MB tied up in duplicate files, mostly a
repeated photo and resume. There's also a 47-file zip archive that looks
unextracted. Recommendation: review the flagged duplicates in
_organizer_review/ and decide whether old_project.zip is still needed before
extracting or removing it.
```

## Project structure

```
src/organizer/
├── scanner.py      # walks the filesystem, collects metadata (no AI)
├── duplicates.py   # size pre-filter + SHA-256 hashing (no AI)
├── archives.py      # extension + magic-byte archive detection (no AI)
├── planner.py       # turns findings into a reviewable action plan (no AI)
├── executor.py       # applies/undoes the plan, dry-run by default (no AI)
├── classifier.py     # optional Gemini-powered plain-English summary
└── cli.py            # argparse entry point
tests/                 # unit tests, no API key required
```

The AI is deliberately isolated to one module (`classifier.py`) that the rest
of the tool doesn't depend on — the deterministic file-handling logic is
testable and trustworthy on its own.

## Running tests

```bash
pip install -e ".[dev]"
pytest
```

## Limitations

- Duplicate detection is content-based, not "similar" — it won't catch a
  resized copy of the same photo or a reformatted version of the same doc.
- Archive inspection currently reads entry counts for zip files; other
  formats (`.rar`, `.7z`) are flagged by extension but not inspected inside.
- This is a CLI tool, not a background service — you run it on demand.

## License

MIT
