"""Excel-friendly CSV migration and synchronization without losing local notes."""
import csv
from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile

FIELDS = ['student_name', 'grade', 'notes', 'moodle_grade', 'moodle_status', 'last_checked']


def read_rows(path):
    if not path.exists():
        return []
    with path.open(encoding='utf-8-sig', newline='') as stream:
        sample = stream.read(4096)
        stream.seek(0)
        first = sample.splitlines()[0] if sample else ''
        delimiter = ';' if first.count(';') > first.count(',') else ','
        reader = csv.DictReader(stream, delimiter=delimiter)
        if reader.fieldnames not in (FIELDS, FIELDS[:3]):
            raise ValueError('CSV headers are unrecognized; existing file left untouched.')
        rows = list(reader)
        if any(None in row or any(v is None for v in row.values()) for row in rows):
            raise ValueError('CSV has malformed rows; existing file left untouched.')
        return [{field: row.get(field, '') for field in FIELDS} for row in rows]


def write_rows(path, rows):
    """Atomically replace the CSV, retaining a one-time pre-migration backup."""
    if path.exists():
        backup = path.with_name('students.before_sync.csv')
        if not backup.exists():
            with backup.open('xb') as stream:
                stream.write(path.read_bytes())
    handle, temporary = tempfile.mkstemp(prefix='students_', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, FIELDS, delimiter=';')
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def sync_row(rows, index, submission):
    if index is None:
        rows.append({field: '' for field in FIELDS})
        index = len(rows) - 1
    row = rows[index]
    old_moodle_grade = row['moodle_grade']
    # Refresh a previously mirrored grade; preserve a local grade edited since
    # the last sync. moodle_grade always reflects the latest readable value.
    if submission.moodle_grade != '' and (row['grade'] == '' or row['grade'] == old_moodle_grade):
        row['grade'] = submission.moodle_grade
    row['student_name'] = submission.student_name
    row['moodle_grade'] = submission.moodle_grade
    row['moodle_status'] = submission.moodle_status
    row['last_checked'] = datetime.now(timezone.utc).isoformat()
    return rows
