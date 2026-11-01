# Output files, synchronization and audit records

[Index](README.md) · [Usage](../USAGE.md) · [Storage module](modules/storage.md)

## Directory identity

The output root is explicit via --output, otherwise relative `output`. Account IDs
are numeric strings. Course prefixes use course ID and lesson prefixes include
activity type plus activity ID. Titles are sanitized display suffixes and can
change without creating new folders. The program rejects duplicate matching
identity-prefix directories.

Example paths below use shortened illustrative titles; actual suffixes can contain
Greek characters and spaces. Windows extended-length `\\?\` prefixes in printed
paths support long paths and are not an extra folder.

| Path relative to output | Meaning |
| --- | --- |
| `93/discovered_lessons.jsonl` | Account discovery history |
| `93/grade_upload_log.jsonl` | Account upload audit |
| `93/course_39318__Git/lesson_quiz_557503__Branching/` | Quiz export root |
| `.../history.jsonl` | Dashboard observations when lessons/grading ran |
| `.../test_11_6098587__Essay/` | Optional per-question export root |
| `.../students.csv` | Current editable roster and Moodle snapshots |
| `.../students_index.jsonl` | Persistent response identity mapping |
| `.../students.before_sync.csv` | One-time pre-rewrite snapshot |
| `.../exercise.txt` | Accumulated extracted exercise descriptions |
| `.../John Doe/work.zip` | Original uploaded archive |
| `.../John Doe/project/main.py` | Extracted archive member |
| `.../John Doe/download_history.jsonl` | Attachment completion/reuse/failure records |

One question usually uses the lesson root directly. With multiple questions,
separate test directories are used, except an already established root question
stays at the root. A second response whose name collides gets
`__attempt_<usage>_<slot>` appended to its folder name. This is response identity,
not a general student registry.

## CSV contract

Encoding is UTF-8 BOM; delimiter is semicolon. Headers must be exactly this order:

```csv
student_name;grade;notes;moodle_grade;moodle_status;last_checked
```

The legacy ordered `student_name,grade,notes` fields are also accepted (with comma
or semicolon separators). Missing snapshot fields are populated with empty strings
and the next write emits the current six-field format. Header separator detection
counts commas/semicolons on the first line; this is not a general dialect sniffer.
Malformed rows or unknown/reordered headers are rejected.

| Field | Owner and semantics |
| --- | --- |
| student_name | Exported name; used as a cross-check with the index/live response |
| grade | User-requested mark, or a mirrored observed mark if not locally changed |
| notes | Locally entered plain-text feedback; not imported from remote feedback |
| moodle_grade | Most recently readable mark, including empty when unavailable |
| moodle_status | graded, needs_grading or unknown |
| last_checked | UTC ISO timestamp of local row synchronization |

`sync_row` always updates the last three snapshot fields and name. If the live mark
is nonempty and local grade is empty or equal to the old moodle_grade, it mirrors
the live mark into grade. Otherwise the local mark remains. It never changes notes.
String equality determines the old mirrored-grade check; upload comparison uses
Decimal numbers. A blank new live mark does not clear a previously nonblank local
mark. A graded status with no readable mark is possible through the explicit
manuallygraded report.

| Local grade | Old snapshot | New live mark | Resulting local grade |
| --- | --- | --- | --- |
| blank | blank | 18 | 18 |
| 18 | 18 | 19 | 19 |
| 20 | 18 | 19 | 20 (local edit preserved) |
| 18 | 18 | blank | 18 (snapshot becomes blank) |
| blank | blank | 0 | 0 |

Writes use a same-directory temporary `students_*.tmp` and os.replace. This gives
single-file atomic replacement but does not coordinate with the identity index or
other processes. Close Excel before writes. Temporary files are normally cleaned
up; a process crash can leave them behind. `students_writecheck_*.tmp` is the
separate upload preflight folder-write probe and is removed immediately.

## students.before_sync.csv

Writer: csv_store.write_rows. Created only if students.csv already exists and no
backup exists, immediately before replacing the current file. It is never refreshed
thereafter and may have only the first exported response. It is never selected by
read_edits, which searches the exact filename students.csv. Do not use it as the
active grading sheet or assume it is a complete recent roster. For recovery, keep a
full dated account-folder backup so CSV and index can be restored together.

## students_index.jsonl

Writer: export.register_student. Readers: export and grade_upload. One appended
record per new response; reruns reuse an existing key rather than append duplicates.

```json
{"submission_key":"101:11","student_name":"John Doe","attempt_number":"1","folder":"John Doe"}
```

The response key is `<question_usage_id>:<slot>`. `attempt_number` is heading text,
not the key. `folder` is a relative direct child name. Index and CSV must have equal
row counts. Unique names can be matched after sorting; duplicate names fall back
to index position. Renaming students, dropping rows, or losing the index can make
upload unsafe, so the code fails instead of guessing. New registration writes the
CSV before appending its index record, leaving a possible interruption window.

## exercise.txt

Writer: export.append_exercise. Stores extracted plain text. New nonempty text is
appended if it is not already a substring of the existing file; later additions
have a UTC update separator. This is not an exact version-ID history or HTML archive.
Text formatting, images and downloadable assets in the prompt are not reconstructed.

## history.jsonl

Writer: storage.append_scan, called by lessons/grading. One record per unique
course/lesson within a scan. Fields: schema_version (1), scan_id (UUID),
observed_at_utc, account, course_title, course_url, lesson_title, lesson_url,
exams_awaiting_correction, listed_exam_entries. Counts are dashboard snapshots.
Do not add repeated runs' counts together as if they represented different exams.
merge_known_lessons reads the latest line from each lesson's history to recover URLs.

## discovered_lessons.jsonl

Writer: storage.remember_lessons during download. Fields: course_title, course_url,
lesson_title, lesson_url, discovered_at_utc. Reruns append observations, including
repeated URLs. merge_known_lessons deduplicates by URL and prefers supplied live
records. For saved-only data it accepts the first encountered record for a URL;
it does not implement a general latest-timestamp database. This file records what
was discovered, not what finished downloading.

## download_history.jsonl

Writer: files.download_event; export adds failure events. Stored per student.
All events include UTC time_utc and status. No raw attachment URL is stored by
these calls.

| Status | Additional fields | Meaning |
| --- | --- | --- |
| complete | key, file, sha256, etag, last_modified | Bytes saved and any ZIP extraction completed |
| reused | key, file | Verified local file reused after HTTP 304; ZIP contents rechecked/extracted |
| failed | file, error_type | Export caught an attachment error; not completion |

`key` is SHA-256 of the original download URL. `sha256` hashes file content.
`cached_upload` finds the latest complete entry with that key, then verifies local
path and content. It ignores malformed JSON lines, but this is not a fully repaired
transaction log. A missing/corrupt file invalidates cache reuse. A changed remote
URL gets a different cache key. A reuse event alone does not replace the original
complete record needed for validators and hash checking.

Every scan still contacts Moodle. ETag/Last-Modified permits conditional GET; no
validator means a full GET and byte comparison. Missing extracted ZIP files are
restored from a valid local ZIP on a 304. Changed content is saved under
`<stem>__<first-16-sha256><suffix>` and old bytes are retained. No downloaded code
is executed. Arbitrary user edits are preserved as old local content, not sent back.

Limits are 100 MiB per attachment/member, 300 MiB summed uncompressed ZIP sizes,
2000 archive entries, and six request iterations per download. ZIP extraction is
bounded and rejects unsafe paths/symlinks; nested ZIPs remain files.

## grade_upload_log.jsonl

Writer: grade_upload.log_event. Account-level append-only audit, including previews.
All records carry UTC time_utc and status. Some contain student names, intended
marks and notes; they are operational data, not safe-to-publish test fixtures.
Passwords, cookies and sesskeys are not intentionally logged.

| Event | Key payload / interpretation |
| --- | --- |
| preflight_started | apply_requested, lesson_id; invocation began |
| local_csv_summary | csv_files, csv_rows, candidate_rows, blank_rows, per-file details |
| lesson_scope | saved_lessons, lesson_id |
| page_observed | Allowed report query fields, response_keys, rendered_paging_links, effective_order |
| already_graded_skipped | submission_key, relative CSV path, CSV row number |
| already_matches_moodle | Candidate has no eligible change |
| responses_not_found | Requested/observed keys and reported_total for diagnosis |
| graded_skip_summary | skipped_responses count |
| preflight_failed | error_type and controlled message; no apply started |
| preflight_completed | proposed_updates |
| no_changes | submitted_updates=0 |
| preview | Response identity/name, lesson, old/new grade and notes |
| local_write_check_failed | CSV access explanation; no first save started |
| local_write_checks_passed | Number of affected CSV files checked |
| already_graded_skipped_at_apply | Identity/name; response became graded before its save |
| submitting | Before/after values logged immediately before save attempt |
| unverified_after_submit | Submit or subsequent verification failed; outcome requires inspection |
| moodle_verified | Requested remote values read back successfully |
| moodle_verified_csv_sync_failed | Remote success followed by local error type/CSV path |
| verified | Remote verification and local CSV write both succeeded |

There is no invocation UUID in this log; interpret ordered preflight_started blocks
and timestamps. There is no guaranteed final run-completed record after apply and
some pre-save apply failures appear only in terminal output. Do not treat preview
as proof of saving or a missing verified event as proof that Moodle was unchanged.
Already-graded skip events do not refresh the local CSV; run download to refresh
snapshots after grades were entered elsewhere.

## Backup, retention and credentials

Back up complete account trees when preserving work. Old lesson/student files are
not automatically deleted, logs are not rotated, and downloads are not a mirror
that removes content missing remotely. .gitignore excludes runtime trees/records
inside the repository but does not encrypt data or remove files already tracked.
Windows Credential Locker entries are separate from output backups; credentials
must be registered on the Windows profile used for execution.
