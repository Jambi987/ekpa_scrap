# `ekpa_scraper/accounts.py` — Credential registration and retrieval

[Source](../../ekpa_scraper/accounts.py) · [Documentation index](../README.md) · [Architecture](../ARCHITECTURE.md)

## Responsibility and connections

Called by `cli.main` before any browser session. It extracts an account number
from the username and binds it to one Windows Credential Locker entry. The record
passed to `browser.authenticated_page` contains `username` and `password` in memory.
It does not read or write export folders, validate credentials against Moodle, or
choose a generic keyring backend.

`SERVICE` is `ekpa-lms-scraper-v1`. Changing it makes existing saved accounts appear
missing unless migrated. Account IDs are strings; leading zeros remain significant.
Only one full username can occupy a given extracted number. All registered values
are local to the Windows credential context; copying repository files does not
copy credentials.

## API reference

### `account_id`

```python
account_id(username)
```

Return the unique numeric substring from exactly one profNUMBERlms occurrence; raise ValueError for zero or multiple matches.

### `credential_store`

```python
credential_store()
```

Require sys.platform == win32 and instantiate WinVaultKeyring explicitly. Import keyring lazily; no plaintext fallback.

### `read_account`

```python
read_account(store, number)
```

Read SERVICE/account, decode JSON, and verify the stored username still maps to the requested account and the password is nonempty. Return the credential dictionary.

### `add_account`

```python
add_account(store)
```

Prompt for username, reject duplicate account number, prompt twice with getpass, validate nonempty matching passwords, then store JSON. Does not test login.

## Local dependencies

No imports from another application module.

## Side effects, failure handling and tests

ValueError messages are shown by the CLI; other credential/backend exceptions
are reduced to their type by its generic handler. Registration/deletion change
credential state. Do not log the returned record or include it in test fixtures.
There is no dedicated accounts test file in this snapshot; Windows storage needs
a real Windows smoke test separate from the parser suite.
