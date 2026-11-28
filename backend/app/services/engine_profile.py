"""
The Fill engine's profile and policies for one student, built from what
WorkIt holds: what WorkIt Auto Apply fills with (`GET /apply-app/profile`,
W11), in place of an Applicant profile file on the Mac.

A port of the WorkIt extension's own mapping
(autofiller_extension/src/background/engine.js: `engineProfile`,
`enginePolicies` and what they call), with the two Fill engine helpers it
uses (`homePlace`, `degreeLevel`, and their tables) ported from the engine.
The two must give the same profile for the same student, so the app fills
as the extension does: `tests/test_engine_profile.py` runs the extension's
on the same input in Node and compares. A change to either changes both.

Pure: it takes the student as the extension assembles it (`AutofillProfile`,
its JSON as the API's routes answer it) and returns plain data. A JS
`undefined` is a key left out here, and `null` is None.
"""

import math
import re
from datetime import date
from typing import Any

# The extension's tables: the words a form reads for each Application answer's option key.
CITIZENSHIP = {
    "us_citizen": "US citizen",
    "permanent_resident": "U.S. Permanent Resident (Green Card)",
    "f1_student": "F-1 Student (CPT, OPT or STEM OPT)",
    "h1b": "H-1B",
    "other_visa": "Other Visa",
    "asylee_refugee": "Asylee or Refugee",
}
CLEARANCE = {"none": "None", "public_trust": "Public Trust", "confidential": "Confidential", "secret": "Secret",
             "top_secret": "Top Secret", "ts_sci": "Top Secret / SCI"}
GENDER = {"male": "Male", "female": "Female", "non_binary": "Non-Binary", "declined": "decline"}
RACE = {
    "american_indian_alaska_native": "American Indian or Alaska Native",
    "asian": "Asian",
    "black_african_american": "Black or African American",
    "native_hawaiian_pacific_islander": "Native Hawaiian or Other Pacific Islander",
    "white": "White",
    "two_or_more": "Two or More Races",
    "declined": "decline",
}
VETERAN = {"protected_veteran": True, "not_protected_veteran": "I am not a protected veteran",
           "not_veteran": "I am not a veteran", "declined": "decline"}
ORIENTATION = {"heterosexual": "Heterosexual", "gay": "Gay", "lesbian": "Lesbian", "bisexual": "Bisexual",
               "asexual": "Asexual", "queer": "Queer", "declined": "decline"}
PRONOUNS = {"he_him": "He/him", "she_her": "She/her", "they_them": "They/them", "declined": "decline"}
COMMUNITY = {"disability": "Person with disability", "neurodiverse": "Neurodiverse", "veteran": "Veteran",
             "parent": "Parent", "refugee_immigrant": "Refugee or immigrant", "first_generation": "First-generation",
             "lgbtq": "LGBTQ+"}
ROLE_INTEREST = {"backend": "Backend", "frontend": "Frontend", "full_stack": "Full-Stack", "mobile": "Mobile",
                 "embedded": "Embedded", "ml": "Machine Learning", "data": "Data", "infrastructure": "Infrastructure",
                 "security": "Security", "robotics": "Robotics"}
YES_NO_DECLINE = {"yes": True, "no": False, "declined": "decline"}
YES_NO = {"yes": True, "no": False}
CLASS_YEARS = ["4th Year Undergrad (Senior)", "3rd Year Undergrad (Junior)", "2nd Year Undergrad (Sophomore)",
               "1st Year Undergrad (Freshman)"]
# How WorkIt answers what no student fact covers (the extension's POLICIES).
POLICIES = {
    "how_heard": {"first": ["WorkIt", "LinkedIn"], "prefer": ["job board", "other"], "text": "WorkIt"},
    "marketing_opt_in": False,
    "sms_opt_in": False,
    "high_stakes_job_systems": [],
    "us_roles_only": True,
}

# The Fill engine's (fit.ts US_STATES, label-parts.ts COUNTRIES' names), for homePlace.
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky",
    "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota",
    "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}
COUNTRY_NAMES = [["united kingdom", "uk", "great britain", "britain", "england"], ["canada"], ["portugal"]]


