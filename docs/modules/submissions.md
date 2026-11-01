# `ekpa_scraper/submissions.py` — Response identity, attachment and paging parsing

[Source](../../ekpa_scraper/submissions.py) · [Documentation index](../README.md) · [Architecture](../ARCHITECTURE.md)

## Responsibility and connections

Pure parsing used by both export and grade_upload. `Upload` holds a URL and
filename. `Submission` holds a response key, name, attempt number, exercise text,
attachment tuple, and observed Moodle grade/status.

The response key is question-usage ID plus slot from `question-<usage>-<slot>`,
joined with a colon. It is not a student account ID. Names come from a preceding
English h4 matching Attempt number N for NAME; trailing parenthesized text is
removed. An anonymous or localized heading may require changing ATTEMPT.
Exercise text preserves selected block breaks but collapses whitespace, including
inside preformatted text; it is a plain-text extraction, not a faithful HTML copy.

## API reference

### `Upload`

Fields/settings in declaration order:

- `url: str`
- `filename: str`

### `Submission`

Fields/settings in declaration order:

- `key: str`
- `student_name: str`
- `attempt_number: str`
- `exercise: str`
- `uploads: tuple[Upload, ...]`
- `moodle_grade: str` = `''`
- `moodle_status: str` = `'unknown'`

### `parse_submissions`

```python
parse_submissions(html, selectors=SELECTORS)
```

Parse essay divs, require heading/identity/prompt, collect unique same-origin response_attachments links, read the actual mark input and status classes, and return Submission records. Raise if no responses exist.

### `next_pages`

```python
next_pages(html, current_url, selectors=SELECTORS)
```

Resolve rendered paging anchors and retain only HTTPS same-origin manual-report links matching the current quiz ID, slot, question ID and grade filter; deduplicate URLs.

## Local dependencies

[moodle.py](moodle.md)

## Side effects, failure handling and tests

Marks accept a simple signed integer/decimal format after comma-to-dot conversion.
A nonempty mark (including zero) means graded; otherwise needsgrading/requiresgrading
classes mean needs_grading, else unknown. Maximum-mark display text is ignored.
The parser does not import remote feedback into CSV notes. Third-party viewer links
are ignored. Paging accepts all, manuallygraded and needsgrading; it does not infer
pages from counts. Tests: test_downloads.py and test_csv_sync.py; upload paging tests
exercise the same parser through orchestration.
