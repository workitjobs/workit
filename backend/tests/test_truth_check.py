"""The truth check (app/auto_apply/truth.py, KAN-748), as a pure function:
the claims in an answer that none of the student's sources hold. The
connector's tests (test_connector_review.py) show the flag in the tab."""

from app.auto_apply.truth import reason, unsupported

OWN = (
    "Software Intern, Hitachi Rail", "June 2025 – August 2025", "IEEE Stony Brook Micromouse",
    "Built a dispatch dashboard in Python and FastAPI for train dispatchers", "Cut page load time by 30%",
)
POSTING = ("Acme", "Acme builds payments software. You will deploy services to production on Kubernetes.",
           "Why do you want to work at Acme?")
CLEAN = ("At Hitachi Rail in summer 2025 I built a dispatch dashboard in Python and FastAPI, and I cut page load "
         "time by 30%. I want to build fast payments software at Acme on Kubernetes.")


def _found(answer: str) -> list[tuple[str, str]]:
    return [(c.kind, c.text) for c in unsupported(answer, OWN, POSTING)]


def test_a_clean_answer_has_no_claims():
    assert unsupported(CLEAN, OWN, POSTING) == []


def test_a_made_up_number_and_a_made_up_outcome_are_named_with_their_sentence():
    answer = "At Hitachi Rail I built a dispatch dashboard. I wrote 40 tests for it, and it went into use in 2025."

    claims = unsupported(answer, OWN, POSTING)

    assert [(c.kind, c.text) for c in claims] == [("number", "40"), ("outcome", "went into use")]
    assert {c.sentence for c in claims} == {"I wrote 40 tests for it, and it went into use in 2025."}
    assert reason(claims) == ('Not in your experience or the posting: "40" (a number); "went into use" (an outcome). '
                              "Make sure each one is true before you submit.")


def test_a_tool_or_employer_no_source_names_is_a_claim():
    assert _found("At Hitachi Rail I also used Kafka and PyTorch with CUDA.") == [
        ("name", "Kafka"), ("name", "PyTorch"), ("name", "CUDA")]
    assert _found("My work at Stripe taught me to test.") == [("name", "Stripe")]
    # Names the sources hold, in any case and side by side, are not.
    assert _found("I raced with IEEE Stony Brook Micromouse and wrote python at hitachi rail.") == []


def test_a_month_or_season_outside_the_sources_dates_is_a_claim():
    assert _found("I joined Hitachi Rail in July 2025.") == []
    assert _found("I joined Hitachi Rail in fall 2025.") == [("date", "fall 2025")]


def test_an_outcome_counts_only_when_the_student_gave_it_not_the_posting():
    # The posting says "deploy" and "production"; the student never did.
    assert _found("I deployed the dashboard to production.") == [("outcome", "deployed")]
    assert unsupported("I deployed the dashboard.", (*OWN, "Deployed the dashboard to every control center")) == []


def test_everyday_capitals_and_sentence_openers_are_no_claim():
    assert _found("Building tools in Python is what I like. In English and in AI, I read a lot on Monday.") == []
