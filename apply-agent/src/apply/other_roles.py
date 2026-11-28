"""Other roles here: a form's question whether the student applies to other
roles at the same company ("Are you applying to any Strava internship besides
Software Engineering Intern, Server? If so, which ones and why?").

Apply answers it in code, never with a model and never from the student.
Strava, 2026-11-26: the essay plan asked the student for it as an Essay fact
("You answer this once. We'll use it on every application that asks."), and
the answer, true of Strava only, joined the Story bank for every company.

The answer comes from what Apply holds:

- the student's applications to the same company (`model.is_company`) in
  Apply's Tracker: a submitted row is "applied", a row still on its way
  (queued, filling, held, waiting on a Missing fact, paused) is "applying",
  and a Request on the same job board is "applying";
- the company's open postings on its job board (Greenhouse, Lever, Ashby,
  one public read), which name a Request's role and give each role's text.

It names each other application and never one that does not exist. When the
question asks why, each named role gets one sentence from the profile only:
an area of `experience_facts.role_interests` its title names, else the
`experience_facts.skills` its text lists. With no other application the
answer is "No", with one such sentence for this role when one holds.

The answer is this Posting's alone: it goes on this form and its Record, and
never into the Answer bank or the Story bank."""

import html
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from apply import fill_engine, tracker
from apply.adapters import JobSite
from apply.model import Posting, Question, Status, is_company, one_line, plain_text
from apply.profile import ApplicantProfile
from apply.workit import job_key

# Words that name a role, an internship or a posting.
ROLE = r"(?:roles?|positions?|jobs?|internships?|intern\b|openings?|postings?|requisitions?|opportunit(?:y|ies)|co-?ops?|programs?)"
# The question asks of other roles at this company: applying (or applied) to others, besides this one, or only this.
ASKS = re.compile(
    rf"\b(?:apply(?:ing)?|applied|submitted)\b[^?]{{0,120}}?\b(?:other|another|additional|more\s+than\s+one|multiple|besides"
    rf"|apart\s+from|aside\s+from|in\s+addition\s+to|else)\b[^?]{{0,80}}?{ROLE}"
    rf"|\b(?:other|another|additional|more\s+than\s+one|multiple)\s+(?:\w+\s+){{0,3}}?{ROLE}[^?]{{0,80}}?\b(?:apply(?:ing)?|applied)\b"
    rf"|\b{ROLE}[^?]{{0,80}}?\bbesides\b"
    rf"|\bonly\s+(?:\w+\s+){{0,3}}?{ROLE}[^?]{{0,60}}?\b(?:apply(?:ing)?|applied)\b",
    re.IGNORECASE)
# A question about other companies, not other roles here: Apply leaves it to the plan.
ELSEWHERE = re.compile(r"\bother\s+(?:compan(?:y|ies)|employers?|firms?|organi[sz]ations?|offers?)\b|\belsewhere\b",
                       re.IGNORECASE)
# The question names this company: by name ("at Strava"), or as "here", "with us", "our", "besides" a role.
HERE = re.compile(r"\b(?:here|with\s+us|our|this\s+(?:company|organi[sz]ation|team)|internal(?:ly)?|besides)\b",
                  re.IGNORECASE)
ONLY = re.compile(r"\bonly\b", re.IGNORECASE)  # "Is this the only role you are applying to?": Yes means none other
# "Have you applied": sent applications only; "are you applying" counts those on their way too.
PAST = re.compile(r"\b(?:have|has)\s+(?:you\s+)?(?:already\s+|previously\s+|ever\s+)?applied\b", re.IGNORECASE)
WHY = re.compile(r"\bwhy\b|\breasons?\b|\bexplain\b", re.IGNORECASE)
INTERN = re.compile(r"\bintern(?:ship)?s?\b|\bco-?op\b", re.IGNORECASE)
# Tracker statuses: sent, and still on its way to being sent.
APPLIED = frozenset({Status.SUBMITTED})
APPLYING = frozenset({Status.QUEUED, Status.FILLING, Status.HELD, Status.MISSING_FACT, Status.PAUSED})
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
NAMED = 2  # roles at most that each get a why sentence
SKILLS = 3  # skills at most that one why sentence lists


