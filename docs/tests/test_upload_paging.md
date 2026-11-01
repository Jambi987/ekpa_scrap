# `tests/test_upload_paging.py` — Rendered paging and preflight diagnostics

[Source](../../tests/test_upload_paging.py) · [Testing guide](../TESTING.md) · [Index](../README.md)

## Purpose and interactions

Fake pages intentionally link to page 7 with an extra report parameter, proving traversal follows rendered URLs rather than inventing consecutive pages. Duplicate response content can be observed on different links without a traversal loop. Mirrored downloaded grades remain live-check candidates. A preflight exception creates an audit entry and never calls apply.

Application modules exercised: [grade_upload.py](../modules/grade_upload.md), [export.py](../modules/export.md), [submissions.py](../modules/submissions.md).

Local fake/helper classes: `FakeLocator`, `FakePage`. They substitute for browser/service behavior; they are not runtime modules.

## Test cases

| Method | Scenario |
| --- | --- |
| `test_follows_actual_links_and_tolerates_duplicate_responses` | Follows actual links and tolerates duplicate responses |
| `test_downloaded_grades_are_live_check_candidates` | Downloaded grades are live check candidates |
| `test_preflight_failure_always_creates_audit_log` | Preflight failure always creates audit log |

## Run this file

From the repository root:

```powershell
python -m unittest discover -s tests -p "test_upload_paging.py" -v
```

Use discovery with `-s tests`: several tests import synthetic fixtures from peer
files by short module name. This command makes those imports available. It needs
no saved account and writes only temporary test output.

## Limits and maintenance

The iterator can yield duplicate identities; build_plan handles response deduplication. These tests are not live performance or network-retry tests.

Keep fixtures synthetic and session-free. If the behavior changes intentionally,
update assertions alongside the owning module's documentation; do not remove a
validation assertion merely to make a changed live page pass.
