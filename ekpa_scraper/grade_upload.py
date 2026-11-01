"""Preview and apply local CSV grades/notes through Moodle's normal grading form."""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html import escape
import json
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from bs4 import BeautifulSoup
from .csv_store import read_rows, sync_row, write_rows
from .grading import pending_questions_for_lesson, ensure_logged_in, normalized, ordered_report_url, validate_report_order
from .moodle import ORIGIN, SELECTORS, MoodleLayoutError
from .storage import merge_known_lessons, output_path, lesson_folder
from .submissions import parse_submissions, next_pages
from .upload_io import check_upload_writes, csv_access_message

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


def read_edits(root, diagnostics=None):
    """Map each CSV row via the saved submission index, not by name alone."""
    changes = []
    report = {'csv_files': 0, 'csv_rows': 0, 'candidate_rows': 0, 'blank_rows': 0, 'files': []}
    for csv_path in sorted(root.rglob('students.csv')):
        index_path = csv_path.with_name('students_index.jsonl')
        if not index_path.exists():
            raise ValueError(f'Missing student index beside {csv_path.name}; cannot safely identify responses.')
        index = [json.loads(line) for line in index_path.read_text(encoding='utf-8').splitlines() if line.strip()]
        try:
            rows = read_rows(csv_path)
        except PermissionError:
            raise ValueError(csv_access_message(csv_path)) from None
        if len(index) != len(rows):
            raise ValueError('CSV and student index row counts differ; no grade upload started.')
        file_report = {'csv': str(csv_path.relative_to(root)), 'rows': len(rows), 'candidate_rows': 0, 'blank_rows': 0}
        report['csv_files'] += 1
        report['csv_rows'] += len(rows)
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
                file_report['blank_rows'] += 1
                report['blank_rows'] += 1
                continue
            if grade:
                number(grade)
            # A cached moodle_grade is only a snapshot. Check every nonempty
            # requested grade against the live response before deciding no-op.
            file_report['candidate_rows'] += 1
            report['candidate_rows'] += 1
            changes.append(Edit(csv_path, j, record['submission_key'], row['student_name'], grade, notes, row['moodle_grade']))
        report['files'].append(file_report)
    if diagnostics is not None:
        diagnostics.update(report)
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



def is_graded(submission, current_grade):
    return bool(current_grade.strip()) or submission.moodle_status == 'graded'

def make_change(edit, lesson_title, url, submission, old_grade, old_notes, minimum, maximum):
    if submission.student_name != edit.student_name:
        raise ValueError('CSV student name does not match the live response; nothing was submitted.')
    if is_graded(submission, old_grade):
        return Change(edit, lesson_title, url, old_grade, old_notes, old_grade, old_notes, False, False)
    update_grade = bool(edit.grade) and (not old_grade or number(edit.grade) != number(old_grade))
    update_notes = bool(edit.notes) and plain_notes(notes_html(edit.notes)) != old_notes
    if edit.grade and not minimum <= number(edit.grade) <= maximum:
        raise ValueError(f'Grade for {edit.student_name} is outside the allowed range {minimum} to {maximum}.')
    return Change(edit, lesson_title, url, old_grade, old_notes,
                  str(number(edit.grade)) if edit.grade else old_grade,
                  edit.notes if edit.notes else old_notes, update_grade, update_notes)


def response_url(url, page_number, selectors=SELECTORS, grade_filter='all'):
    parts = urlsplit(url)
    args = parse_qs(parts.query)
    if grade_filter not in ('all', 'manuallygraded'):
        raise ValueError('Unsupported upload report filter.')
    args.update(grade=[grade_filter])
    all_url = parts._replace(query=urlencode([(k, v) for k, values in args.items() for v in values])).geturl()
    return ordered_report_url(all_url, pagesize=1, page=page_number, selectors=selectors)



def response_pages(page, question, root, selectors=SELECTORS, grade_filter='all'):
    """Follow rendered Moodle paging links; never infer page indexes from totals."""
    from .export import page_key
    queue = [response_url(question.url, 0, selectors, grade_filter=grade_filter)]
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
        effective_order = validate_report_order(html, selectors)
        submissions = parse_submissions(html, selectors)
        links = next_pages(html, page.url, selectors)
        queue.extend(url for url in links if page_key(url) not in visited)
        query = parse_qs(urlsplit(page.url).query)
        safe_query = {key: values for key, values in query.items()
                      if key in {'id', 'mode', 'grade', 'slot', 'qid', 'page', 'pagesize', 'order'}}
        log_event(root, {'status': 'page_observed', 'query': safe_query,
                         'response_keys': [s.key for s in submissions],
                         'rendered_paging_links': len(links), 'effective_order': effective_order})
        yield requested, submissions

