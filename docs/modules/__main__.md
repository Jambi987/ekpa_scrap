# `ekpa_scraper/__main__.py`

[Source](../../ekpa_scraper/__main__.py) · [Index](../README.md)

Package entry point for `python -m ekpa_scraper ...`. It imports .cli.main and
immediately raises SystemExit(main()). The behavior and options are identical to
the compatibility script. Unlike ekpa_login.py, it has no __name__ guard, so importing
this specific module executes the CLI; import the package or parser modules instead
when writing tests. No network operation occurs for --help because argparse exits
before the credential backend is initialized.

## Connections

See [CLI](cli.md), [architecture](../ARCHITECTURE.md), and [usage](../../USAGE.md).
