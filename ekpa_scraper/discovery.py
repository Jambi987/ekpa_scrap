"""Account-wide enrolled-course discovery and course quiz indexes.

Reuse the My Courses page's actual read-only AJAX request rather than guessing
which course cards/pagination happen to be rendered in the browser.
"""
import copy
import json
from urllib.parse import urljoin, urlsplit, parse_qs
from bs4 import BeautifulSoup
from .dashboard import Lesson
from .grading import ensure_logged_in
from .moodle import ORIGIN, MoodleLayoutError
from .errors import request_error_hint


def courses_from_response(payload):
    if not isinstance(payload, list):
        raise MoodleLayoutError('Unexpected My Courses service response.')
    for item in payload:
        data = item.get('data', {})
        if item.get('error'):
            raise MoodleLayoutError('Moodle refused the enrolled-course listing request.')
        if isinstance(data, dict) and isinstance(data.get('courses'), list):
            return data
    raise MoodleLayoutError('My Courses service response contains no course list.')


def parse_course_quizzes(html, course, page_url=None):
    soup = BeautifulSoup(html, 'html.parser')
    region = soup.select_one('#region-main') or soup.select_one('main')
    if region is None:
        raise MoodleLayoutError('Course quiz index main content is missing.')
    if region.select_one('.alert-danger, .errorbox, [data-rel="fatalerror"]'):
        raise MoodleLayoutError('Course quiz index reported a Moodle error.')
    # A bare view.php link is relative to /mod/quiz/, not to the site root.
    base = page_url or ORIGIN + '/mod/quiz/index.php?id=' + str(course['id'])
    base_tag = soup.select_one('base[href]')
    if base_tag:
        candidate = urljoin(base, base_tag['href'])
        if urlsplit(candidate).netloc == urlsplit(ORIGIN).netloc:
            base = candidate
    result = {}
    for anchor in region.select('a[href]'):
        url = urljoin(base, anchor['href'])
        parts = urlsplit(url)
        ids = parse_qs(parts.query).get('id', [])
        if (parts.scheme == 'https' and parts.netloc == urlsplit(ORIGIN).netloc
                and parts.path in ('/mod/quiz/view.php', '/mod/quiz/report.php')
                and len(ids) == 1 and ids[0].isdigit()):
            url = ORIGIN + '/mod/quiz/view.php?id=' + ids[0]
            name = anchor.select_one('.instancename') or anchor
            title = ' '.join(name.get_text(' ', strip=True).split())
            title = title or anchor.get('aria-label') or anchor.get('title') or 'Quiz ' + ids[0]
            # Report icons can duplicate the activity link. Keep the first name.
            result.setdefault(url, Lesson(course['fullname'], title, url, 0, 0,
                                          ORIGIN + '/course/view.php?id=' + str(course['id'])))
    return list(result.values())



