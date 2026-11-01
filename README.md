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

Editing the CSV alone does not change Moodle. Only the upload command with
--apply submits grades/comments; download and preview do not submit them.
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

70 local tests pass, covering pending/all links, saved lessons, Greek decimal
marks, zero grades, CSV migration and notes preservation, duplicates, ZIP
traversal, and file versions. Authenticated execution must be tested locally.

Each quiz/test activity is processed independently. If one cannot be read
(permissions, no grading report, or changed markup), the scan continues with
other activities and reports incomplete lessons at the end with a nonzero
exit status. Download does not submit grades/comments. CSVs remain semicolon-
delimited with their existing local grade/notes preservation behavior.

## Upload grades and feedback from CSV

Edit the grade and notes columns of students.csv, then close Excel. Use the
question's mark scale shown in Moodle (for example, 0 to 20); these are question
marks, not percentages or the quiz's final total. Decimal comma and decimal
point are supported. Grade 0 is valid. Leave a field empty to leave its Moodle
value untouched. A nonempty note replaces that response's teacher feedback.
The command does not append feedback or clear existing feedback for blank CSV
notes. Already graded Moodle responses are always skipped, including grade 0;
neither their marks nor feedback are changed. The moodle_grade column is a sync snapshot, not the upload input.

Preview (no grading forms submitted):

```bash
python ekpa_login.py upload 93 --output "$HOME/Desktop/ekpa_desktop" --keep-open
```

Submit and verify the CSV changes:

```bash
python ekpa_login.py upload 93 --output "$HOME/Desktop/ekpa_desktop" --apply --keep-open
```

Optionally add --lesson-id 557503 to restrict either command to one quiz/test.
Every indexed CSV row with a nonempty grade or note is checked against the live
Moodle response. The cached moodle_grade is not used to skip the live check.
A row is submitted only when the requested value differs from the live value.
No download is run before upload, so your edited local values are read first.

The uploader reads saved lesson URLs, opens Βαθμολόγηση όλων, and requests
one response per page in stable lastname order, following Moodle-rendered
pagination links rather than calculating subsequent page numbers from totals. Submission IDs from
students_index.jsonl determine identity; display names are also cross-checked.
Unique names can be matched if CSV rows were sorted. Keep the order of rows
with identical names. Missing submissions, invalid grades for ungraded responses, and ambiguous Save
controls stop preflight before any submission. Already graded responses are
skipped using the explicit manuallygraded report and current mark fields,
not the potentially stale CSV status. The preview lists the old/new grades and notes. Existing unchanged
responses are skipped.

All proposed changes are checked before applying. Apply then reloads each
response, checks it has not changed since preflight, and uses the native Moodle
grading form. The comment editor and backing textarea are synchronized; local
notes are escaped as plain text. Form destination and quiz ID must match,
and only a form with one response mark and a unique Save action is accepted.
If your Moodle markup differs, the command stops and requests form HTML rather
than guessing. The source HTML supplied so far did not include the Save footer;
live submission and verification still require local validation.

After each save, the response is reloaded and its actual grade and feedback
are compared with the requested values. Verified values refresh the CSV sync
columns, preserving local notes. grade_upload_log.jsonl under the account
folder is created before preflight and records page observations, early failures,
preview, submitting and verified/unverified events with before/
after values (never credentials or session tokens). If submission succeeds
but verification fails, it is marked unverified_after_submit; inspect Moodle
before retrying. There are no automatic submission retries or rollback of
previously verified responses. Successful partial uploads stay saved.

New module: grade_upload.py. The 70 offline tests include grade range and
zero checks, decimal commas, blank-field preservation, remote grade conflicts,
HTML escaping, unique Save selection, CSV identity mapping, and confirmation
that preview never calls the apply function. No live grades were changed while
building this release.

Upload pagination update: repeated response IDs on navigation links are skipped
rather than immediately aborting. Missing requested responses still fail
preflight before any save. The audit log records only a whitelisted set of
report query parameters and response IDs, not session keys or page HTML. If
pagination still cannot locate a requested edit, supply the audit log and the
paging/settings form HTML (remove session keys). Upload does not download
student attachments; use download for that. There is no additional student-file
output from a failed upload preflight.


## Upload reports zero updates

The uploader now prints the exact CSV paths it read, file/row counts, blank-row
counts, rows requiring live checks, and the number of known lessons in scope.
The audit log includes local_csv_summary, lesson_scope, preflight_completed and
no_changes events, and already_matches_moodle for verified no-op responses.
Blank notes never suppress a nonempty grade and never clear Moodle feedback.
A grade equal to the cached moodle_grade is still checked live; only matching
live values are considered unchanged. These checks do not bypass identity,
mark-range, or remote-change conflict protections.

If no changes are submitted, read the printed paths and counts before editing
or rerunning. A preflight_started event alone was not proof that any response
had been visited, saved, or verified. The new completion event distinguishes
zero work from a run that stopped before finishing preflight.

The grading report requests now use Moodle's real sorting option value
studentlastname. The previous lastname value was invalid in Moodle 4.5 and
silently selected random ordering, which suppresses paging. See
TROUBLESHOOTING.md for source references and the seven-response paging
regression. The rendered ordering is checked before response processing.

## Already graded responses and PermissionError during upload

The uploader now omits responses already graded in Moodle. This includes a
numeric zero and any response found in Moodle's manuallygraded report even
when the mark field is blank. Skipping applies to both marks and feedback.
Graded status is checked again at apply time; if another instructor has graded
the response after preflight, it is skipped rather than changed. Downloads
still include graded responses in the CSV; only upload omits them.

Close students.csv in Excel before --apply. Before the first Moodle save, the
uploader checks every affected CSV for read/write access and probes its folder
for temporary-file creation/removal. On Windows it also requests DELETE access
without deleting the file, to detect the sharing lock that blocks atomic CSV
replacement. These are preflight checks, not a guarantee against a lock being
acquired later. Audit-file locks report the audit path explicitly as well.

The older generic PermissionError did not identify the failing file. Excel
locking is a likely cause, but that old output alone does not establish whether
a Moodle save occurred first. The new workflow records these stages:

- local_write_check_failed: no new Moodle save started in this apply run.
- moodle_verified: remote mark/feedback was saved and read back successfully.
- moodle_verified_csv_sync_failed: Moodle save was confirmed but the local CSV
  could not be synchronized; do not interpret this as an unsuccessful save.
- unverified_after_submit: a save was attempted but remote readback failed.
- already_graded_skipped / already_graded_skipped_at_apply: no mark or feedback
  was submitted for that response.

A subsequent run skips grades already saved, including one that saved before a
local CSV error. The audit log and terminal distinguish remote verification
from successful local bookkeeping. The 70 offline tests cover graded-zero
skips, graded reports with blank marks, concurrent grading, blocked CSV writes,
unchanged probe bytes, and remote-success/local-permission-failure reporting.
The native Windows file-sharing probe still needs validation on Windows.
