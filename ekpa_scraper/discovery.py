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


def parse_course_quizzes(html, course):
    soup = BeautifulSoup(html, 'html.parser')
    region = soup.select_one('#region-main') or soup.select_one('main')
    if region is None:
        raise MoodleLayoutError('Course quiz index main content is missing.')
    if region.select_one('.alert-danger, .errorbox, [data-rel="fatalerror"]'):
        raise MoodleLayoutError('Course quiz index reported a Moodle error.')
    result = {}
    for anchor in region.select('a[href]'):
        url = urljoin(ORIGIN, anchor['href'])
        parts = urlsplit(url)
        ids = parse_qs(parts.query).get('id', [])
        if (parts.scheme == 'https' and parts.netloc == urlsplit(ORIGIN).netloc
                and parts.path == '/mod/quiz/view.php' and len(ids) == 1 and ids[0].isdigit()):
            url = ORIGIN + '/mod/quiz/view.php?id=' + ids[0]
            title = ' '.join(anchor.get_text(' ', strip=True).split())
            if title:
                result[url] = Lesson(course['fullname'], title, url, 0, 0,
                                     ORIGIN + '/course/view.php?id=' + str(course['id']))
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
        page.goto(ORIGIN + '/my/courses.php', wait_until='domcontentloaded', timeout=45000)
        ensure_logged_in(page)
        for _ in range(60):
            if captured:
                break
            page.wait_for_timeout(250)
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
            response = page.context.request.post(endpoint, data=[request], timeout=45000)
            try:
                if not response.ok:
                    raise MoodleLayoutError('Could not retrieve the enrolled-course list.')
                data = courses_from_response(response.json())
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
        response = page.goto(ORIGIN + '/mod/quiz/index.php?id=' + str(course['id']),
                             wait_until='domcontentloaded', timeout=45000)
        ensure_logged_in(page)
        if response and response.status >= 400:
            raise MoodleLayoutError('Course quiz index is inaccessible; complete discovery stopped.')
        for lesson in parse_course_quizzes(page.content(), course):
            lessons[lesson.url] = lesson
    print(f'Quiz/test activities discovered: {len(lessons)}')
    return list(lessons.values())
