# `tests/test_report_order.py` — Shared report ordering adapter

[Source](../../tests/test_report_order.py) · [Testing guide](../TESTING.md) · [Index](../README.md)

## Purpose and interactions

Checks that URL construction preserves report identity and sets the actual studentlastname option value. Rendered random ordering is rejected, valid lastname ordering is accepted, and a missing settings fragment returns no order rather than being misread as random.

Application modules exercised: [grading.py](../modules/grading.md), [moodle.py](../modules/moodle.md).

## Test cases

| Method | Scenario |
| --- | --- |
| `test_uses_moodle_option_value_and_retains_identity` | Uses moodle option value and retains identity |
| `test_rejects_random_effective_order` | Rejects random effective order |
| `test_accepts_rendered_student_lastname_order` | Accepts rendered student lastname order |
| `test_missing_settings_fragment_is_not_misread_as_random` | Missing settings fragment is not misread as random |

## Run this file

From the repository root:

```powershell
python -m unittest discover -s tests -p "test_report_order.py" -v
```

Use discovery with `-s tests`: several tests import synthetic fixtures from peer
files by short module name. This command makes those imports available. It needs
no saved account and writes only temporary test output.

## Limits and maintenance

The missing-selector case is intentionally tolerated; other identity/count safeguards remain responsible for detecting incomplete traversal.

Keep fixtures synthetic and session-free. If the behavior changes intentionally,
update assertions alongside the owning module's documentation; do not remove a
validation assertion merely to make a changed live page pass.