def enrolled_courses(page):
    captured = []
    def capture(response):
        parts = urlsplit(response.url)
        if parts.netloc != urlsplit(ORIGIN).netloc or parts.path != '/lib/ajax/service.php':
            return
        try:
            payload = response.request.post_data_json
            if isinstance(payload, list):
                for request in payload:
                    if request.get('methodname', '').endswith('get_enrolled_courses_by_timeline_classification'):
                        captured.append((response.url, copy.deepcopy(request)))
        except Exception:
            pass
    page.on('response', capture)
    try:
        print('Opening My Courses...')
        page.goto(ORIGIN + '/my/courses.php', wait_until='domcontentloaded', timeout=45000)
        ensure_logged_in(page)
        for _ in range(60):
            if captured:
                break
            page.wait_for_timeout(250)
    except ValueError:
        raise
    except Exception as exc:
        raise MoodleLayoutError('Opening My Courses failed: ' + request_error_hint(exc)) from None
    finally:
        page.remove_listener('response', capture)
    if not captured:
        raise MoodleLayoutError('Could not capture the My Courses listing request. Supply the My Courses page HTML; no complete-course export was claimed.')
    endpoint, template = captured[0]
    found = {}
    # Moodle's normal All view may exclude courses hidden by the user.
    for classification in ('all', 'hidden'):
        offset = 0
        seen_batches = set()
        for _ in range(1000):
            request = copy.deepcopy(template)
            request['index'] = 0
            request['args'].update(classification=classification, offset=offset, limit=100)
            # Remove a UI text search so discovery is not restricted by a saved filter.
            if 'searchvalue' in request['args']:
                request['args']['searchvalue'] = ''
            print(f'Reading enrolled courses ({classification}, offset {offset})...')
            try:
                response = page.context.request.post(endpoint, data=[request], timeout=45000)
            except Exception as exc:
                raise MoodleLayoutError('Retrieving enrolled courses failed: ' + request_error_hint(exc)) from None
            try:
                if not response.ok:
                    raise MoodleLayoutError(f'Course listing returned HTTP {response.status}.')
                try:
                    payload = response.json()
                except Exception as exc:
                    raise MoodleLayoutError('Reading the course-list response failed: ' + request_error_hint(exc)) from None
                data = courses_from_response(payload)
            finally:
                response.dispose()
            courses = data['courses']
            if not courses:
                break
            batch = tuple(str(course['id']) for course in courses)
            if batch in seen_batches:
                raise MoodleLayoutError('Course pagination repeated a page; complete discovery could not be confirmed.')
            seen_batches.add(batch)
            for course in courses:
                if not str(course.get('id', '')).isdigit() or not course.get('fullname'):
                    raise MoodleLayoutError('Invalid course identity from Moodle.')
                found[str(course['id'])] = course
            nextoffset = data.get('nextoffset')
            if nextoffset is not None:
                if int(nextoffset) < 0:
                    break
                if int(nextoffset) <= offset:
                    if len(courses) < 100:
                        break
                    raise MoodleLayoutError('Course listing did not advance its offset.')
                offset = int(nextoffset)
            else:
                offset += len(courses)
                if len(courses) < 100:
                    break
        else:
            raise MoodleLayoutError('Enrolled-course pagination exceeded the scan limit.')
    return list(found.values())


def discover_all_lessons(page):
    courses = enrolled_courses(page)
    print(f'Enrolled courses discovered: {len(courses)}')
    lessons = {}
    for course in courses:
        print(f'  Scanning course: {course["fullname"]}')
        index_url = ORIGIN + '/mod/quiz/index.php?id=' + str(course['id'])
        try:
            response = page.goto(index_url, wait_until='domcontentloaded', timeout=45000)
        except Exception as exc:
            raise MoodleLayoutError('Opening the course quiz index failed: ' + request_error_hint(exc)) from None
        ensure_logged_in(page)
        if response and response.status >= 400:
            raise MoodleLayoutError('Course quiz index is inaccessible; complete discovery stopped.')
        found = parse_course_quizzes(page.content(), course, page_url=page.url)
        print(f'    Quiz index matched {len(found)} activities (course {course["id"]}).')
        if not found:
            # Some course formats expose activity links only on the course page.
            course_url = ORIGIN + '/course/view.php?id=' + str(course['id'])
            print(f'    Checking course page: {course_url}')
            try:
                response = page.goto(course_url, wait_until='domcontentloaded', timeout=45000)
            except Exception as exc:
                raise MoodleLayoutError('Opening the course page failed: ' + request_error_hint(exc)) from None
            ensure_logged_in(page)
            if response and response.status >= 400:
                raise MoodleLayoutError('Course page is inaccessible; complete discovery stopped.')
            found = parse_course_quizzes(page.content(), course, page_url=page.url)
            print(f'    Course page matched {len(found)} activities.')
        for lesson in found:
            lessons[lesson.url] = lesson
    print(f'Quiz/test activities discovered: {len(lessons)}')
    if courses and not lessons:
        raise MoodleLayoutError('Courses were found, but no quiz/test links matched on their quiz indexes or course pages. No successful export was claimed. Supply the main-content HTML from one course quiz index (/mod/quiz/index.php?id=COURSE_ID) to inspect this site layout.')
    return list(lessons.values())
