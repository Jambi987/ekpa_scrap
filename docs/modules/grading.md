# `ekpa_scraper/grading.py` — Manual-grading navigation and question discovery

[Source](../../ekpa_scraper/grading.py) · [Documentation index](../README.md) · [Architecture](../ARCHITECTURE.md)

## Responsibility and connections

Connects a Lesson to its PendingQuestion records. Despite the module name, it
never fills or saves grades. Both download and upload use
pending_questions_for_lesson(include_all=True); the grading inspection command
uses pending-only discovery.

The workflow follows the actual Results link, reads the manual-grading option
from the jump dropdown, validates its URL, and navigates directly there. This
avoids dependence on generated YUI IDs or the dropdown's JavaScript initialization.
The question table is parsed by normalized header text: pending vs total column.
With include_all, explicit manuallygraded and needsgrading URLs are also retained.

## API reference

### `PendingQuestion`

Fields/settings in declaration order:

- `number: str`
- `title: str`
- `url: str`
- `expected_responses: int | None` = `None`
- `graded_url: str` = `''`
- `ungraded_url: str` = `''`

### `normalized`

```python
normalized(text)
```

Casefold, normalize spaces and strip combining accents for UI label comparisons.

### `checked_report_url`

```python
checked_report_url(href, *, quiz_id=None, pending=False)
```

Resolve a report URL and enforce HTTPS EKPA origin, exact report path, optional quiz ID, and optional needsgrading mode/filter.

### `ordered_report_url`

```python
ordered_report_url(url, pagesize=100, page=0, selectors=SELECTORS)
```

Build a validated grading URL with stable adapter ordering, page size (default 100), and page number while retaining other query fields.

### `validate_report_order`

```python
validate_report_order(html, selectors=SELECTORS)
```

Read the rendered selected ordering; reject random/empty order. Return None if the settings selector is absent, rather than treating absence as random.

### `parse_pending_questions`

```python
parse_pending_questions(html, selectors=SELECTORS, quiz_id=None, include_all=False)
```

Locate exactly one question table and requested header, validate links, deduplicate and return PendingQuestion records with count and optional state URLs.

### `ensure_logged_in`

```python
ensure_logged_in(page, selectors=SELECTORS)
```

Reject navigation outside the EKPA HTTPS origin and a reappearing login form.

### `pending_questions_for_lesson`

```python
pending_questions_for_lesson(page, lesson, selectors=SELECTORS, include_all=False)
```

Validate quiz identity, navigate Results and the live manual-grading option, wait for the question table, and invoke its parser.

### `open_pending_grading`

```python
open_pending_grading(page, lessons, selectors=SELECTORS)
```

Deduplicate lessons/question links and open pending reports in new tabs in the same context. Return the number opened; no saves.

## Local dependencies

[moodle.py](moodle.md)

## Side effects, failure handling and tests

PendingQuestion.expected_responses is parsed from the selected column's leading
integer and can be None. That count is a validation aid, not an instruction to
invent pagination links. Tests cover pending/total columns, report origins,
relative dropdown destinations, ordering fallback, and the historical one-page
regression. Some stale internal comments describe pending-only behavior; the
include_all branch is the effective implementation.
