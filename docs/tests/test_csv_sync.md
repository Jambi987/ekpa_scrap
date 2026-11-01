# `tests/test_csv_sync.py` — CSV migration and observed-grade synchronization

[Source](../../tests/test_csv_sync.py) · [Testing guide](../TESTING.md) · [Index](../README.md)

## Purpose and interactions

Uses temporary CSVs and synthetic grading HTML to verify legacy migration, preservation of local notes, propagation of mirrored live marks including zero, and separation of actual marks from maximum-score labels. It also exercises total-column response links and saved lessons that disappear from the dashboard.

Application modules exercised: [csv_store.py](../modules/csv_store.md), [submissions.py](../modules/submissions.md), [grading.py](../modules/grading.md), [storage.py](../modules/storage.md).

## Test cases

| Method | Scenario |
| --- | --- |
| `test_migrate_and_sync_preserves_notes` | Migrate and sync preserves notes |
| `test_mirrored_grade_updates_including_zero` | Mirrored grade updates including zero |
| `test_read_mark_and_never_infer_maximum` | Read mark and never infer maximum |
| `test_total_column_and_all_paging` | Total column and all paging |
| `test_saved_lessons_disappearing_from_dashboard` | Saved lessons disappearing from dashboard |

## Run this file

From the repository root:

```powershell
python -m unittest discover -s tests -p "test_csv_sync.py" -v
```

Use discovery with `-s tests`: several tests import synthetic fixtures from peer
files by short module name. This command makes those imports available. It needs
no saved account and writes only temporary test output.

## Limits and maintenance

Connects parsing to persistence rather than testing an Excel process. It does not prove every locale-specific CSV import setting or recovery of a broken CSV/index pair.

Keep fixtures synthetic and session-free. If the behavior changes intentionally,
update assertions alongside the owning module's documentation; do not remove a
validation assertion merely to make a changed live page pass.
