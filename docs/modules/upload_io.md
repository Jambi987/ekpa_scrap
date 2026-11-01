# `ekpa_scraper/upload_io.py` — Pre-save CSV write and replacement checks

[Source](../../ekpa_scraper/upload_io.py) · [Documentation index](../README.md) · [Architecture](../ARCHITECTURE.md)

## Responsibility and connections

Used by grade_upload after a complete plan has been built and preview events
written, but before the first remote save. Checks all distinct CSV paths in the
plan, not every CSV under the account. This reduces the chance of saving a grade
only to discover that Excel prevents local bookkeeping.

On Windows, ordinary open-for-write is insufficient: Excel may permit some access
while denying the DELETE access needed by os.replace. The native probe requests
read, write and delete access to an existing file, allowing shared read/write/delete,
then closes the handle without modifying or deleting the file.

## API reference

### `_windows_replace_access`

```python
_windows_replace_access(path)
```

Use ctypes CreateFileW/CloseHandle with OPEN_EXISTING and read/write/delete access. Convert invalid-handle result to PermissionError.

### `csv_access_message`

```python
csv_access_message(path)
```

Build a path-specific close-Excel/permissions explanation for local CSV access failures.

### `check_csv_writable`

```python
check_csv_writable(path)
```

Open the CSV r+b without writes, run the Windows replacement probe, create/remove a temporary file in the parent directory, and convert PermissionError into actionable ValueError.

### `check_upload_writes`

```python
check_upload_writes(plan)
```

Deduplicate and sort the CSV paths in a Change plan, then probe each.

## Local dependencies

No imports from another application module.

## Side effects, failure handling and tests

This is a point-in-time check, not a held lock or reservation. Access can change
after it passes, which is why grade_upload separately records a verified remote
save followed by local sync failure. Tests in test_upload_safety.py cover bytes
preservation and mocked sharing violations; they do not exercise real Excel or
CreateFileW on a Windows host in the Linux test environment.
