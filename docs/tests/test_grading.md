# `tests/test_grading.py` — Manual-grading question table parsing

[Source](../../tests/test_grading.py) · [Testing guide](../TESTING.md) · [Index](../README.md)

## Purpose and interactions

Uses table fixtures to prove pending-only column selection, extraction of every valid pending link, deduplication, a valid no-pending case, rejection of changed layouts/wrong destinations and resolution of a relative manual-grading option URL.

Application modules exercised: [grading.py](../modules/grading.md).

## Test cases

| Method | Scenario |
| --- | --- |
| `test_only_pending_column` | Only pending column |
| `test_every_pending_link_and_deduplication` | Every pending link and deduplication |
| `test_no_pending_links` | No pending links |
| `test_layout_failures` | Layout failures |
| `test_wrong_links_fail_instead_of_opening_all` | Wrong links fail instead of opening all |
| `test_relative_dropdown_url` | Relative dropdown url |

## Run this file

From the repository root:

```powershell
python -m unittest discover -s tests -p "test_grading.py" -v
```

Use discovery with `-s tests`: several tests import synthetic fixtures from peer
files by short module name. This command makes those imports available. It needs
no saved account and writes only temporary test output.

## Limits and maintenance

Primarily pure parsing. The dropdown JavaScript and actual browser navigation are not end-to-end exercised here.

Keep fixtures synthetic and session-free. If the behavior changes intentionally,
update assertions alongside the owning module's documentation; do not remove a
validation assertion merely to make a changed live page pass.
