import unittest
from ekpa_scraper.dashboard import parse_dashboard
from ekpa_scraper.moodle import MoodleLayoutError

def fixture():
    groups = []
    for course, counts in [('Course A', [6, 1]), ('Course B', [5])]:
        items = ''
        for count in counts:
            entries = '<li class="gradable"></li>' * count
            items += f'<dd class="module"><div class="dd-wrap"><a class="grademe-mod-name" href="/mod/quiz/view.php?id={count}">Lesson {count}</a><span class="badge">{count}</span></div><ul class="gradable-list block_grade_me_hide">{entries}</ul></dd>'
        groups.append(f'<div><dt class="cmod"><a class="grademe-course-name">{course}</a></dt>{items}</div>')
    return '<section data-block="grade_me"><dl>' + ''.join(groups) + '</dl></section>'

class DashboardTests(unittest.TestCase):
    def test_grouping_counts_and_hidden_entries(self):
        result = parse_dashboard(fixture())
        self.assertEqual([x.title for x in result], ['Lesson 6', 'Lesson 1', 'Lesson 5'])
        self.assertEqual([x.course_title for x in result], ['Course A', 'Course A', 'Course B'])
        self.assertEqual([x.displayed_count for x in result], [6, 1, 5])
        self.assertEqual([x.listed_entries for x in result], [6, 1, 5])
        self.assertTrue(result[0].url.startswith('https://lms.elearningekpa.gr/mod/quiz/'))
    def test_mismatch(self):
        result = parse_dashboard(fixture().replace('<span class="badge">6</span>', '<span class="badge">7</span>'))
        self.assertEqual((result[0].displayed_count, result[0].listed_entries), (7, 6))
    def test_missing_or_changed_layout_raises(self):
        for html in ['<html>Login</html>', fixture().replace('class="module"', 'class="changed"'), fixture().replace('class="badge"', 'class="changed"')]:
            with self.subTest(html=html[:30]), self.assertRaises(MoodleLayoutError):
                parse_dashboard(html)
    def test_empty(self):
        self.assertEqual(parse_dashboard('<section data-block="grade_me"></section>'), [])
    def test_external_url(self):
        with self.assertRaises(MoodleLayoutError):
            parse_dashboard(fixture().replace('/mod/quiz/view.php?id=6', 'https://other.example/'))
    def test_whitespace(self):
        result = parse_dashboard(fixture().replace('Lesson 6', 'Lesson&nbsp; 6\n'))
        self.assertEqual(result[0].title, 'Lesson 6')
