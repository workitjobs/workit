"""An optional question no source answers (KAN-759): asked in Needs you with a Skip, never holding the form, and never
asked when the known facts say it can't exist. JPMorgan's Oracle form (2026-11-10) left its optional Tax District
blank and listed Address Line 2 and 3 as needing Lisul. No browser: the engine's plan, the window's routes and fakes."""

import json
import urllib.request
from datetime import date
from pathlib import Path

import yaml
from conftest import FIXTURES
from fakes import FakeClaude

from apply import cli, dashboard, verify, worker
from apply.answer_bank import AnswerBank
from apply.answers_tab import AnswersTab
from apply.dashboard import Dashboard, NoFrames
from apply.model import Posting, Question
from apply.profile import ApplicantProfile

ORACLE = Posting("210773869", "JPMorgan Chase", "Analyst",
                 "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210773869")
TAX = Question("tax", "Tax District", "text", False)
LINE_2 = Question("l2", "Address Line 2", "text", False)
LINE_3 = Question("l3", "Address Line 3", "text", False)
CITY = Question("city", "City", "text", True)
HOME = {"line1": "1 Main St", "line2": "", "city": "Hicksville", "state": "NY", "zip": "11801", "country": "United States"}


def profile_at(folder: Path, **home) -> Path:
    """The test Applicant profile, with `home` as its home address when given."""
    profile = yaml.safe_load((FIXTURES / "profile.yaml").read_text())
    profile["files"]["resume_pdf"] = str(FIXTURES / "one-pager.pdf")
    if home:
        profile["identity"]["home_address"] = home
    path = folder / "profile.yaml"
    path.write_text(yaml.safe_dump(profile, sort_keys=False))
    (folder / "policies.yaml").write_text((FIXTURES / "policies.yaml").read_text())
    return path


def planned(path: Path, rehearse: bool) -> worker._Planned:
    return worker._Planned(ORACLE, None, ApplicantProfile.load(path), FakeClaude(), {}, None, rehearse, AnswerBank(),
                           date(2026, 11, 10))


def test_tax_district_on_a_new_york_home_is_left_blank_and_never_asked(tmp_path):
    form = planned(profile_at(tmp_path, **HOME), rehearse=True)

    assert form.add([CITY, LINE_2, LINE_3, TAX]) is None
    assert form.missing == ()  # neither Tax District nor the address lines need him
    assert form.blanks == {"l2": "Your home address on file has no line 2", "l3": "Your home address on file has no line 3",
                           "tax": "Your home is in no local tax district"}
    flags = form.verify({"city": "Hicksville", "l2": "", "l3": "", "tax": ""}, [], ()).flags
    assert {f.field for f in flags if f.holds} == set()  # only notes: blank on purpose


def test_tax_district_on_an_ohio_home_is_an_optional_question_with_its_own_flag(tmp_path):
    form = planned(profile_at(tmp_path, **(HOME | {"city": "Columbus", "state": "OH"})), rehearse=True)

    assert form.add([CITY, TAX]) is None  # the form goes on
    assert form.missing == ("Tax District",) and form.required == {"Tax District": False}


def test_an_optional_question_never_stops_a_run_and_verifying_only_notes_it(tmp_path):
    form = planned(profile_at(tmp_path, **(HOME | {"city": "Columbus", "state": "OH"})), rehearse=False)

    assert form.add([CITY, TAX]) is None  # a required Missing fact would be a Result here
    [note] = [f for f in form.verify({"city": "Columbus", "tax": ""}, [], ()).flags if f.field == "Tax District"]
    assert (note.why, note.holds) == (verify.OPTIONAL_UNANSWERED, False)


def test_a_required_missing_fact_still_stops_a_run(tmp_path):
    form = planned(profile_at(tmp_path, **(HOME | {"city": "Columbus", "state": "OH"})), rehearse=False)

    result = form.add([Question("tax", "Tax District", "text", True)])
    assert result is not None and result.missing_fact == "Tax District"


def test_his_skip_is_kept_so_the_next_form_leaves_it_blank_without_asking(tmp_path):
    path = profile_at(tmp_path, **(HOME | {"city": "Columbus", "state": "OH"}))
    tab = AnswersTab(AnswerBank(tmp_path / "answer-bank.yaml"), path)
    answer = cli._answering(lambda: None, tab)

    said = answer({"status": "ready to submit"}, "Tax District", "")
    assert said.startswith("Skipped") and ApplicantProfile.load(path).get("answered_questions") == {"Tax District": ""}
    form = planned(path, rehearse=True)
    assert form.add([CITY, TAX]) is None and form.missing == ()
    assert form.blanks == {"tax": "Optional, and you chose to leave it blank"}


def test_his_answer_is_kept_so_the_next_form_fills_it(tmp_path):
    path = profile_at(tmp_path, **(HOME | {"city": "Columbus", "state": "OH"}))
    answer = cli._answering(lambda: None, AnswersTab(AnswerBank(tmp_path / "answer-bank.yaml"), path))

    answer({"status": "ready to submit"}, "Tax District", "Columbus CSD")
    form = planned(path, rehearse=True)
    assert form.add([CITY, TAX]) is None and form.missing == () and form.answers["tax"] == "Columbus CSD"


def test_an_optional_question_alone_asks_with_a_skip_and_is_not_a_missing_fact():
    caption = {"status": "ready to submit", "missing": ["Tax District"], "required": {"Tax District": False}}
    shown = dashboard.verdict(caption)
    assert (shown["kind"], shown["do"], shown["why"], shown["optional"]) == \
        ("missing fact", dashboard.OPTIONAL_ASK, "Tax District", ["Tax District"])

    both = dashboard.verdict(caption | {"missing": ["Pronouns", "Tax District"],
                                        "required": {"Pronouns": True, "Tax District": False}})
    assert (both["do"], both["why"]) == ("Answer a question only you know", "Pronouns")


def test_a_skip_from_the_window_reaches_the_save_and_leaves_needs_you():
    saved = []
    with Dashboard(1, NoFrames(), answer=lambda item, q, a: saved.append((q, a)) or "Skipped, and kept.") as board:
        board.update(0, company="JPMorgan Chase", posting_url="https://j.example/1", status="ready to submit",
                     missing=["Tax District"], required={"Tax District": False})
        [item] = board.state()["items"]
        assert item["questions"] == ["Tax District"]
        body = json.dumps({"id": item["id"], "question": "Tax District", "answer": ""}).encode()
        reply = json.loads(urllib.request.urlopen(urllib.request.Request(
            board.url + "/answer", body, {"X-Apply-Token": board.token})).read())

        assert reply["message"] == "Skipped, and kept." and saved == [("Tax District", "")]
        assert board.state()["items"][0]["answered"] is True  # it waits on him no more
