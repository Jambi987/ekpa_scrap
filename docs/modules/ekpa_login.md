# `ekpa_login.py`

[Source](../../ekpa_login.py) · [Index](../README.md)

Compatibility script for `python ekpa_login.py ...`. It imports cli.main and,
only when run as the main script, raises SystemExit with the returned exit code.
Importing this file does not start login, although it loads CLI imports. It owns
no argument definitions or scraping logic; change cli.py to add commands.

Equivalent module execution is `python -m ekpa_scraper ...`. The filename remains
for existing user commands and scripts. There is no dedicated wrapper unit test;
`python ekpa_login.py --help` is a credential-free smoke check.

## Connections

See [CLI](cli.md), [architecture](../ARCHITECTURE.md), and [usage](../../USAGE.md).
