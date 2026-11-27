"""The Lever Filler: has the Fill engine (apply.fill_engine) read a Posting's
Question set from its /apply page's HTML, fill the form, attach the one-pager
and read every field back. Submitting stays here.
"""

import re

from playwright.sync_api import Page

from apply import fill_engine
from apply.adapters import JobSite
from apply.confirmation import wait_for_confirmation
from apply.model import Answers, QuestionSet, Readback


class LeverFiller:
    def form_url(self, url: str) -> str:
        """The /apply page, where the form is: a posting link without /apply opens the job's
        description, which has no form (Hermeus's, live: "the form never finished loading")."""
        return (fill_engine.job_of(url) or {}).get("form") or url

    def question_set(self, url: str, site: JobSite) -> QuestionSet:
        return fill_engine.fetched_question_set(url, site)

    def fill(self, page: Page, questions: QuestionSet, answers: Answers) -> Readback:
        return fill_engine.fill(page, "lever", questions, answers)

    def submit(self, page: Page) -> None:
        page.get_by_role("button", name="Submit application").click()
        # Lever's "There was an error verifying your application", when its invisible hCaptcha turns the sent form
        # down, is a bot block (apply.captcha.BLOCKS): wait_for_confirmation raises it.
        wait_for_confirmation(page, lambda: confirmed(page))


# Lever's application form. A page that still has it was never sent on: refused in the page, sending, or a captcha.
FORM = "form#application-form"
# A heading or title that says the application went in. Lever's own /thanks says "Application submitted!"; a company
# can send the browser to a page of its own instead (Zoox's "Application Received!", live 2026-11-26, whose
# confirmation email came while the tile said it may not have gone in).
THANKS = re.compile(r"application (has been |was )?(submitted|received)|thank(s| you) for (applying|your application)",
                    re.IGNORECASE)


def confirmed(page: Page) -> bool:
    """Whether Lever shows its page for a submitted application (its /thanks link), or the page a company has Lever
    send the browser to after the submit: no application form on it, and a title or heading that says it went in."""
    try:
        if page.url.split("#")[0].split("?")[0].rstrip("/").endswith("/thanks"):
            return True
        if page.locator(FORM).count():
            return False
        return bool(THANKS.search(page.title())) or page.locator("h1, h2, h3, h4").filter(has_text=THANKS).first.is_visible()
    except Exception:
        return False  # a page loading, or gone

