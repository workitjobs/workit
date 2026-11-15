"""Claude writes as the applicant the profile names: every prompt Apply builds
for an Application says the profile's first name and school, never another
applicant's."""

import json

import pytest
from conftest import FIXTURES, POLICIES
from fakes import FakeClaude

from apply import answering, essays, gates, home, presubmit, story_map, writing
from apply.applicant import personal
from apply.model import Posting, Question
from apply.profile import ApplicantProfile

PROFILE = FIXTURES / "planner-profile.yaml"  # Test Person, of Example State University
CLUB = "## Example Robotics Club (Sep 2025-present; C++)"
BUILT = "- Built a line-following robot that placed second of 12 teams at the state contest."
BANK = f"""# Story bank

## How Test writes
Plain sentences, mostly short.

## Test's own answers, word for word
> I like building small tools that help my club run its events, and I like seeing other members use them every week.
> When a robot of ours failed on the day of a contest, I rewrote the turn code that night and we placed second.

## Education
- Example State University, B.S. Computer Science, May 2028.

{CLUB}
{BUILT}

## Skills
- Python, C++
"""
POSTING = Posting("p", "Figma", "Software Engineer Intern", "https://jobs.example.com/1")
WHY = Question("why", "Why do you want to work at Figma?", "textarea", True)
LETTER = Question("cl", "Cover Letter", "file", False)


@pytest.fixture
def test_persons_bank(monkeypatch, tmp_path):
    bank = tmp_path / "story-bank.md"
    bank.write_text(BANK)
    monkeypatch.setattr(home, "STORY_BANK", bank)
    monkeypatch.setattr(writing, "VOICE", tmp_path / "voice.md")  # no style card
    return bank


def written(profile: ApplicantProfile, drafts: tuple[Question, ...] = (), answered: dict | None = None) -> list[dict]:
    """Every call Claude gets while Apply writes a why-company essay and a cover letter (and `drafts`, one-off
    questions, with `answered` the form's other answers)."""
    claude = FakeClaude()

    def ask_kind(kind, data):
        if kind != "essays.plan":
            return FakeClaude.ask_kind(claude, kind, data)
        claude.kinds.append({"kind": kind, "data": data})
        types = answering.load()  # a plan that leads every essay with the club's story
        return {"plan": {key: {"type": (t := asked["type"]), "parts": ["What it asks"], "story": CLUB.removeprefix("## "),
                               "company_fact": "", "angle": "His own robot.", "link_kind": "",
                               "slots": [{"slot": s.name, "quotes": [BUILT.removeprefix("- ")], "ask": ""}
                                         for s in types[t].slots if s.required is True]}
                         for key, asked in data["questions"].items()}}

    claude.ask_kind = ask_kind
    essays.answer(claude, POSTING, [WHY, LETTER], list(drafts), profile, answered=answered)
    return claude.asked  # every essay call is a WorkIt kind (D5)


def said(call: dict) -> str:
    if "kind" in call:
        return json.dumps(call["data"])
    return "\n".join([call["system"], call["prompt"], json.dumps(call["schema"])])


def test_claude_writes_as_test_person_never_as_another_applicant(test_persons_bank):
    calls = written(ApplicantProfile.load(PROFILE, POLICIES))

    assert len(calls) >= 4  # plan, draft, claim check, editor
    for call in calls:
        assert "Lisul" not in said(call) and "Stony Brook" not in said(call)
    draft = next(c for c in calls if c.get("kind") == "essays.write")
    assert draft["data"]["school"] == "Example State University"


def test_every_call_says_the_applicants_own_pronouns(test_persons_bank):
    profile = ApplicantProfile.load(PROFILE, POLICIES)
    profile.set("identity.pronouns", "they/them/theirs")

    calls = written(profile)

    for call in calls:
        if "kind" in call:  # WorkIt adds the note from the pronouns the kind goes with
            assert call["data"]["pronouns"] == "they/them/theirs"
        else:
            assert "Test's pronouns are they/them/theirs." in call["system"]


def test_test_persons_own_answers_are_the_samples_of_his_voice(test_persons_bank):
    assert "I rewrote the turn code that night" in writing.samples()


def test_a_company_named_only_in_test_persons_past_answers_is_still_a_leftover(monkeypatch, tmp_path):
    briefs = tmp_path / "company-briefs"
    briefs.mkdir()
    (briefs / "notion.md").write_text("# Notion\n")
    monkeypatch.setattr(gates, "BRIEFS", briefs)
    bank = "## Test's own answers, word for word\nNotion, \"Why Notion?\": I use it daily.\n\n## Education\n- A school.\n"
    assert gates.other_companies("I would bring this to Notion.", "Figma", bank) == ["names another company: Notion"]


def test_test_persons_story_areas_come_from_his_bank_headings():
    assert story_map.episodes(BANK) == [("- Example State University, B.S. Computer Science, May 2028.", "education"),
                                        (BUILT, "example-robotics-club")]


def test_a_kind_goes_with_the_pronouns_and_school_and_its_answer_gets_the_name_back(tmp_path):
    from apply.applicant import as_applicant

    class Kinds:
        def __init__(self):
            self.sent = []

        def ask_kind(self, kind, data):
            self.sent.append((kind, data))
            return {"letter": 'Sincerely, @NAME@'}

    profile = ApplicantProfile({"identity": {"preferred_first_name": 'Te"st', "pronouns": "she/her/hers"},
                                "education": {"school": "Example State University"}}, tmp_path, {})
    kinds = Kinds()
    answer = as_applicant(kinds, profile).ask_kind("essays.write", {"drafts": {}})
    assert kinds.sent == [("essays.write", {"drafts": {}, "pronouns": "she/her/hers",
                                            "school": "Example State University"})]
    assert answer == {"letter": 'Sincerely, Te"st'}


def test_no_call_is_sent_who_the_applicant_is_or_their_self_id(test_persons_bank):
    # D8: the Fill engine fills these from the profile, so no draft or review needs them.
    profile = ApplicantProfile.load(PROFILE, POLICIES)
    profile.set("voluntary_self_id.race", "East Asian")
    profile.set("experience_facts.professional_references", [{"name": "Ref Erence", "email": "ref@example.org"}])
    email, race = Question("email", "Email", "text", True), Question("race", "Race", "select", False, ("East Asian",))
    planned = Question("why_now", "Why are you applying now?", "text", True)

    calls = written(profile, (planned,), {email: "test.person@example.com", race: "East Asian"})
    reviewer = FakeClaude()
    presubmit.review(reviewer, POSTING, [email, race, WHY], {"email": "test.person@example.com", "race": "East Asian",
                                                             "why": "Because I use it."}, who=personal(profile))

    [draft] = [c for c in calls if c.get("kind") == "essays.write"]
    assert draft["data"]["short_questions"] and "Springfield" in draft["data"]["sources"]  # where they live: yes
    assert [row["question"] for row in reviewer.kinds[0]["data"]["rows"]] == [WHY.label]
    # The facts and the form's answers every call is sent; a draft is the form's own text, sent whole.
    sent = json.dumps([{part: c["data"].get(part) for part in ("sources", "form_answers", "rows")}
                       for c in calls + reviewer.kinds if "kind" in c])
    for kept in ("Person", "test.person@example.com", "5550100199", "1 Main St", "Test-ee", "East Asian", "Ref Erence"):
        assert kept not in sent
