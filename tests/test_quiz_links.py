import unittest
from unittest.mock import patch
from ekpa_scraper.discovery import parse_course_quizzes, discover_all_lessons
from ekpa_scraper.moodle import ORIGIN

COURSE={'id':39318,'fullname':'Git course'}

class Locator:
    def count(self): return 0

class FakePage:
    def __init__(self,index_html,course_html):
        self.index_html=index_html; self.course_html=course_html; self.visits=[]
    def goto(self,url,**kwargs):
        self.url=url
        self.visits.append(url)
        return type('Response',(),{'status':200})()
    def content(self):
        return self.index_html if '/mod/quiz/index.php' in self.url else self.course_html
    def locator(self,*args): return Locator()

class QuizLinkTests(unittest.TestCase):
    def test_bare_and_dot_relative_quiz_links_resolve_against_index(self):
        html='<main><a href="view.php?id=557503">Branching</a><a href="./view.php?id=557504">Rebasing</a></main>'
        lessons=parse_course_quizzes(html,COURSE)
        self.assertEqual([x.url for x in lessons],[ORIGIN+'/mod/quiz/view.php?id=557503',ORIGIN+'/mod/quiz/view.php?id=557504'])
    def test_teacher_report_links_and_icon_only_links(self):
        html='<main><a href="report.php?id=557503&amp;mode=overview">Branching</a><a href="view.php?id=557503">Repeat</a><a title="Rebasing" href="view.php?id=557504"><img alt="Quiz"></a></main>'
        lessons=parse_course_quizzes(html,COURSE)
        self.assertEqual([x.title for x in lessons],['Branching','Rebasing'])
    def test_base_tag_and_course_page_context(self):
        html='<base href="/mod/quiz/"><main><a href="view.php?id=557503">Quiz</a><a href="https://other.example/mod/quiz/view.php?id=999">External</a></main>'
        lessons=parse_course_quizzes(html,COURSE,page_url=ORIGIN+'/course/view.php?id=39318')
        self.assertEqual(len(lessons),1)
        self.assertTrue(lessons[0].url.endswith('id=557503'))
    def test_course_page_fallback_finds_activity(self):
        page=FakePage('<main>No quiz links here</main>','<main><a href="../mod/quiz/view.php?id=557503">Branching</a></main>')
        with patch('ekpa_scraper.discovery.enrolled_courses',return_value=[COURSE]):
            lessons=discover_all_lessons(page)
        self.assertEqual(len(lessons),1)
        self.assertEqual(len(page.visits),2)
    def test_zero_matches_is_not_reported_as_success(self):
        page=FakePage('<main>No quiz links</main>','<main>No quiz links</main>')
        with patch('ekpa_scraper.discovery.enrolled_courses',return_value=[COURSE]):
            with self.assertRaisesRegex(ValueError,'no quiz/test links matched'):
                discover_all_lessons(page)
