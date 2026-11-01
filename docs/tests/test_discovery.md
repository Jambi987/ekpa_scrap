# `tests/test_discovery.py` — Course service and quiz-index discovery

[Source](../../tests/test_discovery.py) · [Testing guide](../TESTING.md) · [Index](../README.md)

## Purpose and interactions

Uses synthetic service envelopes and page/request fakes to verify course list pagination, inclusion of hidden courses, clearing of UI search filters, quiz deduplication and explicit graded-report links. Error envelopes must not turn into a successful empty list.

Application modules exercised: [discovery.py](../modules/discovery.md), [grading.py](../modules/grading.md).

## Test cases

| Method | Scenario |
| --- | --- |
| `test_course_index_all_quizzes_and_dedup` | Course index all quizzes and dedup |
| `test_error_response_does_not_claim_empty_list` | Error response does not claim empty list |
| `test_explicit_graded_link_discovered` | Explicit graded link discovered |
| `test_replay_real_course_request_with_pagination_and_hidden` | Replay real course request with pagination and hidden |

## Run this file

From the repository root:

```powershell
python -m unittest discover -s tests -p "test_discovery.py" -v
```

Use discovery with `-s tests`: several tests import synthetic fixtures from peer
files by short module name. This command makes those imports available. It needs
no saved account and writes only temporary test output.

## Limits and maintenance

The fake captures/replays the expected service contract; it does not authenticate, exercise real AJAX timing or prove every Moodle plugin uses that contract.

Keep fixtures synthetic and session-free. If the behavior changes intentionally,
update assertions alongside the owning module's documentation; do not remove a
validation assertion merely to make a changed live page pass.
