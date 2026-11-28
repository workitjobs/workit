"""A rehearsal paused at a sign-in Lisul finishes names the company and role
its open page named, so its Record and tile do (Claude fill's Oracle)."""

from conftest import APPLY, FIXTURES
from fakes import FakeClaude
from test_worker_date import Site

from apply.fillers import Handoff
from apply.model import Posting
from apply.profile import ApplicantProfile
from apply.worker import apply_to


class SignInHandoffFiller:
    """Claude fill at a sign-in it hands to Lisul, after its open page named the company and role."""

    names = ("Emerson", "Software Engineering Intern")

    def question_set(self, url, site):
        raise Handoff("the Apply button opened no email step")


def test_a_paused_sign_in_handoff_carries_the_company_its_page_named():
    posting = Posting("request-2", "", "", "https://example.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX/job/1")
    profile = ApplicantProfile.load(FIXTURES / "planner-profile.yaml", APPLY / "policies.default.yaml")
    paused = []
    apply_to(posting, SignInHandoffFiller(), Site(), profile, FakeClaude(), rehearse=True,
             on_pause=lambda stopped, blocked: paused.append(stopped) and False)
    assert [stopped.named for stopped in paused] == [("Emerson", "Software Engineering Intern")]
