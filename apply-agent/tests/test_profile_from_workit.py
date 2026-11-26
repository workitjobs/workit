"""WorkIt Auto Apply's profile is WorkIt's (W11): read at each Start, its files with it, and what the student answers
in Needs you sent back. No profile file and no Test Person: a first launch with neither starts all the same."""

from datetime import date

import pytest

from apply import cli, essays, home, regenerate, student, writing
from apply.adapters import SetupError
from apply.answer_bank import AnswerBank
from apply.model import Question
from apply.profile import ApplicantProfile
from apply.workit import Unreachable

STORY = "# Story bank: Sam\n\n## Sam's own essays\nI built a shelf scanner.\n\n## Acme: Intern (Jun 2026-Aug 2026)\n- Cut the report.\n"


class WorkIt:
    """WorkIt's profile route and file reads, as `apply.workit.WorkIt` answers them."""

    def __init__(self, down: bool = False):
        self.down, self.saved, self.uploaded = down, [], []

    def applicant_profile(self) -> dict:
        if self.down:
            raise Unreachable("api.workitjobs.ai: timed out")
        return {"profile": {"identity": {"legal_first_name": "Sam"}},
                "policies": {"how_heard": {"text": "WorkIt"}, "high_stakes_job_systems": [], "sms_opt_in": False},
                "files": {"resume": {"name": "../Sam_Resume.pdf", "uploaded_resume_id": "r1"}},
                "writing": {"story_bank": STORY, "voice": "Short sentences. No dashes."}}

    def profile_file(self, where: dict) -> bytes:
        return b"%PDF resume " + where["uploaded_resume_id"].encode()

    def save_answered(self, answered: dict, facts: dict, story: list[dict] | None = None) -> None:
        if self.down:
            raise Unreachable("api.workitjobs.ai: timed out")
        self.saved.append((answered, facts) + ((story,) if story else ()))

    def upload_profile(self, profile: dict, story_bank: str, voice: str, story: list[dict]) -> dict:
        self.uploaded.append((profile, story_bank, voice, story))
        return {"facts": 3, "answered": 1, "story": len(story), "samples": 2, "style_card": True}


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
    monkeypatch.setattr(student, "AnswerBank", lambda *_: AnswerBank())
    opened = []
    monkeypatch.setattr(student.app_window, "run", lambda board, start: opened.append(start))

    student.app()

    assert len(opened) == 1  # the window opened, and the patched copy above was never made
    # Until the first Start reads WorkIt's, an empty Story bank, never the data folder's file (a Developer's own).
    assert "<story_bank>\n</story_bank>" in essays.sources(ApplicantProfile({}, tmp_path, {}))


def test_a_start_reads_the_story_bank_and_voice_from_workit_and_leaves_the_data_folders_alone(tmp_path, monkeypatch):
    """Fault: an essay read the data folder's story-bank.md or voice.md (a Developer's own, in `apply app`) in place
    of WorkIt's, or a line a fill added went into that file."""
    monkeypatch.setattr(student, "FILES", tmp_path / "files")
    mine = home.STORY_BANK.read_text()
    profile = ApplicantProfile({}, tmp_path, {}, saver=lambda changes: None)

    student.profile_from_workit(profile, WorkIt())
    essays.remember_fact(f"{essays.ASK}What did the report cut?", "Four minutes to twenty seconds", "Acme",
                         date(2026, 11, 26))

    assert essays.sources(profile).startswith(f"<story_bank>\n{STORY}")
    assert "- What did the report cut? Four minutes to twenty seconds (asked for Acme, 2026-11-26)" in home.story_bank()
    assert writing.style_card() == "Short sentences. No dashes." and "shelf scanner" in writing.samples()
    assert home.STORY_BANK.read_text() == mine


def test_a_line_a_fill_adds_goes_to_workit_and_waits_when_it_doesnt_answer(tmp_path, monkeypatch):
    """Fault: a Story bank line was lost when WorkIt didn't answer, or stopped the fill."""
    monkeypatch.setattr(student, "FILES", tmp_path / "files")
    workit = WorkIt()
    monkeypatch.setattr(student, "WorkIt", lambda: workit)
    profile = ApplicantProfile({}, tmp_path, {}, saver=student.to_workit)
    student.profile_from_workit(profile, workit)
    workit.down = True

    regenerate.keep_context(Question("q1", "Why Acme?", "textarea"), [], "I ride their trains", "Acme",
                            date(2026, 11, 26))
    workit.down = False
    student.profile_from_workit(profile, workit)  # the next Start, with the line still waiting: it is no fact
    assert profile.facts() == {"identity": {"legal_first_name": "Sam"},
                               "files": {"resume_pdf": str(tmp_path / "files" / "Sam_Resume.pdf")}}
    profile.save_answered("Which shift?", "Nights")

    line = '- For "Why Acme?" at Acme: I ride their trains (2026-11-26)'
    assert workit.saved == [({"Which shift?": "Nights"}, {}, [{"section": regenerate.ADDED_SECTION, "line": line}])]


def test_apply_upload_sends_the_data_folders_own_files_and_never_test_persons(monkeypatch, capsys):
    """Fault: `apply upload` left out the Story bank's added lines or the voice, or sent Test Person's sample."""
    workit = WorkIt()
    monkeypatch.setattr(cli.workit, "WorkIt", lambda: workit)
    with pytest.raises(SystemExit, match="Test Person"):
        cli.upload()  # the tests' data folder is Test Person's
    profile = ApplicantProfile.load(cli.DEFAULT_PROFILE)
    profile.set("sample_data", False)
    profile.save()
    home.STORY_BANK.write_text(home.STORY_BANK.read_text() + f"\n{essays.ANSWERED_SECTION}\n- Favorite book? Dune\n")

    cli.upload()

    facts, bank, voice, story = workit.uploaded[0]
    assert facts["identity"]["legal_first_name"] and bank == home.STORY_BANK.read_text()
    assert voice == writing.VOICE.read_text() and story == [{"section": essays.ANSWERED_SECTION,
                                                             "line": "- Favorite book? Dune"}]
    assert "only what it lacked" in capsys.readouterr().out
