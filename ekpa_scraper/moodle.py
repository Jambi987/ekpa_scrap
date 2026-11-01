"""Site-specific selectors. Update this adapter when Moodle/theme/plugins change."""
from dataclasses import dataclass

ORIGIN = 'https://lms.elearningekpa.gr'
LOGIN_URL = ORIGIN + '/login/index.php'
DASHBOARD_URL = ORIGIN + '/my/'

@dataclass(frozen=True)
class MoodleSelectors:
    login_form: str = 'form#login'
    username: str = 'input[name="username"]'
    password: str = 'input[name="password"]'
    submit: str = 'button[type="submit"], input[type="submit"]'
    authenticated: str = 'a[href*="/login/logout.php"][href*="sesskey="]'
    grade_block: str = '[data-block="grade_me"], section.block_grade_me'
    course_heading: str = 'dt.cmod'
    course_title: str = 'a.grademe-course-name'
    lesson: str = 'dd.module'
    lesson_title: str = 'a.grademe-mod-name'
    badge: str = '.dd-wrap > .badge'
    entries: str = 'ul.gradable-list > li.gradable'
    results_link: str = 'li[data-key="quiz_report"] a[href*="/mod/quiz/report.php"]'
    report_dropdown: str = 'select[name="jump"]:has(option[value*="mode=grading"])'
    question_table: str = 'table#questionstograde'
    question_name: str = 'td.c2'
    pending_column_title: str = 'Προς βαθμολόγηση'
    total_column_title: str = 'Σύνολο'
    response_mark: str = '.comment input[name$="-mark"]'
    submission: str = 'div.que.essay'
    exercise_text: str = '.qtext'
    attachment_links: str = '.attachments a[href]'
    paging_links: str = '.paging a[href], .pagination a[href]'
    grading_order: str = 'studentlastname'
    report_order_select: str = 'select[name="order"]'

SELECTORS = MoodleSelectors()

class MoodleLayoutError(ValueError):
    """Required site structure is missing or ambiguous; do not report false zeroes."""
