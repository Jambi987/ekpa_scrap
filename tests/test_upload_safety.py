from contextlib import nullcontext
from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from ekpa_scraper.csv_store import read_rows, write_rows
from ekpa_scraper.dashboard import Lesson
from ekpa_scraper.export import register_student
from ekpa_scraper.grade_upload import Edit, apply_change, build_plan, is_graded, log_event, make_change, response_url, upload_grades
from ekpa_scraper.grading import PendingQuestion
from ekpa_scraper.storage import lesson_folder, remember_lessons
from ekpa_scraper.submissions import parse_submissions
from ekpa_scraper.upload_io import check_csv_writable
from test_downloads import HTML

class UploadSafetyTests(unittest.TestCase):
    def setUp(self):
        self.live=replace(parse_submissions(HTML)[0],moodle_grade='',moodle_status='needs_grading')
    def make_change(self,root):
        edit=Edit(root/'students.csv',0,'101:11','John Doe','20','','')
        return make_change(edit,'Lesson','https://lms.elearningekpa.gr/mod/quiz/report.php?id=1&mode=grading&grade=all',self.live,'','',Decimal(0),Decimal(20))
    def test_zero_and_existing_grades_preserve_grade_and_notes(self):
        edit=Edit(Path('/tmp/students.csv'),0,'101:11','John Doe','20','Replace feedback','0')
        for value in ('0','15'):
            with self.subTest(value=value):
                change=make_change(edit,'Lesson','https://lms.elearningekpa.gr/mod/quiz/report.php?id=1',self.live,value,'Existing feedback',Decimal(0),Decimal(20))
                self.assertFalse(change.update_grade or change.update_notes)
                self.assertEqual(change.new_notes,'Existing feedback')
    def test_confirmed_graded_route_skips_even_when_mark_is_blank(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson=Lesson('Course','Lesson','https://lms.elearningekpa.gr/mod/quiz/view.php?id=1',1,1,'https://lms.elearningekpa.gr/course/view.php?id=2')
            root=lesson_folder(tmp,'93',lesson)
            register_student(root,self.live)
            rows=read_rows(root/'students.csv');rows[0]['grade']='20';write_rows(root/'students.csv',rows)
            remember_lessons(tmp,'93',[lesson])
            url='https://lms.elearningekpa.gr/mod/quiz/report.php?id=1&mode=grading&slot=11&qid=2&grade=all'
            question=PendingQuestion('11','Question',url,1,url.replace('grade=all','grade=manuallygraded'))
            with patch('ekpa_scraper.grade_upload.pending_questions_for_lesson',return_value=[question]),patch('ekpa_scraper.grade_upload.response_pages',return_value=iter([(url,[self.live])])) as pages,patch('ekpa_scraper.grade_upload.snapshot') as snapshot:
                self.assertEqual(build_plan(object(),tmp,'93'),[])
                snapshot.assert_not_called()
                self.assertEqual(pages.call_args.kwargs['grade_filter'],'manuallygraded')
    def test_newly_graded_response_is_not_submitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);change=self.make_change(root);page=MagicMock()
            graded=replace(self.live,moodle_grade='20',moodle_status='graded')
            with patch('ekpa_scraper.grade_upload.ensure_logged_in'),patch('ekpa_scraper.grade_upload.snapshot',return_value=(graded,'20','',Decimal(0),Decimal(20))),patch('ekpa_scraper.grade_upload.grading_controls') as controls:
                self.assertFalse(apply_change(page,change,root))
                controls.assert_not_called()
                page.expect_navigation.assert_not_called()
    def test_locked_csv_check_stops_before_any_remote_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            change=self.make_change(Path(tmp))
            with patch('ekpa_scraper.grade_upload.build_plan',return_value=[change]),patch('ekpa_scraper.grade_upload.check_upload_writes',side_effect=ValueError('Close Excel: CSV is locked')),patch('ekpa_scraper.grade_upload.apply_change') as apply:
                with self.assertRaisesRegex(ValueError,'Close Excel'):
                    upload_grades(object(),tmp,'93',apply=True)
                apply.assert_not_called()
    def test_remote_verified_csv_permission_failure_is_not_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);change=self.make_change(root);page=MagicMock();page.expect_navigation.return_value=nullcontext()
            graded=replace(self.live,moodle_grade='20',moodle_status='graded')
            snapshots=[(self.live,'','',Decimal(0),Decimal(20)),(graded,'20','',Decimal(0),Decimal(20))]
            rows=[{'student_name':'John Doe','grade':'20','notes':'','moodle_grade':'','moodle_status':'needs_grading','last_checked':''}]
            with patch('ekpa_scraper.grade_upload.ensure_logged_in'),patch('ekpa_scraper.grade_upload.snapshot',side_effect=snapshots),patch('ekpa_scraper.grade_upload.read_rows',return_value=rows),patch('ekpa_scraper.grade_upload.grading_controls',return_value=(MagicMock(),MagicMock(),0)),patch('ekpa_scraper.grade_upload.write_rows',side_effect=PermissionError('locked')):
                with self.assertRaisesRegex(ValueError,'Moodle was updated and verified'):
                    apply_change(page,change,root)
            statuses=[json.loads(line)['status'] for line in (root/'grade_upload_log.jsonl').read_text().splitlines()]
            self.assertEqual(statuses,['submitting','moodle_verified','moodle_verified_csv_sync_failed'])
    def test_write_access_probe_preserves_csv_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'students.csv';path.write_bytes(b'original')
            check_csv_writable(path)
            self.assertEqual(path.read_bytes(),b'original')
            self.assertEqual([p.name for p in Path(tmp).iterdir()],['students.csv'])
    def test_windows_sharing_lock_reports_csv_and_excel(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'students.csv';path.write_bytes(b'original')
            with patch('ekpa_scraper.upload_io.sys.platform','win32'),patch('ekpa_scraper.upload_io._windows_replace_access',side_effect=PermissionError('sharing lock')):
                with self.assertRaisesRegex(ValueError,'Close it in Excel|Close the CSV|Close it|Close.*Excel'):
                    check_csv_writable(path)
    def test_audit_lock_names_the_audit_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('pathlib.Path.open',side_effect=PermissionError('locked')):
                with self.assertRaisesRegex(ValueError,'Cannot append audit log'):
                    log_event(Path(tmp),{'status':'test'})
    def test_graded_filter_is_preserved_for_status_scan(self):
        url=response_url('https://lms.elearningekpa.gr/mod/quiz/report.php?id=1&mode=grading&grade=all',0,grade_filter='manuallygraded')
        self.assertIn('grade=manuallygraded',url)
