# `ekpa_scraper/storage.py` — Stable export paths and saved lesson history

[Source](../../ekpa_scraper/storage.py) · [Documentation index](../README.md) · [Architecture](../ARCHITECTURE.md)

## Responsibility and connections

Shared by CLI, export and upload. Converts output roots into absolute paths
(and Windows extended-length paths), derives stable course/quiz folder prefixes,
and retains discovery records so quizzes can be revisited after disappearing
from the dashboard or current listing.

IDs, not display titles, determine folder reuse. Titles are NFC-normalized,
sanitized and shortened to 48 characters. Duplicate directories with the same
stable prefix are rejected rather than guessed. A URL without one numeric id
falls back to a truncated SHA-256 of URL/title.

## API reference

### `output_path`

```python
output_path(value)
```

Expand user paths, make them absolute, and on Windows add extended-length local or UNC prefixes.

### `safe_title`

```python
safe_title(title)
```

Replace Windows-invalid/control characters, collapse whitespace, trim unsafe endings, and limit display title length.

### `entity_key`

```python
entity_key(url, title)
```

Return a numeric URL identity with activity-type prefix where applicable, or a deterministic name hash fallback.

### `entity_folder`

```python
entity_folder(parent, kind, key, title)
```

Find or create a folder matching kind/key, reuse it after a title change, and reject multiple matches.

### `append_scan`

```python
append_scan(output_root, account, lessons)
```

Validate account and consistent duplicate counts before writing; append one schema-versioned dashboard observation per unique course/lesson with shared scan ID and UTC timestamp.

### `lesson_folder`

```python
lesson_folder(output_root, account, lesson)
```

Resolve/create account, course and lesson directories using their stable identities.

### `remember_lessons`

```python
remember_lessons(output_root, account, lessons)
```

Append newly observed course/lesson titles and URLs to account discovered_lessons.jsonl; reruns can add repeated observations.

### `merge_known_lessons`

```python
merge_known_lessons(output_root, account, live_lessons)
```

Prefer supplied live lessons, then recover saved URLs from latest per-lesson history and discovery records; infer legacy course URLs from directory names where possible.

## Local dependencies

[dashboard.py](dashboard.md)

## Side effects, failure handling and tests

Dashboard counts in history are snapshots, not deltas to sum across runs.
merge_known_lessons returns a URL-deduplicated list; retained stale URLs can still
fail during later access. Discovery metadata is append-only, not a database of
completion. There is no cross-file transaction or locking. Tests: test_storage.py
and saved-lesson coverage in test_csv_sync.py.
