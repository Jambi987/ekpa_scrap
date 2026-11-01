# `ekpa_scraper/csv_store.py` — CSV validation, replacement and grade synchronization

[Source](../../ekpa_scraper/csv_store.py) · [Documentation index](../README.md) · [Architecture](../ARCHITECTURE.md)

## Responsibility and connections

Used by export.register_student and grade_upload for local roster data. FIELDS
fixes six ordered columns: student_name, grade, notes, moodle_grade, moodle_status,
last_checked. Reading also accepts the legacy first three columns and fills
missing snapshot fields with empty strings. The module does not identify Moodle
responses; callers supply the correct row index using students_index.jsonl.

The file is rewritten atomically rather than literally appending CSV bytes.
Existing rows remain and new rows are added by the caller. Notes are always
preserved. A nonempty live mark mirrors into grade only when grade is blank or
matches the previous moodle_grade. A differing local grade remains intentional.
A now-blank live mark updates the snapshot but does not erase a nonblank local
grade; this can become an upload candidate if Moodle is truly ungraded.

## API reference

### `read_rows`

```python
read_rows(path)
```

Return [] if absent; read UTF-8-sig, infer comma/semicolon from the header, require exact supported headers and well-formed cells, normalize rows to six fields.

### `write_rows`

```python
write_rows(path, rows)
```

If replacing an existing CSV, create students.before_sync.csv once; write UTF-8 BOM semicolon CSV to a same-directory temporary file, os.replace it, and clean up the temp file.

### `sync_row`

```python
sync_row(rows, index, submission)
```

Mutate/append the selected row according to grade-preservation rules; update name, moodle_grade/status and UTC last_checked; return the rows.

## Local dependencies

No imports from another application module.

## Side effects, failure handling and tests

The backup is taken on the first rewrite, not on every run and not only during
legacy migration. It may contain an early incomplete roster. CSV replacement can
fail under Excel's sharing lock; upload_io prechecks that before remote writes.
A CSV and its response index are separate files, so interruption between their
updates can require manual paired recovery. Tests: test_csv_sync.py,
test_downloads.py, test_grade_upload.py and test_upload_safety.py.
