"""Pure HTML parser: no login, browser, printing or credential dependencies."""
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
from .moodle import ORIGIN, SELECTORS, MoodleLayoutError

@dataclass(frozen=True)
class Lesson:
    course_title: str
    title: str
    url: str
    displayed_count: int
    listed_entries: int
    course_url: str = ""


def text(node):
    return ' '.join(node.get_text(' ', strip=True).split())


def parse_dashboard(html, selectors=SELECTORS):
    soup = BeautifulSoup(html, 'html.parser')
    blocks = soup.select(selectors.grade_block)
    if len(blocks) != 1:
        raise MoodleLayoutError('Expected one Grade Me block. It may be absent, disabled, or changed; check moodle.py.')
    block = blocks[0]
    lessons = []
    for module in block.select(selectors.lesson):
        # In the supplied plugin HTML, each course dt precedes its dd lessons.
        headings = [n for n in module.find_all_previous('dt') if n in block.select(selectors.course_heading)]
        course = headings[0].select_one(selectors.course_title) if headings else None
        title = module.select_one(selectors.lesson_title)
        badge = module.select_one(selectors.badge)
        if course is None or title is None or badge is None:
            raise MoodleLayoutError('Incomplete lesson structure. Check selectors in moodle.py.')
        count_text = text(badge)
        if not count_text.isascii() or not count_text.isdigit():
            raise MoodleLayoutError('Unrecognized lesson count. Check the Grade Me badge format.')
        href = title.get('href')
        if not href:
            raise MoodleLayoutError('Lesson link is missing its destination.')
        url = urljoin(ORIGIN, href)
        parts = urlsplit(url)
        if parts.scheme != 'https' or parts.netloc != urlsplit(ORIGIN).netloc:
            raise MoodleLayoutError('Unexpected lesson link origin.')
        lessons.append(Lesson(text(course), text(title), url, int(count_text), len(module.select(selectors.entries)),
                              urljoin(ORIGIN, course["href"]) if course.get("href") else ""))
    if block.select(selectors.lesson_title) and not lessons:
        raise MoodleLayoutError('Lesson links exist but module selector no longer matches.')
    return lessons


def read_dashboard(page, selectors=SELECTORS):
    from .moodle import DASHBOARD_URL
    page.goto(DASHBOARD_URL, wait_until='domcontentloaded', timeout=45000)
    if page.locator(selectors.login_form).count():
        raise ValueError('Session returned to the login screen.')
    try:
        page.locator(selectors.grade_block).wait_for(state='attached', timeout=20000)
    except Exception:
        raise MoodleLayoutError('Grade Me block did not load. Check the dashboard and moodle.py.') from None
    return parse_dashboard(page.content(), selectors)
