"""The Recording brief (apply.recording): what to say in a video the student records for a link question,
one bullet for each prompt the Posting lists, each with true points that quote the Story bank."""

from datetime import date

from conftest import FIXTURES, POLICIES
from fakes import FakeClaude

from apply import recording
from apply.adapters import ClaudeError
from apply.model import Posting, Question, Status
from apply.profile import ApplicantProfile
from apply.records import Filled, Record, record_files

OPENSESAME = Posting("os", "OpenSesame", "Software Engineering Internship", "https://job-boards.greenhouse.io/opensesame/jobs/1")
LINK = Question("question_1", "Please include a shareable YouTube link to your Creative Project submission (required). "
                "Your project should answer the Creative Project questions listed in the job description and be "
                "accessible to anyone with the link.", "textarea", True)
HELD = "I use AI tools as a guide, not as the author."  # a line the tests' Story bank holds


class Briefing(FakeClaude):
    """A Claude whose `recording.brief` gives `points`, or raises `fails`."""

    def __init__(self, points: dict | None = None, fails: bool = False):
        super().__init__()
        self._points, self._fails = points or {}, fails

    def ask_kind(self, kind: str, data: dict) -> dict:
        if kind != "recording.brief":
            return super().ask_kind(kind, data)
        self.kinds.append({"kind": kind, "data": data})
        if self._fails:
            raise ClaudeError("down")
        return {"points": self._points}


def profile() -> ApplicantProfile:
    return ApplicantProfile.load(FIXTURES / "planner-profile.yaml", POLICIES)


def text() -> str:
    return (FIXTURES / "opensesame-description.txt").read_text()


def test_a_brief_has_a_bullet_for_each_listed_prompt_and_keeps_only_points_the_story_bank_holds():
    claude = Briefing({"p3": [{"say": "Checking an agent's code against the tests", "quote": HELD},
                              {"say": "An invented win", "quote": "I shipped an AI tutor used by a million learners."}]})

    brief = recording.brief(claude, OPENSESAME, LINK, profile(), text())

    [asked] = claude.kinds
    assert list(asked["data"]["prompts"].values()) == [prompt for prompt, _ in brief.prompts]
    assert "<asked_in_description>" in asked["data"]["posting"]
    shown = brief.shown()
    assert shown.startswith("Recording brief: cover each prompt")
    assert "- Show us something you've built with AI." in shown
    assert "  - Checking an agent's code against the tests" in shown
    assert "invented" not in shown
    assert shown.count("(nothing in your Story bank yet: your own point)") == len(brief.prompts) - 1


def test_a_failed_call_still_gives_the_prompts_with_a_note():
    brief = recording.brief(Briefing(fails=True), OPENSESAME, LINK, profile(), text())

    assert brief.prompts and all(points == () for _, points in brief.prompts)
    assert "model call failed" in brief.shown()


def test_no_brief_when_the_posting_lists_no_prompts():
    claude = Briefing()
    assert recording.brief(claude, OPENSESAME, LINK, profile(), "We build learning software. Apply today.") is None
    assert claude.kinds == []


def test_the_records_readme_shows_each_brief_under_its_question():
    brief = recording.Brief(LINK.label, (("Show us something you've built with AI.", ("Checking an agent's code",)),))
    record = Record(OPENSESAME, Status.HELD, "", Filled([LINK], {}, {}, b"png"), date(2026, 11, 26),
                    briefs=((LINK.label, brief.shown()),))

    readme = record_files(record)["README.md"].decode()

    assert "## Recording briefs" in readme
    assert f"### {LINK.label}" in readme
    assert "  - Checking an agent's code" in readme
