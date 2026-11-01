# `tests/test_upload_safety.py` — Already-graded and local-write safeguards

[Source](../../tests/test_upload_safety.py) · [Testing guide](../TESTING.md) · [Index](../README.md)

## Purpose and interactions

Verifies existing marks including zero preserve grade and feedback; an explicit manuallygraded route skips even a blank readable mark; a response graded since preflight is not submitted. Mocked local locks stop before apply. A mocked verified remote save followed by CSV PermissionError yields moodle_verified_csv_sync_failed rather than an uncertain remote outcome. Also checks non-mutating write probes, sharing-lock messages, audit-lock errors and the graded filter.

Application modules exercised: [grade_upload.py](../modules/grade_upload.md), [upload_io.py](../modules/upload_io.md), [csv_store.py](../modules/csv_store.md).

## Test cases

| Method | Scenario |
| --- | --- |
| `test_zero_and_existing_grades_preserve_grade_and_notes` | Zero and existing grades preserve grade and notes |
| `test_confirmed_graded_route_skips_even_when_mark_is_blank` | Confirmed graded route skips even when mark is blank |
| `test_newly_graded_response_is_not_submitted` | Newly graded response is not submitted |
| `test_locked_csv_check_stops_before_any_remote_save` | Locked csv check stops before any remote save |
| `test_remote_verified_csv_permission_failure_is_not_unverified` | Remote verified csv permission failure is not unverified |
| `test_write_access_probe_preserves_csv_bytes` | Write access probe preserves csv bytes |
| `test_windows_sharing_lock_reports_csv_and_excel` | Windows sharing lock reports csv and excel |
| `test_audit_lock_names_the_audit_file` | Audit lock names the audit file |
| `test_graded_filter_is_preserved_for_status_scan` | Graded filter is preserved for status scan |

## Run this file

From the repository root:

```powershell
python -m unittest discover -s tests -p "test_upload_safety.py" -v
```

Use discovery with `-s tests`: several tests import synthetic fixtures from peer
files by short module name. This command makes those imports available. It needs
no saved account and writes only temporary test output.

## Limits and maintenance

The native Windows sharing check is mocked in the cross-platform suite. Real Excel locks, browser form controls and live Moodle read-back still need separate integration validation.

Keep fixtures synthetic and session-free. If the behavior changes intentionally,
update assertions alongside the owning module's documentation; do not remove a
validation assertion merely to make a changed live page pass.
