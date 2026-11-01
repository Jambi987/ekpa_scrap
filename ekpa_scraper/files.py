"""Authenticated file retrieval, non-overwriting saves and bounded ZIP extraction."""
from hashlib import sha256
from pathlib import Path, PurePosixPath
import re
import json
from datetime import datetime, timezone
import stat
from urllib.parse import urljoin, urlsplit
import zipfile
from .moodle import ORIGIN

MAX_FILE = 100 * 1024 * 1024
MAX_ZIP_TOTAL = 300 * 1024 * 1024
MAX_ZIP_FILES = 2000


def filename(value):
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', value).strip(' .') or 'upload'
    if value.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *[f'COM{i}' for i in range(1,10)], *[f'LPT{i}' for i in range(1,10)]}:
        value = '_' + value
    p = Path(value)
    return p.stem[:90] + p.suffix[:12]


def save_bytes(path, data):
    """Identical bytes are skipped; changed files get a content-hash suffix."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError('Refusing to replace a symbolic link.')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_file() and path.read_bytes() == data:
            return path
        digest = sha256(data).hexdigest()[:16]
        path = path.with_name(path.stem + '__' + digest + path.suffix)
        if path.is_symlink():
            raise ValueError('Refusing a symbolic link destination.')
        if path.exists():
            if path.is_file() and path.read_bytes() == data:
                return path
            raise ValueError('Versioned destination already contains different content.')
    with path.open('xb') as stream:
        stream.write(data)
    return path


def extract_zip(path, student_dir):
    root = Path(student_dir).resolve()
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ZIP_FILES or sum(i.file_size for i in infos) > MAX_ZIP_TOTAL:
            raise ValueError('ZIP exceeds extraction limits; original archive was retained.')
        destinations = []
        for item in infos:
            raw = item.filename.replace('\\', '/')
            parts = PurePosixPath(raw)
            if parts.is_absolute() or '..' in parts.parts or ':' in raw or stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError('ZIP contains an unsafe path or symbolic link; original archive was retained.')
            if item.file_size > MAX_FILE:
                raise ValueError('ZIP member exceeds the size limit.')
            target = root.joinpath(*(filename(part) for part in parts.parts))
            if not target.resolve().is_relative_to(root):
                raise ValueError('ZIP destination is outside the student folder.')
            destinations.append((item, target))
        for item, target in destinations:
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                save_bytes(target, archive.read(item))


def download_event(student_dir, status, **fields):
    root = Path(student_dir)
    root.mkdir(parents=True, exist_ok=True)
    with (root / 'download_history.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(dict(time_utc=datetime.now(timezone.utc).isoformat(),
                                     status=status, **fields), ensure_ascii=False) + '\n')


def cached_upload(student_dir, key):
    root = Path(student_dir)
    history = root / 'download_history.jsonl'
    record = None
    if history.exists():
        for line in history.read_text(encoding='utf-8').splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue  # An interrupted final log write is not completion.
            if item.get('key') == key and item.get('status') == 'complete':
                record = item
    if record:
        path = root / record['file']
        if (path.parent.resolve() == root.resolve() and not path.is_symlink()
                and path.is_file() and sha256(path.read_bytes()).hexdigest() == record['sha256']):
            return record, path
    return None, None


def download_upload(context, upload, student_dir):
    url = upload.url
    data = None
    key = sha256(upload.url.encode('utf-8')).hexdigest()
    cached, cached_path = cached_upload(student_dir, key)
    headers = {}
    if cached:
        if cached.get('etag'):
            headers['If-None-Match'] = cached['etag']
        elif cached.get('last_modified'):
            headers['If-Modified-Since'] = cached['last_modified']
    response_headers = {}
    for _ in range(6):
        parts = urlsplit(url)
        if parts.scheme != 'https' or parts.netloc != urlsplit(ORIGIN).netloc:
            raise ValueError('Unexpected attachment download origin.')
        response = context.request.get(url, headers=headers, max_redirects=0, timeout=60000)
        try:
            if response.status in (301, 302, 303, 307, 308):
                location = response.headers.get('location')
                if not location:
                    raise ValueError('Attachment redirect has no location.')
                url = urljoin(url, location)
                continue
            if response.status == 304:
                if not cached_path or not headers:
                    raise ValueError('Attachment returned 304 without a verified local copy.')
                # Re-extract to restore missing files without fetching the archive.
                if zipfile.is_zipfile(cached_path):
                    extract_zip(cached_path, student_dir)
                download_event(student_dir, 'reused', key=key, file=cached_path.name)
                return cached_path
            if not response.ok:
                raise ValueError(f'Attachment download returned HTTP {response.status}.')
            length = response.headers.get('content-length', '0')
            if length.isdigit() and int(length) > MAX_FILE:
                raise ValueError('Attachment exceeds the 100 MiB download limit.')
            response_headers = response.headers
            data = response.body()
            if len(data) > MAX_FILE:
                raise ValueError('Attachment exceeds the 100 MiB download limit.')
            if 'text/html' in response.headers.get('content-type', '').lower():
                from bs4 import BeautifulSoup
                html = BeautifulSoup(data, 'html.parser')
                if html.select_one('form#login, body#page-login-index'):
                    raise ValueError('Attachment returned the Moodle login page; session may have expired.')
            break
        finally:
            response.dispose()
    if data is None:
        raise ValueError('Too many attachment redirects.')
    path = save_bytes(Path(student_dir) / filename(upload.filename), data)
    if zipfile.is_zipfile(path):
        extract_zip(path, student_dir)
    elif path.suffix.lower() == '.zip':
        raise ValueError('Downloaded .zip is not a valid ZIP archive; original file retained.')
    download_event(student_dir, 'complete', key=key, file=path.name,
                   sha256=sha256(data).hexdigest(), etag=response_headers.get('etag', ''),
                   last_modified=response_headers.get('last-modified', ''))
    return path
