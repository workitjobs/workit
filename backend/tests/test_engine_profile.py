"""WorkIt Auto Apply's profile from WorkIt (W11): services/engine_profile.py is a port of the WorkIt extension's own
mapping, so the app fills as the extension does. Each student here runs through both, the extension's in Node
(engine_profile_parity.mjs), and the two must agree on every key. Skipped without node or the extension's engine."""

import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest

from app.services.engine_profile import engine_policies, engine_profile, home_place

EXTENSION = Path(__file__).parents[2] / "autofiller_extension"
TODAY = date(2026, 11, 24)

STUDENTS = [
    {  # Everything WorkIt holds, under a profile brought from Apply.
        "full_name": "Grace Brewster Hopper", "first_name": "Grace", "middle_name": "Brewster", "last_name": "Hopper",
        "email": "grace@example.com", "phone_number": "555-0100", "location": "Stony Brook, NY",
        "linkedin_url": "https://linkedin.com/in/g", "github_url": None, "portfolio_url": None,
        "other_url": "https://grace.dev",
        "bank": {"entries": [
            {"section": "education", "title": "Stony Brook University", "degree": "B.S.", "field_of_study": "Computer Science",
             "gpa": "3.71", "gpa_scale": "4.0", "start_month": "2024-08", "end_month": "2028-05", "end_kind": "expected"},
            {"section": "education", "title": "Ward Melville High School", "degree": None, "end_month": "2024-06",
             "end_kind": "month"},
            {"section": "experience", "title": "Software Engineering Intern", "organization": "Acme",
             "start_month": "2025-06", "end_month": "2025-08", "end_kind": "month", "location": "New York, NY",
             "bullets": [{"text": "Second", "position": 2}, {"text": "First", "position": 1}]},
            {"section": "experience", "title": "Research Assistant", "organization": "SBU Lab", "start_month": "2025-09",
             "end_kind": "present", "bullets": []},
        ], "skills": [{"name": "Docker", "group": "Tools"}, {"name": "Python", "group": "Languages"},
                      {"name": "Go", "group": "Programming languages"}]},
        "answers": {
            "age_18_or_over": "yes", "onsite_ok": "no", "full_time_40h": "yes", "earliest_start": "2027-06-01",
            "latest_end": "2027-08-15", "available_terms": ["Summer 2027"], "willing_to_relocate": "yes",
            "location_preferences": ["Seattle, WA", "New York"], "referred_at": [], "address_line1": "1 Main St",
            "postal_code": "11790", "internship_location": "Seattle, WA", "languages": ["English", "Spanish"],
            "relatives_at": [], "relative_public_official": "no", "prior_government_work": "no", "non_compete": "no",
            "pending_offers": [], "pronouns": "she_her", "x_url": "https://x.com/g",
            "role_interests": ["backend", "ml", "unknown"], "work_authorized_us": "yes", "needs_sponsorship": "no",
            "work_authorization_status": "us_citizen", "citizenship_countries": ["United States"],
            "security_clearance": "none", "gender": "female", "hispanic_latino": "declined", "race": "asian",
            "veteran_status": "not_veteran", "disability_status": "no", "sexual_orientation": "declined",
            "transgender": "no", "communities": ["first_generation", "lgbtq"], "expected_hourly_pay": 32,
            "accept_posted_pay": "yes",
        },
        "resume": {"filename": "Grace_Hopper.pdf"}, "transcript": {"filename": "Transcript_Grace_Hopper.pdf"},
        "fill": {"profile": {"identity": {"preferred_first_name": "Amazing Grace", "legal_first_name": "Old"},
                             "answered_questions": {"Why us?": "Boats."}, "education": {"school": "Old U"}},
                 "policies": {"how_heard": {"text": "A friend"}, "cover_letter": "optional"}},
    },
    {  # A name to split, a home abroad, a graduate school still going, a decline among communities.
        "full_name": "Alan  Mathison Turing", "email": "alan@example.com", "location": "Toronto, ON, Canada",
        "bank": {"entries": [{"section": "education", "title": "UofT", "degree": "M.Eng", "start_month": "2025-09",
                              "end_kind": "present"}], "skills": []},
        "answers": {"communities": ["declined", "lgbtq"], "veteran_status": "protected_veteran",
                    "expected_hourly_pay": "40", "accept_posted_pay": "no", "latest_end": None},
        "resume": None, "transcript": None, "fill": {"profile": {}, "policies": {}},
    },
    {  # A finished degree, a home with a street and ZIP, no bank and nothing brought.
        "full_name": "Katherine Johnson", "email": "kj@example.com", "location": "123 Elm St, Springfield, IL 62704",
        "bank": {"entries": [{"section": "education", "title": "WVSU", "degree": "Bachelor of Arts",
                              "end_month": "2025-05", "end_kind": "month"}], "skills": []},
        "answers": {"earliest_start": "2026-06-01"}, "resume": None, "transcript": None, "fill": None,
    },
    {"full_name": "", "email": "x@example.com", "location": "Columbus, Ohio, USA", "bank": None, "answers": {}},
]


@pytest.mark.skipif(shutil.which("node") is None or not (EXTENSION / "fill-engine" / "dist" / "engine.js").is_file(),
                    reason="needs node and the extension's engine")
def test_the_app_gets_the_profile_the_extension_fills_with(tmp_path):
    """Fault: the port drifted from the extension's mapping (a table, a branch, a helper), so the app filled a field
    the extension fills differently."""
    (tmp_path / "students.json").write_text(json.dumps(STUDENTS))
    run = subprocess.run(["node", str(Path(__file__).with_name("engine_profile_parity.mjs")), str(EXTENSION),
                          str(tmp_path / "students.json"), TODAY.isoformat()], capture_output=True, text=True, timeout=60, check=False)
    assert run.returncode == 0, run.stderr
    for student, extension in zip(STUDENTS, json.loads(run.stdout), strict=True):
        assert engine_profile(student, TODAY) == extension["profile"]
        assert engine_policies(student) == extension["policies"]


def test_a_home_is_read_only_when_its_state_or_country_is_sure():
    """The engine's homePlace: a place it can't be sure of is nothing, so its questions stay the student's."""
    assert home_place("Stony Brook, NY") == {"city": "Stony Brook", "state": "NY", "country": "United States"}
    assert home_place("Columbus, Ohio, USA") == {"city": "Columbus", "state": "OH", "country": "United States"}
    assert home_place("London, UK") == {}
    assert home_place("USA") == {"country": "United States"}
