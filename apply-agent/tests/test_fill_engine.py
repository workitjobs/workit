"""The Fill engine's loader on its own: what Apply asks of the engine with no page open."""

import json
from datetime import date

import pytest
from conftest import APPLY, FIXTURES, FORMS

from apply import essays, fill_engine
from apply.answer_bank import AnswerBank
from apply.model import FillError, Outcome, Posting, Question, Status, host_company
from apply.profile import ApplicantProfile
from apply.tracker import FileTracker, Row

PROFILE = ApplicantProfile.load(FIXTURES / "planner-profile.yaml", APPLY / "policies.default.yaml")
POSTING = Posting("p", "Acme", "Software Engineer Intern", "https://job-boards.greenhouse.io/acme/jobs/1")


def test_the_postings_text_is_read_only_when_the_engine_asks_for_it():
    reads = []

    def posting_text():
        reads.append(1)
        return "The pay is $30 to $40 an hour."

    fill_engine.plan([Question("q1", "First Name", "text", True)], POSTING, PROFILE, posting_text=posting_text)
    assert reads == []
    pay = Question("q2", "What hourly rate do you expect?", "text", True)
    fill_engine.plan([pay], POSTING, PROFILE, posting_text=posting_text)
    assert reads == [1]


def test_a_workday_try_list_answer_is_shown_by_whichever_of_its_wordings_the_page_shows():
    # How Did You Hear About Us? is never read on Workday: it is answered with sources to search for in turn.
    posting = Posting("w", "Acme", "Intern", "https://acme.wd1.myworkdayjobs.com/en-US/careers/job/Intern_R1")
    heard = Question("q1", "How Did You Hear About Us?", "select", True)
    planned = fill_engine.plan([heard], posting, PROFILE)
    tries = planned.answers["q1"].split("|")

    assert len(tries) > 1
    assert fill_engine.readback_problems([heard], planned.answers, {"q1": tries[1].title()}, planned.accepted) == []
    assert fill_engine.readback_problems([heard], planned.answers, {"q1": "Somewhere else"}, planned.accepted)


def test_a_workday_answer_with_a_bar_that_is_no_try_list_must_show_whole(tmp_path):
    # Only the how-heard plan is a try-list; any other answer that holds a "|" is meant as it is.
    posting = Posting("w", "Acme", "Intern", "https://acme.wd1.myworkdayjobs.com/en-US/careers/job/Intern_R1")
    shell = Question("q1", "Which shell do you use?", "text", True)
    bank = AnswerBank(tmp_path / "answer-bank.yaml")
    bank.add(shell, "zsh|bash", "Acme", date(2026, 11, 2))
    planned = fill_engine.plan([shell], posting, PROFILE, bank)

    assert planned.answers["q1"] == "zsh|bash"
    assert "q1" not in planned.accepted
    assert fill_engine.readback_problems([shell], planned.answers, {"q1": "bash"}, planned.accepted)


def test_an_engine_error_comes_back_as_apply_own():
    try:
        fill_engine.call_without_page("parseQuestions", "bamboohr", "")
    except FillError as error:
        assert str(error) == "the engine has no parser for bamboohr"
    else:
        raise AssertionError("no FillError")


def test_an_essay_on_a_job_system_the_policies_name_holds_its_application():
    # The real policies name Ashby: the engine must read the Posting's link as Ashby's.
    essay = Question("q1", "Tell us about a project you are proud of.", "textarea", True)
    ashby = Posting("p", "Acme", "Intern", "https://jobs.ashbyhq.com/acme/00000000-0000-0000-0000-000000000000")
    assert fill_engine.plan([essay], ashby, PROFILE).high_stakes == [essay]


class Site:
    """A JobSite's fetch over saved answers, recording what was asked."""

    def __init__(self, answers):
        self.answers, self.asked = answers, []

    def fetch(self, url, body=None):
        self.asked.append((url, body and json.loads(body)["operationName"]))
        if url not in self.answers:
            raise LookupError(f"nothing saved at {url}")
        return self.answers[url].encode()


