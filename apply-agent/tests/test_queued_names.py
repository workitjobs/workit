"""Naming a link that waits to start when no queue named it (apply.queued_names, Dashboard.names_by): a link the
student sent in or pasted shows its company, role and logo as soon as it waits, not its host. No browser, and no
network past the fake WorkIt and a fake job board."""

import json
import threading

import pytest
from fake_workit import FakeWorkIt, Reply
from test_app_window import OneFrame

from apply import dashboard, queued_names, workit
from apply.dashboard import Dashboard
from apply.workit import WorkIt

AIRBNB = "https://careers.airbnb.com/positions/7363316?gh_jid=7363316"
JOB_API = "https://boards-api.greenhouse.io/v1/boards/airbnb/jobs/7363316"


class Greenhouse:
    """Greenhouse's job API, with Airbnb's job 7363316 on it: every other read fails."""

    def __init__(self):
        self.fetched: list[str] = []

    def fetch(self, url, body=None):
        self.fetched.append(url)
        if url.startswith(JOB_API):
            return json.dumps({"title": "Software Engineer, Intern", "company_name": "Airbnb",
                               "absolute_url": "https://careers.airbnb.com/positions/7363316"}).encode()
        raise OSError("HTTP 404")

    def open(self, url, worker=0):
        raise AssertionError("naming a link opened a browser")


@pytest.fixture
def board(monkeypatch):
    monkeypatch.setattr(dashboard, "ThreadingHTTPServer", lambda *_, **__: pytest.fail("the window opened a port"))
    with Dashboard(2, OneFrame(), serve=False) as made:
        yield made


def test_a_link_sent_in_is_named_as_it_waits_without_holding_the_run(board):
    """Fault: a link sent in shows only its host and a letter tile till its form starts filling; the run waits on its
    name; a link the queue named, or one already named, is read again."""
    asked, go = [], threading.Event()

    def namer(link):
        asked.append(link)
        go.wait(5)
        return {"company": "Airbnb", "title": "Software Engineer, Intern", "company_domain": "airbnb.com",
                "stage": "not a name"}

    board.logos({"https://jobs.lever.co/acme/3": {"company": "Acme", "title": "Intern"}})
    board.names_by(namer)
    board.run(waiting=["https://jobs.lever.co/acme/3", AIRBNB])
    assert board.state()["run"]["waiting"][1] == {"link": AIRBNB}  # the run goes on: its host shows meanwhile
    go.set()
    for _ in range(100):
        if board.state()["run"]["waiting"][1] != {"link": AIRBNB}:
            break
        threading.Event().wait(0.02)
    board.run(waiting=[AIRBNB])
    assert board.state()["run"]["waiting"] == [{"link": AIRBNB, "company": "Airbnb",
                                                "title": "Software Engineer, Intern", "company_domain": "airbnb.com"}]
    assert asked == [AIRBNB]
    board.update(0, link=AIRBNB, status="filling")  # its form, before it reads its own names
    tile = board.state()["tiles"][0]
    assert (tile["company"], tile["role"], tile["company_domain"]) == ("Airbnb", "Software Engineer, Intern",
                                                                       "airbnb.com")


def test_a_link_is_named_by_workit_first_then_its_job_board_else_by_nothing(tmp_path):
    """Fault: a link WorkIt lists loses the logo WorkIt has for it; a careers page that names its Greenhouse job stays
    unnamed, or takes Greenhouse's domain for its logo; a link nothing names gets a made-up name."""
    listed = "https://jobs.ashbyhq.com/benchling/0b3c1a52-0000-4000-8000-000000000001"
    job = {"id": "j1", "company": "Benchling", "title": "Software Engineer, Intern (Summer 2027)",
           "logo_url": "https://app.ashbyhq.com/api/images/benchling.png", "company_domain": "benchling.com",
           "description": "not a name"}
    site = Greenhouse()
    with FakeWorkIt() as fake:
        fake.route("POST", "/jobs/listed-by-link", lambda seen, fake: Reply(200, {"job_id": "j1", "stage": None})
                   if seen.body == {"url": listed} else Reply(404, {"detail": "WorkIt doesn't list this job yet."}))
        fake.route("GET", "/jobs/j1", lambda seen, fake: Reply(200, job))
        client = WorkIt(fake.site, tmp_path / "workit-login.json", fake.keychain)
        workit.login(client, fake.browser)
        assert queued_names.names(listed, client, site) == {key: job[key] for key in dashboard.QUEUED_JOB}
        assert not site.fetched  # WorkIt named it: no job board read
        assert queued_names.names(AIRBNB, client, site) == {
            "company": "Airbnb", "title": "Software Engineer, Intern", "company_domain": "airbnb.com"}
        assert queued_names.names("https://www.lucidmotors.com/careers/1234", client, site) == {}
