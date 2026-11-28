"""A one-off choice with more options than the essays.write kind takes (Oracle's 500-city lists) is left to
Lisul, and the form's other one-off questions are still drafted."""

from conftest import FIXTURES, POLICIES
from fakes import FakeClaude

from apply import essays
from apply.model import Posting, Question
from apply.profile import ApplicantProfile

POSTING = Posting("p", "Oracle", "Software Engineer Intern", "https://jobs.example.com/1")
CITY = Question("city", "City", "select", True, tuple(f"City {i}" for i in range(essays.MAX_OPTIONS + 200)))
HOUSING = Question("housing", "Will you need housing?", "select", True, ("Yes", "No"))


def test_a_choice_too_long_to_send_is_lisuls_and_the_rest_are_drafted():
    claude = FakeClaude()

    _, drafted = essays.answer(claude, POSTING, [], [CITY, HOUSING], ApplicantProfile.load(FIXTURES / "planner-profile.yaml", POLICIES))

    [call] = [c for c in claude.asked if "kind" in c]
    assert [q["label"] for q in call["data"]["short_questions"].values()] == ["Will you need housing?"]
    assert {d.question.name: d.needs_applicant for d in drafted}["city"] is True
    assert {d.question.name for d in drafted} == {"city", "housing"}
