import io
import json
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from ekpa_scraper.csv_store import read_rows, write_rows
from ekpa_scraper.dashboard import Lesson
from ekpa_scraper.export import export_pending, register_student
from ekpa_scraper.grade_upload import upload_grades
from ekpa_scraper.grading import is_empty_grading_report, parse_pending_questions, pending_questions_for_lesson
from ekpa_scraper.moodle import MoodleLayoutError, SELECTORS
from ekpa_scraper.storage import lesson_folder, remember_lessons
from ekpa_scraper.submissions import parse_submissions
from test_downloads import HTML
from test_grading import fixture

URL = 'https://lms.elearningekpa.gr/mod/quiz/report.php?id=557503&mode=grading'
LESSON = Lesson('Course', 'Quiz', 'https://lms.elearningekpa.gr/mod/quiz/view.php?id=557503', 0, 0,
                'https://lms.elearningekpa.gr/course/view.php?id=39318')


def empty_html(message='Nothing to display'):
    return f'''<main id="region-main"><h3>Questions that need grading</h3>
    <p class="toggleincludeauto"><a href="{URL}&amp;includeauto=1">Show automatic questions</a></p>
    <div class="alert alert-info" role="alert">{message}</div></main>'''


class EmptyGradingTests(unittest.TestCase):
    def test_empty_notice_recognized_without_language_dependency(self):
        for message in ('Nothing to display', 'Δεν υπάρχει τίποτα προς εμφάνιση'):
            for include_all in (False, True):
                with self.subTest(message=message, include_all=include_all):
                    self.assertEqual(parse_pending_questions(empty_html(message), quiz_id='557503',
                                                            include_all=include_all), [])

    def test_missing_table_permissions_and_ambiguous_layout_are_not_skipped(self):
        pages = [
            '<main><div class="alert alert-info">No permission</div></main>',
            empty_html().replace('class="toggleincludeauto"', 'class="changed"'),
            empty_html().replace('includeauto=1', 'includeauto=0'),
            empty_html().replace('id=557503', 'id=42'),
            empty_html().replace('https://lms.elearningekpa.gr', 'https://other.example'),
            empty_html().replace('</main>', '<div class="alert-danger">Denied</div></main>'),
            empty_html().replace('</main>', '<table id="changed-layout"></table></main>'),
            '<form id="login"></form>' + empty_html(),
            empty_html().replace('Nothing to display', ''),
            empty_html().replace('&amp;includeauto=1', '&amp;includeauto=1&amp;slot=11'),
        ]
        for html in pages:
            with self.subTest(html=html), self.assertRaises(MoodleLayoutError):
                parse_pending_questions(html, quiz_id='557503', include_all=True)

    def test_real_table_still_returns_manual_questions(self):
        html = empty_html().replace('</main>', fixture() + '</main>')
        self.assertFalse(is_empty_grading_report(html, quiz_id='557503'))
        self.assertEqual(len(parse_pending_questions(html, quiz_id='557503', include_all=True)), 1)

    def test_navigation_waits_for_table_or_notice_then_parses(self):
        page = MagicMock()
        page.goto.side_effect = lambda url, **kwargs: setattr(page, 'url', url)
        page.content.return_value = empty_html()
        login = MagicMock(); login.count.return_value = 0
        results = MagicMock(); results.get_attribute.return_value = URL.replace('grading', 'overview')
        dropdown = MagicMock()
        dropdown.locator.return_value.evaluate_all.return_value = [{'value': URL, 'label': 'Manual grading'}]
        signal = MagicMock()
        expected = SELECTORS.question_table + ', ' + SELECTORS.grading_empty_notice
        page.locator.side_effect = lambda selector: {
            SELECTORS.login_form: login, SELECTORS.results_link: results,
            SELECTORS.report_dropdown: dropdown, expected: signal}[selector]
        self.assertEqual(pending_questions_for_lesson(page, LESSON, include_all=True), [])
        signal.first.wait_for.assert_called_once_with(state='attached', timeout=30000)

    def test_export_logs_skip_and_continues_without_downloading(self):
        with tempfile.TemporaryDirectory() as tmp:
            other = replace(LESSON, title='Another quiz', url=LESSON.url.replace('557503', '557504'))
            with patch('ekpa_scraper.export.pending_questions_for_lesson', return_value=[]) as navigate, \
                 patch('ekpa_scraper.export.download_upload') as download, redirect_stdout(io.StringIO()) as output:
                export_pending(object(), [LESSON, other], tmp, '93')
            self.assertEqual(navigate.call_count, 2)
            download.assert_not_called()
            events = [json.loads(line) for line in (Path(tmp)/'93/download_scan_log.jsonl').read_text().splitlines()]
            self.assertEqual([x['lesson_id'] for x in events], ['557503', '557504'])
            self.assertTrue(all(x['status'] == 'lesson_skipped_no_manual_responses' for x in events))
            self.assertIn('Finished scanning 2', output.getvalue())

    def test_text_only_manual_response_is_still_registered(self):
        html = HTML[:HTML.index('<div class="attachments">')] + '</div>'
        submission, = parse_submissions(html)
        self.assertEqual(submission.uploads, ())
        with tempfile.TemporaryDirectory() as tmp:
            register_student(Path(tmp), submission)
            self.assertEqual(read_rows(Path(tmp)/'students.csv')[0]['student_name'], 'John Doe')

    def test_upload_does_not_silently_discard_requested_grades_on_empty_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = lesson_folder(tmp, '93', LESSON)
            submission, = parse_submissions(HTML)
            register_student(root, submission)
            rows = read_rows(root/'students.csv'); rows[0]['grade'] = '20'; write_rows(root/'students.csv', rows)
            remember_lessons(tmp, '93', [LESSON])
            with patch('ekpa_scraper.grade_upload.pending_questions_for_lesson', return_value=[]), \
                 patch('ekpa_scraper.grade_upload.apply_change') as apply, redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError, '1 CSV responses were not found'):
                    upload_grades(object(), tmp, '93', apply=True)
                apply.assert_not_called()
