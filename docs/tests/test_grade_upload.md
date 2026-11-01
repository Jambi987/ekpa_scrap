# `tests/test_grade_upload.py` — Upload values, mapping and preview behavior

[Source](../../tests/test_grade_upload.py) · [Testing guide](../TESTING.md) · [Index](../README.md)

## Purpose and interactions

Exercises Decimal parsing and bounds, blank-field preservation, identity checking, already-graded no-ops, note escaping/normalization, unique Save button selection, index-to-CSV matching, single-response URL generation and preview never invoking apply.

Application modules exercised: [grade_upload.py](../modules/grade_upload.md), [csv_store.py](../modules/csv_store.md), [export.py](../modules/export.md).

## Test cases

| Method | Scenario |
| --- | --- |
| `test_decimal_zero_and_ranges` | Decimal zero and ranges |
| `test_blank_grade_and_blank_notes_do_not_erase` | Blank grade and blank notes do not erase |
| `test_already_graded_is_noop_and_identity_is_checked` | Already graded is noop and identity is checked |
| `test_notes_are_plain_text_and_html_escaped` | Notes are plain text and html escaped |
| `test_save_button_requires_unique_save_action` | Save button requires unique save action |
| `test_csv_mapping_and_local_values` | Csv mapping and local values |
| `test_single_response_url_retains_target_and_all_filter` | Single response url retains target and all filter |
| `test_preview_never_calls_apply` | Preview never calls apply |

## Run this file

From the repository root:

```powershell
python -m unittest discover -s tests -p "test_grade_upload.py" -v
```

Use discovery with `-s tests`: several tests import synthetic fixtures from peer
files by short module name. This command makes those imports available. It needs
no saved account and writes only temporary test output.

## Limits and maintenance

Logic and mock-based tests do not prove that a live rich-text editor receives change events or that Moodle persists a submitted form.

Keep fixtures synthetic and session-free. If the behavior changes intentionally,
update assertions alongside the owning module's documentation; do not remove a
validation assertion merely to make a changed live page pass.
