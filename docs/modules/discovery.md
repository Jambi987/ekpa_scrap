# `ekpa_scraper/discovery.py` — Enrolled-course and quiz discovery

[Source](../../ekpa_scraper/discovery.py) · [Documentation index](../README.md) · [Architecture](../ARCHITECTURE.md)

## Responsibility and connections

Used by download before exporting submissions. It captures the actual
get_enrolled_courses_by_timeline_classification AJAX request made by My Courses,
replays its template with the current authenticated request context, and scans
both all and hidden classifications. Session-bearing request details stay in
memory and are not copied to logs.

Course IDs deduplicate results. Each course is visited at its quiz index;
if no quizzes match, its course page is tried. Relative links resolve against
the actual page URL, including bare view.php links and same-site base elements.
Only quiz view/report URLs are accepted, and report links are canonicalized to
view URLs. Titles are taken from the activity text, then accessibility/title
attributes, then a Quiz ID fallback.

## API reference

### `courses_from_response`

```python
courses_from_response(payload)
```

Validate the service JSON envelope, reject error entries, and return the data object containing the course list.

### `parse_course_quizzes`

```python
parse_course_quizzes(html, course, page_url=None)
```

Parse the main content of a quiz index/course page, reject Moodle error boxes, deduplicate quiz IDs, and return Lesson records for a supplied course.

### `enrolled_courses`

```python
enrolled_courses(page)
```

Temporarily attach a response listener, capture the request template, enumerate all/hidden course pages with advancing offsets and repeat detection, dispose responses, and return course dictionaries.

### `discover_all_lessons`

```python
discover_all_lessons(page)
```

Visit each discovered course index/fallback, print counts, deduplicate all quiz URLs, and fail if nonempty enrolled courses produce zero quizzes everywhere.

## Local dependencies

[dashboard.py](dashboard.md), [grading.py](grading.md), [moodle.py](moodle.md), [errors.py](errors.md)

## Side effects, failure handling and tests

Course pages use a requested limit of 100 and at most 1000 batches per
classification; repeated batches and non-advancing full batches are errors. The
capture window polls up to 60 times at 250 ms. Network failures use errors.py's
sanitized hints. A failure in discovery stops before export; per-lesson recovery
inside export does not cover this initial phase. Lazy course sections not exposed
in the index/fallback may require another adapter. Tests: test_discovery.py,
test_quiz_links.py, and test_errors.py.
