"""Authenticated browser lifecycle. Each invocation creates an isolated context."""
from contextlib import contextmanager
from urllib.parse import urlsplit
from .moodle import ORIGIN, LOGIN_URL, SELECTORS

@contextmanager
def authenticated_page(record, selectors=SELECTORS):
    from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(accept_downloads=False)
        try:
            page = context.new_page()
            page.goto(LOGIN_URL, wait_until='domcontentloaded', timeout=45000)
            if urlsplit(page.url).scheme != 'https' or urlsplit(page.url).netloc != urlsplit(ORIGIN).netloc:
                raise ValueError('Unexpected login destination. Credentials were not entered.')
            form = page.locator(selectors.login_form)
            form.locator(selectors.password).wait_for()
            if form.evaluate('(f) => f.action') != LOGIN_URL:
                raise ValueError('Unexpected login form action. Credentials were not entered.')
            form.locator(selectors.username).fill(record['username'])
            form.locator(selectors.password).fill(record['password'])
            form.locator(selectors.submit).first.click()
            print('Login submitted once. Complete additional verification in the browser if needed.')
            try:
                page.locator(selectors.authenticated).first.wait_for(state='attached', timeout=60000)
            except BrowserTimeout:
                input('Login not confirmed. Inspect the browser; press Enter to close... ')
                raise ValueError('Login could not be confirmed. No automatic retry was made.') from None
            if urlsplit(page.url).netloc != urlsplit(ORIGIN).netloc:
                raise ValueError('Unexpected destination after login.')
            yield page
        finally:
            context.close()
            browser.close()
