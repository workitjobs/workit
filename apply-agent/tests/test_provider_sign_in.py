"""A provider sign-in in the way of a Claude fill form (KAN-763): Microsoft Careers' Apply now opens a window that
offers "Sign in using Google" (Microsoft, LinkedIn, Facebook). The stop there is a Needs sign-in pause, and the
rehearsal goes on by itself once the applicant has signed in on the page, with no Resume. Apply presses no
provider button and sends nothing. On the fake Microsoft Careers (tests/fake_microsoft.py); opens Chromium."""

import json
import re

from fake_microsoft import APPLY, URL, FakeMicrosoftServer, sign_in
from fakes import FakeClaude, RecordingBoard
from test_rehearse import adapters
from test_resume import handed_pages
from test_run_answers import profile_with

from apply import provider_sign_in, rehearsal, worker
from apply.claude_fill import ClaudeFill
from apply.profile import ApplicantProfile

QUESTIONS = [{"label": label, "kind": "text", "required": True, "options": []}
             for label in ("First Name", "Last Name", "Email")]
# Claude's own words on the live page (2026-11-10): only plain code's read of the page makes it a sign-in.
WHY = ('Clicking "Apply now" opens a Microsoft Careers sign-in window, and the form can\'t be reached without '
       'signing in. The window offers "Sign in using Google" (and Microsoft, LinkedIn and Facebook), so the person '
       "needs to sign in themselves.")


def microsoft_driver(page, schema: dict, prompt: str, files: list) -> dict:
    """Plays Haiku on the fake Microsoft Careers: Apply now on the posting, then the form's questions, or the stop
    at the sign-in window; a fill types each answer and names the button that sends."""
    if "questions" in schema["properties"]:
        if page.get_by_role("button", name="Apply now").is_visible():
            page.get_by_role("button", name="Apply now").click()
            page.wait_for_url(APPLY)
        if page.get_by_role("dialog").is_visible():
            return {"blocked": True, "why": WHY, "questions": []}
        return {"blocked": False, "why": "", "questions": QUESTIONS}
    fields = json.loads(re.search(r"<fields>(.*?)</fields>", prompt, re.DOTALL)[1])
    for field in fields:
        page.get_by_label(field["question"], exact=True).fill(field["answer"])
    return {"blocked": False, "why": "", "submit_button": "Submit application",
            "filled": [{"field": f["field"], "shown": [f["answer"]]} for f in fields]}


def test_the_page_reads_as_a_provider_sign_in_until_the_account_menu_shows():
    with FakeMicrosoftServer() as server, server.open(URL) as page:
        assert provider_sign_in.shows(page) == [] and not provider_sign_in.signed_in(page)  # "Sign in" in its header
        page.get_by_role("button", name="Apply now").click()
        page.wait_for_url(APPLY)
        assert provider_sign_in.shows(page) == ["Google", "Microsoft", "LinkedIn", "Facebook"]
        assert not provider_sign_in.signed_in(page)
        sign_in(page)
        assert provider_sign_in.shows(page) == [] and provider_sign_in.signed_in(page)
    assert server.provider_opened == [] and server.submissions == []


def test_a_claude_fill_stop_at_a_provider_sign_in_goes_on_by_itself_once_signed_in(monkeypatch, tmp_path):
    handed = handed_pages(monkeypatch)

    class Lisul(RecordingBoard):
        turns, paused = 0, {}

        def resumed(self, worker):
            return False  # he never presses Resume

        def answered(self, worker):  # each turn of the held page, on its own thread
            if not handed or handed[-1].is_closed():
                return []
            page, self.turns = handed[-1], self.turns + 1
            caption = self.captions[worker]
            if "Went on by itself" in " ".join(caption.get("history") or []) and caption.get("status") != "filling" \
                    or self.turns > 40:
                page.close()
            elif self.turns == 2:
                self.paused = dict(caption)
                sign_in(page)  # in the provider's own window, then the apply page reloads signed in
            return []

    board, lines = Lisul(), []
    with FakeMicrosoftServer() as server:
        [first] = rehearsal.rehearse([URL], adapters(server, FakeClaude(driver=microsoft_driver), board=board),
                                     ApplicantProfile.load(profile_with(tmp_path)), 1, keep_open=True,
                                     out=lines.append)

    # Paused as a sign-in, not as Claude's free-text handoff, with Resume offered.
    assert first.outcome == rehearsal.SIGN_IN and "asks you to sign in (Google, Microsoft, LinkedIn, Facebook)" in first.why
    assert board.paused["status"] == rehearsal.SIGN_IN and board.paused["resume"] == {"ok": True}
    history = board.captions[0]["history"]
    assert [h.split(" ", 1)[1].split(":")[0] for h in history][:2] == ["Paused", "Went on by itself"], history
    # With no Resume, the form was read again and filled to its last page; nothing pressed a provider or sent it.
    assert board.captions[0]["status"] == "ready to submit", board.captions[0].get("why")
    assert server.provider_opened == [] and server.submissions == []
    assert len({id(page) for page in handed}) <= 2


def test_a_claude_fill_stop_with_no_provider_sign_in_keeps_no_signed_in_check():
    class Said:
        def drive(self, **_):
            raise AssertionError("not driven")

    fill = ClaudeFill(Said())
    assert fill.signed_in is None and worker.ResumeCheck(fill).signed_in is None
    fill._at_provider = True  # the last drive stopped at a provider sign-in
    assert worker.ResumeCheck(fill).signed_in is provider_sign_in.signed_in
