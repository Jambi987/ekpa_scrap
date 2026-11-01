"""Command orchestration and console presentation."""
import argparse
import re
import sys
from .accounts import credential_store, add_account, read_account
from .browser import authenticated_page


def print_lessons(lessons):
    courses = set()
    for index, lesson in enumerate(lessons, 1):
        courses.add(lesson.course_title)
        print(f'\n{index}. {lesson.title}')
        print(f'   Course: {lesson.course_title}')
        print(f'   Exams awaiting correction: {lesson.displayed_count} | Entries beneath lesson: {lesson.listed_entries}')
        if lesson.displayed_count != lesson.listed_entries:
            print('   NOTE: Badge and listed entries differ; the plugin may limit or filter its list.')
    print(f'\nCourses: {len(courses)} | Lessons: {len(lessons)}')
    print(f'Total exams awaiting correction: {sum(x.displayed_count for x in lessons)}')
    print(f'Total entries beneath lessons: {sum(x.listed_entries for x in lessons)}')


def main():
    parser = argparse.ArgumentParser(description='EKPA account login and Grade Me lesson listing')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('add', help='Register an account in Windows Credential Locker')
    for name in ('remove', 'login', 'lessons', 'grading', 'download', 'upload'):
        command = sub.add_parser(name)
        command.add_argument('account', help='Number in profXXlms; preserve leading zeros')
        if name in ('login', 'lessons', 'grading', 'download', 'upload'):
            command.add_argument('--keep-open', action='store_true', help='Keep browser open until Enter')
    for name in ("lessons", "grading", "download", "upload"):
        sub.choices[name].add_argument("--output", default="output", help="Root folder for appended lesson history (default: output)")
    sub.choices['upload'].add_argument('--apply', action='store_true', help='Submit and verify CSV grades/notes; default is preview only')
    sub.choices['upload'].add_argument('--lesson-id', help='Limit to one quiz activity ID, e.g. 557503')
    args = parser.parse_args()
    if args.command != 'add' and not re.fullmatch('[0-9]+', args.account):
        parser.error('Account must contain only digits.')
    try:
        store = credential_store()
        if args.command == 'add':
            add_account(store)
        elif args.command == 'remove':
            store.delete_password('ekpa-lms-scraper-v1', args.account)
            print('Stored account removed.')
        else:
            record = read_account(store, args.account)
            with authenticated_page(record) as page:
                print(f'Login confirmed for account {args.account}.')
                if args.command in ('lessons', 'grading'):
                    from .dashboard import read_dashboard
                    from .storage import append_scan
                    try:
                        lessons = read_dashboard(page)
                    except ValueError:
                        if args.command != 'download':
                            raise
                        from .storage import merge_known_lessons
                        if not merge_known_lessons(args.output, args.account, []):
                            raise
                        print('Dashboard could not be read; refreshing previously saved lessons only.')
                        lessons = []
                    print_lessons(lessons)
                    paths = append_scan(args.output, args.account, lessons)
                    print(f"Appended {len(paths)} lesson records under {args.output}/{args.account}/")
                if args.command == 'grading':
                    from .grading import open_pending_grading
                    try:
                        open_pending_grading(page, lessons)
                    except Exception as exc:
                        print(f'Grading navigation stopped ({type(exc).__name__}). Existing tabs remain open for inspection.')
                        input('Press Enter to close the browser... ')
                        raise
                if args.command == 'download':
                    from .storage import merge_known_lessons
                    from .discovery import discover_all_lessons
                    discovered = discover_all_lessons(page)
                    from .storage import remember_lessons
                    remember_lessons(args.output, args.account, discovered)
                    lessons = merge_known_lessons(args.output, args.account, discovered)
                    print(f'Current and saved quiz/test activities: {len(lessons)}')
                    from .storage import lesson_folder
                    for lesson in lessons:
                        lesson_folder(args.output, args.account, lesson)
                    from .export import export_pending
                    try:
                        export_pending(page, lessons, args.output, args.account)
                    except Exception as exc:
                        print(f'Download stopped ({type(exc).__name__}). Existing files were preserved.')
                        input('Inspect the browser; press Enter to close... ')
                        raise
                if args.command == 'upload':
                    from .grade_upload import upload_grades
                    try:
                        upload_grades(page, args.output, args.account, apply=args.apply, lesson_id=args.lesson_id)
                    except Exception as exc:
                        print(f'Grade upload stopped ({type(exc).__name__}). Inspect Moodle and grade_upload_log.jsonl before retrying.')
                        input('Press Enter to close the browser... ')
                        raise
                if args.command in ('login', 'grading') or args.keep_open:
                    input('Press Enter to close this browser session... ')
        return 0
    except (KeyboardInterrupt, EOFError):
        print('\nStopped.')
        return 1
    except ModuleNotFoundError as exc:
        print(f'Missing Python module: {exc.name}. Install requirements.txt with this interpreter.', file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    except Exception as exc:
        print(f'Operation failed ({type(exc).__name__}). Check the browser, network and Windows credential store. Sensitive call logs are omitted.', file=sys.stderr)
        return 1
