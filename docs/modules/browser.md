# `ekpa_scraper/browser.py` — Authenticated browser lifecycle

[Source](../../ekpa_scraper/browser.py) · [Documentation index](../README.md) · [Architecture](../ARCHITECTURE.md)

## Responsibility and connections

A context manager used by `cli.main` for every network-backed command. It creates
one Chromium browser, one isolated context, and the initial page; downstream
modules share that page or create tabs inside its context. Credentials come only
from `accounts.read_account`. Site URL and login locators come from `moodle`.

On Windows it sets NODE_USE_SYSTEM_CA to 1 only if not already set. The Playwright
import is delayed until the context manager runs. `accept_downloads=False` is
intentional: attachments are fetched explicitly by `files.download_upload` through
the authenticated request context.

## API reference

### `authenticated_page`

```python
authenticated_page(record, selectors=SELECTORS)
```

Start synchronous Playwright, launch headless Chromium, navigate to the login URL, validate same HTTPS origin and exact form action, fill credentials, submit once, and wait for the authenticated locator. Yield the page and close context/browser in finally.

## Local dependencies

[moodle.py](moodle.md)

## Side effects, failure handling and tests

Navigation has a 45-second timeout and confirmation waits up to 60 seconds.
A confirmation timeout pauses for Enter and raises ValueError; it does not retry
credentials. The context is not persisted to disk. Browser windows cannot be
made visible by --keep-open because headless=True is hardcoded. The printed
manual-verification prompt is therefore not an implemented interactive solution.
There is no live browser/credential integration test in the offline suite.
