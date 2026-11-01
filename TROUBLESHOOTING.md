# Browser login succeeds, then course discovery fails

Login uses Chromium, while course enumeration also uses Playwright's bundled
Node request client. Those clients can trust different certificate stores.
On Windows the scraper now defaults NODE_USE_SYSTEM_CA to 1 before starting
Playwright. An explicitly set value is preserved. Certificate verification is
still enabled; nothing sets ignore_https_errors or disables TLS validation.

To set it explicitly in PowerShell:

```powershell
$env:NODE_USE_SYSTEM_CA = "1"
python ekpa_login.py download 93 --output "$env:USERPROFILE\Desktop\ekpa_desktop"
```

For Git Bash:

```bash
NODE_USE_SYSTEM_CA=1 python ekpa_login.py download 93 --output "$HOME/Desktop/ekpa_desktop"
```

If a company proxy uses a CA not available in the system store, obtain its
trusted PEM root certificate from IT and set NODE_EXTRA_CA_CERTS to that file
before starting Python. Do not disable certificate verification.

Course discovery now prints its stage and reports a sanitized cause for TLS,
timeout, DNS and navigation failures. Raw URLs, headers, cookies and request
bodies are omitted. A failure before any course counts or downloads may leave
no student output; credentials need not be removed or re-added.

TLS is only one possible cause of a post-login error. The new message is needed
to identify whether it is the cause on your machine. Live EKPA access was not
used to validate this fix; tests reproduce a certificate error at the same
request boundary and confirm that session details are not exposed.

# Courses found but zero quiz/test activities

Quiz-index links may be relative to /mod/quiz/ (for example view.php?id=557503).
Discovery now resolves them against the actual page URL, honors same-site base
URLs, and accepts teacher report links as quiz activity references. If the
index has no matches, the scanner also checks the course's main page. It prints
per-course counts and treats zero matches across nonempty courses as an error,
rather than claiming a successful export.

The relative-link case is regression-tested but has not been verified against
your authenticated page. If it still finds no quizzes, supply the main-content
HTML from one printed quiz index URL, removing any session keys. A site-specific
course format may require a different adapter; course-page fallback by itself
cannot prove that lazily loaded or separately paged sections were all scanned.

# Only the first response is found in each quiz

The grading report order parameter must be the option VALUE studentlastname,
not the label lastname. Moodle 4.5 validates against random, date,
studentfirstname and studentlastname (plus permitted identity fields). An
unrecognized value falls back to random; random ordering forces page zero
and suppresses the pagination bar. That can cause repeated first attempts
or most CSV response IDs not being found.

Report URLs now share one builder using the adapter value in moodle.py.
The rendered order selector is checked before processing responses. Random
ordering is reported as an error instead of attempting an incomplete scan.
The regression test models Moodle's validation and traverses seven single-
response pages. Identity checks and preflight-before-save remain in place.

Source inspected:
https://github.com/moodle/moodle/blob/MOODLE_405_STABLE/mod/quiz/report/grading/report.php
https://github.com/moodle/moodle/blob/MOODLE_405_STABLE/mod/quiz/report/grading/renderer.php
