# `tests/test_storage.py` — Stable folders and append-only dashboard observations

[Source](../../tests/test_storage.py) · [Testing guide](../TESTING.md) · [Index](../README.md)

## Purpose and interactions

Uses temporary output roots to verify repeated scans append without changing earlier bytes, duplicates within a scan are recorded once, title renames reuse stable-ID folders, accounts/courses remain separate, and invalid account IDs or conflicting duplicate counts fail before appending.

Application modules exercised: [storage.py](../modules/storage.md), [dashboard.py](../modules/dashboard.md).

## Test cases

| Method | Scenario |
| --- | --- |
| `test_repeat_scan_appends_and_preserves_previous_bytes` | Repeat scan appends and preserves previous bytes |
| `test_duplicate_rows_once_per_scan_and_rename_reuses_folder` | Duplicate rows once per scan and rename reuses folder |
| `test_accounts_and_course_ids_are_isolated` | Accounts and course ids are isolated |
| `test_invalid_account_and_conflicting_duplicates_do_not_write` | Invalid account and conflicting duplicates do not write |

## Run this file

From the repository root:

```powershell
python -m unittest discover -s tests -p "test_storage.py" -v
```

Use discovery with `-s tests`: several tests import synthetic fixtures from peer
files by short module name. This command makes those imports available. It needs
no saved account and writes only temporary test output.

## Limits and maintenance

Does not provide concurrent-write or crash-recovery testing, and native Windows extended-path behavior requires a Windows check.

Keep fixtures synthetic and session-free. If the behavior changes intentionally,
update assertions alongside the owning module's documentation; do not remove a
validation assertion merely to make a changed live page pass.
