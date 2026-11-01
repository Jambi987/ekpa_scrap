# `ekpa_scraper/export.py` — Download orchestration and student roster registration

[Source](../../ekpa_scraper/export.py) · [Documentation index](../README.md) · [Architecture](../ARCHITECTURE.md)

## Responsibility and connections

Called by the download CLI after discovery and saved-lesson merging. Uses grading
for report navigation, submissions for HTML conversion, storage for stable folders,
csv_store for local rows, and files for attachments/ZIPs. It never calls the grade
submission API.

Each question uses one response tab and an ordered queue of graded, ungraded and
all URLs where available. Response IDs deduplicate overlaps within that question.
Explicit state filters override parsed status. A single question normally writes
into the lesson root; multiple questions use test_<slot>_<qid> directories, while
an established root slot remains there. Exercise and CSV/index files belong at
the question's export root; downloads belong in the student's subfolder.

## API reference

### `append_exercise`

```python
append_exercise(root, text)
```

Append a nonempty description only if it is not already a substring of previous text; add a UTC update separator after the first version.

### `register_student`

```python
register_student(root, submission)
```

Validate CSV/index row counts, rematch unique names, reuse a saved response folder and sync its row, or create a collision-safe new student folder and append its identity index record.

### `page_key`

```python
page_key(url)
```

Normalize report query ordering and missing page=0 into a visited-page key; shared with uploader traversal.

### `_export_batch`

```python
_export_batch(page, lessons, output, account, selectors=SELECTORS)
```

Process lessons/questions/pages, validate ordering and response totals, write exercise/roster, fetch attachments, record file failures and continue remaining attachments.

### `export_pending`

```python
export_pending(page, lessons, output, account, selectors=SELECTORS)
```

Deduplicate lessons and run each independently; catch per-lesson failures, attempt later lessons, and raise an aggregate failure if any remained incomplete.

## Local dependencies

[files.py](files.md), [grading.py](grading.md), [moodle.py](moodle.md), [storage.py](storage.md), [submissions.py](submissions.md), [csv_store.py](csv_store.md)

## Side effects, failure handling and tests

A question allows at most 100 visited pages with initial requested page size 100.
A missing/ambiguous parser structure or row mismatch stops that lesson. Individual
attachment errors are logged by exception type and processing continues; a failure
to write the failure log itself can escalate to the lesson handler. Failed tabs
remain until browser cleanup, though the current browser is headless. Counters
include unchanged attachments. Tests directly cover registration/exercise behavior
in test_downloads.py; attachment tests cover file logic, not every full export
error-continuation path.
