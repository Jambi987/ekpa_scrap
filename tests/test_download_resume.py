import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import zipfile
from ekpa_scraper.files import download_upload


class DownloadResumeTests(unittest.TestCase):
    def context(self, payload):
        calls = []
        class Response:
            status = 200
            ok = True
            headers = {'etag': '"v1"'}
            def body(self):
                if self.status == 304:
                    raise AssertionError('304 must not read a body')
                return payload
            def dispose(self): pass
        response = Response()
        def get(url, **kwargs):
            calls.append(kwargs['headers'])
            response.status = 304 if kwargs['headers'] else 200
            return response
        return SimpleNamespace(request=SimpleNamespace(get=get)), calls

    def test_reuse_and_restore_missing_zip_member(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('project/main.py', 'answer')
        context, calls = self.context(buffer.getvalue())
        upload = SimpleNamespace(url='https://lms.elearningekpa.gr/pluginfile.php/1/work.zip', filename='work.zip')
        with tempfile.TemporaryDirectory() as tmp:
            path = download_upload(context, upload, tmp)
            member = Path(tmp) / 'project/main.py'
            member.unlink()
            self.assertEqual(download_upload(context, upload, tmp), path)
            self.assertEqual(member.read_text(), 'answer')
            self.assertEqual(calls, [{}, {'If-None-Match': '"v1"'}])
            events = [json.loads(x) for x in (Path(tmp)/'download_history.jsonl').read_text().splitlines()]
            self.assertEqual([x['status'] for x in events], ['complete', 'reused'])

    def test_missing_attachment_is_fetched_again(self):
        context, calls = self.context(b'answer')
        upload = SimpleNamespace(url='https://lms.elearningekpa.gr/pluginfile.php/1/work.txt', filename='work.txt')
        with tempfile.TemporaryDirectory() as tmp:
            path = download_upload(context, upload, tmp)
            path.unlink()
            self.assertEqual(download_upload(context, upload, tmp).read_bytes(), b'answer')
            self.assertEqual(calls, [{}, {}])

    def test_changed_local_attachment_is_preserved_and_remote_version_restored(self):
        context, calls = self.context(b'answer')
        upload = SimpleNamespace(url='https://lms.elearningekpa.gr/pluginfile.php/1/work.txt', filename='work.txt')
        with tempfile.TemporaryDirectory() as tmp:
            path = download_upload(context, upload, tmp)
            path.write_bytes(b'local edit')
            restored = download_upload(context, upload, tmp)
            self.assertNotEqual(restored, path)
            self.assertEqual(path.read_bytes(), b'local edit')
            self.assertEqual(restored.read_bytes(), b'answer')
            self.assertEqual(calls, [{}, {}])