def test_a_jobs_question_set_and_names_are_fetched_through_the_sites_fetch():
    url = "https://jobs.ashbyhq.com/semgrep/1b1e3e7c-c19e-4cd0-9e8b-8d5c09a6d8e0/application"
    graphql = "https://jobs.ashbyhq.com/api/non-user-graphql"
    site = Site({f"{graphql}?op=ApiJobPosting": (FORMS / "ashby-semgrep" / "questions.json").read_text(),
                 f"{graphql}?op=ApiOrganizationFromHostedJobsPageName": '{"data": {"organization": {"name": "Semgrep"}}}'})

    questions = fill_engine.fetched_question_set(url, site)
    company, title = fill_engine.job_names(url, site)

    assert [q.label for q in questions][:2] == ["Name", "Email"] and company == "Semgrep" and title
    assert site.asked[0] == (f"{graphql}?op=ApiJobPosting", "ApiJobPosting")


def test_a_fetch_that_fails_raises_the_sites_own_error():
    with pytest.raises(LookupError, match="nothing saved"):
        fill_engine.job_description("https://apply.workable.com/acme/j/AB12", Site({}))


def test_a_link_the_engine_covers_names_its_job_system_and_form():
    assert fill_engine.job_of("https://explore.jobs.netflix.net/careers/job/790318904468") == {
        "site": "eightfold", "pid": "790318904468", "form": "https://explore.jobs.netflix.net/careers/apply?pid=790318904468", "onForm": False}
    assert fill_engine.job_of("https://example.com/jobs/1") is None


def test_a_host_call_may_call_the_engine_again():
    # The Posting's text is read only when the plan asks, and reading it makes text of HTML with the engine.
    pay = Question("q2", "What hourly rate do you expect?", "text", True)
    planned = fill_engine.plan([pay], POSTING, PROFILE, posting_text=lambda: fill_engine.text_of("<p>The pay is $30 to $40 an hour.</p>"))
    assert pay in planned.missing or planned.answers


def test_the_options_lisul_picked_for_a_missing_multi_select_are_each_ticked():
    profile = ApplicantProfile.load(FIXTURES / "planner-profile.yaml", APPLY / "policies.default.yaml")
    question = Question("q1", "Which offices would you work in?", "multi_select", True, ("Austin", "Boston", "Denver"))
    fill_engine.remember(profile, POSTING, question, "Austin; Denver")  # as the Inbox joins his picks

    assert fill_engine.plan([question], POSTING, profile).answers["q1"] == ["Austin", "Denver"]


def test_a_question_keeps_the_help_text_and_limit_the_engine_reads():
    # the essay call needs them: Figma asks for "3-4 sentences" only in a description
    found = {"name": "q1", "label": "Why Figma?", "kind": "textarea", "required": True, "options": [],
             "description": "Please answer in 3-4 sentences.", "maxLength": 1500}
    [question] = fill_engine.question_set([found])
    assert (question.description, question.max_length) == ("Please answer in 3-4 sentences.", 1500)
    [bare] = fill_engine.question_set([{k: v for k, v in found.items() if k not in ("description", "maxLength")}])
    assert (bare.description, bare.max_length) == ("", None)


def engine_bundle(**env):
    """The bundle a fresh Apply process loads, with the given environment."""
    import os
    import subprocess
    import sys
    code = "from apply.fill_engine import ENGINE; print(ENGINE)"
    run = subprocess.run([sys.executable, "-c", code], env={**os.environ, **env}, capture_output=True, text=True, check=True)
    return run.stdout.strip()


def test_apply_loads_the_extensions_engine_from_the_workit_checkout():
    bundle = engine_bundle(APPLY_FILL_ENGINE="")
    assert bundle == str(APPLY.resolve().parent / "autofiller_extension" / "fill-engine" / "dist" / "engine.js")
    assert fill_engine.ENGINE.is_file()


def test_apply_fill_engine_points_apply_at_another_engine_checkout(tmp_path):
    assert engine_bundle(APPLY_FILL_ENGINE=str(tmp_path)) == str(tmp_path / "dist" / "engine.js")


def test_apply_fill_engine_may_start_at_the_home_folder(tmp_path):
    assert engine_bundle(APPLY_FILL_ENGINE="~/fill-engine", HOME=str(tmp_path)) == str(tmp_path / "fill-engine" / "dist" / "engine.js")


