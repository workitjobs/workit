"""The truth check (app/auto_apply/truth.py, KAN-748), as a pure function:
the claims in an answer that none of the student's sources hold. The
connector's tests (test_connector_review.py) show the flag in the tab."""

from types import SimpleNamespace

from app.auto_apply.truth import reason, unsupported
from app.auto_apply.written import bank_facts
from app.services.bank import Bank

# One text per bank entry, its heading naming the role or project (as written._own_facts gives them).
OWN = (
    ("## Software Intern, Hitachi Rail\nJune 2025 – August 2025\n"
     "Built a dispatch dashboard in Python and FastAPI for train dispatchers\nCut page load time by 30%"),
    "## IEEE Stony Brook Micromouse\nWrote the maze solver in C++",
)
POSTING = ("Acme", "Acme builds payments software. You will deploy services to production on Kubernetes.",
           "Why do you want to work at Acme?")
CLEAN = ("At Hitachi Rail in summer 2025 I built a dispatch dashboard in Python and FastAPI, and I cut page load "
         "time by 30%. I want to build fast payments software at Acme on Kubernetes.")


def _found(answer: str) -> list[tuple[str, str]]:
    return [(c.kind, c.text) for c in unsupported(answer, OWN, POSTING)]


def _found_in(answer: str, own: tuple[str, ...]) -> list[tuple[str, str]]:
    return [(c.kind, c.text) for c in unsupported(answer, own, POSTING)]


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
    assert unsupported("At Hitachi Rail I deployed the dashboard.",
                       (OWN[0] + "\nDeployed the dashboard to every control center", OWN[1])) == []


def test_an_outcome_stands_only_on_a_fact_about_the_same_project():
    # KAN-750: Micromouse's facts say "deployed"; Hitachi Rail's never do.
    own = (OWN[0], OWN[1] + "\nDeployed the solver on the competition mouse")
    assert _found_in("At Hitachi Rail I built a dispatch dashboard, and it went into use.", own) == [
        ("outcome", "went into use")]
    # The project may be named in the sentence before; "it" is the dashboard.
    assert _found_in("At Hitachi Rail I built a dispatch dashboard. It went into use.", own) == [
        ("outcome", "went into use")]
    assert _found_in("For Micromouse I wrote the maze solver in C++. It went into use at every race.", own) == []
    # A fact in the student's own words that names the project counts as about it.
    assert _found_in("At Hitachi Rail I built a dispatch dashboard, and it went into use.",
                     (*own, "My Hitachi Rail dashboard went into daily use.")) == []


def test_an_outcome_whose_project_no_sentence_tells_is_a_claim():
    own = (OWN[0] + "\nDeployed the dashboard to every control center", OWN[1])
    assert _found_in("I deployed the dashboard.", own) == [("outcome", "deployed")]


def test_a_name_that_opens_a_sentence_is_a_claim_unless_it_is_a_plain_word():
    assert _found("Stripe hired me to build dashboards.") == [("name", "Stripe")]
    assert _found("Hitachi Rail hired me to build a dispatch dashboard.") == []
    assert _found("Building tools is fun. Recently I learned C++. Teamwork matters to me, and teamwork wins.") == []


def test_a_short_answer_has_no_name_claim():
    assert _found("Yes") == []
    assert _found("Chicago") == []
    assert _found("Remote, please.") == []


def test_everyday_capitals_and_sentence_openers_are_no_claim():
    assert _found("Building tools in Python is what I like. In English and in AI, I read a lot on Monday.") == []


def test_everyday_uses_of_outcome_words_are_no_claim():
    assert _found("I won't forget that summer, and I never cut corners.") == []


def test_the_bank_gives_each_entry_its_own_heading_so_an_outcome_stays_with_its_entry():
    def entry(title, organization, *bullets):
        row = SimpleNamespace(**dict.fromkeys(
            ("location", "degree", "field_of_study", "gpa", "gpa_scale", "honors", "issuer", "coursework", "tools",
             "start_month", "end_month", "award_date")), title=title, organization=organization)
        return SimpleNamespace(row=row, bullets=[SimpleNamespace(text=b) for b in bullets])

    bank = Bank(entries=[entry("Software Intern", "Hitachi Rail", "Built a dispatch dashboard"),
                         entry("Captain", "Micromouse", "Deployed the maze solver on our mouse")], skills=[])
    own = bank_facts(bank)

    assert own[0].startswith("## Software Intern, Hitachi Rail\n")
    assert _found_in("At Hitachi Rail my dashboard went into use.", own) == [("outcome", "went into use")]
    assert _found_in("As Micromouse captain I deployed the maze solver.", own) == []


def test_a_tool_two_projects_share_tells_neither_project():
    own = ("## Software Intern, Hitachi Rail\nBuilt a depot tracker in Python",
           "## WorkIt\nDeployed the Python API to production")
    assert _found_in("I used Python for the depot tracker, and it went into use.", own) == [
        ("outcome", "went into use")]


def test_the_plans_story_tells_the_project_when_no_sentence_names_one():
    own = ("## Software Intern, Hitachi Rail\nBuilt a depot tracker that went into use at every depot",
           "## WorkIt\nBuilt the job search")
    answer = "I built a depot tracker. It went into use."
    assert _found_in(answer, own) == [("outcome", "went into use")]
    assert unsupported(answer, own, POSTING, story="Built a depot tracker that went into use at every depot") == []
    assert unsupported(answer, own, POSTING, story="## WorkIt") != []


def test_a_short_reply_that_opens_with_a_plain_word_has_no_name_claim():
    for reply in ("Sure, happy to relocate anywhere.", "Happy to relocate for this.", "Excited to apply here.",
                  "Either location works for me.", "Referral from a friend."):
        assert _found(reply) == [], reply


def test_a_plain_noun_opening_a_sentence_is_no_name():
    assert _found("Small robots that sort marbles.") == []
    assert _found("Google taught me to test, and Stripe hired me.") == [("name", "Google"), ("name", "Stripe")]
