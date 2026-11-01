# Historical troubleshooting reference

[Source](../../TROUBLESHOOTING.md) · [Index](../README.md)

Documents three investigated failures: login working while course-request TLS
trust fails, enrolled courses returning no matched quiz links, and response paging
being suppressed by an invalid order option. It includes PowerShell/Git Bash trust
configuration and links to the Moodle source consulted for the ordering behavior.

The associated runtime owners are browser/errors/discovery for trust and discovery,
and grading/moodle for order construction. Focused regression files include
test_errors.py, test_quiz_links.py and test_moodle_order_paging.py.

This is diagnostic context, not an exhaustive command guide. USAGE.md covers CSV
locks, one-time backups, upload outcomes and log interpretation. Treat statements
about prior live validation as historical scope; inspect current evidence before
claiming a new site issue is fixed. No runtime module reads this file.
