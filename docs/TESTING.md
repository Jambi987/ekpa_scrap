# Testing and validation

[Index](README.md) · [Architecture](ARCHITECTURE.md)

## Run the suite

From the repository root in your installed environment:

```powershell
python -m unittest discover -s tests -v
```

The documented source snapshot contains **73 unittest tests across 15 files**.
They use synthetic HTML, temporary files, fake HTTP/page objects and unittest.mock.
They do not log into EKPA, read real Windows credentials or save actual grades.
BeautifulSoup is needed for parser imports; full runtime installation uses
requirements.txt. Linux can run these tests although credential-backed commands
explicitly require Windows.

To run one area:

```powershell
python -m unittest discover -s tests -p "test_download_resume.py" -v
python -m unittest discover -s tests -p "test_upload_safety.py" -v
python ekpa_login.py --help
python -m ekpa_scraper --help
python ekpa_login.py upload --help
```

Use unittest discovery rather than assuming tests is an importable installed
package. Several tests reuse `test_downloads.HTML`; test_errors also relies on
discovery fakes. Discovery adds the test directory to its import path.

## What passing tests establishes

The suite checks parsing contracts, response identity mapping, URL scope, stable
ordering/paging, CSV preservation, archive handling, conditional download reuse,
and critical preview/apply guards. Each test file has an individual reference
linked in the [inventory](README.md#test-files), including its cases and limits.

Passing does not prove that the current authenticated site still matches fixtures,
that Windows Credential Locker is available under another profile, that Excel's
real sharing locks behave like mocks, or that every browser/editor event persists
correctly on the live site. There is no CI workflow or dedicated accounts/browser/
CLI unit suite in this snapshot, and no full export-continuation end-to-end test.

## Manual Windows smoke checks

1. Verify the selected Python executable and dependency installation.
2. Run help without credentials, then add a dedicated authorized account and check login.
3. Run lessons and compare its counts to the actual dashboard.
4. Download to a separate test output directory and compare known submissions,
   exercise text and attachments to Moodle.
5. Download again: verify stable folders/rows, local edits preserved, missing copied
   attachment/ZIP member restoration, and completion/reuse logs. Use disposable
   output copies for destructive file-removal checks.
6. Preview one known quiz with --lesson-id; confirm the student identities, mark range
   and already-graded skips. Preview should not change Moodle marks.
7. Only when a real change is intended, apply an authorized mark in a test course or
   controlled submission and verify the site plus CSV and audit record afterward.
8. Check the CSV-lock guard with a controlled file open in Excel before any intended
   remote save. Close Excel and repeat only after understanding the failure.

Do not use real student work as committed test fixtures. Save sanitized HTML that
preserves IDs/relationships structurally but replaces names and removes session
keys, cookies, hidden secrets and unrelated personal content.

## When Moodle changes

Capture the failing page region and final error. Identify which contract changed:
course discovery, table header, response identity, report ordering, editor or Save
form. Add a focused synthetic regression, update the owning module/adapter and its
reference, run focused tests then the suite, and perform the appropriate live
Windows check. Report offline and live validation separately.
