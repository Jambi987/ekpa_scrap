from pathlib import Path
import tempfile
import unittest
from ekpa_scraper.discovery import courses_from_response, parse_course_quizzes, enrolled_courses
from ekpa_scraper.grading import parse_pending_questions
from ekpa_scraper.storage import remember_lessons, merge_known_lessons
from test_grading import fixture

class DiscoveryTests(unittest.TestCase):
    def test_course_index_all_quizzes_and_dedup(self):
        html='''<main><table><tr><td><a href="/mod/quiz/view.php?id=11">Old graded exam</a></td></tr>
        <tr><td><a href="/mod/quiz/view.php?id=12">Pending exam</a></td></tr></table>
        <a href="/mod/quiz/view.php?id=11">Repeat</a><a href="https://other.example/mod/quiz/view.php?id=13">External</a></main>'''
        lessons=parse_course_quizzes(html,{'id':3,'fullname':'Course A'})
        self.assertEqual(len(lessons),2)
        self.assertTrue(all(x.course_url.endswith('id=3') for x in lessons))
        with tempfile.TemporaryDirectory() as root:
            remember_lessons(root,'93',lessons)
            self.assertEqual(len(merge_known_lessons(root,'93',[])),2)
            self.assertEqual(merge_known_lessons(root,'92',[]),[])
    def test_error_response_does_not_claim_empty_list(self):
        with self.assertRaises(ValueError):
            courses_from_response([{'error':True}])
    def test_explicit_graded_link_discovered(self):
        html=fixture().replace('<td>0</td>', '<td>2 <a href="https://lms.elearningekpa.gr/mod/quiz/report.php?id=557503&amp;mode=grading&amp;slot=11&amp;qid=6098587&amp;grade=manuallygraded">Update</a></td>')
        question,=parse_pending_questions(html,quiz_id='557503',include_all=True)
        self.assertIn('grade=manuallygraded',question.graded_url)
        self.assertIn('grade=needsgrading',question.ungraded_url)
        self.assertIn('grade=all',question.url)
    def test_replay_real_course_request_with_pagination_and_hidden(self):
        class Reply:
            ok=True
            def __init__(self,data): self.data=data
            def json(self): return [{'error':False,'data':self.data}]
            def dispose(self): pass
        class Request:
            calls=[]
            def post(self,url,data,timeout):
                args=data[0]['args']
                self.calls.append(dict(args))
                classification=args['classification']
                offset=args['offset']
                if classification=='all' and offset==0:
                    return Reply({'courses':[{'id':1,'fullname':'Past course'}],'nextoffset':1})
                if classification=='hidden' and offset==0:
                    return Reply({'courses':[{'id':2,'fullname':'Hidden course'}],'nextoffset':1})
                return Reply({'courses':[],'nextoffset':offset})
        class Context: request=Request()
        class Locator:
            def count(self): return 0
        class Page:
            context=Context()
            url='https://lms.elearningekpa.gr/my/courses.php'
            def on(self,event,handler): self.handler=handler
            def remove_listener(self,*args): pass
            def locator(self,*args): return Locator()
            def wait_for_timeout(self,*args): pass
            def goto(self,*args,**kwargs):
                class Observed:
                    url='https://lms.elearningekpa.gr/lib/ajax/service.php'
                    class request:
                        post_data_json=[{'index':0,'methodname':'core_course_get_enrolled_courses_by_timeline_classification','args':{'classification':'inprogress','offset':0,'limit':12,'searchvalue':'old filter'}}]
                self.handler(Observed())
        page=Page()
        courses=enrolled_courses(page)
        self.assertEqual({c['id'] for c in courses},{1,2})
        self.assertTrue(all(c['searchvalue']=='' for c in page.context.request.calls))