def build_plan(page, output, account, lesson_id=None, selectors=SELECTORS):
    root = output_path(output) / account
    if not root.exists() or not any(root.rglob('students.csv')):
        raise ValueError('No student CSVs found for this account. Run download with this output folder first.')
    diagnostics = {}
    all_edits = read_edits(root, diagnostics)
    print(f"Local CSV summary: {diagnostics['csv_files']} files, {diagnostics['csv_rows']} rows, "
          f"{diagnostics['candidate_rows']} rows to check in Moodle, {diagnostics['blank_rows']} blank rows skipped.")
    for item in diagnostics['files']:
        print(f"  CSV: {root / item['csv']} | rows={item['rows']} | live checks={item['candidate_rows']} | blank={item['blank_rows']}")
    log_event(root, {'status': 'local_csv_summary', **diagnostics})
    lessons = merge_known_lessons(output, account, [])
    if lesson_id:
        lessons = [lesson for lesson in lessons if parse_qs(urlsplit(lesson.url).query).get('id') == [lesson_id]]
    print(f'Saved lessons in upload scope: {len(lessons)}')
    log_event(root, {'status': 'lesson_scope', 'saved_lessons': len(lessons), 'lesson_id': lesson_id})
    plan = []
    skipped_graded = 0
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
            # The explicit manuallygraded report establishes graded status even
            # if Moodle does not expose the existing numeric mark in the form.
            if question.graded_url:
                graded_question = replace(question, url=question.graded_url)
                for _, graded_rows in response_pages(page, graded_question, root, selectors, grade_filter='manuallygraded'):
                    for graded in graded_rows:
                        if graded.key not in targets:
                            continue
                        edit = targets.pop(graded.key)
                        remaining.discard((edit.csv_path, edit.submission_key))
                        skipped_graded += 1
                        log_event(root, {'status': 'already_graded_skipped', 'submission_key': graded.key,
                                         'csv': str(edit.csv_path.relative_to(root)), 'csv_row': edit.row_index + 2})
                        print(f'  Skipped already graded: {edit.student_name}')
                    if not targets:
                        break
            if not targets:
                continue
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
                if is_graded(state[0], state[1]):
                    skipped_graded += 1
                    remaining.discard((edit.csv_path, edit.submission_key))
                    log_event(root, {'status': 'already_graded_skipped', 'submission_key': edit.submission_key,
                                     'csv': str(edit.csv_path.relative_to(root)), 'csv_row': edit.row_index + 2})
                    print(f'  Skipped already graded: {edit.student_name}')
                    continue
                change = make_change(edit, lesson.title, url, *state)
                remaining.discard((edit.csv_path, edit.submission_key))
                if not change.update_grade and not change.update_notes:
                    log_event(root, {'status': 'already_matches_moodle', 'submission_key': edit.submission_key,
                                     'csv': str(edit.csv_path.relative_to(root)), 'csv_row': edit.row_index + 2})
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
    print(f'Already graded responses skipped: {skipped_graded}')
    log_event(root, {'status': 'graded_skip_summary', 'skipped_responses': skipped_graded})
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
    path = root / 'grade_upload_log.jsonl'
    try:
        root.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'time_utc': datetime.now(timezone.utc).isoformat(), **event}, ensure_ascii=False) + '\n')
    except PermissionError:
        raise ValueError(f'Cannot append audit log: {path}. Close programs holding this file and check folder write permissions. If a save was already verified, inspect Moodle before retrying.') from None


def apply_change(page, change, root, selectors=SELECTORS):
    edit = change.edit
    page.goto(change.url, wait_until='domcontentloaded', timeout=45000)
    ensure_logged_in(page, selectors)
    page.locator(selectors.submission).first.wait_for(state='attached', timeout=30000)
    submission, current_grade, current_notes, minimum, maximum = snapshot(page, edit.submission_key, selectors)
    if is_graded(submission, current_grade):
        log_event(root, {'status': 'already_graded_skipped_at_apply', 'submission_key': edit.submission_key,
                         'student_name': edit.student_name})
        print(f'Skipped response graded since preflight: {edit.student_name}')
        return False
    if current_grade != change.old_grade or current_notes != change.old_notes:
        raise ValueError('Moodle changed after preview. Nothing was submitted for this response; rerun preview.')
    make_change(edit, change.lesson_title, change.url, submission, current_grade, current_notes, minimum, maximum)
    try:
        rows = read_rows(edit.csv_path)
    except PermissionError:
        raise ValueError(csv_access_message(edit.csv_path)) from None
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
    except Exception:
        log_event(root, {'status': 'unverified_after_submit', **event})
        raise
    print(f'Moodle save verified: {edit.student_name}')
    log_event(root, {'status': 'moodle_verified', **event})
    try:
        rows = read_rows(edit.csv_path)
        write_rows(edit.csv_path, sync_row(rows, edit.row_index, verified))
    except Exception as exc:
        log_event(root, {'status': 'moodle_verified_csv_sync_failed', 'error_type': type(exc).__name__,
                         'csv': str(edit.csv_path), **event})
        hint = 'Close the CSV in Excel and check file/folder write permissions.' if isinstance(exc, PermissionError) else 'Check the local CSV and its folder.'
        raise ValueError(f'Moodle was updated and verified for {edit.student_name}, but local CSV synchronization failed ({type(exc).__name__}): {edit.csv_path}. {hint} The remote save must not be treated as failed.') from None
    log_event(root, {'status': 'verified', **event})
    return True


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
    log_event(root, {'status': 'preflight_completed', 'proposed_updates': len(plan)})
    print(f'\nProposed response updates: {len(plan)}')
    if not plan:
        log_event(root, {'status': 'no_changes', 'submitted_updates': 0})
        print('No changes submitted. Check the local CSV summary and selected lesson scope above. Blank rows are ignored; matching live values need no save.')
        return
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
    try:
        check_upload_writes(plan)
    except ValueError as exc:
        log_event(root, {'status': 'local_write_check_failed', 'message': str(exc)})
        raise
    log_event(root, {'status': 'local_write_checks_passed', 'csv_files': len({c.edit.csv_path for c in plan})})
    applied = skipped = 0
    for change in plan:
        if apply_change(page, change, root):
            applied += 1
            print(f'Verified saved response: {change.edit.student_name}')
        else:
            skipped += 1
    print(f'Applied and verified {applied} response updates; skipped {skipped} newly graded responses.')
