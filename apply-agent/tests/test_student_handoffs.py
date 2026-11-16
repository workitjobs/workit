"""The Student build hands the student what Apply can't do, in the Apply window (KAN-855, W2 step 1): a form with no
Filler is held for them to fill, a field the form didn't take is a Needs-you item with its planned answer, and their
answer goes in by the Fill engine, with no model. Chromium on the fake job sites: run on a Mac, not in CI."""

from contextlib import contextmanager

import pytest
from conftest import ARC_FORM, ARC_URL
from fake_bamboohr import FakeBambooServer
from fakes import FakeClaude, FakeJobServer, RecordingBoard
from test_claude_fill import LUNAR_FORM, LUNAR_URL
from test_rehearse import NeverSubmits, adapters, rehearse
from test_run_answers import profile_with

from apply import build, rehearsal, rescue
from apply.fillers import FILLERS
from apply.greenhouse import GreenhouseFiller
from apply.model import FillError
from apply.profile import ApplicantProfile


@pytest.fixture(autouse=True)
def student_build(monkeypatch):
    monkeypatch.setattr(build, "STUDENT", True)
    monkeypatch.setattr(rescue.Rescue, "field", lambda *a, **k: pytest.fail("a model filled a field in the Student build"))


def keeping(server):
    """`server`, with each page it opens kept in `pages`, so the test closes it as the student would."""
    pages = []
    opened = server.open

    @contextmanager
    def open(url, worker=0):
        with opened(url, worker) as page:
            pages.append(page)
            yield page
    server.open = open
    return pages


def test_a_form_apply_has_no_filler_for_is_filled_by_the_generic_filler_with_no_model_driving(tmp_path):
    """KAN-861 (W2 step 2): a BambooHR form, a job system with no Filler, is read and filled by code. Nothing is sent,
    no model drives the page (the fixture fails Rescue's), and what it can't fill is the student's."""
    claude = FakeClaude()
    claude.drive = lambda **_: pytest.fail("a model drove the page in the Student build")
    with FakeBambooServer(LUNAR_FORM) as server:
        [done] = rehearse([LUNAR_URL], server, profile_with(tmp_path), claude=claude)
    assert done.outcome != "handoff" or "can't fill" not in done.why, done.why
    assert done.filled >= 8, (done.outcome, done.why, done.filled, done.asked)
    assert server.submissions == []


class FailsEmailOnce(NeverSubmits):
    """Greenhouse's Filler, but its first fill fails on Email, as the engine fails on a field it can't fill."""

    failed = False

    def fill(self, page, questions, answers):
        email = next(q.name for q in questions if q.label.strip() == "Email")
        if email in answers and not self.failed:
            self.failed = True
            raise FillError("Email: the field took no text")
        return self._filler.fill(page, questions, answers)


def test_a_field_the_form_didnt_take_is_a_needs_you_item_with_its_answer_and_the_engine_fills_it_again(
        monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", FailsEmailOnce(GreenhouseFiller()))
    turns = []

    class Board(RecordingBoard):
        def answered(self, worker):  # the held page's turns: the second comes after its left-behind answer went in
            turns.append(dict(self.captions[worker]))
            if len(turns) == 2 and pages:
                pages.pop().close()
            return []

    board, lines = Board(), []
    with FakeJobServer(ARC_FORM) as fake:
        pages = keeping(fake)
        rehearsal.rehearse([ARC_URL], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)), 1,
                           keep_open=True, out=lines.append)

    assert "Email" in turns[0]["missing"] and turns[0]["planned"]["Email"]  # a Needs-you item, with what Apply planned
    assert "Email" not in board.captions[0]["missing"]  # the Fill engine put it in on the held form
    assert any("filled 'Email' with your answer" in line for line in lines), lines
    assert fake.submissions == []


def test_an_answer_given_in_the_app_is_filled_into_the_held_form_by_the_fill_engine(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    profile = profile_with(tmp_path, **{"identity.email": None, "identity.legal_last_name": None})

    class Board(RecordingBoard):
        given = [("Email", "lisul@example.com")]

        def answered(self, worker):
            given, self.given = self.given, []
            if not given and "Email" not in self.captions[worker].get("missing", ["Email"]) and pages:
                pages.pop().close()  # it went in: the student closes the form
            return given

    board, lines = Board(), []
    with FakeJobServer(ARC_FORM) as fake:
        pages = keeping(fake)
        rehearsal.rehearse([ARC_URL], adapters(fake, board=board), ApplicantProfile.load(profile), 1,
                           keep_open=True, out=lines.append)

    assert board.captions[0]["missing"] == ["Last Name"]  # what is still left blank
    assert any("filled 'Email' with your answer" in line for line in lines), lines
    assert fake.submissions == []
