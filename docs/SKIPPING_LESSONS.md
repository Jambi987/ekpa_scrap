# Skipping empty manual-grading reports

The download command can encounter quizzes containing only automatically graded
questions, or quizzes without manual responses yet. Moodle's manual-grading report
then renders an informational notification instead of `table#questionstograde`.
Previously, waiting only for that table produced a layout error and a failed lesson.

## Recognition and control flow

`moodle.MoodleSelectors` now exposes `grading_toggle` and `grading_empty_notice`.
`grading.is_empty_grading_report` recognizes the main-content report structure:
exactly one show-automatic-questions toggle, a same-quiz HTTPS grading URL with
`includeauto=1`, and its immediately following nonempty informational alert.
It rejects login forms, error messages, response bodies, unexpected tables and
ambiguous or mismatched links. Detection does not depend on Greek/English text.

`pending_questions_for_lesson` waits for either the question table or the empty
notification. `parse_pending_questions` returns an empty list only for a recognized
empty report (or the existing valid table with no selected links). Missing tables
without that evidence still fail. This preserves layout and permission diagnostics.

`export._export_batch` reports a skip and appends an account-level
`download_scan_log.jsonl` entry with UTC time, status
`lesson_skipped_no_manual_responses`, lesson_id and lesson_title. It continues to
the next lesson. This new runtime file is ignored by Git. Reruns check the report
again, so later submissions can be found; a skip is not a permanent blacklist.
Existing files are retained, and CLI discovery may already have created an empty
lesson directory before export skips it.

## Scope

An empty report means no manual response rows are available in that report's
current visibility/group scope. It does not prove that file uploads are disabled
in the quiz configuration. Text-only essay responses still get a roster/CSV entry;
without attachment links, there is simply no attachment to download. We do not
skip an entire quiz because one student has no file.

Upload continues to reject missing requested response identities. If a CSV contains
grades to apply but Moodle now returns an empty report, those edits are not silently
accepted or discarded. No grades are submitted by the empty-report detection.

## Usage

```powershell
python ekpa_login.py download 93 --output "$env:USERPROFILE\Desktop\ekpa_desktop"
Get-Content -Encoding UTF8 -LiteralPath "$env:USERPROFILE\Desktop\ekpa_desktop\93\download_scan_log.jsonl" -Tail 20
```

The skip message is `Skipped: no manual-grading responses are available in this lesson.`
An unfamiliar empty-page layout still needs inspection rather than being assumed safe.

## Validation and source

`tests/test_empty_grading.py` covers English/Greek notifications, incorrect origins
and IDs, permission/login/error pages, changed tables, real manual-question tables,
navigation waiting, skip logging and continuation, text-only responses, and upload
preflight refusing unresolved CSV grades. Tests use synthetic HTML and mocks, not
an authenticated EKPA session.

The structural behavior was checked against Moodle's `MOODLE_405_STABLE` source:

- [Grading renderer](https://github.com/moodle/moodle/blob/MOODLE_405_STABLE/mod/quiz/report/grading/renderer.php)
- [Report index](https://github.com/moodle/moodle/blob/MOODLE_405_STABLE/mod/quiz/report/grading/report.php)

The site's actual Moodle version/HTML may differ. The user's error is consistent
with this empty-report case but does not itself establish the full page contents.
