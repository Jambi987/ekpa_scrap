# `ekpa_scraper/moodle.py` — Site adapter and shared layout errors

[Source](../../ekpa_scraper/moodle.py) · [Documentation index](../README.md) · [Architecture](../ARCHITECTURE.md)

## Responsibility and connections

Centralizes the EKPA origin, login/dashboard URLs, selectors, Greek column
headings, and the manual-report ordering option. Pure parsers and browser flows
accept a `selectors=SELECTORS` parameter in many entry points so changes can be
injected without rewriting storage.

`MoodleSelectors` is frozen. `SELECTORS` is its default instance.
`MoodleLayoutError` subclasses ValueError so CLI failures can be explained without
printing raw Playwright request data. These settings are site-specific rather than
a claim of universal Moodle compatibility.

## API reference

### `MoodleSelectors`

Fields/settings in declaration order:

- `login_form: str` = `'form#login'`
- `username: str` = `'input[name="username"]'`
- `password: str` = `'input[name="password"]'`
- `submit: str` = `'button[type="submit"], input[type="submit"]'`
- `authenticated: str` = `'a[href*="/login/logout.php"][href*="sesskey="]'`
- `grade_block: str` = `'[data-block="grade_me"], section.block_grade_me'`
- `course_heading: str` = `'dt.cmod'`
- `course_title: str` = `'a.grademe-course-name'`
- `lesson: str` = `'dd.module'`
- `lesson_title: str` = `'a.grademe-mod-name'`
- `badge: str` = `'.dd-wrap > .badge'`
- `entries: str` = `'ul.gradable-list > li.gradable'`
- `results_link: str` = `'li[data-key="quiz_report"] a[href*="/mod/quiz/report.php"]'`
- `report_dropdown: str` = `'select[name="jump"]:has(option[value*="mode=grading"])'`
- `question_table: str` = `'table#questionstograde'`
- `question_name: str` = `'td.c2'`
- `pending_column_title: str` = `'Προς βαθμολόγηση'`
- `total_column_title: str` = `'Σύνολο'`
- `response_mark: str` = `'.comment input[name$="-mark"]'`
- `submission: str` = `'div.que.essay'`
- `exercise_text: str` = `'.qtext'`
- `attachment_links: str` = `'.attachments a[href]'`
- `paging_links: str` = `'.paging a[href], .pagination a[href]'`
- `grading_order: str` = `'studentlastname'`
- `report_order_select: str` = `'select[name="order"]'`

### `MoodleLayoutError`

Required site structure is missing or ambiguous; do not report false zeroes.

## Local dependencies

No imports from another application module.

## Side effects, failure handling and tests

The valid ordering value is studentlastname, not lastname. An invalid value can
make Moodle fall back to random ordering and hide pagination. Some markup is
still embedded in other modules: the English attempt heading in submissions,
form validation/editor selectors in grade_upload, and course AJAX discovery.
Changing this adapter alone may therefore not handle every theme or version.
Review tests for dashboard, grading, report order, quiz links, and submissions
when changing it. This module has no I/O side effects.
