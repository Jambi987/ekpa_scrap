"""Preview and apply local CSV grades/notes through Moodle's normal grading form."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html import escape
import json
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from bs4 import BeautifulSoup
from .csv_store import read_rows, sync_row, write_rows
from .grading import pending_questions_for_lesson, ensure_logged_in, normalized
from .moodle import ORIGIN, SELECTORS, MoodleLayoutError
from .storage import merge_known_lessons, output_path, lesson_folder
from .submissions import parse_submissions, next_pages

@dataclass(frozen=True)
class Edit:
    csv_path: Path
    row_index: int
    submission_key: str
    student_name: str
    grade: str
    notes: str
    last_moodle_grade: str

@dataclass(frozen=True)
class Change:
    edit: Edit
    lesson_title: str
    url: str
    old_grade: str
    old_notes: str
    new_grade: str
    new_notes: str
    update_grade: bool
    update_notes: bool


def number(value):
    try:
        result = Decimal(value.strip().replace(',', '.'))
    except (InvalidOperation, AttributeError):
        raise ValueError('Grade must be a number such as 18 or 17,5.') from None
    if not result.is_finite():
        raise ValueError('Grade must be finite.')
    return result


def plain_notes(html):
    soup = BeautifulSoup(html or '', 'html.parser')
    for br in soup.select('br'):
        br.replace_with('\n')
    for p in soup.select('p, div, li'):
        p.append('\n')
    return '\n'.join(line.rstrip() for line in soup.get_text().replace('\r\n', '\n').splitlines()).strip()


def notes_html(notes):
    return '<p>' + escape(notes).replace('\r\n', '\n').replace('\n', '<br>') + '</p>'


def read_edits(root):
    """Map each CSV row via the saved submission index, not by name alone."""
    changes = []
    for csv_path in sorted(root.rglob('students.csv')):
        index_path = csv_path.with_name('students_index.jsonl')
        if not index_path.exists():
            raise ValueError(f'Missing student index beside {csv_path.name}; cannot safely identify responses.')
        index = [json.loads(line) for line in index_path.read_text(encoding='utf-8').splitlines() if line.strip()]
        rows = read_rows(csv_path)
        if len(index) != len(rows):
            raise ValueError('CSV and student index row counts differ; no grade upload started.')
        used = set()
        for i, record in enumerate(index):
            matches = [j for j, row in enumerate(rows) if row['student_name'] == record['student_name']]
            j = matches[0] if len(matches) == 1 else i
            if j in used or rows[j]['student_name'] != record['student_name']:
                raise ValueError('CSV student order cannot be matched safely to the saved index.')
            used.add(j)
            row = rows[j]
            grade = row['grade'].strip()
            notes = row['notes'].strip()
            if not grade and not notes:
                continue
            if grade:
                number(grade)
            # A populated grade copied during download is not itself an edit.
            # Do not resubmit it or force a search for an unchanged response.
            if (not notes and grade and row['moodle_grade'].strip()
                    and number(grade) == number(row['moodle_grade'])):
                continue
            changes.append(Edit(csv_path, j, record['submission_key'], row['student_name'], grade, notes, row['moodle_grade']))
    return changes


def snapshot(page, submission_key, selectors=SELECTORS):
    questions = page.locator(selectors.submission)
    if questions.count() != 1:
        raise MoodleLayoutError('Expected exactly one response on this upload page; nothing was submitted.')
    submission, = parse_submissions(page.content(), selectors)
    if submission.key != submission_key:
        raise ValueError('The response order changed or the submission identity did not match; nothing was submitted.')
    question = questions.first
    mark = question.locator(selectors.response_mark)
    maximum = question.locator('input[name$="-maxmark"]')
    comment = question.locator('.comment textarea[name$="-comment"]')
    if mark.count() != 1 or maximum.count() != 1 or comment.count() != 1:
        raise MoodleLayoutError('Grade/comment fields are missing or ambiguous. Supply the response form HTML.')
    current_grade = mark.input_value().strip()
    maxmark = number(maximum.input_value())
    minfraction = question.locator('input[name$=":minfraction"]')
    maxfraction = question.locator('input[name$=":maxfraction"]')
    minimum = number(minfraction.input_value()) * maxmark if minfraction.count() == 1 else Decimal(0)
    ceiling = number(maxfraction.input_value()) * maxmark if maxfraction.count() == 1 else maxmark
    return submission, current_grade, plain_notes(comment.input_value()), minimum, ceiling


def make_change(edit, lesson_title, url, submission, old_grade, old_notes, minimum, maximum):
    if submission.student_name != edit.student_name:
        raise ValueError('CSV student name does not match the live response; nothing was submitted.')
    update_grade = bool(edit.grade) and (not old_grade or number(edit.grade) != number(old_grade))
    update_notes = bool(edit.notes) and plain_notes(notes_html(edit.notes)) != old_notes
    if edit.grade and not minimum <= number(edit.grade) <= maximum:
        raise ValueError(f'Grade for {edit.student_name} is outside the allowed range {minimum} to {maximum}.')
    if (update_grade and edit.last_moodle_grade and old_grade
            and number(edit.last_moodle_grade) != number(old_grade)):
        raise ValueError(f'Moodle grade changed since the last CSV sync for {edit.student_name}. Download current data and review the CSV first.')
    return Change(edit, lesson_title, url, old_grade, old_notes,
                  str(number(edit.grade)) if edit.grade else old_grade,
                  edit.notes if edit.notes else old_notes, update_grade, update_notes)


def response_url(url, page_number):
    parts = urlsplit(url)
    args = parse_qs(parts.query)
    args.update(grade=['all'], pagesize=['1'], page=[str(page_number)], order=['lastname'])
    return parts._replace(query=urlencode([(k, v) for k, values in args.items() for v in values])).geturl()



def response_pages(page, question, root, selectors=SELECTORS):
    """Follow rendered Moodle paging links; never infer page indexes from totals."""
    from .export import page_key
    queue = [response_url(question.url, 0)]
    visited = set()
    while queue:
        requested = queue.pop(0)
        key = page_key(requested)
        if key in visited:
            continue
        if len(visited) >= 10000:
            raise ValueError('Response paging exceeded its bound; no upload was started.')
        visited.add(key)
        page.goto(requested, wait_until='domcontentloaded', timeout=45000)
        ensure_logged_in(page, selectors)
        page.locator(selectors.submission).first.wait_for(state='attached', timeout=30000)
        html = page.content()
        submissions = parse_submissions(html, selectors)
        links = next_pages(html, page.url, selectors)
        queue.extend(url for url in links if page_key(url) not in visited)
        query = parse_qs(urlsplit(page.url).query)
        safe_query = {key: values for key, values in query.items()
                      if key in {'id', 'mode', 'grade', 'slot', 'qid', 'page', 'pagesize', 'order'}}
        log_event(root, {'status': 'page_observed', 'query': safe_query,
                         'response_keys': [s.key for s in submissions],
                         'rendered_paging_links': len(links)})
        yield requested, submissions

def build_plan(page, output, account, lesson_id=None, selectors=SELECTORS):
    root = output_path(output) / account
    if not root.exists() or not any(root.rglob('students.csv')):
        raise ValueError('No student CSVs found for this account. Run download with this output folder first.')
    all_edits = read_edits(root)
    lessons = merge_known_lessons(output, account, [])
    if lesson_id:
        lessons = [lesson for lesson in lessons if parse_qs(urlsplit(lesson.url).query).get('id') == [lesson_id]]
    plan = []
    remaining = set()
    for lesson in lessons:
        folder = lesson_folder(output, account, lesson)
        edits = [edit for edit in all_edits if edit.csv_path.is_relative_to(folder)]
        if not edits:
            continue
        by_key = {}
        for edit in edits:
            if edit.submission_key in by_key:
                raise ValueError('The same response appears in multiple CSVs; resolve duplicates before uploading.')
            by_key[edit.submission_key] = edit
            remaining.add((edit.csv_path, edit.submission_key))
        print(f'Checking CSV against Moodle: {lesson.title}')
        questions = pending_questions_for_lesson(page, lesson, selectors, include_all=True)
        for question in questions:
            slot = parse_qs(urlsplit(question.url).query).get('slot', [''])[0]
            targets = {key: edit for key, edit in by_key.items() if key.split(':')[-1] == slot}
            if not targets:
                continue
            if question.expected_responses is None or question.expected_responses > 10000:
                raise ValueError('Cannot determine a bounded complete response list for grade upload.')
            seen = set()
            for url, submissions in response_pages(page, question, root, selectors):
                if len(submissions) != 1:
                    raise MoodleLayoutError('Moodle returned multiple responses on a single-response upload page; no upload was started. Supply the paging/settings form HTML.')
                submission = submissions[0]
                if submission.key in seen:
                    # Some report links render the same response (for example,
                    # a previous/current-page link). Do not invent later pages.
                    continue
                seen.add(submission.key)
                if submission.key not in targets:
                    continue
                edit = targets.pop(submission.key)
                state = snapshot(page, edit.submission_key, selectors)
                change = make_change(edit, lesson.title, url, *state)
                remaining.discard((edit.csv_path, edit.submission_key))
                if change.update_grade or change.update_notes:
                    grading_controls(page.locator(selectors.submission).first, url)
                    plan.append(change)
                if not targets:
                    break
            if targets:
                log_event(root, {'status': 'responses_not_found',
                                 'requested_keys': sorted(targets), 'observed_keys': sorted(seen),
                                 'reported_total': question.expected_responses})
    # Detect CSV folders that no saved lesson can identify as well.
    if not lesson_id:
        matched = {edit.csv_path for lesson in lessons for edit in all_edits
                   if edit.csv_path.is_relative_to(lesson_folder(output, account, lesson))}
        if any(edit.csv_path not in matched for edit in all_edits):
            raise ValueError('Some CSVs have no saved lesson URL. Run download before uploading.')
    if remaining:
        raise ValueError(f'{len(remaining)} CSV responses were not found in Moodle. No grades were submitted.')
    return plan


def save_button_index(buttons):
    candidates = []
    for index, button in enumerate(buttons):
        label = normalized(button.get('label', ''))
        if (label.startswith('save') or label.startswith('αποθηκευση')) and not button.get('disabled'):
            candidates.append(index)
    if len(candidates) != 1:
        raise MoodleLayoutError('Cannot identify one Save button. Supply the grading form footer HTML; nothing was submitted.')
    return candidates[0]



def grading_controls(question, url):
    form = question.locator('xpath=ancestor::form[1]')
    if form.count() != 1 or form.locator('input[name$="-mark"]').count() != 1:
        raise MoodleLayoutError('Expected a grading form for exactly one response.')
    info = form.evaluate('(f) => ({action: f.action, method: f.method})')
    parts = urlsplit(info['action'])
    expected_id = parse_qs(urlsplit(url).query).get('id')
    actual_id = parse_qs(parts.query).get('id')
    hidden_id = form.locator('input[name="id"]')
    if actual_id is None and hidden_id.count() == 1:
        actual_id = [hidden_id.input_value()]
    if (info['method'].lower() != 'post' or parts.scheme != 'https'
            or parts.netloc != urlsplit(ORIGIN).netloc or parts.path != '/mod/quiz/report.php'
            or actual_id != expected_id):
        raise MoodleLayoutError('Unexpected grading form destination; nothing was submitted.')
    buttons = form.locator('button:not([type="button"]):not([type="reset"]), input[type="submit"]')
    descriptors = buttons.evaluate_all('(bs) => bs.map(b => ({label: b.tagName === "INPUT" ? b.value : b.textContent, disabled: b.disabled}))')
    return form, buttons, save_button_index(descriptors)

def log_event(root, event):
    root.mkdir(parents=True, exist_ok=True)
    with (root / 'grade_upload_log.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({'time_utc': datetime.now(timezone.utc).isoformat(), **event}, ensure_ascii=False) + '\n')


def apply_change(page, change, root, selectors=SELECTORS):
    edit = change.edit
    page.goto(change.url, wait_until='domcontentloaded', timeout=45000)
    ensure_logged_in(page, selectors)
    page.locator(selectors.submission).first.wait_for(state='attached', timeout=30000)
    submission, current_grade, current_notes, minimum, maximum = snapshot(page, edit.submission_key, selectors)
    if current_grade != change.old_grade or current_notes != change.old_notes:
        raise ValueError('Moodle changed after preview. Nothing was submitted for this response; rerun preview.')
    make_change(edit, change.lesson_title, change.url, submission, current_grade, current_notes, minimum, maximum)
    rows = read_rows(edit.csv_path)
    if (rows[edit.row_index]['student_name'], rows[edit.row_index]['grade'].strip(), rows[edit.row_index]['notes'].strip()) != (edit.student_name, edit.grade, edit.notes):
        raise ValueError('CSV changed during upload; rerun the command.')
    question = page.locator(selectors.submission).first
    form, buttons, button_index = grading_controls(question, change.url)
    if change.update_grade:
        question.locator(selectors.response_mark).fill(change.new_grade)
    if change.update_notes:
        comment = question.locator('.comment textarea[name$="-comment"]')
        editor = question.locator('.comment .editor_atto_content[contenteditable="true"]')
        if editor.count() == 1:
            editor.evaluate('(el, html) => {el.innerHTML = html; el.dispatchEvent(new Event("input", {bubbles:true}));}', notes_html(change.new_notes))
        comment.evaluate('''(textarea, html) => {
            const editor = window.tinyMCE && window.tinyMCE.get(textarea.id);
            if (editor) { editor.setContent(html); editor.save(); }
            textarea.value = html;
            textarea.dispatchEvent(new Event('input', {bubbles:true}));
            textarea.dispatchEvent(new Event('change', {bubbles:true}));
        }''', notes_html(change.new_notes))
    event = {'submission_key': edit.submission_key, 'student_name': edit.student_name,
             'lesson': change.lesson_title, 'old_grade': change.old_grade,
             'new_grade': change.new_grade, 'old_notes': change.old_notes, 'new_notes': change.new_notes}
    log_event(root, {'status': 'submitting', **event})
    try:
        with page.expect_navigation(wait_until='domcontentloaded', timeout=45000):
            buttons.nth(button_index).click()
        page.goto(change.url, wait_until='domcontentloaded', timeout=45000)
        ensure_logged_in(page, selectors)
        page.locator(selectors.submission).first.wait_for(state='attached', timeout=30000)
        verified, grade, notes, _, _ = snapshot(page, edit.submission_key, selectors)
        if change.update_grade and (not grade or number(grade) != number(change.new_grade)):
            raise ValueError('Saved grade could not be verified. Inspect Moodle before rerunning apply.')
        if change.update_notes and notes != plain_notes(notes_html(change.new_notes)):
            raise ValueError('Saved note could not be verified. Inspect Moodle before rerunning apply.')
        rows = read_rows(edit.csv_path)
        write_rows(edit.csv_path, sync_row(rows, edit.row_index, verified))
        log_event(root, {'status': 'verified', **event})
    except Exception:
        log_event(root, {'status': 'unverified_after_submit', **event})
        raise


def upload_grades(page, output, account, apply=False, lesson_id=None):
    root = output_path(output) / account
    log_event(root, {'status': 'preflight_started', 'apply_requested': apply, 'lesson_id': lesson_id})
    print(f'Audit log: {root / "grade_upload_log.jsonl"}')
    try:
        plan = build_plan(page, output, account, lesson_id)
    except Exception as exc:
        log_event(root, {'status': 'preflight_failed', 'error_type': type(exc).__name__,
                         'message': str(exc) if isinstance(exc, ValueError) else 'See terminal error type.'})
        raise
    print(f'\nProposed response updates: {len(plan)}')
    for change in plan:
        grade = f'{change.old_grade or "blank"} -> {change.new_grade}' if change.update_grade else 'unchanged'
        print(f'{change.lesson_title} | {change.edit.student_name} | grade: {grade}')
        if change.update_notes:
            print(f'  Note to save: {change.new_notes}')
    root = output_path(output) / account
    for change in plan:
        log_event(root, {'status': 'preview', 'submission_key': change.edit.submission_key,
                         'student_name': change.edit.student_name, 'lesson': change.lesson_title,
                         'old_grade': change.old_grade, 'new_grade': change.new_grade,
                         'old_notes': change.old_notes, 'new_notes': change.new_notes})
    if not apply:
        print('Preview only. Rerun with --apply to submit these CSV changes.')
        return
    for change in plan:
        apply_change(page, change, root)
        print(f'Verified saved response: {change.edit.student_name}')
    print(f'Applied and verified {len(plan)} response updates.')
