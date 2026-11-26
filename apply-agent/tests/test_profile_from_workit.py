"""WorkIt Auto Apply's profile is WorkIt's (W11): read at each Start, its files with it, and what the student answers
in Needs you sent back. No profile file and no Test Person: a first launch with neither starts all the same."""

import pytest

from apply import essays, student
from apply.adapters import SetupError
from apply.answer_bank import AnswerBank
from apply.profile import ApplicantProfile
from apply.workit import Unreachable


class WorkIt:
    """WorkIt's profile route and file reads, as `apply.workit.WorkIt` answers them."""

    def __init__(self, down: bool = False):
        self.down, self.saved = down, []

    def applicant_profile(self) -> dict:
        if self.down:
            raise Unreachable("api.workitjobs.ai: timed out")
        return {"profile": {"identity": {"legal_first_name": "Sam"}},
                "policies": {"how_heard": {"text": "WorkIt"}, "high_stakes_job_systems": [], "sms_opt_in": False},
                "files": {"resume": {"name": "../Sam_Resume.pdf", "uploaded_resume_id": "r1"}}}

    def profile_file(self, where: dict) -> bytes:
        return b"%PDF resume " + where["uploaded_resume_id"].encode()

    def save_answered(self, answered: dict, facts: dict) -> None:
        if self.down:
            raise Unreachable("api.workitjobs.ai: timed out")
        self.saved.append((answered, facts))


def test_a_start_reads_the_profile_and_its_files_from_workit(tmp_path, monkeypatch):
    """Fault: the profile or its resume came from the Mac, WorkIt's empty list wiped one of Apply's own, or the
    extension's "WorkIt" answered "How did you hear about us?" in place of Apply's own answer."""
    monkeypatch.setattr(student, "FILES", tmp_path / "files")
    profile = ApplicantProfile({}, tmp_path, {"high_stakes_job_systems": ["ashby"], "how_heard": {"text": "Company "
                               "careers page"}, "sms_opt_in": True})

    student.profile_from_workit(profile, WorkIt())

    resume = profile.get("files.resume_pdf")
    assert profile.get("identity.legal_first_name") == "Sam"
    assert resume == tmp_path / "files" / "Sam_Resume.pdf" and resume.read_bytes() == b"%PDF resume r1"  # a name only
    assert profile.policy("sms_opt_in") is False and profile.policy("high_stakes_job_systems") == ["ashby"]
    assert profile.policy("how_heard.text") == "Company careers page"


def test_a_start_workit_doesnt_answer_says_so_and_changes_nothing(tmp_path):
    profile = ApplicantProfile({"identity": {"legal_first_name": "Before"}}, tmp_path, {})

    with pytest.raises(SetupError, match="didn't come from WorkIt"):
        student.profile_from_workit(profile, WorkIt(down=True))
    assert profile.get("identity.legal_first_name") == "Before"


def test_a_needs_you_answer_goes_to_workit_and_waits_there_when_it_doesnt_answer(tmp_path, monkeypatch):
    """Fault: an answer saved into a profile with no file was lost, or a failed send dropped it."""
    workit = WorkIt(down=True)
    monkeypatch.setattr(student, "WorkIt", lambda: workit)
    profile = ApplicantProfile({}, tmp_path, {}, saver=student.to_workit)

    with pytest.raises(Unreachable):
        profile.save_answered("Which shift?", "Nights")
    profile.set("identity.pronouns", "They/them")
    profile.set("files.resume_pdf", "/Users/sam/r.pdf")
    workit.down = False
    profile.save()

    assert workit.saved == [({"Which shift?": "Nights"}, {"identity.pronouns": "They/them"})]  # never a file's path
    student.profile_from_workit(profile, workit)
    assert profile.answered("Which shift?") is None  # sent: WorkIt's profile holds it from now on


def test_a_run_reads_the_profile_after_the_bank_and_before_any_form_opens(tmp_path):
    started = []
    runs = student.Runs(ApplicantProfile({}, tmp_path, {}), AnswerBank(), make=lambda profile, bank: started.append(1),
                        refresh=lambda: (_ for _ in ()).throw(SetupError("Your profile didn't come from WorkIt")))

    with pytest.raises(SetupError, match="profile"):
        runs.run(["https://jobs.lever.co/acme/1"], show=lambda board: None)
    assert started == []


def test_a_first_launch_with_no_profile_and_no_sample_opens(tmp_path, monkeypatch):
    """Fault (found building the app, KAN-833): the app copied Test Person's sample/ into a data folder with no
    profile, and stopped at launch where the build ships no sample/. Without the copy, the first essay stopped
    on a Story bank file that wasn't there."""
    monkeypatch.setattr("apply.home.fill_from_sample", lambda: pytest.fail("Test Person copied"))
    monkeypatch.setattr("apply.home.STORY_BANK", tmp_path / "story-bank.md")
    monkeypatch.setattr(student, "AnswerBank", lambda *_: AnswerBank())
    opened = []
    monkeypatch.setattr(student.app_window, "run", lambda board, start: opened.append(start))

    student.app()

    assert len(opened) == 1  # the window opened, and the patched copy above was never made
    assert "<story_bank>\n</story_bank>" in essays.sources(ApplicantProfile({}, tmp_path, {}))  # empty, not missing
