"""A page's chrome never names a job (model.job_title): a sign-in wall's title became an Amazon job's role on the
Applied page ("Log in or create account | Amazon.jobs", 2026-11-27). No browser, no network."""

import json

import pytest

from apply.model import Status, job_title
from apply.tracker import FileTracker, Row


# Fault: a chrome title kept as the role (the guard off, or a pattern missing).
@pytest.mark.parametrize("title", [
    "Log in or create account | Amazon.jobs", "Sign In", "Amazon.jobs | Sign in", "Login - Workday",
    "Create an account", "Careers", "Jobs | Amazon", "Just a moment...", "Page Not Found | Acme", "",
])
def test_a_pages_chrome_names_no_role(title):
    assert job_title(title) == ""


# Fault: a real role dropped because it starts with or holds a chrome word.
@pytest.mark.parametrize("title", [
    "Software Development Engineer Intern - Amazon.jobs", "Software Engineer | Jobs", "Application Developer Intern",
    "Registered Nurse", "Sign Language Interpreter", "Account Executive Intern",
])
def test_a_jobs_title_stays_as_it_is(title):
    assert job_title(title) == title


# Fault: a chrome role saved before the guard stays in the Tracker, and so on the Applied page.
def test_a_chrome_role_saved_before_leaves_the_tracker_as_it_loads(tmp_path):
    path = tmp_path / "tracker.json"
    tracker = FileTracker(path)
    tracker.add(Row("a", "Amazon", "Log in or create account | Amazon.jobs", "https://www.amazon.jobs/en/jobs/10593521/",
                    "amazon", Status.SUBMITTED))
    tracker.add(Row("b", "Acme", "Intern", "https://jobs.lever.co/acme/1", "lever", Status.SUBMITTED))

    assert [row.role for row in FileTracker(path).rows()] == ["", "Intern"]
    FileTracker(path).update("b", reason="kept")
    assert [row["role"] for row in json.loads(path.read_text())["applications"]] == ["", "Intern"]
