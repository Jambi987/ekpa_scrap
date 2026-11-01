"""Download orchestration and append-only exercise/roster records."""
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit, urlencode
from .files import download_upload, filename, download_event
from .grading import pending_questions_for_lesson, ensure_logged_in, ordered_report_url, validate_report_order
from .moodle import SELECTORS
from .storage import lesson_folder, entity_folder
from .submissions import parse_submissions, next_pages


def append_exercise(root, text):
    path = root / 'exercise.txt'
    previous = path.read_text(encoding='utf-8') if path.exists() else ''
    if text and text not in previous:
        with path.open('a', encoding='utf-8', newline='\n') as stream:
            if previous:
                stream.write('\n\n--- Updated exercise: ' + datetime.now(timezone.utc).isoformat() + ' ---\n')
            stream.write(text + '\n')


def register_student(root, submission):
    """Synchronize CSV rows while preserving locally edited grade/notes fields.

    Internal roster uses the response's Moodle question-usage ID and slot,
    not a guessed user ID. Separate attempts with identical names get separate
    folders and rows; repeated scans of the same attempt reuse both.
    """
    root.mkdir(parents=True, exist_ok=True)
    roster_path = root / 'students_index.jsonl'
    roster = [json.loads(line) for line in roster_path.read_text(encoding='utf-8').splitlines()] if roster_path.exists() else []
    from .csv_store import read_rows, write_rows, sync_row
    csv_path = root / 'students.csv'
    rows = read_rows(csv_path)
    if len(rows) != len(roster):
        raise ValueError('CSV and student index row counts differ; restore matching records before syncing.')
    # Match names to recover user-sorted CSVs where names are unique.
    for index, record in enumerate(roster):
        if record['submission_key'] == submission.key:
            matches = [i for i, row in enumerate(rows) if row['student_name'] == record['student_name']]
            csv_index = matches[0] if len(matches) == 1 else index
            if rows[csv_index]['student_name'] != record['student_name']:
                raise ValueError('Cannot match a CSV row to its student index; existing CSV was preserved.')
            folder = root / record['folder']
            if folder.parent.resolve() != root.resolve():
                raise ValueError('Invalid student folder in the local index.')
            folder.mkdir(exist_ok=True)
            write_rows(csv_path, sync_row(rows, csv_index, submission))
            return folder
    name = filename(submission.student_name)
    folder = root / name
    if folder.exists():
        folder = root / (name + '__attempt_' + submission.key.replace(':', '_'))
    folder.mkdir(exist_ok=True)
    write_rows(csv_path, sync_row(rows, None, submission))
    with roster_path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({'submission_key': submission.key, 'student_name': submission.student_name,
                                 'attempt_number': submission.attempt_number, 'folder': folder.name}, ensure_ascii=False) + '\n')
    return folder


def page_key(url):
    parts = urlsplit(url)
    args = parse_qs(parts.query)
    args.setdefault('page', ['0'])
    return parts.path + '?' + urlencode(sorted((k, v) for k, values in args.items() for v in values))


def _export_batch(page, lessons, output, account, selectors=SELECTORS):
    students = files = 0
    failed_files = 0
    seen_lessons = set()
    for lesson in lessons:
        if lesson.url in seen_lessons:
            continue
        seen_lessons.add(lesson.url)
        print(f'\nDownloading lesson: {lesson.title}')
        questions = pending_questions_for_lesson(page, lesson, selectors, include_all=True)
        root = lesson_folder(output, account, lesson)
        for question in questions:
            params = parse_qs(urlsplit(question.url).query)
            # A single test lives directly in the lesson folder. Multiple tests
            # each get their own exercise/CSV/student folders.
            slot = params.get('slot', [question.number])[0]
            test_key = slot + '_' + params.get('qid', ['unknown'])[0]
            root_index = root / 'students_index.jsonl'
            existing_slots = {json.loads(line)['submission_key'].split(':')[-1]
                              for line in root_index.read_text(encoding='utf-8').splitlines()} if root_index.exists() else set()
            existing_test = list(root.glob('test_' + test_key + '__*'))
            use_root = slot in existing_slots or (len(questions) == 1 and not existing_test and not existing_slots)
            test_root = root if use_root else entity_folder(root, 'test', test_key, question.title)
            tab = page.context.new_page()
            queue = [ordered_report_url(url, selectors=selectors)
                     for url in (question.graded_url, question.ungraded_url, question.url) if url]
            visited = set()
            seen_submissions = set()
            try:
                while queue:
                    url = queue.pop(0)
                    key = page_key(url)
                    if key in visited:
                        continue
                    if len(visited) >= 100:
                        raise ValueError('More than 100 grading pages encountered; export stopped rather than silently truncating.')
                    visited.add(key)
                    tab.goto(url, wait_until='domcontentloaded', timeout=45000)
                    ensure_logged_in(tab, selectors)
                    tab.locator(selectors.submission).first.wait_for(state='attached', timeout=30000)
                    html = tab.content()
                    validate_report_order(html, selectors)
                    state_filter = parse_qs(urlsplit(tab.url).query).get('grade', [''])[0]
                    for submission in parse_submissions(html, selectors):
                        if state_filter in ('manuallygraded', 'needsgrading'):
                            submission = replace(submission, moodle_status='graded' if state_filter == 'manuallygraded' else 'needs_grading')
                        if submission.key in seen_submissions:
                            continue
                        seen_submissions.add(submission.key)
                        test_root.mkdir(parents=True, exist_ok=True)
                        append_exercise(test_root, submission.exercise)
                        folder = register_student(test_root, submission)
                        students += 1
                        if not submission.uploads:
                            print(f'  {submission.student_name}: no uploaded attachment found.')
                        for upload in submission.uploads:
                            try:
                                saved = download_upload(page.context, upload, folder)
                            except Exception as exc:
                                failed_files += 1
                                download_event(folder, 'failed', file=filename(upload.filename),
                                               error_type=type(exc).__name__)
                                print(f'  {submission.student_name}: attachment failed ({type(exc).__name__}); continuing.')
                                continue
                            files += 1
                            print(f'  {submission.student_name}: saved or already present: {saved.name}')
                    queue.extend(next_pages(html, tab.url, selectors))
                if question.expected_responses is not None and len(seen_submissions) < question.expected_responses:
                    raise ValueError(f'Found {len(seen_submissions)} responses but Moodle listed {question.expected_responses}. Saved files are preserved. Supply the paging controls HTML to check for missing pages.')
            except Exception:
                # Keep the failing page available until the CLI inspection pause.
                raise
            else:
                tab.close()
    if failed_files:
        raise ValueError(f'{failed_files} attachments failed; rerun download to retry. See student download_history.jsonl files.')
    print(f'\nProcessed {students} student responses and {files} attachments (including unchanged files).')
    print('Exercise text and student CSV saved. No Moodle grades were submitted.')


def export_pending(page, lessons, output, account, selectors=SELECTORS):
    failures = []
    seen = set()
    for lesson in lessons:
        if lesson.url in seen:
            continue
        seen.add(lesson.url)
        try:
            _export_batch(page, [lesson], output, account, selectors)
        except Exception as exc:
            message = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            print(f'Lesson could not be fully exported: {lesson.title}: {message}')
            failures.append(lesson.title)
    if failures:
        raise ValueError(f'{len(failures)} of {len(seen)} lessons could not be fully exported; other lessons were still processed. See the per-lesson messages above.')
    print(f'Finished scanning {len(seen)} quiz/test activities.')