@dataclass(frozen=True)
class Opening:
    """One open posting on the company's job board."""

    title: str
    url: str
    text: str = ""  # its description, as plain text


@dataclass(frozen=True)
class Other:
    """One of the student's other applications to the same company."""

    title: str  # "" when nothing names its role
    applied: bool  # sent; else still on its way
    url: str = ""


def asks(q: Question, company: str) -> bool:
    """Whether `q` asks if the student applies to other roles at `company`: never at other companies, nor
    other jobs anywhere ("Are you applying for other jobs?" names no company)."""
    text = f"{q.label} {q.description}"
    named = bool(company.strip()) and re.search(rf"(?<!\w){re.escape(company.strip())}(?!\w)", text, re.IGNORECASE)
    return (q.kind in ("text", "textarea", "select") and bool(ASKS.search(text)) and not ELSEWHERE.search(text)
            and bool(named or HERE.search(text)))


def openings(posting: Posting, site: JobSite) -> list[Opening]:
    """The open postings on `posting`'s job board (Greenhouse, Lever or Ashby), read from its public API;
    [] for another job system or a board that can't be read."""
    try:
        job = fill_engine.job_of(posting.url) or {}
        kind, board = job.get("site"), job.get("board") or job.get("company")
        if not board:
            return []
        if kind == "greenhouse":
            jobs = json.loads(site.fetch(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"))["jobs"]
            return [Opening(one_line(j.get("title") or ""), j.get("absolute_url") or "",
                            plain_text(html.unescape(j.get("content") or ""))) for j in jobs]
        if kind == "ashby":
            jobs = json.loads(site.fetch(f"https://api.ashbyhq.com/posting-api/job-board/{board}"))["jobs"]
            return [Opening(one_line(j.get("title") or ""), j.get("jobUrl") or "", one_line(j.get("descriptionPlain") or ""))
                    for j in jobs if j.get("isListed", True)]
        if kind == "lever":
            jobs = json.loads(site.fetch(f"https://api.lever.co/v0/postings/{board}?mode=json"))
            return [Opening(one_line(j.get("text") or ""), j.get("hostedUrl") or "", one_line(j.get("descriptionPlain") or ""))
                    for j in jobs]
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError):
        pass  # no board (unreachable, or not the shape its API gives): the Tracker alone says what he applies to
    return []


def others(posting: Posting, board: Sequence[Opening], path: Path | None = None) -> list[Other]:
    """The student's other applications to `posting`'s company, from the Tracker (saved at `path`), and each
    Request on the same board (`board`). Read without the lock, as tracker.past_applications reads it."""
    if not posting.company.strip():
        return []
    saved = tracker.saved(path)  # WorkIt Auto Apply's applications on WorkIt are among its rows (W11)
    own, found, seen = _job(posting.url), [], set()
    for row in saved.get("applications", []):
        company, url = str(row.get("company") or ""), str(row.get("posting_url") or "")
        if not company.strip() or not (is_company(company, posting.company) or is_company(posting.company, company)):
            continue
        if row.get("application_id") == posting.id or not url or (key := _job(url)) == own or key in seen:
            continue
        if row.get("status") in APPLIED or row.get("status") in APPLYING:
            seen.add(key)
            found.append(Other(one_line(str(row.get("role") or "")) or _titled(url, board), row.get("status") in APPLIED, url))
    on_board = {_job(o.url): o for o in board if o.url}
    for url in saved.get("requests", []):
        if isinstance(url, str) and (key := _job(url)) != own and key not in seen and key in on_board:
            seen.add(key)
            found.append(Other(on_board[key].title, False, url))
    return found


def answer(q: Question, posting: Posting, found: Sequence[Other], board: Sequence[Opening], profile: ApplicantProfile,
           posting_text: str = "") -> str | None:
    """The answer to `q`, an `asks` question, from the student's other applications (`found`): None when
    `q` offers no option that says it. "Is this the only role" flips Yes and No; a list's "Have you applied"
    counts only sent applications."""
    only = bool(ONLY.search(q.label))
    if q.kind == "select":
        yes = bool([o for o in found if o.applied] if PAST.search(q.label) else found) != only
        return next((o for o in q.options if re.match(r"\s*yes\b" if yes else r"\s*no\b", o, re.IGNORECASE)), None)
    company = posting.company.strip() or "this company"
    noun = "internship" if INTERN.search(f"{posting.title} {q.label}") else "role"
    why = bool(WHY.search(f"{q.label} {q.description}"))
    if not found:
        said = [f"{'Yes' if only else 'No'}, {posting.title.strip()} is the only {company} {noun} I'm applying to."
                if posting.title.strip() else f"{'Yes' if only else 'No'}, this is the only {company} {noun} I'm applying to."]
        if why and (reason := _reason("It", posting.title, posting_text, profile)):
            said.append(reason)
        return _fit(said, q)
    applied = [o for o in found if o.applied]
    applying = [o for o in found if not o.applied]
    said = ["No." if only else "Yes."]
    if applied:
        said.append(f"I have also applied to {_listed(applied, company, noun)}.")
    if applying:
        said.append(f"I am {'' if applied else 'also '}applying to {_listed(applying, company, noun)}.")
    if why:
        texts = {_job(o.url): o.text for o in board if o.url}
        said += [reason for o in found[:NAMED] if o.title
                 and (reason := _reason(o.title, o.title, texts.get(_job(o.url), ""), profile))]
    return _fit(said, q)


def _reason(subject: str, title: str, text: str, profile: ApplicantProfile) -> str:
    """One sentence on why a role fits, from the profile only: an area of role_interests its title names,
    else the skills its text lists; "" when neither holds."""
    for interest in profile.get("experience_facts.role_interests") or []:
        for area in re.split(r"\s*/\s*", str(interest)):
            if len(area) > 2 and re.search(rf"(?<!\w){re.escape(area)}(?!\w)", title, re.IGNORECASE):
                return f"{subject} matches my interest in {area if any(c.isupper() for c in area[1:]) else area.lower()} work."
    listed = [s for s in (str(s).strip() for s in profile.get("experience_facts.skills") or [])
              if s and re.search(rf"(?<!\w){re.escape(s)}(?!\w)", text, re.IGNORECASE)][:SKILLS]
    if not listed:
        return ""
    skills = listed[0] if len(listed) == 1 else f"{', '.join(listed[:-1])} and {listed[-1]}"
    return f"{subject} lists {skills}, which I have worked with."


def _listed(found: Sequence[Other], company: str, noun: str) -> str:
    """The roles of `found`, named as their rows and the board name them; one nothing names is "one other"."""
    names = [o.title for o in found if o.title]
    if unnamed := len(found) - len(names):
        names.append(f"one other {company} {noun}" if unnamed == 1 else f"{unnamed} other {company} {noun}s")
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def _fit(said: list[str], q: Question) -> str:
    """The sentences that fit the field's limit, the first always."""
    text = said[0]
    for sentence in said[1:]:
        if q.max_length and len(f"{text} {sentence}") > q.max_length:
            break
        text = f"{text} {sentence}"
    return text


def _job(url: str) -> str:
    """The job `url` is for, as one key: the job's UUID where its link holds one (Lever's and Ashby's, so a
    posting and its form are one job), else WorkIt's link rule (a Greenhouse job by its ID)."""
    return found[0].lower() if (found := UUID.findall(url)) else job_key(url)


def _titled(url: str, board: Sequence[Opening]) -> str:
    """The title the board gives the job at `url`, else ""."""
    key = _job(url)
    return next((o.title for o in board if o.url and _job(o.url) == key), "")