def test_past_applications_and_interviews_at_the_company_come_from_the_tracker_too():
    # Rocket Lab's "Have you previously interviewed at Rocket Lab?" (live, 2026-11-04) went to Lisul.
    rocket_lab = Posting("r", "Rocket Lab", "Software Engineering Intern", "https://job-boards.greenhouse.io/rocketlab/jobs/2")
    asks = [Question("q1", "Have you previously applied to Rocket Lab?", "select", True, ("Yes", "No")),
            Question("q2", "Have you previously interviewed at Rocket Lab?", "select", True, ("Yes", "No"))]
    plan = lambda: fill_engine.plan(asks, rocket_lab, PROFILE).answers
    assert plan() == {"q1": "No", "q2": "No"}
    rows = FileTracker()
    # This Posting's own row is not a past application.
    rows.add(Row("a1", "Rocket Lab", "Intern", rocket_lab.url, "greenhouse", Status.SUBMITTED))
    rows.add(Row("a2", "Rocket Lab", "Intern", "https://job-boards.greenhouse.io/rocketlab/jobs/1", "greenhouse", Status.HELD))
    assert plan() == {"q1": "No", "q2": "No"}
    # An earlier one sent: applied, and an interview there is Lisul's to say...
    rows.update("a2", status=Status.SUBMITTED)
    assert plan() == {"q1": "Yes"}
    # ...till his Outcome records one.
    rows.edit_as_lisul("a2", outcome=Outcome.INTERVIEW)
    assert plan() == {"q1": "Yes", "q2": "Yes"}


def test_the_pre_submit_review_reads_the_past_applications_the_plan_answered_from():
    # amazon.jobs (live 2026-11-10, KAN-753): the plan said Yes to "previously applied to Amazon?" from the Tracker, and
    # the review, shown a profile with previously_applied_to empty, called it wrong. The link names no company:
    # Apply names it from the host, and the Tracker's row is named so too.
    amazon = Posting("a", host_company("https://www.amazon.jobs/en/jobs/2/intern"), "Intern", "https://www.amazon.jobs/en/jobs/2/intern")
    asked = Question("q1", "Have you previously applied to Amazon or any Amazon subsidiary or affiliate?", "select", False, ("Yes", "No"))
    FileTracker().add(Row("a1", "Amazon", "Intern", "https://www.amazon.jobs/en/jobs/1/intern", "amazon", Status.SUBMITTED))

    assert fill_engine.plan([asked], amazon, PROFILE).answers == {"q1": "Yes"}
    shown = json.loads(essays.profile_block(PROFILE, amazon).removeprefix("<profile>\n").removesuffix("\n</profile>\n"))
    assert shown["screeners"]["previously_applied_to"] == ["Amazon"]
    assert "Amazon" in essays.sources(PROFILE, facts=True, posting=amazon)
    # Without the Posting, the profile as it is: the Tracker's join is for the Application being checked.
    assert '"previously_applied_to": []' in essays.profile_block(PROFILE)
    # The profile itself is never changed.
    assert PROFILE.get("screeners.previously_applied_to") == []


def test_a_changed_bundle_on_disk_is_reloaded_before_the_next_posting(tmp_path, monkeypatch):
    # The long-lived Node read the bundle once; a merged engine fix must not need a restart (KAN-645).
    bundle = tmp_path / "engine.js"
    bundle.write_bytes(fill_engine.ENGINE.read_bytes())
    monkeypatch.setattr(fill_engine, "ENGINE", bundle)
    monkeypatch.setattr(fill_engine, "_nodes", {})
    monkeypatch.setattr(fill_engine, "_loaded", {})
    assert fill_engine.text_of("<p>one</p>") == "one"
    node = fill_engine._nodes[0]
    assert not fill_engine.fresh()  # nothing changed: the same Node
    bundle.write_bytes(bundle.read_bytes() + b"\nFillEngine.reloadedForTest = true;\n")
    assert fill_engine.fresh()
    assert node.poll() is not None and 0 not in fill_engine._nodes
    assert fill_engine.call_without_page("textOf", "<p>two</p>") == "two"
    assert fill_engine._nodes[0] is not node


