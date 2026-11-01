# `tests/test_download_resume.py` — Attachment reuse and repair

[Source](../../tests/test_download_resume.py) · [Testing guide](../TESTING.md) · [Index](../README.md)

## Purpose and interactions

Builds an in-memory ZIP and fake authenticated HTTP responses with an ETag. A second conditional request returns 304 and must not read a body; missing extracted members are restored. Deleting an attachment causes an unconditional fetch. Modifying a local file preserves that edit and saves restored remote bytes under a versioned name.

Application modules exercised: [files.py](../modules/files.md).

## Test cases

| Method | Scenario |
| --- | --- |
| `test_reuse_and_restore_missing_zip_member` | Reuse and restore missing zip member |
| `test_missing_attachment_is_fetched_again` | Missing attachment is fetched again |
| `test_changed_local_attachment_is_preserved_and_remote_version_restored` | Changed local attachment is preserved and remote version restored |

## Run this file

From the repository root:

```powershell
python -m unittest discover -s tests -p "test_download_resume.py" -v
```

Use discovery with `-s tests`: several tests import synthetic fixtures from peer
files by short module name. This command makes those imports available. It needs
no saved account and writes only temporary test output.

## Limits and maintenance

Checks real temporary files and history statuses but fake HTTP responses. It does not establish whether the live Moodle server supplies ETags or Last-Modified headers.

Keep fixtures synthetic and session-free. If the behavior changes intentionally,
update assertions alongside the owning module's documentation; do not remove a
validation assertion merely to make a changed live page pass.
