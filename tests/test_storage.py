from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from ekpa_scraper.dashboard import Lesson
from ekpa_scraper.storage import append_scan

BASE = Lesson('Course / A', 'Εξέταση: Lesson?', 'https://lms.elearningekpa.gr/mod/quiz/view.php?id=12', 6, 6,
              'https://lms.elearningekpa.gr/course/view.php?id=34')

class StorageTests(unittest.TestCase):
    def test_repeat_scan_appends_and_preserves_previous_bytes(self):
        with tempfile.TemporaryDirectory() as root:
            path, = append_scan(root, '93', [BASE])
            before = path.read_bytes()
            repeated, = append_scan(root, '93', [replace(BASE, displayed_count=5, listed_entries=5)])
            self.assertEqual(path, repeated)
            self.assertTrue(path.read_bytes().startswith(before))
            rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
            self.assertEqual([r['exams_awaiting_correction'] for r in rows], [6, 5])
            self.assertNotEqual(rows[0]['scan_id'], rows[1]['scan_id'])
            self.assertEqual(path.parent.parent.parent.name, '93')
    def test_duplicate_rows_once_per_scan_and_rename_reuses_folder(self):
        with tempfile.TemporaryDirectory() as root:
            path, = append_scan(root, '93', [BASE, BASE])
            repeated, = append_scan(root, '93', [replace(BASE, title='New title', course_title='New course')])
            self.assertEqual(path, repeated)
            self.assertEqual(len(path.read_text(encoding='utf-8').splitlines()), 2)
    def test_accounts_and_course_ids_are_isolated(self):
        with tempfile.TemporaryDirectory() as root:
            a, = append_scan(root, '93', [BASE])
            b, = append_scan(root, '92', [BASE])
            c, = append_scan(root, '93', [replace(BASE, course_url=BASE.course_url.replace('34','35'))])
            self.assertNotEqual(a,b)
            self.assertNotEqual(a,c)
    def test_invalid_account_and_conflicting_duplicates_do_not_write(self):
        with tempfile.TemporaryDirectory() as root:
            for account, lessons in [('../93',[BASE]), ('93',[BASE, replace(BASE, displayed_count=7)])]:
                with self.assertRaises(ValueError):
                    append_scan(root, account, lessons)
            self.assertEqual(list(Path(root).rglob('history.jsonl')), [])
