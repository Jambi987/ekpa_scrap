import unittest
from ekpa_scraper.grading import parse_pending_questions, checked_report_url
from ekpa_scraper.moodle import MoodleLayoutError

ROOT = 'https://lms.elearningekpa.gr/mod/quiz/report.php?id=557503&amp;mode=grading'

def fixture():
    return f'''<table id="questionstograde"><thead><tr>
    <th>Ερ. #</th><th>T</th><th>Όνομα ερώτησης</th><th>Προς βαθμολόγηση</th><th>Ήδη βαθμολογημένο</th><th>Σύνολο</th>
    </tr></thead><tbody><tr><td>11</td><td>Essay</td><td class="c2">11-l4219-c1-u3</td>
    <td>6 <a href="{ROOT}&amp;slot=11&amp;qid=6098587&amp;grade=needsgrading">βαθμός</a></td>
    <td>0</td><td>6 <a href="{ROOT}&amp;slot=11&amp;qid=6098587&amp;grade=all">Βαθμολόγηση όλων</a></td>
    </tr></tbody></table>'''

class GradingTests(unittest.TestCase):
    def test_only_pending_column(self):
        links = parse_pending_questions(fixture(), quiz_id='557503')
        self.assertEqual(len(links), 1)
        self.assertEqual((links[0].number, links[0].title), ('11', '11-l4219-c1-u3'))
        self.assertIn('grade=needsgrading', links[0].url)
        self.assertNotIn('&amp;', links[0].url)
    def test_every_pending_link_and_deduplication(self):
        html = fixture().replace('</tbody>', fixture().split('<tbody>')[1].split('</tbody>')[0].replace('slot=11', 'slot=12') + '</tbody>')
        links = parse_pending_questions(html, quiz_id='557503')
        self.assertEqual(len(links), 2)
        html = fixture().replace('</tbody>', fixture().split('<tbody>')[1].split('</tbody>')[0] + '</tbody>')
        self.assertEqual(len(parse_pending_questions(html)), 1)
    def test_no_pending_links(self):
        html = fixture().replace('6 <a href="' + ROOT + '&amp;slot=11&amp;qid=6098587&amp;grade=needsgrading">βαθμός</a>', '0')
        self.assertEqual(parse_pending_questions(html), [])
    def test_layout_failures(self):
        for html in ['<html>Login</html>', fixture().replace('Προς βαθμολόγηση', 'Changed heading')]:
            with self.subTest(html=html[:30]), self.assertRaises(MoodleLayoutError):
                parse_pending_questions(html)
    def test_wrong_links_fail_instead_of_opening_all(self):
        for html in [fixture().replace('grade=needsgrading', 'grade=all'), fixture().replace('id=557503', 'id=123'), fixture().replace('https://lms.elearningekpa.gr', 'https://other.example')]:
            with self.subTest(html=html[:30]), self.assertRaises(MoodleLayoutError):
                parse_pending_questions(html, quiz_id='557503')
    def test_relative_dropdown_url(self):
        result = checked_report_url('/mod/quiz/report.php?id=557503&mode=grading', quiz_id='557503')
        self.assertTrue(result.startswith('https://lms.elearningekpa.gr/'))
