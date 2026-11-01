# `ekpa_scraper/dashboard.py` — Dashboard lesson and pending-count parsing

[Source](../../ekpa_scraper/dashboard.py) · [Documentation index](../README.md) · [Architecture](../ARCHITECTURE.md)

## Responsibility and connections

Defines `Lesson`, the shared immutable activity record used not just by the
dashboard but also by discovery, storage, export, and upload. Fields are course
and lesson titles/URLs plus dashboard badge and rendered-entry counts. Discovery
constructs these records with counts of zero; those zeroes are placeholders,
not a live assertion that no grading is pending.

The parser expects one Grade Me block and course `dt` headings followed by lesson
`dd` entries. It uses the nearest preceding matching course heading. A recognized
empty block returns an empty list; an absent/ambiguous block is a layout error.

## API reference

### `Lesson`

Fields/settings in declaration order:

- `course_title: str`
- `title: str`
- `url: str`
- `displayed_count: int`
- `listed_entries: int`
- `course_url: str` = `''`

### `text`

```python
text(node)
```

Collapse DOM node text whitespace to a single-space string.

### `parse_dashboard`

```python
parse_dashboard(html, selectors=SELECTORS)
```

Convert supplied HTML into Lesson records; validate expected block, titles, ASCII numeric badge and same-origin HTTPS lesson links. Count rendered entry nodes separately from the badge.

### `read_dashboard`

```python
read_dashboard(page, selectors=SELECTORS)
```

Navigate the authenticated page to /my/, detect login return, wait for the Grade Me block, and pass page content to the pure parser.

## Local dependencies

[moodle.py](moodle.md)

## Side effects, failure handling and tests

parse_dashboard itself has no browser, storage, printing, or credential I/O.
read_dashboard does navigate and wait. Missing structures fail explicitly rather
than silently reporting zero. `cli.print_lessons` presents results and
`storage.append_scan` records them. Tests: test_dashboard.py and test_storage.py.
This is the path for the lessons command, not full enrolled-course discovery.
