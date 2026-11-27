"""Opinion, preference and personality questions under answer_opinion_questions (the Safety level's balanced and
full_auto): answered from the closest backed facts, never asked, never invented."""

import pytest

from apply import essays
from apply.model import Question

FAVORITE = Question("q1", "What's your favorite design artifact you've made, and why?", "textarea", required=True)
WHY = Question("q2", "Why Acme?", "textarea", required=True)


class Profile:
    def __init__(self, on: bool = True):
        self._on = on

    def policy(self, key):
        return self._on if key == "answer_opinion_questions" else None

    def facts(self):
        return {}


# Fault: Reliable Robotics' favourite-artifact question not told from a plain why question.
@pytest.mark.parametrize("label", [FAVORITE.label, "What is your favourite tool?", "Which team would you prefer?",
                                   "Describe yourself in three words", "In your opinion, what makes good software?"])
def test_an_opinion_question_is_told_by_its_words(label):
    assert essays.asks_opinion(Question("q", label, "textarea"))
    assert not essays.asks_opinion(WHY)


# Fault: a why-us essay or a fact asked as a preference answered from the closest facts, never asked.
@pytest.mark.parametrize("label", ["What excites you about joining Acme?", "Preferred location", "Preferred name",
                                   "What's your favorite thing about working at Acme?",
                                   "Which team would you prefer to join at our company?"])
def test_a_question_about_them_or_a_fact_is_no_opinion_question(label):
    assert not essays.asks_opinion(Question("q", label, "textarea"))


# Fault: the policy off (careful), yet an opinion question answered without the applicant.
def test_only_the_policy_answers_it_from_the_closest_facts():
    assert essays.closest(FAVORITE, Profile(True))
    assert not essays.closest(FAVORITE, Profile(False)) and not essays.closest(WHY, Profile(True))
    assert essays._sent(FAVORITE, "preference", True)["closest_facts"] is True
    assert "closest_facts" not in essays._sent(WHY, "why-company")


# Fault: the plan still asks "Which artifact is your favorite?" though the policy says answer from the facts.
def test_its_plan_asks_nothing_and_keeps_only_the_backed_slots():
    held = "I designed the dashboard for example.com in Figma, styled after VS Code."
    planned = essays.Plan("preference", slots=(essays.Backed("closest-project", (held,)),))
    asked = essays._backed(essays.Plan("preference"), held)
    assert asked.asks and not asked.closest  # careful, and no slot backed: the pick is asked
    nearest = essays._backed(planned, held, nearest=True)
    assert nearest.asks == () and nearest.slots == planned.slots and nearest.closest


# Fault: a one-off opinion question dropped as a Missing fact though Claude answered it from the sources.
def test_a_drafted_answer_stands_whatever_needs_lisul_says():
    given = {"answer": "The portfolio site styled after VS Code", "needs_lisul": True}
    prompt = "example.com, a portfolio site styled after VS Code"
    q = Question("d1", "What's your favorite thing you've built?", "text")
    assert essays._draft(q, given, prompt, Profile(), prompt, nearest=True).answer == given["answer"]
    assert essays._draft(q, given, prompt, Profile(), prompt).needs_lisul
    assert essays._draft(q, {"answer": "", "needs_lisul": True}, prompt, Profile(), prompt, nearest=True).needs_lisul


# Fault: an essay naming the tools that fill the form reaches it (it says the application was automated).
@pytest.mark.parametrize("text", ["we designed WorkIt's front end in Figma.", "My auto-apply agent fills forms.",
                                  "I wrote the fill engine.", "the Apply agent"])
def test_an_essay_naming_the_tools_is_caught(text):
    assert essays.names_tools(text)


def test_a_plain_essay_names_none():
    assert essays.names_tools("As an Eagle Scout I applied what I learned to the robot's firmware.") == ()
