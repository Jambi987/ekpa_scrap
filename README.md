# EKPA Moodle scraper

A Windows Python command-line tool for instructor accounts on
<https://lms.elearningekpa.gr>. It lists pending grading, downloads quiz essay
attachments, maintains local student CSVs, and submits grades and feedback from
those CSVs through Moodle's normal manual-grading form.

**Start with [USAGE.md](USAGE.md)** for installation, credentials, daily workflow,
all commands, worked PowerShell examples, and recovery instructions.

## What the program does

- Keeps each account's credentials in Windows Credential Locker and its output in
  a separate numbered directory.
- Lists the dashboard's **Βαθμολόγησε με** lessons and pending counts.
- Discovers enrolled courses and quiz activities, including hidden course-list
  entries, rather than relying only on dashboard items with pending grading.
- Downloads both graded and ungraded essay responses; retains uploaded ZIPs and
  extracts their contents without executing them.
- Preserves local grade/notes edits during CSV refreshes and versions changed
  attachments instead of overwriting their original bytes.
- Previews uploads by default. `--apply` is required to save to Moodle.
- Skips responses already graded in Moodle, including a grade of zero, and checks
  again immediately before each save.
- Records download completion and grade-upload audit events.

## Quick workflow

Run these from the repository directory after completing installation:

```powershell
python ekpa_login.py add
python ekpa_login.py lessons 93 --output "$env:USERPROFILE\Desktop\ekpa_desktop"
python ekpa_login.py download 93 --output "$env:USERPROFILE\Desktop\ekpa_desktop"
# Edit grade and optional notes in students.csv, save, and close Excel.
python ekpa_login.py upload 93 --output "$env:USERPROFILE\Desktop\ekpa_desktop" --lesson-id 557503
python ekpa_login.py upload 93 --output "$env:USERPROFILE\Desktop\ekpa_desktop" --lesson-id 557503 --apply
```

Replace account and quiz IDs with your own. Omitting `--output` uses **`output`
relative to the working directory**, not the Desktop. `students.before_sync.csv`
is a one-time recovery snapshot; it is not the input to uploads.

## Documentation map

| Document | Purpose |
| --- | --- |
| [USAGE.md](USAGE.md) | Complete operator guide and commands |
| [docs/README.md](docs/README.md) | Complete file-to-documentation inventory |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Module relationships, command flows, and extension points |
| [docs/DATA_AND_LOGS.md](docs/DATA_AND_LOGS.md) | Output paths, CSV rules, identities, logs, and resume semantics |
| [docs/TESTING.md](docs/TESTING.md) | Running tests, test file map, and live-validation limits |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Network, discovery, and Moodle paging diagnosis |

Every Python source file has an individual reference in `docs/modules/`; every
test file has an individual guide in `docs/tests/`. Configuration and existing
Markdown files are explained in `docs/repository/`.

## Scope and limitations

The implemented export is for **Moodle quiz essay responses**, not every Moodle
activity type or every possible answer format. Selectors and some English/Greek
labels are specific to this site. The browser is currently always headless;
`--keep-open` pauses the process but does not show a browser window. There is no
CLI headed-mode option, automatic grade calculation, combined grading dashboard,
or option to overwrite already graded responses.

Runtime credentials require Windows Python; parser and mocked workflow tests can
run on other systems. The repository has no CI workflow at this snapshot. See
[testing](docs/TESTING.md) before treating offline tests as live Moodle validation.
