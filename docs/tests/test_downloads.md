# `tests/test_downloads.py` — Response parsing, roster persistence and downloads

[Source](../../tests/test_downloads.py) · [Testing guide](../TESTING.md) · [Index](../README.md)

## Purpose and interactions

Defines the shared synthetic HTML fixture with John Doe, question-101-11, an essay prompt, an allowed attachment and an external viewer link. Tests response/name association, required heading failures, local grade/note preservation, duplicate names, exercise appends, binary versions, safe ZIP extraction, paging scope and expired-session download detection.

Application modules exercised: [submissions.py](../modules/submissions.md), [export.py](../modules/export.md), [files.py](../modules/files.md).

## Test cases

| Method | Scenario |
| --- | --- |
| `test_association_prompt_and_attachment_filter` | Association prompt and attachment filter |
| `test_missing_header_fails` | Missing header fails |
| `test_roster_preserves_grade_notes_and_distinguishes_same_names` | Roster preserves grade notes and distinguishes same names |
| `test_description_appends_only_when_changed` | Description appends only when changed |
| `test_binary_versioning` | Binary versioning |
| `test_zip_extract_and_reject_traversal` | Zip extract and reject traversal |
| `test_paging_stays_with_same_pending_question` | Paging stays with same pending question |
| `test_authenticated_request_file_and_expired_session` | Authenticated request file and expired session |

## Run this file

From the repository root:

```powershell
python -m unittest discover -s tests -p "test_downloads.py" -v
```

Use discovery with `-s tests`: several tests import synthetic fixtures from peer
files by short module name. This command makes those imports available. It needs
no saved account and writes only temporary test output.

## Limits and maintenance

This file also provides HTML imported by several other tests. Its expected markup is deliberately narrow and should be extended with sanitized fixtures when the live site changes.

Keep fixtures synthetic and session-free. If the behavior changes intentionally,
update assertions alongside the owning module's documentation; do not remove a
validation assertion merely to make a changed live page pass.
