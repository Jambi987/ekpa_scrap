from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs,urlsplit,urlencode
from ekpa_scraper.grade_upload import response_pages
from ekpa_scraper.grading import PendingQuestion
from test_downloads import HTML

class Locator:
    first=property(lambda self:self)
    def count(self): return 0
    def wait_for(self,**kwargs): pass

class MoodlePage:
    """Model Moodle's real invalid-order fallback and paging suppression."""
    def goto(self,url,**kwargs): self.url=url
    def locator(self,*args): return Locator()
    def content(self):
        parts=urlsplit(self.url)
        args=parse_qs(parts.query)
        order=args.get('order',['random'])[0]
        # Moodle rejects the old 'lastname' value, resets to random, and forces page zero.
        if order not in ('random','date','studentfirstname','studentlastname'):
            order='random'
        index=0 if order=='random' else int(args.get('page',['0'])[0])
        html=HTML.replace('question-101-11',f'question-{101+index}-11').replace('John Doe',f'Student {index}')
        options=''.join(f'<option value="{value}" {"selected" if value==order else ""}>{value}</option>' for value in ('random','studentlastname'))
        html+='<select name="order">'+options+'</select>'
        if order!='random' and index<6:
            args['page']=[str(index+1)]
            url=parts._replace(query=urlencode([(k,v) for k,values in args.items() for v in values])).geturl()
            html+=f'<div class="pagination"><a href="{url}">Next</a></div>'
        return html

class MoodleOrderPagingTests(unittest.TestCase):
    def test_all_seven_response_ids_found_with_valid_moodle_order(self):
        url='https://lms.elearningekpa.gr/mod/quiz/report.php?id=557501&mode=grading&slot=11&qid=2&grade=all'
        with tempfile.TemporaryDirectory() as tmp:
            pages=list(response_pages(MoodlePage(),PendingQuestion('11','Question',url,7),Path(tmp)))
        self.assertEqual([rows[0].key for _,rows in pages],[f'{101+i}:11' for i in range(7)])
        self.assertTrue(all(parse_qs(urlsplit(url).query)['order']==['studentlastname'] for url,_ in pages))
