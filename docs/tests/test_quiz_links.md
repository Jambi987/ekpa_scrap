# `tests/test_quiz_links.py` — Relative quiz links and fallback discovery

[Source](../../tests/test_quiz_links.py) · [Testing guide](../TESTING.md) · [Index](../README.md)

## Purpose and interactions

Tests bare and dot-relative quiz URLs, report/icon links, title fallbacks, base tags and course-page context. Fake navigation confirms the course page is tried when the index has no matches and all-course zero matches are reported as an error.

Application modules exercised: [discovery.py](../modules/discovery.md).

Local fake/helper classes: `Locator`, `FakePage`. They substitute for browser/service behavior; they are not runtime modules.

## Test cases

| Method | Scenario |
| --- | --- |
| `test_bare_and_dot_relative_quiz_links_resolve_against_index` | Bare and dot relative quiz links resolve against index |
| `test_teacher_report_links_and_icon_only_links` | Teacher report links and icon only links |
| `test_base_tag_and_course_page_context` | Base tag and course page context |
| `test_course_page_fallback_finds_activity` | Course page fallback finds activity |
| `test_zero_matches_is_not_reported_as_success` | Zero matches is not reported as success |

## Run this file

From the repository root:

```powershell
python -m unittest discover -s tests -p "test_quiz_links.py" -v
```

Use discovery with `-s tests`: several tests import synthetic fixtures from peer
files by short module name. This command makes those imports available. It needs
no saved account and writes only temporary test output.

## Limits and maintenance

Does not simulate every lazily loaded course format or prove that a fallback course page contains all activities.

Keep fixtures synthetic and session-free. If the behavior changes intentionally,
update assertions alongside the owning module's documentation; do not remove a
validation assertion merely to make a changed live page pass.
