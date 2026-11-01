# Using the EKPA Moodle scraper

This guide describes the commands implemented in this branch. Examples use
**Windows PowerShell**, Windows Python 3.12, account `93`, and quiz activity
`557503`. Replace those IDs as needed. Run commands from the folder containing
`ekpa_login.py`.

## 1. Install and select the environment

If you already have the repository, use your existing checkout. To create one:

```powershell
cd "$env:USERPROFILE\Desktop"
git clone https://github.com/Jambi987/ekpa_scrap.git
cd ekpa_scrap
```

To read this documentation branch locally:

```powershell
git fetch origin
git switch documentation
git pull --ff-only
```

Use Windows Python, not Python inside WSL, for credential-backed commands. Python
3.12 is the documented setup; source annotations such as `int | None` require
Python 3.10 or newer, so the earlier Python 3.9 environment is unsuitable for this
source version. Dependencies use version ranges rather than a lock file.

Create a virtual environment and invoke its interpreter directly. This avoids a
PowerShell activation-policy dependency:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:NODE_USE_SYSTEM_CA = "1"
.\.venv\Scripts\python.exe -m playwright install chromium
```

If activation is allowed on your machine:

```powershell
.\.venv\Scripts\Activate.ps1
python --version
python -m pip --version
```

All remaining examples use `python`. Without activation, substitute
`.\.venv\Scripts\python.exe` everywhere. Install Playwright browsers with the same
interpreter/environment used to run the program.

For a certificate-chain failure, keep certificate verification enabled. If your
organization supplies a trusted PEM root certificate, set its actual path before
installing Chromium or starting Python:

```powershell
$env:NODE_EXTRA_CA_CERTS = "C:\certs\company-root.pem"
python -m playwright install chromium
```

The scraper sets `NODE_USE_SYSTEM_CA=1` on Windows before starting Playwright
unless you already set it. That does not help a separate browser-install command
unless you set the variable there too. See [troubleshooting](TROUBLESHOOTING.md).

## 2. Register credentials

```powershell
python ekpa_login.py add
```

Enter your full username and password twice at the prompts. Password entry is
hidden. A username such as `prof93lms_164` is registered as account **93**, derived
from the single `profNUMBERlms` pattern. Leading zeros are preserved: account
`093` is distinct from `93`. Registration stores the credentials but does not test
login. There can be only one saved username per extracted account number.

Credentials are JSON inside Windows Credential Locker, under service
`ekpa-lms-scraper-v1`; they are not a JSON file in the repository. There is no
plaintext or WSL fallback. Use the same Windows user profile when running later.

```powershell
python ekpa_login.py login 93
```

A successful login prints confirmation and waits for Enter. To replace a password
or username for the same account number:

```powershell
python ekpa_login.py remove 93
python ekpa_login.py add
```

`remove` deletes the saved credential only. Downloaded files remain. Register
accounts 91, 92, and 93 separately by running `add` for each full username.

## 3. Choose one output root and reuse it

```powershell
$EkpaOutput = "$env:USERPROFILE\Desktop\ekpa_desktop"
```

Use `--output $EkpaOutput` for listing, download, and upload. The program adds the
account directory automatically: pass `ekpa_desktop`, **not** `ekpa_desktop\93`.
Without `--output`, the default is `output` below your current working directory.
If your Desktop is redirected to OneDrive or another location, set `$EkpaOutput`
to its actual path. The program does not discover redirected Desktop folders.

Use one running command per account/output tree. CSV replacement is atomic, but
CSV and index updates are not a multi-file transaction and no account-wide lock
prevents concurrent writers.

## 4. See what needs grading

```powershell
python ekpa_login.py lessons 93 --output $EkpaOutput
```

This reads **Βαθμολόγησε με**, prints each course/lesson, the badge count of exams
awaiting correction, the number of listed entries, and totals. Badge and entry
counts can differ because the plugin may limit or filter the displayed list.
It also appends local lesson history. This is a dashboard view, not an all-course
submission inventory or a consolidated report of locally entered grades.

```powershell
python ekpa_login.py grading 93 --output $EkpaOutput
```

`grading` opens the dashboard lessons' pending manual-grading question pages in
browser tabs and pauses. It does not submit grades. The browser remains headless,
so this command currently provides console navigation diagnostics rather than
visible tabs you can inspect.

## 5. Download submissions from all courses

```powershell
python ekpa_login.py download 93 --output $EkpaOutput
```

The command enumerates enrolled courses through the My Courses request, checks
quiz indexes and (where needed) course pages, remembers quiz URLs, and combines
live discoveries with previously saved lessons. For each quiz it opens Results,
then Manual grading, then response lists including graded and ungraded entries.
It exports essay exercise descriptions, rosters, grades visible in Moodle, and
uploaded attachments. This command never saves grades to Moodle.

Example directories (display titles are sanitized and shortened):

| Location | Contents |
| --- | --- |
| `ekpa_desktop/93/` | Account-level discovery and upload audit records |
| `93/course_39318__Git/` | A course identified by its Moodle course ID |
| `course_39318__Git/lesson_quiz_557503__Branching/` | A quiz activity, called a lesson locally |
| `lesson_quiz_557503__Branching/test_11_6098587__Essay/` | Optional question directory when multiple questions need separate exports |
| `.../John Doe/` | One student's response attachments, extracted ZIP contents, download log |

With a single question, `exercise.txt`, `students.csv`, `students_index.jsonl`,
and student folders normally sit directly inside the lesson. Existing single-
question layouts remain in place if additional questions are later discovered.
Two attempts sharing a student's name can have separate suffixed folders.

### Running download again

Reruns rescan Moodle; they do not jump directly to an opaque saved cursor.
Existing folder identities and student response keys are reused. New responses
are added and current Moodle status is refreshed. Existing notes and locally
edited grades are preserved according to the [CSV rules](docs/DATA_AND_LOGS.md).
Old submissions are retained even if absent from a later scan.

Each attachment's completion record stores a hash and any ETag/Last-Modified
validator. A verified local file can be reused after an HTTP 304 response. Without
validators, the bytes are downloaded and compared. Missing/damaged local files
are fetched again; changed bytes are saved under a hash-suffixed filename. ZIPs
remain present and are re-extracted, even on reuse, to restore missing members.
Existing files from before tracking was added are fetched once to establish their
records. There is no `--resume` flag to supply.

An attachment failure is logged and remaining attachments continue. A broader
lesson error stops that lesson's processing, but later lessons are attempted.
The command ultimately reports incomplete work if any lessons failed. After fixing
the cause, rerun `download` with the same account/output. This does not guarantee
that a damaged CSV/index pair can be repaired automatically.

## 6. Enter grades in the correct CSV

Open **`students.csv`** for the desired lesson/question. The format is UTF-8 with
BOM and semicolon-delimited. If Excel puts everything in one column, import it as
UTF-8 text/CSV and choose the semicolon delimiter.

| Column | Edit it? | Meaning |
| --- | --- | --- |
| `student_name` | No | Name used with the index to match the response |
| `grade` | Yes | Grade requested for an ungraded response |
| `notes` | Optional | Plain-text feedback requested for an ungraded response |
| `moodle_grade` | No | Last observed Moodle mark |
| `moodle_status` | No | `graded`, `needs_grading`, or `unknown` |
| `last_checked` | No | UTC time of the last local synchronization |

An illustrative row is:

```csv
student_name;grade;notes;moodle_grade;moodle_status;last_checked
John Doe;20;Good work;;needs_grading;2026-11-01T12:00:00+00:00
```

Grades accept decimal points or commas, for example `17.5` or `17,5`. The live
question's permitted minimum/maximum is checked; `20` is an example, not a global
maximum. `0` is an intentional grade, not a blank. Empty notes preserve current
feedback. Empty grades preserve current marks. Blank fields cannot clear a mark
or feedback. A notes-only change can be submitted for an ungraded response, but
already graded responses are skipped entirely, including their feedback.

Save as CSV, not `.xlsx`, retaining the exact header names/order. Keep the
`students_index.jsonl` beside it. Do not add/delete roster rows or rename students.
Unique names can be rematched after sorting; duplicate names rely on row order,
so leave their relative order intact. **Save and close Excel before uploading or
refreshing downloads.**

### What is students.before_sync.csv?

It is a **one-time** copy made before the first replacement of an existing CSV.
It may have been created when the roster contained only one student. It is not a
rolling backup, not necessarily your latest grades, and never read for uploads.
If you accidentally graded it, transfer the intended values into the matching
rows of `students.csv`; do not replace the current roster wholesale with an old
backup. Back up the complete account folder for reliable manual recovery.

## 7. Preview and upload

Preview all eligible local CSV entries for this account:

```powershell
python ekpa_login.py upload 93 --output $EkpaOutput
```

Preview just one quiz:

```powershell
python ekpa_login.py upload 93 --output $EkpaOutput --lesson-id 557503
```

`557503` is the `id` from `/mod/quiz/view.php?id=557503` or
`/mod/quiz/report.php?id=557503`, not the course ID, question ID, or question slot.
Currently only `upload` accepts `--lesson-id`; `download` always scans all courses
in its discovery scope.

After checking the proposed updates, apply with:

```powershell
python ekpa_login.py upload 93 --output $EkpaOutput --lesson-id 557503 --apply
```

To apply across all saved lessons, omit `--lesson-id`:

```powershell
python ekpa_login.py upload 93 --output $EkpaOutput --apply
```

Each invocation builds a fresh plan; an earlier preview is not a persisted approval
file. It reads CSVs and their response indexes, looks up saved lesson URLs, checks
live Moodle responses and grade ranges, skips already graded responses, validates
the form, and checks CSV write/replace access before the first remote save.
It then rechecks each response and local row, submits one response, reads it back,
and updates the CSV snapshot after verification.

The initial CSV summary covers the **entire account**, even with `--lesson-id`.
The later saved-lesson scope determines which quiz is visited for updates. Thus
another lesson can show seven candidate rows while your selected lesson has six
blank rows and zero proposed changes. Malformed CSVs elsewhere in the account can
also fail this early read even when a lesson filter is supplied.

`Proposed response updates` counts response changes, not CSV files or students
across all courses. The same person can have multiple response identities. Already
graded responses are never overwritten by this version, even if a local mark differs.

## 8. Read logs and handle interrupted work

```powershell
Get-Content -Encoding UTF8 -LiteralPath "$EkpaOutput\93\grade_upload_log.jsonl" -Tail 30
```

JSONL means one JSON object per line; timestamps are UTC. Explicit UTF-8 avoids
PowerShell displaying Greek names with the wrong encoding.

| Last relevant upload event | Meaning and next step |
| --- | --- |
| `preflight_failed` | Plan failed before saves; fix the reported mapping/layout/value issue |
| `local_write_check_failed` | No save started in this invocation; close Excel and check file/folder permissions |
| `preview` only | Proposed changes; not proof of a save; check the terminal's final error |
| `submitting` / `unverified_after_submit` | Save outcome may be uncertain; inspect Moodle before retrying |
| `moodle_verified` | Remote values were read back successfully |
| `moodle_verified_csv_sync_failed` | Remote save succeeded, local bookkeeping failed; fix local access and refresh |
| `verified` | Remote read-back and local CSV synchronization succeeded |
| `already_graded_skipped` | Moodle response was graded at preflight |
| `already_graded_skipped_at_apply` | It became graded before its save; skipped |
| `no_changes` | No eligible differences were planned |

Earlier responses may already be saved when a later apply step fails; upload is
not an all-or-nothing transaction. There is no rollback or automatic retry of an
uncertain submission. Some exceptions occur before a specific failure event is
written: press Enter at the pause to see the final `Error: ...` line.

Per-student download logs contain `complete`, `reused`, or `failed` events. They
track attachments, not grading. A complete attachment record is emitted after ZIP
extraction succeeds. Neither a CSV row nor an existing student directory proves
all attachments finished successfully.

## 9. Command and option reference

```powershell
python ekpa_login.py --help
python ekpa_login.py upload --help
python -m ekpa_scraper --help
```

| Command | Account argument | Options | Main effect |
| --- | --- | --- | --- |
| `add` | None | Help only | Prompt and save credentials |
| `remove` | Required | Help only | Delete that saved credential |
| `login` | Required | `--keep-open` | Authenticate, then always pause |
| `lessons` | Required | `--output`, `--keep-open` | Dashboard summary and local history |
| `grading` | Required | `--output`, `--keep-open` | Open pending report tabs, then always pause |
| `download` | Required | `--output`, `--keep-open` | Discover quizzes and refresh local exports |
| `upload` | Required | `--output`, `--keep-open`, `--lesson-id`, `--apply` | Preview or apply CSV changes |

`--keep-open` waits for Enter after success; it does **not** set `headless=False`.
Some failure paths also pause regardless of that flag. The login message mentions
additional verification, but interactive verification is not supported by the
current headless CLI; there is no `--headed` option. The browser implementation
would need a deliberate change for a visible manual verification flow.

Handled application failures return exit code 1; successful commands return 0.
Argument parsing errors use argparse's normal exit behavior (usually 2).

## 10. Multiple accounts and shell differences

Process registered accounts sequentially:

```powershell
foreach ($AccountId in @('91', '92', '93')) {
    python ekpa_login.py download $AccountId --output $EkpaOutput
    if ($LASTEXITCODE -ne 0) { break }
}
```

Each invocation uses a fresh isolated browser context. Files and saved credentials
are selected by account number. There is no built-in `--all-accounts` flag or
account-listing command.

For Git Bash with Windows Python, use its environment-variable syntax instead:

```bash
NODE_USE_SYSTEM_CA=1 python -m playwright install chromium
python ekpa_login.py download 93 --output "$HOME/Desktop/ekpa_desktop"
```

In PowerShell use `$env:NODE_USE_SYSTEM_CA = "1"`; the Bash inline assignment will
be interpreted as an unknown command there.

## 11. Updating, tests, and recovery

For normal operation after changes are merged to master:

```powershell
git switch master
git pull --ff-only
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m unittest discover -s tests -v
```

Tests use temporary folders and synthetic/mocked Moodle pages. They do not need
real credentials and do not submit real grades. See [TESTING](docs/TESTING.md).

For `ModuleNotFoundError`, install requirements with the same Python executable.
For CSV locks, close Excel and check Read-only attributes and folder permissions.
For missing student indexes or mismatched row counts, restore a matching CSV/index
pair from a full backup; the one-time CSV alone cannot reconstruct identities.
For layout/paging errors, consult [TROUBLESHOOTING](TROUBLESHOOTING.md) and the
[architecture guide](docs/ARCHITECTURE.md). Do not edit response IDs to force a match.
