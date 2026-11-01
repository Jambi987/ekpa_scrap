"""Manual-grading navigation and pure question-table parsing.

Only opens pending-grading pages. Never fills, submits, or saves grading forms.
"""
from dataclasses import dataclass
import unicodedata
import re
from urllib.parse import parse_qs, urljoin, urlsplit, urlencode
from bs4 import BeautifulSoup
from .moodle import ORIGIN, SELECTORS, MoodleLayoutError

@dataclass(frozen=True)
class PendingQuestion:
    number: str
    title: str
    url: str
    expected_responses: int | None = None
    graded_url: str = ""
    ungraded_url: str = ""


def normalized(text):
    value = unicodedata.normalize('NFD', ' '.join(text.split()).casefold())
    return ''.join(ch for ch in value if unicodedata.category(ch) != 'Mn')


def checked_report_url(href, *, quiz_id=None, pending=False):
    url = urljoin(ORIGIN, href)
    parts = urlsplit(url)
    params = parse_qs(parts.query)
    if (parts.scheme != 'https' or parts.netloc != urlsplit(ORIGIN).netloc
            or parts.path != '/mod/quiz/report.php'):
        raise MoodleLayoutError('Unexpected report link destination; check the Moodle adapter.')
    if quiz_id is not None and params.get('id') != [quiz_id]:
        raise MoodleLayoutError('Report link belongs to a different lesson.')
    if pending and (params.get('mode') != ['grading'] or params.get('grade') != ['needsgrading']):
        raise MoodleLayoutError('Pending column contains an unexpected grading link; navigation stopped.')
    return url



def ordered_report_url(url, pagesize=100, page=0, selectors=SELECTORS):
    """Use Moodle's actual report option value, not its human-readable label."""
    url = checked_report_url(url)
    parts = urlsplit(url)
    args = parse_qs(parts.query)
    if args.get('mode') != ['grading']:
        raise MoodleLayoutError('Expected a manual-grading report URL.')
    args.update(order=[selectors.grading_order], pagesize=[str(pagesize)], page=[str(page)])
    return parts._replace(query=urlencode([(k, v) for k, values in args.items() for v in values])).geturl()


def validate_report_order(html, selectors=SELECTORS):
    """Moodle silently resets unknown order values to random and hides paging."""
    soup = BeautifulSoup(html, 'html.parser')
    dropdown = soup.select_one(selectors.report_order_select)
    if dropdown is None:
        return None
    selected = dropdown.select_one('option[selected]') or dropdown.select_one('option')
    if selected is None:
        raise MoodleLayoutError('The grading order selector has no options.')
    value = selected.get('value', '')
    if not value or value == 'random':
        raise MoodleLayoutError('Moodle returned random response ordering, which disables pagination. Check the grading_order adapter value against the report Order attempts by options. No grade upload was started.')
    return value

def is_empty_grading_report(html, selectors=SELECTORS, quiz_id=None):
    """Recognize Moodle's empty manual-report renderer, independent of language.

    Moodle renders a show-auto toggle immediately followed by an info notice
    instead of the questions table when no manual response rows are available.
    A missing table or arbitrary notification alone is never evidence of empty.
    """
    soup = BeautifulSoup(html, 'html.parser')
    region = soup.select_one('#region-main') or soup.select_one('main')
    if region is None or soup.select_one(selectors.login_form):
        return False
    if region.select_one('table, .alert-danger, .errorbox, [data-rel="fatalerror"]'):
        return False
    if region.select_one(selectors.submission):
        return False
    toggles = region.select(selectors.grading_toggle)
    notices = region.select(selectors.grading_empty_notice)
    if len(toggles) != 1 or len(notices) != 1 or not notices[0].get_text(' ', strip=True):
        return False
    links = toggles[0].select('a[href]')
    if len(links) != 1:
        return False
    try:
        url = checked_report_url(links[0]['href'], quiz_id=quiz_id)
    except MoodleLayoutError:
        return False
    params = parse_qs(urlsplit(url).query)
    return (params.get('mode') == ['grading'] and params.get('includeauto') == ['1']
            and len(params.get('id', [])) == 1 and params['id'][0].isdigit()
            and not any(key in params for key in ('slot', 'qid', 'grade')))


