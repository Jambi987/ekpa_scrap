import unittest
from urllib.parse import parse_qs,urlsplit
from ekpa_scraper.grading import ordered_report_url, validate_report_order

class ReportOrderTests(unittest.TestCase):
    def test_uses_moodle_option_value_and_retains_identity(self):
        url=ordered_report_url('https://lms.elearningekpa.gr/mod/quiz/report.php?id=557501&mode=grading&slot=11&qid=2&grade=all',pagesize=1,page=3)
        args=parse_qs(urlsplit(url).query)
        self.assertEqual(args['order'],['studentlastname'])
        self.assertEqual(args['page'],['3'])
        self.assertEqual(args['pagesize'],['1'])
        self.assertEqual(args['id'],['557501'])
    def test_rejects_random_effective_order(self):
        with self.assertRaisesRegex(ValueError,'random response ordering'):
            validate_report_order('<select name="order"><option selected value="random">Random</option><option value="studentlastname">Lastname</option></select>')
    def test_accepts_rendered_student_lastname_order(self):
        self.assertEqual(validate_report_order('<select name="order"><option value="random">Random</option><option selected value="studentlastname">Lastname</option></select>'),'studentlastname')
    def test_missing_settings_fragment_is_not_misread_as_random(self):
        self.assertIsNone(validate_report_order('<main>Response fragment</main>'))
