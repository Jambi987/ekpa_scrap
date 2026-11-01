# `tests/test_dashboard.py` — Grade Me block parsing

[Source](../../tests/test_dashboard.py) · [Testing guide](../TESTING.md) · [Index](../README.md)

## Purpose and interactions

Constructs representative course headings, lesson links, badges and entry lists. Verifies course association, counts, whitespace normalization and mismatch visibility. Recognized empty content is distinct from missing markup; unexpected external lesson URLs are rejected.

Application modules exercised: [dashboard.py](../modules/dashboard.md).

## Test cases

| Method | Scenario |
| --- | --- |
| `test_grouping_counts_and_hidden_entries` | Grouping counts and hidden entries |
| `test_mismatch` | Mismatch |
| `test_missing_or_changed_layout_raises` | Missing or changed layout raises |
| `test_empty` | Empty |
| `test_external_url` | External url |
| `test_whitespace` | Whitespace |

## Run this file

From the repository root:

```powershell
python -m unittest discover -s tests -p "test_dashboard.py" -v
```

Use discovery with `-s tests`: several tests import synthetic fixtures from peer
files by short module name. This command makes those imports available. It needs
no saved account and writes only temporary test output.

## Limits and maintenance

Pure HTML tests cannot confirm whether the live Grade Me plugin is enabled for an account or whether delayed browser content appears.

Keep fixtures synthetic and session-free. If the behavior changes intentionally,
update assertions alongside the owning module's documentation; do not remove a
validation assertion merely to make a changed live page pass.
