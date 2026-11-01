# `ekpa_scraper/files.py` — Attachment fetching, content versions, ZIPs and cache history

[Source](../../ekpa_scraper/files.py) · [Documentation index](../README.md) · [Architecture](../ARCHITECTURE.md)

## Responsibility and connections

Called by export with the authenticated Playwright context and an Upload record.
Fetches via context.request rather than browser download events. Each redirect is
checked against EKPA HTTPS origin. Downloads remain in memory before saving;
Content-Length and actual body-size checks enforce 100 MiB, but a missing/incorrect
header can still mean the body is received before the size rejection.

The history key is SHA-256 of the original URL, not the content hash. A separate
SHA-256 verifies local file bytes. The latest complete record for that key is used
only if its direct child path exists, is not a symlink and matches its hash.
ETag is preferred over Last-Modified for conditional requests. A 304 reuses the
verified file; otherwise content is fetched and non-overwriting save rules apply.
The cache therefore avoids transfers only when the server supports validation.

## API reference

### `filename`

```python
filename(value)
```

Sanitize Windows-invalid names and reserved device stems; limit stem to 90 characters and suffix to 12.

### `save_bytes`

```python
save_bytes(path, data)
```

Reuse identical files, otherwise save under a 16-character SHA-256 suffix; reject symlink destinations and conflicting versioned contents. Return the saved Path.

### `extract_zip`

```python
extract_zip(path, student_dir)
```

Validate entry count, advertised sizes and destination paths before extracting via save_bytes; reject traversal/absolute/drive paths and symlinks.

### `download_event`

```python
download_event(student_dir, status, **fields)
```

Append a UTC JSON object to the student directory download_history.jsonl.

### `cached_upload`

```python
cached_upload(student_dir, key)
```

Read history, ignore malformed JSON lines, select the latest matching complete entry and validate its local file hash; return record/path or (None, None).

### `download_upload`

```python
download_upload(context, upload, student_dir)
```

Perform at most six request iterations (redirects included), dispose responses, reject login-page payloads and invalid ZIPs, save/extract, record completion or reuse, and return a Path.

## Local dependencies

[moodle.py](moodle.md)

## Side effects, failure handling and tests

ZIP limits: 2000 entries, 100 MiB per member and 300 MiB summed advertised
uncompressed size. Archives remain on disk; extracted files are never executed,
and nested archives are not recursively unpacked. Reused ZIPs are re-extracted to
repair missing members. Complete is logged only after extraction succeeds; export
logs failed events. Changed local files are preserved and a remote content version
is created instead. Logs have no compaction, locking or transactional durability;
malformed JSON lines are skipped, but malformed valid JSON records may still fail.
Tests: test_downloads.py and test_download_resume.py.
