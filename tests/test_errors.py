import unittest
from ekpa_scraper.errors import request_error_hint
from ekpa_scraper.discovery import enrolled_courses

class Error(Exception):
    pass

class ErrorTests(unittest.TestCase):
    def test_certificate_hint_does_not_echo_session_details(self):
        hint=request_error_hint(Error('self-signed certificate in certificate chain; sesskey=SECRET; Cookie: private'))
        self.assertIn('NODE_USE_SYSTEM_CA',hint)
        self.assertIn('NODE_EXTRA_CA_CERTS',hint)
        self.assertNotIn('SECRET',hint)
        self.assertNotIn('Cookie',hint)
    def test_unknown_error_keeps_request_data_private(self):
        hint=request_error_hint(Error('POST /lib/ajax/service.php?sesskey=SECRET password=private'))
        self.assertEqual(hint,'Request failed (Error). Raw request details were omitted.')
    def test_navigation_interrupt_is_distinguished(self):
        self.assertIn('interrupted',request_error_hint(Error('Navigation interrupted by another navigation')))
    def test_course_request_certificate_failure_reports_the_stage(self):
        class Locator:
            def count(self): return 0
        class Request:
            def post(self,*args,**kwargs):
                raise Error('self-signed certificate in certificate chain; sesskey=SECRET')
        class Context: request=Request()
        class Page:
            context=Context()
            url='https://lms.elearningekpa.gr/my/courses.php'
            def on(self,event,handler): self.handler=handler
            def remove_listener(self,*args): pass
            def locator(self,*args): return Locator()
            def wait_for_timeout(self,*args): pass
            def goto(self,*args,**kwargs):
                class Observed:
                    url='https://lms.elearningekpa.gr/lib/ajax/service.php?sesskey=SECRET'
                    class request:
                        post_data_json=[{'index':0,'methodname':'core_course_get_enrolled_courses_by_timeline_classification','args':{}}]
                self.handler(Observed())
        with self.assertRaises(ValueError) as error:
            enrolled_courses(Page())
        self.assertIn('Retrieving enrolled courses failed',str(error.exception))
        self.assertIn('NODE_USE_SYSTEM_CA',str(error.exception))
        self.assertNotIn('SECRET',str(error.exception))
