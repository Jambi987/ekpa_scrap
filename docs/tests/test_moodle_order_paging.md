# `tests/test_moodle_order_paging.py` — Regression for invalid Moodle ordering

[Source](../../tests/test_moodle_order_paging.py) · [Testing guide](../TESTING.md) · [Index](../README.md)

## Purpose and interactions

MoodlePage models how an invalid order such as lastname falls back to random, forces page zero and suppresses paging. With studentlastname the iterator follows seven synthetic pages and discovers all seven distinct response keys.

Application modules exercised: [grade_upload.py](../modules/grade_upload.md), [grading.py](../modules/grading.md).

Local fake/helper classes: `Locator`, `MoodlePage`. They substitute for browser/service behavior; they are not runtime modules.

## Test cases

| Method | Scenario |
| --- | --- |
| `test_all_seven_response_ids_found_with_valid_moodle_order` | All seven response ids found with valid moodle order |

## Run this file

From the repository root:

```powershell
python -m unittest discover -s tests -p "test_moodle_order_paging.py" -v
```

Use discovery with `-s tests`: several tests import synthetic fixtures from peer
files by short module name. This command makes those imports available. It needs
no saved account and writes only temporary test output.

## Limits and maintenance

The model encodes the inspected Moodle behavior rather than running a Moodle server. A later version can change allowed values; retain the rendered-order validation and update fixtures from evidence.

Keep fixtures synthetic and session-free. If the behavior changes intentionally,
update assertions alongside the owning module's documentation; do not remove a
validation assertion merely to make a changed live page pass.
