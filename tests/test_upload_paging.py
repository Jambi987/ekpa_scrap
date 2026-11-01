from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ekpa_scraper.grade_upload import response_pages, response_url, read_edits, upload_grades
from ekpa_scraper.grading import PendingQuestion
from ekpa_scraper.submissions import parse_submissions
from ekpa_scraper.export import register_student
from test_downloads import HTML

class FakeLocator:
    first = property(lambda self:self)
    def count(self): return 0
    def wait_for(self,**kwargs): pass

class FakePage:
    def __init__(self,pages): self.pages=pages; self.visits=[]
    def goto(self,url,**kwargs): self.url=url; self.visits.append(url)
    def locator(self,*args): return FakeLocator()
    def content(self): return self.pages[self.url]

class UploadPagingTests(unittest.TestCase):
    def test_follows_actual_links_and_tolerates_duplicate_responses(self):
        url='https://lms.elearningekpa.gr/mod/quiz/report.php?id=1&mode=grading&slot=11&qid=2&grade=all'
        start=response_url(url,0)
        # Link intentionally uses an extra Moodle report parameter and page 7;
        # the iterator must follow it rather than inventing pages 1..total.
        actual=url+'&pagesize=1&page=7&order=studentlastname&includeauto=0'
        html=HTML+f'<div class="paging"><a href="{actual}">Next</a></div>'
        page=FakePage({start:html,actual:html})
        with tempfile.TemporaryDirectory() as root:
            results=list(response_pages(page,PendingQuestion('11','Question',url,50),Path(root)))
            self.assertEqual(page.visits,[start,actual])
            self.assertEqual(len(results),2)
            self.assertEqual(results[0][1][0].key,results[1][1][0].key)
            self.assertIn('page_observed',(Path(root)/'grade_upload_log.jsonl').read_text())
    def test_downloaded_grades_are_live_check_candidates(self):
        submission=replace(parse_submissions(HTML)[0],moodle_grade='18',moodle_status='graded')
        with tempfile.TemporaryDirectory() as root:
            register_student(Path(root),submission)
            edits = read_edits(Path(root))
            self.assertEqual(len(edits), 1)
            self.assertEqual(edits[0].grade, '18')
    def test_preflight_failure_always_creates_audit_log(self):
        with tempfile.TemporaryDirectory() as root:
            with patch('ekpa_scraper.grade_upload.build_plan',side_effect=ValueError('Paging failed')), patch('ekpa_scraper.grade_upload.apply_change') as apply:
                with self.assertRaises(ValueError):
                    upload_grades(object(),root,'93',apply=True)
                apply.assert_not_called()
                text=(Path(root)/'93/grade_upload_log.jsonl').read_text()
                self.assertIn('preflight_started',text)
                self.assertIn('preflight_failed',text)
