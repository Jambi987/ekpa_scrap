# EKPA scraper

Windows Python 3.12 (64-bit). Extract the ZIP so ekpa_login.py sits alongside
its ekpa_scraper/ package directory. Existing stored credentials remain usable.

## Install (Git Bash)

```bash
python -m venv .venv
./.venv/Scripts/python.exe -m pip install --upgrade pip
./.venv/Scripts/python.exe -m pip install --only-binary=:all: -r requirements.txt
./.venv/Scripts/python.exe -m playwright install chromium
```

Use your existing working environment if already installed.

## Commands

```bash
python ekpa_login.py add
python ekpa_login.py login 93
python ekpa_login.py lessons 93 --output "$HOME/Desktop/ekpa_desktop"
python ekpa_login.py grading 93 --output "$HOME/Desktop/ekpa_desktop"
python ekpa_login.py download 93 --output "$HOME/Desktop/ekpa_desktop" --keep-open
python ekpa_login.py remove 93
```

Account 93 comes from prof93lms_164 (not from the trailing 164). Leading zeros
are preserved. Passwords are entered locally with hidden prompts and stored
with an explicit Windows Credential Locker backend, never a plaintext fallback.

- login: open an authenticated browser for inspection.
- lessons: list the Grade Me block and append dashboard count snapshots.
- grading: open only pending-grading question links in separate tabs.
- download: export responses (pending AND already graded) and refresh CSVs.

Use the same output root on successive runs. Output is isolated by account,
course, lesson and, for multiple tests, test question. Identity comes from
Moodle IDs instead of display titles; existing folders are reused on renames.

## Download and grade synchronization

Every download run opens My Courses, captures its actual enrolled-course AJAX
request, and reuses that read-only request to enumerate All and Hidden courses
with pagination. It clears a saved text search. This is scoped to courses
available to the logged-in account through My Courses, not the global catalog.
Each course's /mod/quiz/index.php lists quiz/test activities independent of the
Grade Me block and course-section collapse state. Previously saved lessons are
also revisited. Discovered lesson URLs are appended to discovered_lessons.jsonl.
Course discovery failing stops the run with a clear error; supply My Courses
HTML if the site's version uses a different service. Live discovery has not
been tested against the authenticated EKPA site.

The downloader opens lesson Results, reads the manual-grading option's live
URL and navigates directly to it, avoiding JavaScript dropdown timing issues.
It reads the explicit Already graded (grade=manuallygraded) and Needs grading
links, then the Total / Βαθμολόγηση όλων link (grade=all). The two filtered
reports establish status even when the editable score field is blank. The grading command retains its pending-only
behavior. HTML layout changes raise explicit errors rather than false zeroes.

Each test folder contains exercise.txt, students.csv, students_index.jsonl,
and student folders holding original attachments and extracted ZIP contents.
A single test uses the lesson folder directly; multiple tests use individual
test subfolders. Existing single-test output is reused if other tests appear.

CSV columns:

| Column | Meaning |
| --- | --- |
| student_name | Student display name |
| grade | Local working grade, initially filled from Moodle when available |
| notes | Your local notes, preserved on synchronization |
| moodle_grade | Latest actual score read from Moodle |
| moodle_status | graded, needs_grading, or unknown |
| last_checked | Timestamp (UTC) of that response's last scan |

CSV is UTF-8 with BOM and semicolon-delimited for Greek Excel. Existing
comma-delimited 3-column CSVs are migrated automatically on the next download.
If Excel still shows one column, use Data -> From Text/CSV and choose the
semicolon delimiter. Close the CSV in Excel before scanning (Excel may lock it).

Existing rows are updated atomically; new responses are added. The first
replacement retains a backup named students.before_sync.csv. The local notes
are never replaced. A grade previously copied from Moodle is refreshed when
Moodle changes it. If you edited grade locally, it is retained while the latest
Moodle value remains visible in moodle_grade. Grade zero is a real grade.

Scores are read from the response mark input, not maximum marks such as
"out of 20". Status is taken from the explicit graded/ungraded report when possible.
An unreadable score is left blank; an unknown status is not assumed ungraded. The supplied HTML had an empty mark field, so populated
grade parsing is fixture-tested but needs confirmation on a live graded response.
If Moodle scores remain blank, provide HTML for an already graded response.

Keep the CSV column headers and students_index.jsonl. Unique names can be
matched even if rows are sorted. For identical names, keep their existing row
order because the visible CSV does not contain submission IDs. Identity in the
index uses Moodle question-usage ID + slot, not a guessed student user ID.
Separate attempts may get separate rows/folders; identical folder names gain
an __attempt_<usage>_<slot> suffix. Reruns of the same response reuse its row.

## Files and pagination

Identical uploaded/extracted files are skipped. Changed contents with the same
filename receive a content-hash suffix; binary files are never byte-appended
or overwritten. Changed descriptions append an update section to exercise.txt.
Dashboard history remains append-only. A failed scan preserves existing output.
Run only one writer for an account at a time.

The downloader uses the existing browser session's authenticated request client.
Only same-site question response attachment links are downloaded. Viewer links
from third-party extensions are ignored. Original ZIPs remain; their contents
are extracted directly inside the student folder, without running anything.
Nested ZIPs are not recursively expanded. Unsafe ZIP paths and symlinks are
rejected. Limits: 100 MiB per file/member, 300 MiB extracted ZIP total, 2,000
ZIP entries. Windows extended-length output paths are used for nested projects.

Response pagination follows recognized .paging/.pagination links for the same
quiz, question, slot and grading filter, up to 100 pages. Requests use stable
lastname ordering and 100 responses per page to avoid randomized page overlap. Fewer retrieved responses
than Moodle's displayed total cause an incomplete-export error. The supplied
HTML contained no pagination controls, so live paging remains unverified.

No Moodle grades/comments are submitted. Updating CSV grade/notes is local.
Cookies, credentials, screenshots and page HTML are not saved as output files.

## Modules and tests

- accounts.py: credential storage and account IDs.
- browser.py: authenticated browser lifetime.
- moodle.py: selectors and URLs (update here for theme/plugin changes).
- dashboard.py: pure dashboard parsing.
- discovery.py: enrolled-course enumeration and complete course quiz indexes.
- grading.py: quiz reports and question-table navigation.
- submissions.py: student names, attachments, exercise and grade parsing.
- files.py: downloads, preserved file versions and ZIP extraction.
- storage.py: folder identity, scan history and saved-lesson discovery.
- csv_store.py: CSV migration and synchronization.
- export.py: response export orchestration.
- cli.py: commands and console output.

```bash
python -m unittest discover -s tests -v
```

33 local tests pass, covering pending/all links, saved lessons, Greek decimal
marks, zero grades, CSV migration and notes preservation, duplicates, ZIP
traversal, and file versions. Authenticated execution must be tested locally.

Each quiz/test activity is processed independently. If one cannot be read
(permissions, no grading report, or changed markup), the scan continues with
other activities and reports incomplete lessons at the end with a nonzero
exit status. Grades/comments are never submitted. CSVs remain semicolon-
delimited with their existing local grade/notes preservation behavior.
