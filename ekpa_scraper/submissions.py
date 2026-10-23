"""Parse student responses and their upload URLs, independent of browser/storage."""
from dataclasses import dataclass
import re
from urllib.parse import urljoin, urlsplit, parse_qs, unquote
from bs4 import BeautifulSoup
from .moodle import ORIGIN, SELECTORS, MoodleLayoutError

@dataclass(frozen=True)
class Upload:
    url: str
    filename: str

@dataclass(frozen=True)
class Submission:
    key: str
    student_name: str
    attempt_number: str
    exercise: str
    uploads: tuple[Upload, ...]
    moodle_grade: str = ""
    moodle_status: str = "unknown"

ATTEMPT = re.compile(r'^Attempt number\s+(\d+)\s+for\s+(.+)$', re.I)


def parse_submissions(html, selectors=SELECTORS):
    soup = BeautifulSoup(html, 'html.parser')
    result = []
    for question in soup.select(selectors.submission):
        header = next((h for h in question.find_all_previous('h4')
                       if ATTEMPT.match(h.get_text(' ', strip=True))), None)
        if header is None:
            raise MoodleLayoutError('Student attempt heading is missing. Include the h4 before each question in the page HTML.')
        match = ATTEMPT.match(header.get_text(' ', strip=True))
        name = re.sub(r'\s*\([^)]*\)\s*$', '', match[2]).strip()
        if not name:
            raise MoodleLayoutError('Student name is empty.')
        identity = re.fullmatch(r'question-([0-9]+)-([0-9]+)', question.get('id', ''))
        prompt = question.select_one(selectors.exercise_text)
        if not identity or prompt is None:
            raise MoodleLayoutError('Question identity or exercise description is missing.')
        # Extract block boundaries while keeping inline spans within a sentence.
        fragment = BeautifulSoup(str(prompt), 'html.parser')
        for br in fragment.select('br'):
            br.replace_with('\n')
        for block in fragment.select('p, li, pre'):
            block.append('\n')
        lines = [' '.join(line.split()) for line in fragment.get_text().splitlines()]
        description = '\n'.join(line for line in lines if line)
        uploads = []
        seen = set()
        for anchor in question.select(selectors.attachment_links):
            url = urljoin(ORIGIN, anchor['href'])
            parts = urlsplit(url)
            # Ignore third-party document viewer/extension links in the example.
            if parts.scheme != 'https' or parts.netloc != urlsplit(ORIGIN).netloc:
                continue
            if '/pluginfile.php/' not in parts.path or '/response_attachments/' not in parts.path:
                continue
            if url not in seen:
                seen.add(url)
                uploads.append(Upload(url, unquote(parts.path.rsplit('/', 1)[-1])))
        mark = question.select_one(selectors.response_mark)
        grade = (mark.get('value', '') if mark else '').strip().replace(',', '.')
        if grade and not re.fullmatch(r'-?[0-9]+(?:\.[0-9]+)?', grade):
            raise MoodleLayoutError('Unrecognized existing Moodle grade format; CSV was not updated for this response.')
        # Never infer a student's score from maximum marks such as 'out of 20'.
        classes = set(question.get('class', []))
        status = 'graded' if grade != '' else ('needs_grading' if classes & {'needsgrading', 'requiresgrading'} else 'unknown')
        result.append(Submission(':'.join(identity.groups()), name, match[1], description, tuple(uploads), grade, status))
    if not result:
        raise MoodleLayoutError('No essay responses found. The grading page may be empty, anonymized, or changed.')
    return result


def next_pages(html, current_url, selectors=SELECTORS):
    soup = BeautifulSoup(html, 'html.parser')
    base = parse_qs(urlsplit(current_url).query)
    result = []
    for anchor in soup.select(selectors.paging_links):
        url = urljoin(current_url, anchor['href'])
        parts = urlsplit(url)
        args = parse_qs(parts.query)
        if (parts.scheme == 'https' and parts.netloc == urlsplit(ORIGIN).netloc
                and parts.path == '/mod/quiz/report.php'
                and args.get('mode') == ['grading'] and args.get('grade') == base.get('grade') and args.get('grade') in (['needsgrading'], ['all'], ['manuallygraded'])
                and all(args.get(k) == base.get(k) for k in ('id', 'slot', 'qid'))
                and url not in result):
            result.append(url)
    return result
