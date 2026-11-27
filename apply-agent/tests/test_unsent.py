"""Essays an Application wrote but never sent, kept for its next attempt (apply.unsent)."""

from datetime import date, timedelta

from apply import unsent
from apply.essays import Essay
from apply.model import Posting, Question

POSTING = Posting("p", "Example Co", "Software Engineer Intern", "https://jobs.example.com/example/1")
WHY = Question("why", "Why Example Co?", "textarea", True)
PROJECT = Question("project", "Share a project", "textarea", True)
TODAY = date(2026, 11, 26)


def test_a_clean_essay_is_taken_once_kept_and_a_flagged_one_is_written_again():
    unsent.keep(POSTING, [Essay(WHY, "Because it builds rockets.", named="Rocket"),
                          Essay(PROJECT, "47 clubs adopted it.", unsupported=("47",))], TODAY)

    [taken] = unsent.take(POSTING, [WHY, PROJECT], TODAY + timedelta(days=1))

    assert (taken.question, taken.text, taken.named) == (WHY, "Because it builds rockets.", "Rocket")


def test_a_kept_essay_past_its_keep_or_forgotten_is_not_taken():
    unsent.keep(POSTING, [Essay(WHY, "Because it builds rockets.")], TODAY)
    assert unsent.take(POSTING, [WHY], TODAY + unsent.KEEP + timedelta(days=1)) == []

    unsent.forget(POSTING)
    assert unsent.take(POSTING, [WHY], TODAY) == []
