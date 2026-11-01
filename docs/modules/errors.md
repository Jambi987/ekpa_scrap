# `ekpa_scraper/errors.py` — Sanitized network error hints

[Source](../../ekpa_scraper/errors.py) · [Documentation index](../README.md) · [Architecture](../ARCHITECTURE.md)

## Responsibility and connections

Used by discovery to turn exceptions into actionable summaries without echoing
request headers, bodies, URLs, cookies, or session keys. It examines text in memory
but returns a controlled message. This is a targeted helper, not a universal
exception logger used by every module.

## API reference

### `request_error_hint`

```python
request_error_hint(exc)
```

Recognize certificate-trust errors, timeouts, interrupted navigation, net::ERR_* codes and DNS failures; otherwise return only the exception class and a generic failure hint.

## Local dependencies

No imports from another application module.

## Side effects, failure handling and tests

TLS hints mention NODE_USE_SYSTEM_CA and an IT-provided PEM root via
NODE_EXTRA_CA_CERTS; they do not turn verification off. The helper performs no
network or filesystem operations. Tests in test_errors.py inject exceptions
containing session-like strings and check that those strings are not returned.
