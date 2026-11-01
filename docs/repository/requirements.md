# Dependency manifest

[Source](../../requirements.txt) · [Index](../README.md)

This file is consumed by `python -m pip install -r requirements.txt`. It is a set
of allowed version ranges, not a reproducible lock file.

| Requirement | Used by | Purpose |
| --- | --- | --- |
| `keyring>=25,<26` | accounts.py | Explicit Windows WinVaultKeyring backend |
| `pywin32>=306; sys_platform == 'win32'` | Windows runtime | Windows integration; installed only on Windows |
| `playwright>=1.49,<2` | browser.py and workflow page/context objects | Browser automation and authenticated HTTP client |
| `beautifulsoup4>=4.12,<5` | Parsers, grade_upload, login-payload detection | HTML extraction and validation |

Chromium is installed separately using `python -m playwright install chromium`.
Use the same interpreter for installation and execution. Python 3.12 is the usage
example; source uses Python 3.10+ syntax. Most file, CSV, hashing, archive, decimal,
ctypes and test functions use the standard library.

A dependency update can affect browser binaries or HTML behavior despite unchanged
source. Run the offline suite and appropriate Windows/Moodle smoke checks. No
package installer, pyproject.toml or pinned dependency lock is supplied here.
