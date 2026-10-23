import csv
from dataclasses import replace
import io
from pathlib import Path
import tempfile
import unittest
import zipfile
from ekpa_scraper.submissions import parse_submissions, next_pages
from ekpa_scraper.export import register_student, append_exercise
from ekpa_scraper.files import save_bytes, extract_zip, download_upload

HTML = '''<h4>Attempt number 1 for John Doe ()</h4>
<div class="que essay" id="question-101-11"><div class="qtext"><p>Write <span>Python</span> code.</p><p>Return a PDF.</p></div>
<div class="attachments"><a href="https://lms.elearningekpa.gr/pluginfile.php/1/question/response_attachments/101/11/2/work.pdf?forcedownload=1">work.pdf</a><a href="https://docs.google.com/viewer?url=anything">viewer</a></div></div>'''

class DownloadTests(unittest.TestCase):
    def test_association_prompt_and_attachment_filter(self):
        other = HTML.replace('John Doe', 'Jane Doe').replace('question-101-', 'question-102-')
        rows = parse_submissions(HTML + other)
        self.assertEqual([r.student_name for r in rows], ['John Doe', 'Jane Doe'])
        self.assertEqual(rows[0].exercise, 'Write Python code.\nReturn a PDF.')
        self.assertEqual(len(rows[0].uploads), 1)
        self.assertEqual(rows[0].key, '101:11')
    def test_missing_header_fails(self):
        with self.assertRaises(ValueError):
            parse_submissions(HTML[HTML.index('<div'):])
    def test_roster_preserves_grade_notes_and_distinguishes_same_names(self):
        item, = parse_submissions(HTML)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = register_student(root, item)
            path = root / 'students.csv'
            with path.open('w', encoding='utf-8-sig', newline='') as f:
                csv.writer(f).writerows([['student_name','grade','notes'], ['John Doe','18','Reviewed, good']])
            before = path.read_bytes()
            self.assertEqual(folder, register_student(root, item))
            from ekpa_scraper.csv_store import read_rows
            self.assertEqual(read_rows(path)[0]['grade'], '18')
            self.assertEqual(read_rows(path)[0]['notes'], 'Reviewed, good')
            another = register_student(root, replace(item, key='102:11'))
            self.assertNotEqual(folder, another)
            self.assertEqual(read_rows(path)[0]['grade'], '18')
            with path.open(encoding='utf-8-sig') as stream:
                self.assertEqual(len(list(csv.DictReader(stream, delimiter=';'))), 2)
    def test_description_appends_only_when_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            append_exercise(root, 'Original exercise')
            before=(root/'exercise.txt').read_bytes()
            append_exercise(root, 'Original exercise')
            self.assertEqual((root/'exercise.txt').read_bytes(),before)
            append_exercise(root, 'New exercise')
            self.assertTrue((root/'exercise.txt').read_bytes().startswith(before))
    def test_binary_versioning(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'work.pdf'
            self.assertEqual(save_bytes(path,b'old'),save_bytes(path,b'old'))
            newer=save_bytes(path,b'new')
            self.assertNotEqual(path,newer)
            self.assertEqual(path.read_bytes(),b'old')
            self.assertEqual(newer.read_bytes(),b'new')
    def test_zip_extract_and_reject_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            good=root/'good.zip'
            with zipfile.ZipFile(good,'w') as z:
                z.writestr('project/main.py','print(1)')
            extract_zip(good,root)
            extract_zip(good,root)
            self.assertEqual((root/'project/main.py').read_text(),'print(1)')
            bad=root/'bad.zip'
            with zipfile.ZipFile(bad,'w') as z:
                z.writestr('../outside.txt','no')
            with self.assertRaises(ValueError):
                extract_zip(bad,root)
            self.assertFalse((root.parent/'outside.txt').exists())
    def test_paging_stays_with_same_pending_question(self):
        base='https://lms.elearningekpa.gr/mod/quiz/report.php?id=1&mode=grading&slot=11&qid=22&grade=needsgrading'
        html=f'<div class="paging"><a href="{base}&page=1">Next</a><a href="{base.replace("needsgrading","all")}&page=2">All</a></div>'
        self.assertEqual(next_pages(html,base),[base+'&page=1'])
    def test_authenticated_request_file_and_expired_session(self):
        upload=parse_submissions(HTML)[0].uploads[0]
        class Response:
            status=200
            ok=True
            headers={'content-type':'application/pdf'}
            payload=b'%PDF-test'
            def body(self): return self.payload
            def dispose(self): pass
        response=Response()
        class Request:
            def get(self,*args,**kwargs): return response
        class Context:
            request=Request()
        with tempfile.TemporaryDirectory() as tmp:
            path=download_upload(Context(),upload,tmp)
            self.assertEqual(path.read_bytes(),b'%PDF-test')
            response.headers={'content-type':'text/html'}
            response.payload=b'<form id="login"><input name="password"></form>'
            with self.assertRaises(ValueError):
                download_upload(Context(),upload,tmp)