def parse_pending_questions(html, selectors=SELECTORS, quiz_id=None, include_all=False):
    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.select(selectors.question_table)
    if not tables and is_empty_grading_report(html, selectors, quiz_id):
        return []
    if len(tables) != 1:
        raise MoodleLayoutError('Expected the manual-grading question table. Check question_table in moodle.py.')
    table = tables[0]
    headers = table.select('thead th')
    column_title = selectors.total_column_title if include_all else selectors.pending_column_title
    matches = [i for i, cell in enumerate(headers)
               if normalized(cell.get_text(' ', strip=True)) == normalized(column_title)]
    if len(matches) != 1:
        raise MoodleLayoutError('Cannot identify the pending-grading column; check its heading in moodle.py.')
    column = matches[0]
    result = []
    seen = set()
    for row in table.select('tbody tr'):
        cells = row.find_all('td', recursive=False)
        if not cells:
            continue
        if len(cells) <= column:
            raise MoodleLayoutError('Question-table row has unexpected columns.')
        # Scope anchors strictly to the pending column, never the grade=all column.
        for anchor in cells[column].select('a[href]'):
            url = checked_report_url(anchor['href'], quiz_id=quiz_id, pending=not include_all)
            if include_all and (parse_qs(urlsplit(url).query).get('grade') != ['all']
                                or parse_qs(urlsplit(url).query).get('mode') != ['grading']):
                raise MoodleLayoutError('Total column does not contain the expected grade=all link.')
            if url in seen:
                continue
            seen.add(url)
            name = row.select_one(selectors.question_name)
            if name is None:
                raise MoodleLayoutError('Question name is missing; check question_name in moodle.py.')
            state_urls = {}
            if include_all:
                for link in row.select('a[href]'):
                    args = parse_qs(urlsplit(link['href']).query)
                    state = args.get('grade', [''])[0]
                    if args.get('mode') == ['grading'] and state in ('manuallygraded', 'needsgrading'):
                        state_urls[state] = checked_report_url(link['href'], quiz_id=quiz_id)
            count = re.match(r'\s*([0-9]+)', cells[column].get_text(' ', strip=True))
            result.append(PendingQuestion(cells[0].get_text(' ', strip=True),
                                          name.get_text(' ', strip=True), url,
                                          int(count[1]) if count else None,
                                          state_urls.get('manuallygraded', ''), state_urls.get('needsgrading', '')))
    return result


def ensure_logged_in(page, selectors=SELECTORS):
    parts = urlsplit(page.url)
    if parts.scheme != 'https' or parts.netloc != urlsplit(ORIGIN).netloc:
        raise ValueError('Unexpected destination while opening a lesson.')
    if page.locator(selectors.login_form).count():
        raise ValueError('Session expired; the site returned to login.')


def pending_questions_for_lesson(page, lesson, selectors=SELECTORS, include_all=False):
    """Follow actual UI links/options, avoiding generated IDs or hardcoded quiz IDs."""
    quiz_ids = parse_qs(urlsplit(lesson.url).query).get('id', [])
    if len(quiz_ids) != 1 or not quiz_ids[0].isdigit():
        raise MoodleLayoutError('Cannot identify this lesson quiz ID.')
    quiz_id = quiz_ids[0]
    page.goto(lesson.url, wait_until='domcontentloaded', timeout=45000)
    ensure_logged_in(page, selectors)
    results = page.locator(selectors.results_link)
    results.wait_for(state='attached', timeout=20000)
    href = results.get_attribute('href')
    if not href:
        raise MoodleLayoutError('Results navigation has no destination.')
    checked_report_url(href, quiz_id=quiz_id)
    results.click()
    dropdown = page.locator(selectors.report_dropdown)
    dropdown.wait_for(state='visible', timeout=20000)
    options = dropdown.locator('option').evaluate_all(
        '(options) => options.map(o => ({value: o.value, label: o.textContent}))')
    matching = [o for o in options if parse_qs(urlsplit(o['value']).query).get('mode') == ['grading']]
    if len(matching) != 1:
        raise MoodleLayoutError('Manual-grading option is missing or ambiguous.')
    value = matching[0]['value']
    destination = checked_report_url(value, quiz_id=quiz_id)
    # Moodle's urlselect submits via a JS change handler. Reading the actual
    # option destination avoids races with handler initialization and redirects.
    print('  Opening Χειροκίνητη βαθμολόγηση...')
    page.goto(destination, wait_until='domcontentloaded', timeout=45000)
    ensure_logged_in(page, selectors)
    current = parse_qs(urlsplit(page.url).query)
    if current.get('mode') != ['grading'] or current.get('id') != [quiz_id]:
        raise MoodleLayoutError('Moodle did not open manual grading for this lesson.')
    try:
        page.locator(selectors.question_table + ', ' + selectors.grading_empty_notice).first.wait_for(state='attached', timeout=30000)
    except Exception:
        raise MoodleLayoutError('Manual grading opened, but neither the question table nor a recognized empty-report notice loaded. Check the page for a permission message or changed layout.') from None
    ensure_logged_in(page, selectors)
    return parse_pending_questions(page.content(), selectors, quiz_id, include_all=include_all)


def open_pending_grading(page, lessons, selectors=SELECTORS):
    """Collect links first per lesson, then open each in the same authenticated context."""
    opened = set()
    seen_lessons = set()
    for lesson in lessons:
        if lesson.url in seen_lessons:
            continue
        seen_lessons.add(lesson.url)
        print(f'\nLesson: {lesson.title}')
        questions = pending_questions_for_lesson(page, lesson, selectors)
        print(f'  Pending-grading links: {len(questions)}')
        for question in questions:
            if question.url in opened:
                continue
            tab = page.context.new_page()
            tab.goto(question.url, wait_until='domcontentloaded', timeout=45000)
            ensure_logged_in(tab, selectors)
            opened.add(question.url)
            print(f'  Opened question {question.number}: {question.title}')
    print(f'\nOpened {len(opened)} pending-grading tabs. No grades were submitted.')
    return len(opened)
