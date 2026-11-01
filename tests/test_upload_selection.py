from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ekpa_scraper.csv_store import read_rows, write_rows
from ekpa_scraper.export import register_student
from ekpa_scraper.grade_upload import read_edits, make_change, upload_grades
from ekpa_scraper.submissions import parse_submissions
from test_downloads import HTML

class UploadSelectionTests(unittest.TestCase):
    def test_counts_and_blank_notes_do_not_suppress_grades(self):
        item=replace(parse_submissions(HTML)[0],moodle_grade='18',moodle_status='graded')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for i,name in enumerate(['John Doe','Jane Doe','Third Student','Fourth Student']):
                register_student(root,replace(item,key=f'{101+i}:11',student_name=name))
            rows=read_rows(root/'students.csv')
            rows[1]['grade']=''
            rows[2]['grade']='0'
            rows[3]['grade']=''
            rows[3]['notes']='Feedback'
            write_rows(root/'students.csv',rows)
            diagnostics={}
            edits=read_edits(root,diagnostics)
            self.assertEqual([e.submission_key for e in edits],['101:11','103:11','104:11'])
            self.assertEqual((diagnostics['csv_files'],diagnostics['csv_rows'],diagnostics['candidate_rows'],diagnostics['blank_rows']),(1,4,3,1))
    def test_cached_grade_does_not_hide_live_ungraded_response(self):
        item=replace(parse_submissions(HTML)[0],moodle_grade='18',moodle_status='graded')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            register_student(root,item)
            edit,=read_edits(root)
            change=make_change(edit,'Lesson','https://lms.elearningekpa.gr/mod/quiz/report.php?id=1',item,'','',Decimal(0),Decimal(20))
            self.assertTrue(change.update_grade)
            self.assertFalse(change.update_notes)
            self.assertEqual(change.new_grade,'18')
            unchanged=make_change(edit,'Lesson',change.url,item,'18','',Decimal(0),Decimal(20))
            self.assertFalse(unchanged.update_grade)
    def test_zero_plan_logs_completion_and_no_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('ekpa_scraper.grade_upload.build_plan',return_value=[]),patch('ekpa_scraper.grade_upload.apply_change') as apply:
                upload_grades(object(),tmp,'93',apply=True)
                apply.assert_not_called()
            events=[json.loads(line) for line in (Path(tmp)/'93/grade_upload_log.jsonl').read_text().splitlines()]
            self.assertEqual([e['status'] for e in events],['preflight_started','preflight_completed','no_changes'])
