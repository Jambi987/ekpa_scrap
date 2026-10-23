import getpass
import json
import re
import sys

SERVICE = "ekpa-lms-scraper-v1"

def account_id(username):
    matches = re.findall(r'prof([0-9]+)lms', username)
    if len(matches) != 1:
        raise ValueError('Username must contain exactly one profNUMBERlms pattern.')
    return matches[0]


def credential_store():
    if sys.platform != 'win32':
        raise ValueError('Run this script with Windows Python, not WSL.')
    # Explicit backend: never silently fall back to a plaintext credential file.
    from keyring.backends.Windows import WinVaultKeyring
    return WinVaultKeyring()


def read_account(store, number):
    raw = store.get_password(SERVICE, number)
    if raw is None:
        raise ValueError('Account is not registered. Run the add command first.')
    record = json.loads(raw)
    if account_id(record['username']) != number or not record['password']:
        raise ValueError('Stored account record is invalid. Remove it and add it again.')
    return record


def add_account(store):
    username = input('Full username: ').strip()
    number = account_id(username)
    if store.get_password(SERVICE, number) is not None:
        raise ValueError('This account number already exists. Remove it before replacing it.')
    password = getpass.getpass('Password (hidden): ')
    if not password:
        raise ValueError('Password cannot be empty.')
    if password != getpass.getpass('Confirm password: '):
        raise ValueError('Passwords do not match.')
    store.set_password(SERVICE, number, json.dumps({'username': username, 'password': password}))
    print(f'Account {number} saved to Windows Credential Locker. Login has not yet been tested.')


