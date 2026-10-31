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
