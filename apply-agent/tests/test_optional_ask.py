"""An optional question no source answers: left blank, never asked in Needs you nor holding the form (Lisul,
2026-11-26, replacing KAN-759's optional ask). JPMorgan's Oracle form (2026-11-10) left its optional Tax District blank
and listed Address Line 2 and 3 as needing Lisul; Braze's Greenhouse (2026-11-26) asked an "If you chose ..., please
specify" box after a LinkedIn answer. No browser: the engine's plan, the window's routes and fakes."""

import json
import urllib.request
from datetime import date
from pathlib import Path

import yaml
from conftest import FIXTURES
from fakes import FakeClaude

from apply import cli, dashboard, worker
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


def test_tax_district_on_an_ohio_home_is_left_blank_and_never_asked(tmp_path):
    form = planned(profile_at(tmp_path, **(HOME | {"city": "Columbus", "state": "OH"})), rehearse=False)

    assert form.add([CITY, TAX]) is None  # the form goes on
    assert form.missing == () and form.blanks == {"tax": "Optional, and no source of yours has it"}
    [note] = [f for f in form.verify({"city": "Columbus", "tax": ""}, [], ()).flags if f.field == "Tax District"]
    assert note.holds is False and note.why.startswith("left blank on purpose")


def test_an_optional_question_claude_cant_answer_is_left_blank_not_asked(tmp_path):
    asked = Question("q1", "Which robotics competitions have you judged?", "text", False)
    form = worker._Planned(ORACLE, None, ApplicantProfile.load(profile_at(tmp_path, **HOME)),
                           FakeClaude(needs_applicant=["Which robotics"]), {}, None, False, AnswerBank(), date(2026, 11, 10))

    assert form.add([CITY, asked]) is None
    assert form.missing == () and "q1" in form.left and "q1" not in form.answers
    required = worker._Planned(ORACLE, None, ApplicantProfile.load(profile_at(tmp_path, **HOME)),
                               FakeClaude(needs_applicant=["Which robotics"]), {}, None, False, AnswerBank(), date(2026, 11, 10))
    result = required.add([CITY, Question("q1", asked.label, "text", True)])
    assert result is not None and result.missing_fact == asked.label  # a required one is still his


def test_an_if_you_chose_follow_up_to_another_pick_is_left_blank(tmp_path):
    heard = Question("q1", "Which robotics league did you compete in?", "select", True, ("FIRST", "VEX", "Other"))
    specify = Question("q2", "If you chose VEX or Other, please specify here:", "text", False)
    form = worker._Planned(ORACLE, None, ApplicantProfile.load(profile_at(tmp_path, **HOME)),
                           FakeClaude(drafts={"Which robotics": "FIRST"}), {}, None, False, AnswerBank(), date(2026, 11, 10))

    assert form.add([CITY, heard, specify]) is None
    assert form.missing == () and form.answers["q1"] == "FIRST" and "q2" not in form.answers and "q2" in form.left


def test_a_required_missing_fact_still_stops_a_run(tmp_path):
    form = planned(profile_at(tmp_path, **(HOME | {"city": "Columbus", "state": "OH"})), rehearse=False)

    result = form.add([Question("tax", "Tax District", "text", True)])
    assert result is not None and result.missing_fact == "Tax District"


def test_his_skip_is_kept_so_the_next_form_leaves_it_blank_without_asking(tmp_path):
    path = profile_at(tmp_path, **(HOME | {"city": "Columbus", "state": "OH"}))
    tab = AnswersTab(AnswerBank(), path)
    answer = cli._answering(lambda: None, tab)

    said = answer({"status": "ready to submit"}, "Tax District", "")
    assert said.startswith("Skipped") and ApplicantProfile.load(path).get("answered_questions") == {"Tax District": ""}
    form = planned(path, rehearse=True)
    assert form.add([CITY, TAX]) is None and form.missing == ()
    assert form.blanks == {"tax": "Optional, and you chose to leave it blank"}


def test_his_answer_is_kept_so_the_next_form_fills_it(tmp_path):
    path = profile_at(tmp_path, **(HOME | {"city": "Columbus", "state": "OH"}))
    answer = cli._answering(lambda: None, AnswersTab(AnswerBank(), path))

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
