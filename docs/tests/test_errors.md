# `tests/test_errors.py` — Sanitized diagnostics

[Source](../../tests/test_errors.py) · [Testing guide](../TESTING.md) · [Index](../README.md)

## Purpose and interactions

Injects certificate and generic exceptions containing session-like details, verifies returned hints omit those secrets, distinguishes interrupted navigation, and checks discovery reports the stage of a failed course request.

Application modules exercised: [errors.py](../modules/errors.md), [discovery.py](../modules/discovery.md).

Local fake/helper classes: `Error`. They substitute for browser/service behavior; they are not runtime modules.

## Test cases

| Method | Scenario |
| --- | --- |
| `test_certificate_hint_does_not_echo_session_details` | Certificate hint does not echo session details |
| `test_unknown_error_keeps_request_data_private` | Unknown error keeps request data private |
| `test_navigation_interrupt_is_distinguished` | Navigation interrupt is distinguished |
| `test_course_request_certificate_failure_reports_the_stage` | Course request certificate failure reports the stage |

## Run this file

From the repository root:

```powershell
python -m unittest discover -s tests -p "test_errors.py" -v
```

Use discovery with `-s tests`: several tests import synthetic fixtures from peer
files by short module name. This command makes those imports available. It needs
no saved account and writes only temporary test output.

## Limits and maintenance

Tests message classification, not a real network outage, proxy certificate chain or all application logging paths.

Keep fixtures synthetic and session-free. If the behavior changes intentionally,
update assertions alongside the owning module's documentation; do not remove a
validation assertion merely to make a changed live page pass.
