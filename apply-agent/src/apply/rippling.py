"""The Rippling Filler: has the Fill engine (apply.fill_engine) read a
Posting's Question set from its job API (public, no login), opens the form and
has the engine fill it, attach the files and read every
field back. Submitting stays here.

The submit sits behind Cloudflare Turnstile, so the form is always filled in
the page and never posted to the API.
"""

import re

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from apply import fill_engine
from apply.adapters import JobSite
from apply.confirmation import wait_for_confirmation
from apply.model import Answers, FillError, QuestionSet, Readback

FIRST_FIELD = '[data-testid="first_name"]'  # every Rippling form asks it first, after the résumé
# Rippling's notice where its form crashed and shows no fields (seen live 2026-11-27 on Overland AI's:
# "We're experiencing an issue. Check back shortly." beside its errorboundary icon).
CRASHED = '[data-testid="errorboundary-icon"]'
NOTICE = re.compile(r"[^\n]*experiencing an issue[^\n]*", re.IGNORECASE)
FORM_WAIT = 20_000  # ms for the form, or Rippling's notice, to show once its page loads
LOADS = 3  # a crashed form is loaded this many times in all before Apply gives up on it


class RipplingFiller:
    def form_url(self, url: str) -> str:
        """The /apply page, where the form is: the Posting's page shows the role and an "Apply now" link."""
        return (fill_engine.job_of(url) or {}).get("form") or url

    def form_shown(self, page: Page) -> None:
        """Have the form showing before Apply plans or fills it; FillError, in seconds, if it won't."""
        _open_form(page)

    def question_set(self, url: str, site: JobSite) -> QuestionSet:
        return fill_engine.fetched_question_set(url, site)

    def fill(self, page: Page, questions: QuestionSet, answers: Answers) -> Readback:
        _open_form(page)
        return fill_engine.fill(page, "rippling", questions, answers)

    def submit(self, page: Page) -> None:
        page.locator('[data-testid="Apply"]').click()
        wait_for_confirmation(page, lambda: _confirmed(page))


def _open_form(page: Page) -> None:
    """Open the form: the Posting's page shows the role, and its form is one step on. Where
    Rippling's form crashed (its notice in place of the fields), the page is loaded again,
    since nothing is typed in it yet; still crashed, or showing neither, is a FillError at once,
    before any Claude call plans its answers (Overland AI's waited 275 s for the engine's)."""
    if "/apply" not in page.url:
        page.goto(page.url.split("?")[0].rstrip("/") + "/apply?step=application")
    for load in range(LOADS):
        if load:
            page.reload()
        shown = page.locator(f"{FIRST_FIELD}, {CRASHED}").first
        try:
            shown.wait_for(state="attached", timeout=FORM_WAIT)
        except PlaywrightTimeout:
            raise FillError(f"the form never showed (nothing on {page.url} after {FORM_WAIT // 1000} s)") from None
        if page.locator(FIRST_FIELD).count():
            return
    said = NOTICE.search(page.locator("body").inner_text())
    raise FillError(f"the form never showed: Rippling's page says \"{said[0].strip() if said else 'it hit an error'}\""
                    f" after {LOADS} loads; try it again later")


def _confirmed(page: Page) -> bool:
    """Rippling's thanks. Its Turnstile box is a captcha challenge (apply.captcha)."""
    return page.get_by_text("You have successfully applied").count() > 0