def engine_profile(student: dict, today: date) -> dict:
    """The engine's profile: WorkIt's own fields laid over what the student brought from Apply (`fill.profile`)."""
    return layered((student.get("fill") or {}).get("profile"), workit_profile(student, today.isoformat()))


def engine_policies(student: dict) -> dict:
    """WorkIt's policies, with what the student brought from Apply over them, and their own pay answers."""
    return layered(layered(POLICIES, (student.get("fill") or {}).get("policies")),
                   {"compensation": _pay(student.get("answers") or {})})


def _holds(value: Any) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return any(_holds(v) for v in value.values())
    return True


def layered(under: dict | None, over: dict | None) -> dict:
    """`over` laid over `under`, section by section: a value `over` holds wins, one it lacks leaves `under`'s."""
    out = dict(under or {})
    for key, value in (over or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = layered(out[key], value)
        elif _holds(value):
            out[key] = value
    return out


def _present(fields: dict) -> dict:
    return {k: v for k, v in fields.items() if v is not None}


def _yes(answer: Any) -> bool | None:
    return True if answer == "yes" else False if answer == "no" else None


def _list(value: Any) -> list | None:
    return value if isinstance(value, list) else None


def _pay(answers: dict) -> dict:
    accepts = _yes(answers.get("accept_posted_pay"))
    hourly = answers.get("expected_hourly_pay")
    return _present({
        "fallback_hourly": hourly if isinstance(hourly, int | float) and not isinstance(hourly, bool) else None,
        "accept_stated_rate": accepts,
        "expectation": "Open to the posted range" if accepts else None,
    })


def _ends(entry: dict) -> str:
    return "9999" if entry.get("end_kind") == "present" else (entry.get("end_month") or "")


def _latest(entries: list[dict], section: str) -> list[dict]:
    return sorted((e for e in entries if e.get("section") == section), key=_ends, reverse=True)


def _newest(entries: list[dict], section: str) -> list[dict]:
    return sorted((e for e in entries if e.get("section") == section),
                  key=lambda e: (e.get("start_month") or "", _ends(e)), reverse=True)


def _skill_names(skills: list[dict]) -> list[str]:
    def language(s: dict) -> bool:
        return re.search("language", s.get("group") or "", re.IGNORECASE) is not None
    return [s["name"] for s in [*filter(language, skills), *(s for s in skills if not language(s))]]


def degree_level(degree: str) -> str:
    """The engine's `degreeLevel`: "B.S." or "Bachelor of Science" as "Bachelor's Degree"; anything else as written."""
    d = degree.lower().replace(".", "").strip()
    if re.search(r"bachelor|^b ?(s|a|eng|sc)\b", d):
        return "Bachelor's Degree"
    if re.search(r"master|^m ?(s|a|eng|sc|ba)\b", d):
        return "Master's Degree"
    if re.search(r"doctor|^phd\b", d):
        return "Doctorate"
    if re.search(r"associate|^a ?(s|a)\b", d):
        return "Associate's Degree"
    return degree


def _level_now(school: dict) -> str | None:
    if not school.get("degree") or school.get("end_kind") == "month":
        return None
    level = degree_level(school["degree"])
    if level in ("Bachelor's Degree", "Associate's Degree"):
        return "Undergraduate"
    return "Graduate" if level in ("Master's Degree", "Doctorate") else None


def _norm(text: str) -> str:
    folded = text.lower().replace("’", "'").replace("“", '"').replace("”", '"')
    return " ".join(folded.split()).strip(" *")


def home_place(text: str) -> dict:
    """The engine's `homePlace`: "Stony Brook, NY" as {city, state, country}, the state as its code; {} when unsure."""
    parts = [p.strip() for p in text.split(",") if p.strip()]
    country = None
    if parts and re.fullmatch(r"(?:u\.?s\.?(a\.?)?|united states( of america)?)", parts[-1], re.IGNORECASE):
        parts.pop()
        country = "United States"
    if len(parts) > 2 and re.fullmatch(r"\d{5}(?:-\d{4})?", parts[-1]):
        parts.pop()
    if len(parts) > 2 and re.match(r"\d+\s", parts[0]):
        parts.pop(0)
    if not country and len(parts) == 3:
        city, state, abroad = parts
        return {"city": city, "state": state, "country": abroad} if any(_norm(abroad) in names for names in COUNTRY_NAMES) else {}
    only = {"country": country} if country else {}
    if len(parts) != 2:
        return {} if parts else only
    city, written = parts
    region = re.sub(r"\s+\d{5}(?:-\d{4})?$", "", written)
    state = region.upper() if region.upper() in US_STATES else next(
        (code for code, name in US_STATES.items() if name.lower() == region.lower()), None)
    return {"city": city, "state": state, "country": "United States"} if state else only


def _home(location: str | None) -> dict | None:
    place = home_place(location) if location else {}
    return place or None


def _month_index(text: str | None) -> int | None:
    m = re.match(r"(\d{4})-(\d{2})", text or "")
    return int(m[1]) * 12 + int(m[2]) - 1 if m else None


def _school_year(school: dict | None, answers: dict, today: str) -> dict:
    graduation = _month_index(school.get("end_month")) if school and school.get("end_kind") != "present" else None
    if graduation is None:
        return {}
    now = _month_index(today)
    class_of = math.floor(graduation / 12) + (1 if graduation % 12 >= 7 else 0)
    year_ends = math.floor(now / 12) + (1 if now % 12 >= 6 else 0)
    start = _month_index(answers.get("earliest_start"))
    end = _month_index(answers.get("latest_end"))
    if end is None:
        end = None if start is None else start + 3
    year = class_of - year_ends
    return _present({
        "class_year": CLASS_YEARS[year] if _level_now(school) == "Undergraduate" and 0 <= year < len(CLASS_YEARS) else None,
        "returning_to_school_after_internship": None if end is None else graduation > end,
    })


def _application_facts(answers: dict, place: dict | None) -> dict:
    prefs = _list(answers.get("location_preferences"))
    languages = _list(answers.get("languages"))
    return {
        "logistics": _present({
            "onsite_5_days_ok": _yes(answers.get("onsite_ok")),
            "can_work_full_time_40h": _yes(answers.get("full_time_40h")),
            "earliest_start_date": answers.get("earliest_start"),
            "latest_end_date": answers.get("latest_end"),
            "available_terms": _list(answers.get("available_terms")),
            "willing_to_relocate_for_summer": _yes(answers.get("willing_to_relocate")),
            "location_preferences": [list(dict.fromkeys([p, p.split(",")[0].strip()])) for p in prefs]
            if prefs is not None else None,
            "referrals": _list(answers.get("referred_at")),
        }),
        "identity": _present({
            "home_address": _present({
                "line1": answers.get("address_line1"), "zip": answers.get("postal_code"),
                "city": (place or {}).get("city"), "state": (place or {}).get("state"),
                "country": (place or {}).get("country"),
            }) if answers.get("address_line1") or answers.get("postal_code") else None,
            "summer_2027_location": answers.get("internship_location"),
            "languages": [{"language": lang, "spoken": True, "written": True} for lang in languages]
            if languages is not None else None,
        }),
        "screeners": _present({
            "relatives_at": _list(answers.get("relatives_at")),
            "relative_of_public_official": _yes(answers.get("relative_public_official")),
            "prior_us_government_employment": _yes(answers.get("prior_government_work")),
            "non_compete_or_conflicting_agreements": _yes(answers.get("non_compete")),
            "pending_offers": _list(answers.get("pending_offers")),
        }),
    }


def _communities(keys: Any) -> str | list | None:
    if not isinstance(keys, list):
        return None
    return "decline" if "declined" in keys else [COMMUNITY[k] for k in keys if COMMUNITY.get(k)]


def _internships(jobs: list[dict]) -> int | None:
    if not jobs:
        return None
    return sum(1 for e in jobs if re.search(r"\bintern(ship)?\b|\bco-?op\b", e.get("title") or "", re.IGNORECASE))


def _current_company(jobs: list[dict]) -> str | None:
    return next((e["organization"] for e in jobs if e.get("end_kind") == "present" and e.get("organization")), None)


def workit_profile(student: dict, today: str) -> dict:
    """The engine profile from WorkIt's own fields alone (the extension's `workitProfile`)."""
    first, *rest = (student.get("full_name") or "").split() or [""]
    named = bool(student.get("first_name") and student.get("last_name"))
    entries = (student.get("bank") or {}).get("entries") or []
    school, *earlier = _latest(entries, "education") or [None]
    skills = _skill_names((student.get("bank") or {}).get("skills") or [])
    answers = student.get("answers") or {}
    place = _home(student.get("location"))
    facts = _application_facts(answers, place)
    jobs = _newest(entries, "experience")
    roles = answers.get("role_interests")
    countries = answers.get("citizenship_countries")
    return {
        "logistics": facts["logistics"],
        "screeners": facts["screeners"],
        "identity": _present({
            **facts["identity"],
            "legal_first_name": (student.get("first_name") if named else first) or None,
            "legal_middle_name": (student.get("middle_name") or None) if named else None,
            "legal_last_name": (student.get("last_name") if named else " ".join(rest)) or None,
            "email": student.get("email"),
            "phone": student.get("phone_number"),
            "current_location": place,
            "age_18_or_over": _yes(answers.get("age_18_or_over")),
            "pronouns": PRONOUNS.get(answers.get("pronouns")),
            "current_company": _current_company(jobs),
        }),
        "links": _present({
            "linkedin_url": student.get("linkedin_url"),
            "github_url": student.get("github_url"),
            "portfolio_url": student.get("portfolio_url") if student.get("portfolio_url") is not None
            else student.get("other_url"),
            "x_twitter_url": answers.get("x_url"),
        }),
        "files": _present({
            "resume_pdf": (student.get("resume") or {}).get("filename"),
            "unofficial_transcript_pdf": (student.get("transcript") or {}).get("filename"),
        }),
        "education": _present({
            "school": school.get("title"),
            "degree": degree_level(school["degree"]) if school.get("degree") else None,
            "degree_level_now": _level_now(school),
            "degree_type": school.get("degree"),
            "majors": [school["field_of_study"]] if school.get("field_of_study") else None,
            "gpa_cumulative": school.get("gpa"),
            "gpa_scale": school.get("gpa_scale"),
            "start_date": school.get("start_month"),
            "expected_graduation": None if school.get("end_kind") == "present" else school.get("end_month"),
            "past_schools": [_present({
                "school": e.get("title"), "degree": e.get("degree"),
                "end": None if e.get("end_kind") == "present" else e.get("end_month"),
            }) for e in earlier] or None,
            **_school_year(school, answers, today),
        }) if school else {},
        "experience_facts": _present({
            "employment_history": [_present({
                "employer": e.get("organization"), "title": e.get("title"), "start": e.get("start_month"),
                "end": None if e.get("end_kind") == "present" else e.get("end_month"), "location": e.get("location"),
                "description": "\n".join(b["text"] for b in sorted(e.get("bullets") or [], key=lambda b: b["position"]))
                or None,
            }) for e in jobs],
            "skills": skills or None,
            "prior_internships_count": _internships(jobs),
            "role_interests": [ROLE_INTEREST[k] for k in roles if ROLE_INTEREST.get(k)] if isinstance(roles, list) else None,
        }),
        "work_authorization": _present({
            "authorized_to_work_us": YES_NO.get(answers.get("work_authorized_us")),
            "requires_sponsorship_now_or_future": YES_NO.get(answers.get("needs_sponsorship")),
            "citizenship": CITIZENSHIP.get(answers.get("work_authorization_status")),
            "citizenship_countries": countries if isinstance(countries, list) and countries else None,
            "security_clearance": CLEARANCE.get(answers.get("security_clearance")),
        }),
        "voluntary_self_id": _present({
            "gender": GENDER.get(answers.get("gender")),
            "hispanic_or_latino": YES_NO_DECLINE.get(answers.get("hispanic_latino")),
            "race": RACE.get(answers.get("race")),
            "veteran": VETERAN.get(answers.get("veteran_status")),
            "disability": YES_NO_DECLINE.get(answers.get("disability_status")),
            "sexual_orientation": ORIENTATION.get(answers.get("sexual_orientation")),
            "transgender": YES_NO_DECLINE.get(answers.get("transgender")),
            "communities": _communities(answers.get("communities")),
        }),
    }
