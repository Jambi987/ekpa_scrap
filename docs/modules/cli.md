# `ekpa_scraper/cli.py` — Command routing and console output

[Source](../../ekpa_scraper/cli.py) · [Documentation index](../README.md) · [Architecture](../ARCHITECTURE.md)

## Responsibility and connections

Both entry points delegate here. `main` creates argparse subcommands, validates
numeric account strings, initializes the Windows credential backend, and enters
`authenticated_page` only for commands requiring Moodle. Feature imports happen
inside their command branches, keeping account-only commands independent of
parser imports until needed.

`lessons` and `grading` call dashboard reading and append_scan; `grading` then opens
pending reports. `download` uses course discovery, remembers/merges lessons, and
calls export_pending. `upload` calls upload_grades with apply and lesson_id.
Download does not depend on successfully reading the Grade Me block.
The dashboard try/except contains a historical download fallback branch that is
unreachable inside the lessons/grading dispatch; actual download discovery follows
the separate download branch.

## API reference

### `print_lessons`

```python
print_lessons(lessons)
```

Print per-lesson course/title, badge pending count and rendered entry count; flag mismatches and print summed totals. Does not change Moodle.

### `main`

```python
main()
```

Parse commands/options; manage credentials/session; dispatch features; pause where configured; return 0 on success or 1 on handled application failure. argparse handles malformed arguments separately.

## Local dependencies

[accounts.py](accounts.md), [browser.py](browser.md), [dashboard.py](dashboard.md), [storage.py](storage.md), [grading.py](grading.md), [discovery.py](discovery.md), [export.py](export.md), [grade_upload.py](grade_upload.md)

## Side effects, failure handling and tests

--output defaults to the literal relative directory output. Only upload has
--apply and --lesson-id. Login/grading always pause after success; --keep-open
adds a success pause to other network commands. Several failure paths pause even
without it. ModuleNotFoundError prints the missing module; ValueError prints its
message; other exceptions omit raw sensitive call logs. Help is available before
credential-store initialization. See the root usage guide for the complete matrix.
There is no dedicated CLI argument test file in the current suite.
