# Documentation index and repository file map

[Usage](../USAGE.md) · [Architecture](ARCHITECTURE.md) · [Data and logs](DATA_AND_LOGS.md) · [Testing](TESTING.md)

This documentation describes the source inherited from master commit
`124b42041552af9af11cfe607017cdaad2c30625`. The documentation branch changes Markdown
only. Every application Python file, test file and configuration file has a
reference below. Runtime-generated files are covered separately in DATA_AND_LOGS.

## Source modules

| Source | Detailed reference |
| --- | --- |
| [ekpa_login.py](../ekpa_login.py) | [ekpa_login](modules/ekpa_login.md) |
| [ekpa_scraper/__init__.py](../ekpa_scraper/__init__.py) | [__init__](modules/__init__.md) |
| [ekpa_scraper/__main__.py](../ekpa_scraper/__main__.py) | [__main__](modules/__main__.md) |
| [ekpa_scraper/accounts.py](../ekpa_scraper/accounts.py) | [accounts](modules/accounts.md) |
| [ekpa_scraper/browser.py](../ekpa_scraper/browser.py) | [browser](modules/browser.md) |
| [ekpa_scraper/cli.py](../ekpa_scraper/cli.py) | [cli](modules/cli.md) |
| [ekpa_scraper/csv_store.py](../ekpa_scraper/csv_store.py) | [csv_store](modules/csv_store.md) |
| [ekpa_scraper/dashboard.py](../ekpa_scraper/dashboard.py) | [dashboard](modules/dashboard.md) |
| [ekpa_scraper/discovery.py](../ekpa_scraper/discovery.py) | [discovery](modules/discovery.md) |
| [ekpa_scraper/errors.py](../ekpa_scraper/errors.py) | [errors](modules/errors.md) |
| [ekpa_scraper/export.py](../ekpa_scraper/export.py) | [export](modules/export.md) |
| [ekpa_scraper/files.py](../ekpa_scraper/files.py) | [files](modules/files.md) |
| [ekpa_scraper/grade_upload.py](../ekpa_scraper/grade_upload.py) | [grade_upload](modules/grade_upload.md) |
| [ekpa_scraper/grading.py](../ekpa_scraper/grading.py) | [grading](modules/grading.md) |
| [ekpa_scraper/moodle.py](../ekpa_scraper/moodle.py) | [moodle](modules/moodle.md) |
| [ekpa_scraper/storage.py](../ekpa_scraper/storage.py) | [storage](modules/storage.md) |
| [ekpa_scraper/submissions.py](../ekpa_scraper/submissions.py) | [submissions](modules/submissions.md) |
| [ekpa_scraper/upload_io.py](../ekpa_scraper/upload_io.py) | [upload_io](modules/upload_io.md) |

## Test files

| Source | Detailed reference |
| --- | --- |
| [tests/test_csv_sync.py](../tests/test_csv_sync.py) | [CSV migration and observed-grade synchronization](tests/test_csv_sync.md) |
| [tests/test_dashboard.py](../tests/test_dashboard.py) | [Grade Me block parsing](tests/test_dashboard.md) |
| [tests/test_discovery.py](../tests/test_discovery.py) | [Course service and quiz-index discovery](tests/test_discovery.md) |
| [tests/test_download_resume.py](../tests/test_download_resume.py) | [Attachment reuse and repair](tests/test_download_resume.md) |
| [tests/test_downloads.py](../tests/test_downloads.py) | [Response parsing, roster persistence and downloads](tests/test_downloads.md) |
| [tests/test_errors.py](../tests/test_errors.py) | [Sanitized diagnostics](tests/test_errors.md) |
| [tests/test_grade_upload.py](../tests/test_grade_upload.py) | [Upload values, mapping and preview behavior](tests/test_grade_upload.md) |
| [tests/test_grading.py](../tests/test_grading.py) | [Manual-grading question table parsing](tests/test_grading.md) |
| [tests/test_moodle_order_paging.py](../tests/test_moodle_order_paging.py) | [Regression for invalid Moodle ordering](tests/test_moodle_order_paging.md) |
| [tests/test_quiz_links.py](../tests/test_quiz_links.py) | [Relative quiz links and fallback discovery](tests/test_quiz_links.md) |
| [tests/test_report_order.py](../tests/test_report_order.py) | [Shared report ordering adapter](tests/test_report_order.md) |
| [tests/test_storage.py](../tests/test_storage.py) | [Stable folders and append-only dashboard observations](tests/test_storage.md) |
| [tests/test_upload_paging.py](../tests/test_upload_paging.py) | [Rendered paging and preflight diagnostics](tests/test_upload_paging.md) |
| [tests/test_upload_safety.py](../tests/test_upload_safety.py) | [Already-graded and local-write safeguards](tests/test_upload_safety.md) |
| [tests/test_upload_selection.py](../tests/test_upload_selection.py) | [Candidate counts and zero-change reporting](tests/test_upload_selection.md) |

## Repository configuration and existing Markdown

| File | Detailed reference |
| --- | --- |
| [requirements.txt](../requirements.txt) | [requirements](repository/requirements.md) |
| [.gitignore](../.gitignore) | [gitignore](repository/gitignore.md) |
| [README.md](../README.md) | [readme](repository/readme.md) |
| [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) | [troubleshooting](repository/troubleshooting.md) |

## Documentation files created in this branch

| File/group | How it connects |
| --- | --- |
| README.md | Landing page, quick workflow and scope; links to this index and USAGE |
| USAGE.md | Full installation/credential/command guide; links to data and troubleshooting |
| docs/README.md | This inventory; maps every tracked application/test/config file to its reference |
| docs/ARCHITECTURE.md | Cross-module flows and record ownership; links to individual modules |
| docs/DATA_AND_LOGS.md | Every runtime file, CSV schema and event contract; used by operator and maintainer guides |
| docs/TESTING.md | Suite commands and manual validation boundaries; links to test references |
| docs/modules/*.md | One page per Python source file with responsibilities, APIs, dependencies and failure behavior |
| docs/tests/*.md | One page per test file with scenario inventory, dependencies, run command and limits |
| docs/repository/*.md | Requirements, ignore rules, README and troubleshooting roles |

The per-file references document implementation as it exists, including limitations;
they do not imply that every function has direct test coverage. Source links are
relative to the repository. For changed behavior, update the source reference,
relevant test reference, and user-facing commands/data contracts together.
