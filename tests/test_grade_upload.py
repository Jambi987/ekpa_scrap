from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ekpa_scraper.export import register_student
from ekpa_scraper.csv_store import read_rows, write_rows
from ekpa_scraper.submissions import parse_submissions
from ekpa_scraper.grade_upload import Edit, make_change, number, read_edits, plain_notes, notes_html, save_button_index, response_url, upload_grades
from test_downloads import HTML

class GradeUploadTests(unittest.TestCase):
    def setUp(self):
        self.submission=parse_submissions(HTML)[0]
        self.edit=Edit(Path('/tmp/students.csv'),0,'101:11','John Doe','18','Good work','15')
    def change(self,edit,grade='15',notes='Old note'):
        return make_change(edit,'Lesson','https://lms.elearningekpa.gr/mod/quiz/report.php?id=1',self.submission,grade,notes,Decimal(0),Decimal(20))
    def test_decimal_zero_and_ranges(self):
        self.assertEqual(number('17,5'),Decimal('17.5'))
        self.assertEqual(self.change(replace(self.edit,grade='0')).new_grade,'0')
        for grade in ['21','-1','NaN','Infinity','eighteen']:
            with self.subTest(grade=grade),self.assertRaises(ValueError):
                self.change(replace(self.edit,grade=grade))
    def test_blank_grade_and_blank_notes_do_not_erase(self):
        change=self.change(replace(self.edit,grade='',notes=''))
        self.assertFalse(change.update_grade)
        self.assertFalse(change.update_notes)
        self.assertEqual((change.new_grade,change.new_notes),('15','Old note'))
        note_only=self.change(replace(self.edit,grade='',notes='New note'))
        self.assertTrue(note_only.update_notes)
        self.assertFalse(note_only.update_grade)
    def test_identical_values_are_noop_and_conflicts_fail(self):
        change=self.change(replace(self.edit,grade='15,0',notes='Old note'))
        self.assertFalse(change.update_grade or change.update_notes)
        with self.assertRaises(ValueError):
            self.change(self.edit,grade='16')
        with self.assertRaises(ValueError):
            self.change(replace(self.edit,student_name='Wrong person'))
    def test_notes_are_plain_text_and_html_escaped(self):
        text='Good <work> & feedback\nSecond line'
        self.assertEqual(plain_notes(notes_html(text)),text)
        self.assertIn('&lt;work&gt;',notes_html(text))
    def test_save_button_requires_unique_save_action(self):
        self.assertEqual(save_button_index([{'label':'Cancel'},{'label':'Αποθήκευση και μετάβαση στην επόμενη σελίδα'}]),1)
        for buttons in [[{'label':'Cancel'}],[{'label':'Save'},{'label':'Save and next'}],[{'label':'Save','disabled':True}]]:
            with self.assertRaises(ValueError):
                save_button_index(buttons)
    def test_csv_mapping_and_local_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            register_student(root,self.submission)
            rows=read_rows(root/'students.csv')
            rows[0]['grade']='17,5'
            rows[0]['notes']='My feedback'
            write_rows(root/'students.csv',rows)
            edit,=read_edits(root)
            self.assertEqual((edit.submission_key,edit.grade,edit.notes),('101:11','17,5','My feedback'))
    def test_single_response_url_retains_target_and_all_filter(self):
        url=response_url('https://lms.elearningekpa.gr/mod/quiz/report.php?id=1&mode=grading&slot=11&qid=20&grade=needsgrading',3)
        self.assertIn('grade=all',url)
        self.assertIn('pagesize=1',url)
        self.assertIn('page=3',url)
        self.assertIn('slot=11',url)
    def test_preview_never_calls_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('ekpa_scraper.grade_upload.build_plan',return_value=[self.change(self.edit)]), patch('ekpa_scraper.grade_upload.apply_change') as apply:
                upload_grades(object(),tmp,'93',apply=False)
                apply.assert_not_called()
                self.assertIn('preview',(Path(tmp)/'93/grade_upload_log.jsonl').read_text())
