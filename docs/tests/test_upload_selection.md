# `tests/test_upload_selection.py` — Candidate counts and zero-change reporting

[Source](../../tests/test_upload_selection.py) · [Testing guide](../TESTING.md) · [Index](../README.md)

## Purpose and interactions

Constructs four local rows covering mirrored grades, blank requests, zero and notes-only changes; verifies diagnostics and selection. A cached grade must not suppress a request when live Moodle is now ungraded. An empty plan logs completion/no_changes without calling apply.

Application modules exercised: [grade_upload.py](../modules/grade_upload.md), [csv_store.py](../modules/csv_store.md), [export.py](../modules/export.md).

## Test cases

| Method | Scenario |
| --- | --- |
| `test_counts_and_blank_notes_do_not_suppress_grades` | Counts and blank notes do not suppress grades |
| `test_cached_grade_does_not_hide_live_ungraded_response` | Cached grade does not hide live ungraded response |
| `test_zero_plan_logs_completion_and_no_changes` | Zero plan logs completion and no changes |

## Run this file

From the repository root:

```powershell
python -m unittest discover -s tests -p "test_upload_selection.py" -v
```

Use discovery with `-s tests`: several tests import synthetic fixtures from peer
files by short module name. This command makes those imports available. It needs
no saved account and writes only temporary test output.

## Limits and maintenance

Candidate rows are not necessarily proposed updates: the live graded-state check can remove them. Tests do not implement a consolidated user report.

Keep fixtures synthetic and session-free. If the behavior changes intentionally,
update assertions alongside the owning module's documentation; do not remove a
validation assertion merely to make a changed live page pass.
