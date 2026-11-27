"""Already applied (KAN-621): the check, against a fake WorkIt, Apply's Tracker file and Records. No browser."""

from datetime import date

import pytest
from fake_tracker import FakeTracker
from fake_workit import FakeWorkIt

from apply import workit
from apply.already_applied import Check
from apply.dashboard import verdict
from apply.keychain import InMemoryKeychain
from apply.model import Posting, Status
from apply.tracker import FileTracker, Row
from apply.workit import WorkIt

ASTRANIS = "https://job-boards.greenhouse.io/astranis/jobs/4704598006"


def posting(url: str = ASTRANIS, id: str = "request-0001") -> Posting:
    return Posting(id, "Astranis", "Intern", url)


@pytest.fixture
def signed_in(tmp_path):
    """A signed-in student who applied to Astranis on WorkIt, and only saved Bolt."""
    with FakeWorkIt() as fake:
        tracker = FakeTracker(fake)
        tracker.applied_before(tracker.listed("https://boards.greenhouse.io/astranis/jobs/4704598006", "Astranis",
                                              "Intern"), "applied", "2026-10-28T19:00:00+00:00")
        tracker.applied_before(tracker.listed("https://jobs.lever.co/bolt/1", "Bolt", "Intern"), "saved")
        client = WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain)
        workit.login(client, fake.browser)
        yield fake, client


def check(tmp_path, client) -> Check:
    return Check(client, tmp_path / "tracker.json", (tmp_path / "rehearsals",))


def test_a_job_applied_to_on_workit_is_already_applied_by_its_job_on_either_greenhouse_host(tmp_path, signed_in):
    _, client = signed_in
    found = check(tmp_path, client).of(posting())

    assert found and found.on == date(2026, 10, 28)
    assert found.said() == "Already applied on 2026-10-28 (your Applications Tracker on WorkIt: applied)"


def test_a_saved_job_is_not_applied_to(tmp_path, signed_in):
    _, client = signed_in
    seen = check(tmp_path, client)

    assert seen.of(posting("https://jobs.lever.co/bolt/1")) is None
    assert seen.problem() == ""


def test_workit_is_read_once_for_every_link(tmp_path, signed_in):
    fake, client = signed_in
    seen = check(tmp_path, client)
    fake.requests.clear()
    for url in (ASTRANIS, "https://jobs.lever.co/bolt/1", "https://jobs.lever.co/other/2"):
        seen.of(posting(url))

    assert [r.path for r in fake.requests if r.path.endswith("/applications")] == [
        f"/applicants/{fake.account['id']}/applications"]


def test_no_workit_login_is_said_and_apply_s_own_tracker_still_checked(tmp_path):
    FileTracker(tmp_path / "tracker.json").add(Row("request-0001", "Astranis", "Intern", ASTRANIS, "greenhouse",
                                                   Status.SUBMITTED, date(2026, 10, 27)))
    seen = check(tmp_path, WorkIt(workit.LIVE, tmp_path / "no-login.json", InMemoryKeychain()))

    assert "not signed in to WorkIt" in seen.problem()
    found = seen.of(posting("https://boards.greenhouse.io/astranis/jobs/4704598006?gh_src=x", id="other"))
    assert found and (found.on, found.where) == (date(2026, 10, 27), "Apply's Tracker: submitted")


def test_workit_not_answering_is_said(tmp_path, signed_in):
    fake, client = signed_in
    fake.stop()
    seen = check(tmp_path, client)

    assert seen.of(posting()) is None
    assert "WorkIt did not answer" in seen.problem()


def test_a_record_with_its_after_submit_screenshot_is_already_applied(tmp_path):
    sent = tmp_path / "rehearsals" / "2026-11-04" / "astranis-request-0001"
    sent.mkdir(parents=True)
    (sent / "form.png").write_bytes(b"")
    held = tmp_path / "rehearsals" / "2026-11-04" / "bolt-request-0002"
    held.mkdir(parents=True)
    (held / "form.png").write_bytes(b"")  # held, never submitted
    seen = check(tmp_path, WorkIt(workit.LIVE, tmp_path / "no-login.json", InMemoryKeychain()))

    assert seen.of(posting(id="request-0001")) is None
    (sent / "after-submit.png").write_bytes(b"png")
    found = seen.of(posting(id="request-0001"))
    assert found and found.on == date(2026, 11, 4)
    assert seen.of(posting("https://jobs.lever.co/bolt/1", id="request-0002")) is None


def test_a_record_whose_readme_says_submitted_is_already_applied_without_its_screenshot(tmp_path):
    """Fault: Astranis Backend, sent through its emailed code in run10, was saved as submitted with no
    after-submit.png (its confirmation's screenshot failed), so run11 filled it again as new."""
    sent = tmp_path / "rehearsals" / "2026-11-26" / "astranis-request-0003"
    sent.mkdir(parents=True)
    (sent / "README.md").write_text("# Astranis: Backend Intern\n\n- Posting: https://job-boards.greenhouse.io/a/jobs/1\n"
                                    "- Application ID: request-0003\n- Status: held (Rehearsal, not submitted.)\n")
    seen = check(tmp_path, WorkIt(workit.LIVE, tmp_path / "no-login.json", InMemoryKeychain()))

    assert seen.of(posting(id="request-0003")) is None
    (sent / "README.md").write_text("# Astranis: Backend Intern\n\n- Application ID: request-0003\n"
                                    "- Status: submitted (You submitted it yourself from a rehearsal; Apply filled it)\n")
    found = seen.of(posting(id="request-0003"))
    assert found and found.on == date(2026, 11, 26)


def test_the_window_says_already_applied_and_that_nothing_was_filled():
    shown = verdict({"status": "already applied",
                     "why": "Already applied on 2026-10-28 (your Applications Tracker on WorkIt: applied)"})

    assert (shown["tone"], shown["label"]) == ("ended", "Already applied on 2026-10-28")
    assert "Apply didn't open the form" in shown["detail"]