def test_amds_icims_profile_dates_title_phone_type_and_graduation_are_planned_from_the_right_facts():
    # AMD's iCIMS Candidate Profile (rehearsal 2026-11-06, KAN-700): the job's split Start Year got the internship's
    # start as a full date, Title a banked "Mr.", and Phones: Type and Did You Graduate? were Missing facts.
    profile = ApplicantProfile.load(FIXTURES / "planner-profile.yaml", APPLY / "policies.default.yaml")
    profile.set("experience_facts.employment_history",
                [{"employer": "Acme Rail", "title": "Software Engineer Intern", "start": "2026-06", "end": "2026-08"}])
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    days = tuple(str(d) for d in range(1, 32))
    questions = [Question("q6", "Phones: Type", "select", True, ("Mobile",)),
                 Question("q21", "Did You Graduate?", "select", False, ("In Progress", "Not Received", "Received")),
                 Question("q25", "Employer", "text"),
                 Question("q27", "Work Experience: Region (State, Province, County)", "select"),
                 Question("q28", "Title", "text"),
                 Question("q29", "Start Date (Month / Day / Year): Month", "select", False, months),
                 Question("q30", "Start Date (Month / Day / Year): Day", "select", False, days),
                 Question("q31", "Start Date (Month / Day / Year): Year", "text")]
    bank = AnswerBank()
    bank.answer("Title", "Mr.", date(2026, 11, 5))
    planned = fill_engine.plan(questions, POSTING, profile, bank, today=date(2026, 11, 6))
    assert [planned.answers.get(n) for n in ("q6", "q21", "q28", "q29", "q30", "q31")] == [
        "Mobile", "In Progress", "Software Engineer Intern", "Jun", None, "2026"]
    assert "q30" in planned.blanks

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")


def _tal_education(section: str) -> list[Question]:
    # Bank of America's TAL.net (live 2026-11-05, KAN-685): the step's Start date, read as two selects, came to
    # the Question set after the previous step's role ranking, so the questions before it were a job's words.
    return [Question("q1", "Role preference: Software Engineer", "select", True, ("1st choice", "2nd choice")),
            Question("q2", "Role preference: Mainframe Analyst", "select", True, ("1st choice", "2nd choice")),
            Question("q3", "Start date: Month", "select", True, MONTHS, section=section),
            Question("q4", "Start date: Year", "select", True, tuple(str(y) for y in range(1925, 2037)), section=section)]


def test_a_bare_start_date_under_the_steps_education_heading_is_the_degrees_start(tmp_path):
    started = ApplicantProfile({**PROFILE._facts, "education": {**PROFILE._facts["education"], "start_date": "2024-08"}},
                               tmp_path, PROFILE._policies)
    under = fill_engine.plan(_tal_education("current / most recent university education"), POSTING, started)
    assert (under.answers.get("q3"), under.answers.get("q4")) == ("August", "2024")
    # Without its heading the questions before it decide, and "Role preference" reads as a job's: left to ask.
    bare = fill_engine.plan(_tal_education(""), POSTING, started)
    assert (bare.answers.get("q3"), bare.answers.get("q4")) == (None, None)


JPM = Posting("210773869", "JPMorgan Chase", "Analyst",
              "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210773869")


def test_a_file_or_a_path_on_this_mac_never_goes_into_a_field_that_is_no_upload(monkeypatch):
    # KAN-785: JPMorgan's Oracle form got the resume's path in its "Resume or Additional Documents Link 1" box.
    link = Question("q1", "Resume or Additional Documents Link 1", "text", False)
    note = Question("q2", "Anything else?", "textarea", False)
    upload = Question("q3", "Resume", "file", True)
    real = fill_engine.call_without_page

    def planned(name, *args, **kwargs):
        result = real(name, *args, **kwargs)
        if name == "plan":
            result["answers"] |= {"q1": {"file": "/Users/someone/Resume.pdf"}, "q2": "~/Documents/Resume.pdf",
                                  "q3": {"file": "/Users/someone/Resume.pdf"}}
        return result

    monkeypatch.setattr(fill_engine, "call_without_page", planned)
    plan = fill_engine.plan([link, note, upload], JPM, PROFILE)

    assert plan.answers == {"q3": fill_engine.Path("/Users/someone/Resume.pdf")}
    assert plan.blanks["q1"] == plan.blanks["q2"] == fill_engine.LOCAL_PATH


def test_jpmorgans_documents_get_the_resume_only_in_its_slot_and_a_link_in_link_1():
    # KAN-785, on the engine Apply loads: the cover letter slot is the cover_letter policy's, Link 1 the portfolio.
    questions = [Question("r", "Resume or Additional Documents: Resume", "file", True),
                 Question("c", "Resume or Additional Documents: Cover Letter", "file", False),
                 Question("l", "Resume or Additional Documents Link 1", "text", False)]
    plan = fill_engine.plan(questions, JPM, PROFILE)

    assert isinstance(plan.answers["r"], fill_engine.Path)
    assert "c" not in plan.answers and plan.answers["l"] == "https://test-person.example.com"
