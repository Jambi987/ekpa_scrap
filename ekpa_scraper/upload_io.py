"""Check local upload bookkeeping access before changing Moodle."""
import ctypes
import errno
import os
from pathlib import Path
import sys
import tempfile


def _windows_replace_access(path):
    """Request write AND delete access without modifying/deleting the CSV.

    Excel may allow reading while denying the replacement used by atomic CSV
    writes. Requesting DELETE access detects that sharing lock as well.
    """
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = create(str(path), 0x80000000 | 0x40000000 | 0x00010000,
                    0x1 | 0x2 | 0x4, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise PermissionError(errno.EACCES, 'CSV write/replace access denied', str(path))
    kernel.CloseHandle(handle)


def csv_access_message(path):
    return (f'Cannot write or replace CSV: {path}. Close it in Excel and other editors, '
            'then check that the file and its folder are writable. No new Moodle save was started by this write check.')


def check_csv_writable(path):
    path = Path(path)
    temporary = None
    try:
        with path.open('r+b'):
            pass
        if sys.platform == 'win32':
            _windows_replace_access(path)
        descriptor, temporary = tempfile.mkstemp(prefix='students_writecheck_', suffix='.tmp', dir=path.parent)
        os.close(descriptor)
        Path(temporary).unlink()
        temporary = None
    except PermissionError:
        raise ValueError(csv_access_message(path)) from None
    finally:
        if temporary is not None:
            try:
                Path(temporary).unlink(missing_ok=True)
            except OSError:
                pass


def check_upload_writes(plan):
    for path in sorted({change.edit.csv_path for change in plan}):
        check_csv_writable(path)
