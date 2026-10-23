"""Append-only lesson history; filesystem concerns stay outside Moodle parsing."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import unicodedata
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4



def output_path(value):
    path = Path(value).expanduser().absolute()
    # Extended-length paths avoid Windows MAX_PATH with nested student projects.
    if os.name == 'nt' and not str(path).startswith('\\\\?\\'):
        value = str(path)
        value = ('\\\\?\\UNC\\' + value[2:]) if value.startswith('\\\\') else ('\\\\?\\' + value)
        return Path(value)
    return path


def safe_title(title):
    title = unicodedata.normalize('NFC', title)
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', title)
    title = re.sub(r'\s+', ' ', title).strip(' .')
    # Short enough for ordinary Windows paths; Greek text remains readable.
    return title[:48].rstrip(' .') or 'untitled'


def entity_key(url, title):
    parts = urlsplit(url)
    ids = parse_qs(parts.query).get('id', [])
    if len(ids) == 1 and re.fullmatch(r'[0-9]+', ids[0]):
        # Include activity type so quiz/assign IDs cannot collide.
        segments = parts.path.strip('/').split('/')
        kind = segments[1] if len(segments) > 2 and segments[0] == 'mod' else ''
        prefix = re.sub('[^a-zA-Z0-9_]', '_', kind) + '_' if kind else ''
        return prefix + ids[0]
    return 'name_' + sha256((url or title).encode('utf-8')).hexdigest()[:16]


def entity_folder(parent, kind, key, title):
    parent.mkdir(parents=True, exist_ok=True)
    prefix = f'{kind}_{key}__'
    matches = [p for p in parent.iterdir() if p.is_dir() and p.name.startswith(prefix)]
    if len(matches) > 1:
        raise ValueError(f'Multiple folders match the same {kind} ID; resolve duplicate folders before scanning.')
    # IDs, rather than display titles, determine identity. Title changes reuse
    # the existing folder; new titles are retained in appended records.
    folder = matches[0] if matches else parent / (prefix + safe_title(title))
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def append_scan(output_root, account, lessons):
    """Append one observation per unique lesson per scan. Never truncate files.

    Repeated scans append observations even if a count is unchanged. Duplicate
    DOM rows in one scan are collapsed; inconsistent duplicate counts fail
    before writing. Counts are snapshots, not amounts to sum across scans.
    Intended for sequential scans (one writer per account at a time).
    """
    if not re.fullmatch(r'[0-9]+', account):
        raise ValueError('Account must contain only digits.')
    unique = {}
    for lesson in lessons:
        course_key = entity_key(lesson.course_url, lesson.course_title)
        lesson_key = entity_key(lesson.url, lesson.title)
        key = (course_key, lesson_key)
        previous = unique.get(key)
        if previous and (previous.displayed_count, previous.listed_entries) != (lesson.displayed_count, lesson.listed_entries):
            raise ValueError('Duplicate lesson rows disagree on counts. No records were appended.')
        unique[key] = lesson
    account_dir = output_path(output_root) / account
    account_dir.mkdir(parents=True, exist_ok=True)
    scan_id = str(uuid4())
    observed_at = datetime.now(timezone.utc).isoformat()
    paths = []
    for (course_key, lesson_key), lesson in unique.items():
        course_dir = entity_folder(account_dir, 'course', course_key, lesson.course_title)
        lesson_dir = entity_folder(course_dir, 'lesson', lesson_key, lesson.title)
        path = lesson_dir / 'history.jsonl'
        record = {
            'schema_version': 1,
            'scan_id': scan_id,
            'observed_at_utc': observed_at,
            'account': account,
            'course_title': lesson.course_title,
            'course_url': lesson.course_url,
            'lesson_title': lesson.title,
            'course_url': lesson.course_url,
            'lesson_url': lesson.url,
            'exams_awaiting_correction': lesson.displayed_count,
            'listed_exam_entries': lesson.listed_entries,
        }
        with path.open('a', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + '\n')
        paths.append(path)
    return paths


def lesson_folder(output_root, account, lesson):
    if not re.fullmatch(r'[0-9]+', account):
        raise ValueError('Account must contain only digits.')
    course = entity_folder(output_path(output_root) / account, 'course',
                           entity_key(lesson.course_url, lesson.course_title), lesson.course_title)
    return entity_folder(course, 'lesson', entity_key(lesson.url, lesson.title), lesson.title)


def remember_lessons(output_root, account, lessons):
    root = output_path(output_root) / account
    root.mkdir(parents=True, exist_ok=True)
    with (root / 'discovered_lessons.jsonl').open('a', encoding='utf-8') as stream:
        for lesson in lessons:
            stream.write(json.dumps({'course_title': lesson.course_title, 'course_url': lesson.course_url,
                'lesson_title': lesson.title, 'lesson_url': lesson.url,
                'discovered_at_utc': datetime.now(timezone.utc).isoformat()}, ensure_ascii=False) + '\n')


def merge_known_lessons(output_root, account, live_lessons):
    """Revisit saved lessons even after they disappear from the current listing."""
    from .dashboard import Lesson
    lessons = {lesson.url: lesson for lesson in live_lessons}
    root = output_path(output_root) / account
    if root.exists():
        paths = list(root.rglob('history.jsonl'))
        if (root / 'discovered_lessons.jsonl').exists():
            paths.append(root / 'discovered_lessons.jsonl')
        for path in paths:
            records = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
            for record in (records if path.name == 'discovered_lessons.jsonl' else records[-1:]):
                url = record['lesson_url']
                if url in lessons:
                    continue
                course_url = record.get('course_url', '')
                if not course_url:
                    match = re.match(r'course_(?:course_view_)?([0-9]+)__', path.parent.parent.name)
                    if match:
                        course_url = 'https://lms.elearningekpa.gr/course/view.php?id=' + match[1]
                lessons[url] = Lesson(record['course_title'], record['lesson_title'], url, 0, 0, course_url)
    return list(lessons.values())
