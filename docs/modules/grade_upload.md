# `ekpa_scraper/grade_upload.py` — Plan, submit and verify CSV grade changes

[Source](../../ekpa_scraper/grade_upload.py) · [Documentation index](../README.md) · [Architecture](../ARCHITECTURE.md)

## Responsibility and connections

The only module that saves grades/feedback to Moodle. Called by cli for upload.
`Edit` binds a CSV row to a saved question-usage/slot identity and desired fields;
`Change` holds the validated live before/after values, response URL and update flags.
The last_moodle_grade in Edit is a snapshot, not authority to skip a live check.

Preflight reads all account CSVs, resolves lesson scope, maps identities to live
manual-report pages, and validates values/form controls. It scans explicit graded
reports first when available, then all responses. A nonempty live mark, including
zero, or confirmed graded state causes the entire response to be skipped. There
is no overwrite-graded flag. Missing requested identities stop the plan before
any saves. Browser pages have one response at a time for unambiguous form submission.

Apply checks all affected CSVs are writable, then reopens each planned response,
rechecks identity/live values/local input, fills the appropriate fields and uses
the native Save button. Notes update an Atto or TinyMCE editor and backing textarea
where present. It reloads and verifies grade/notes before updating the local CSV.
This is sequential per-response processing, not a transaction across the account.

## API reference

### `Edit`

Fields/settings in declaration order:

- `csv_path: Path`
- `row_index: int`
- `submission_key: str`
- `student_name: str`
- `grade: str`
- `notes: str`
- `last_moodle_grade: str`

### `Change`

Fields/settings in declaration order:

- `edit: Edit`
- `lesson_title: str`
- `url: str`
- `old_grade: str`
- `old_notes: str`
- `new_grade: str`
- `new_notes: str`
- `update_grade: bool`
- `update_notes: bool`

### `number`

```python
number(value)
```

Parse finite Decimal grades after comma-to-dot conversion; reject nonnumeric, NaN or infinity.

### `plain_notes`

```python
plain_notes(html)
```

Convert editor HTML to normalized plain text, preserving selected line breaks for comparison.

### `notes_html`

```python
notes_html(notes)
```

Escape plain-text feedback and wrap it in a paragraph with br line breaks.

### `read_edits`

```python
read_edits(root, diagnostics=None)
```

Read every students.csv/index pair recursively, require row-count/name correspondence, skip completely blank requested fields, validate numeric grades and optionally populate diagnostics.

### `snapshot`

```python
snapshot(page, submission_key, selectors=SELECTORS)
```

Require exactly one response with the requested key; read live mark/comment and min/max mark bounds from the form; return submission, grade, plain notes, minimum and ceiling.

### `is_graded`

```python
is_graded(submission, current_grade)
```

Return true for any nonblank current mark or submission status graded.

### `make_change`

```python
make_change(edit, lesson_title, url, submission, old_grade, old_notes, minimum, maximum)
```

Validate student name, skip already graded responses, validate requested mark range, compare notes, and produce a Change; blanks preserve existing values.

### `response_url`

```python
response_url(url, page_number, selectors=SELECTORS, grade_filter='all')
```

Set all or manuallygraded filter and request one response at a specified page using the shared stable-order builder.

### `response_pages`

```python
response_pages(page, question, root, selectors=SELECTORS, grade_filter='all')
```

Traverse only rendered matching paging links with a 10000-page bound; validate order, log safe query fields/response IDs and yield requested URL plus parsed responses.

### `build_plan`

```python
build_plan(page, output, account, lesson_id=None, selectors=SELECTORS)
```

Print/log account-wide CSV diagnostics, filter saved lesson URLs, skip live graded responses, collect validated changes and reject unresolved selected response identities.

### `save_button_index`

```python
save_button_index(buttons)
```

Require exactly one enabled normalized label starting with save or the Greek equivalent; reject ambiguity.

### `grading_controls`

```python
grading_controls(question, url)
```

Require one response mark within one ancestor form; validate HTTPS same-origin POST report action and quiz ID, then identify the native Save control.

### `log_event`

```python
log_event(root, event)
```

Append UTC audit JSONL; convert PermissionError into a log-path-specific message without exposing session-bearing request data.

### `apply_change`

```python
apply_change(page, change, root, selectors=SELECTORS)
```

Recheck before filling; skip newly graded responses; submit, reload and verify; distinguish uncertain remote outcome from verified remote save/local CSV failure; return true only on full success.

### `upload_grades`

```python
upload_grades(page, output, account, apply=False, lesson_id=None)
```

Create audit start, build and print plan, return for no changes or preview, precheck local writes, apply sequentially and print verified/skipped counts.

## Local dependencies

[csv_store.py](csv_store.md), [grading.py](grading.md), [moodle.py](moodle.md), [storage.py](storage.md), [submissions.py](submissions.md), [upload_io.py](upload_io.md), [export.py](export.md)

## Side effects, failure handling and tests

Preview performs network reads and local audit writes, but never calls apply.
Blank fields cannot erase Moodle values. Notes-only changes are possible only for
ungraded responses. Save-button/form selectors partly live here rather than in
moodle.py. If order shifts between plan and apply, the response key check stops
instead of writing to another student.

The all-account CSV read precedes lesson filtering, so diagnostics and validation
can mention out-of-scope files. A supplied unknown lesson ID currently yields an
empty scope/no changes rather than a dedicated invalid-ID exception. New lessons
must first be discovered/downloaded; upload uses saved URLs rather than full live
course discovery.

Audit states distinguish preflight_failed, local_write_check_failed, submitting,
unverified_after_submit, moodle_verified, moodle_verified_csv_sync_failed and verified.
Not all pre-submit apply exceptions get a dedicated audit failure event; the final
terminal error remains necessary. Already completed responses are not rolled back
when later ones fail. Tests: the test_upload* and test_grade_upload modules plus
test_moodle_order_paging.py. See DATA_AND_LOGS for event details.
