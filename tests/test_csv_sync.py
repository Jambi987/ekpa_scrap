from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from ekpa_scraper.csv_store import read_rows, write_rows
from ekpa_scraper.export import register_student
from ekpa_scraper.submissions import parse_submissions, next_pages
from ekpa_scraper.grading import parse_pending_questions
from ekpa_scraper.storage import append_scan, merge_known_lessons
from ekpa_scraper.dashboard import Lesson
from test_downloads import HTML
from test_grading import fixture

class CsvSyncTests(unittest.TestCase):
    def test_migrate_and_sync_preserves_notes(self):
        item = parse_submissions(HTML)[0]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            register_student(root,item)
            path=root/'students.csv'
            path.write_text('student_name,grade,notes\nJohn Doe,18,"Good, reviewed"\n',encoding='utf-8-sig')
            register_student(root,replace(item,moodle_grade='16',moodle_status='graded'))
            row=read_rows(path)[0]
            self.assertEqual((row['grade'],row['notes'],row['moodle_grade']),('18','Good, reviewed','16'))
            self.assertEqual(row['moodle_status'],'graded')
            self.assertTrue(row['last_checked'])
            self.assertIn('student_name;grade;notes;',path.read_text(encoding='utf-8-sig'))
            self.assertEqual(len(read_rows(path)),1)
    def test_mirrored_grade_updates_including_zero(self):
        item=replace(parse_submissions(HTML)[0],moodle_grade='12',moodle_status='graded')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            register_student(root,item)
            self.assertEqual(read_rows(root/'students.csv')[0]['grade'],'12')
            register_student(root,replace(item,moodle_grade='0'))
            row=read_rows(root/'students.csv')[0]
            self.assertEqual((row['grade'],row['moodle_grade']),('0','0'))
    def test_read_mark_and_never_infer_maximum(self):
        graded=HTML.replace('</div></div>', '<div class="comment"><input name="q101:11_-mark" value="17,5"></div></div></div>')
        row=parse_submissions(graded)[0]
        self.assertEqual((row.moodle_grade,row.moodle_status),('17.5','graded'))
        unknown=parse_submissions(HTML.replace('class="que essay"', 'class="que essay manualgraded complete"').replace('<div class="qtext">','<div class="grade">Out of 20</div><div class="qtext">'))[0]
        self.assertEqual((unknown.moodle_grade,unknown.moodle_status),('','unknown'))
    def test_total_column_and_all_paging(self):
        links=parse_pending_questions(fixture(),quiz_id='557503',include_all=True)
        self.assertIn('grade=all',links[0].url)
        base=links[0].url
        self.assertEqual(next_pages(f'<div class="paging"><a href="{base}&page=1">Next</a></div>',base),[base+'&page=1'])
    def test_saved_lessons_disappearing_from_dashboard(self):
        lesson=Lesson('Course','Lesson','https://lms.elearningekpa.gr/mod/quiz/view.php?id=7',2,2,'https://lms.elearningekpa.gr/course/view.php?id=9')
        with tempfile.TemporaryDirectory() as root:
            append_scan(root,'93',[lesson])
            saved=merge_known_lessons(root,'93',[])
            self.assertEqual(saved[0].url,lesson.url)
            self.assertEqual(saved[0].course_url,lesson.course_url)
            self.assertEqual(merge_known_lessons(root,'92',[]),[])
            self.assertEqual(len(merge_known_lessons(root,'93',[lesson])),1)
