"""
Import (KAN-211, ADR 0003): turn the heuristic parser's reading of an
uploaded resume into entries and skills for the bank. Model parsing (KAN-222)
does the same from the model's reading. No database, no HTTP: the caller
writes the result with `services/bank.py`'s `import_upload` (ADR 0005).
Every upload is read by the model first, the parser behind it
(`read_resume`, KAN-732, ADR 0007).

Drafts keep the resume's words. The only changes are the ones a draft must
pass to be a valid entry: text clipped to the field's length, at most 30
bullets and 40 courses, and dates dropped when the end comes before the start;
and a run of spaces, which PDF extraction leaves after a bold phrase, becomes
one.
"""

import asyncio
import datetime
import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from pydantic import ValidationError
from workit_scout.identity import PLACEHOLDERS, Identity, placeholders_in
from workit_scout.llm import LLM

from app.models.dto import Experience, ParsedResume, bank_section, entry_end_kind
from app.schemas.bank import SECTION_FIELDS, DraftEntry, ModelReading
from app.services import skill_catalog
from app.utils.resume_parser import (
    fix_symbols,
    is_tools_line,
    parse_resume,
    section_of,
    split_tools,
    tool_items,
)

_SHORT, _LONG, _NAME = 200, 500, 60
_COURSEWORK_RE = re.compile(r"^(?:Relevant\s+)?(?:Coursework|Courses)\s*:?\s*", re.IGNORECASE)
_GPA_LINE_RE = re.compile(r"^GPA\b", re.IGNORECASE)
_YEAR_ALONE_RE = re.compile(r"\d{4}")
_LINK_TAIL_RE = re.compile(r"[\s,;:|–—-]*\[link\]\s*$")
_MINOR_JOIN_RE = re.compile(r"\s*[|;,–—-]?\s*\b(minors?)\s*(?:in\b|:)\s*", re.IGNORECASE)
# A minor in a phrase of its own, kept as written: "with a Minor in X",
# "(Minor in X)", "Double Minor in X". Joined, they read "with a, minor in"
_MINOR_AS_WRITTEN_RE = re.compile(r"\b(?:with|plus|and)\s+(?:an?\s+)?(?:double\s+)?minors?\b|\(\s*minors?\b|"
                                  r"\bdouble\s+minors?\b", re.IGNORECASE)
# How a degree is compared with the resume's text: case, spacing and the
# apostrophe's form aside
_DEGREE_FORM_RE = re.compile(r"\s+")
# Not a skill: a name still holding a "|" (a title's tail glued on), a
# qualification ("Computer Science degree", "Bachelor's in ...", "GPA 3.8",
# "3+ years of Java", a citizenship or clearance), or a generic phrase that
# names no product ("AI tools", "communication skills"). A product or a role
# stays: "Scrum Master", "Master Data Management", "Chrome Developer Tools",
# "CI/CD tools", "User Experience".
_NOT_A_SKILL_RE = re.compile(
    r"\||\bdegree\b|\b(?:bachelor|master)(?:'?s)?\s+(?:degree|of|in)\b|\bbachelor(?:'?s)?\b|\bdiploma\b|\bgpa\b"
    r"|\b\d+\+?\s*(?:years?|yrs)\b|\byears?\s+of\b|\bcitizen(?:ship)?\b|\bclearance\b"
    r"|^(?:ai|genai|software|development|productivity|collaboration|communication|soft|interpersonal"
    r"|technical|analytical|leadership|problem[- ]solving)\s+(?:tools|skills)$",
    re.IGNORECASE,
)
logger = logging.getLogger(__name__)


def not_a_skill(name: str) -> bool:
    return bool(_NOT_A_SKILL_RE.search(name.strip()))


def _clip(value: str | None, limit: int = _SHORT) -> str | None:
    # a run of spaces is a PDF gap (after a bold phrase), not the resume's wording
    value = re.sub(r"[ \t]{2,}", " ", (value or "").strip())
    return value[:limit].strip() or None


def _bullets(description: str | None) -> list[str]:
    lines = [_clip(line, _LONG) for line in (description or "").splitlines()]
    return [line for line in lines if line][:30]


def _tools(items: list[str]) -> list[str]:
    """A project's tools as the resume spells them, clipped, each once
    (ignoring case), at most 30. Not checked against the skills catalog:
    the stack line prints what the student wrote (KAN-738)."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        tool = _clip(item, _NAME)
        if tool and tool.casefold() not in seen:
            seen.add(tool.casefold())
            out.append(tool)
    return out[:30]


def _span(start: datetime.date | None, end: datetime.date | None) -> dict:
    """An ongoing role (a start, no end) runs to Present."""
    if end is not None:
        return {"start_month": start, "end_month": end, "end_kind": entry_end_kind.month}
    return {"start_month": start, "end_month": None, "end_kind": entry_end_kind.present if start else None}


def _role(section: bank_section, role: Experience) -> dict:
    title = _clip(role.title) or _clip(role.company_name)
    organization = _clip(role.company_name)
    return {
        "section": section,
        "title": title,
        "organization": organization if organization != title else None,
        "location": _clip(role.location),
        **_span(role.start_date, role.end_date),
        "bullets": _bullets(role.description),
    }


def _raw_drafts(parsed: ParsedResume, today: datetime.date) -> list[dict]:
    drafts: list[dict] = []
    for school in parsed.education:
        coursework: list[str] = []
        bullets: list[str] = []
        for line in _bullets(school.description):
            if _COURSEWORK_RE.match(line):
                coursework += [c for c in (_clip(x) for x in _COURSEWORK_RE.sub("", line).split(",")) if c]
            elif not _GPA_LINE_RE.match(line):
                bullets.append(line)
        end = school.end_date
        drafts.append({
            "section": bank_section.education,
            "title": _clip(school.institution),
            "location": _clip(school.location),
            "degree": _clip(school.degree),
            "field_of_study": _clip(school.field_of_study),
            "gpa": school.gpa,
            "gpa_scale": school.gpa_scale,
            "coursework": coursework[:40],
            "start_month": school.start_date,
            "end_month": end,
            # A graduation still to come is an expected one.
            "end_kind": None if end is None else entry_end_kind.expected if end > today else entry_end_kind.month,
            "bullets": bullets,
        })
    drafts += [_role(bank_section.experience, job) for job in parsed.experience]
    for project in parsed.projects:
        drafts.append({
            "section": bank_section.projects,
            "title": _clip(project.project_name),
            "link": _clip(project.url, _LONG),
            "tools": _tools(project.technologies),
            **_span(project.start_date, project.end_date),
            "bullets": _bullets(project.description),
        })
    drafts += [_role(bank_section.leadership, role) for role in parsed.leadership]
    for award in parsed.awards:
        drafts.append({
            "section": bank_section.awards,
            "title": _clip(award.title),
            "organization": _clip(award.issuer),
            "award_date": award.date,
        })
    for cert in parsed.certifications:
        drafts.append({
            "section": bank_section.certifications,
            "title": _clip(cert.cert_name),
            "issuer": _clip(cert.issuer),
        })
    drafts += _other_drafts(parsed)
    return drafts


def _other_drafts(parsed: ParsedResume) -> list[dict]:
    """Each heading the bank has no section for ("Summary", "Interests") as
    one draft of its lines, for a Lines section of that name (KAN-498): the
    title is the section's name too, since an entry needs one, and a Lines
    section never prints it."""
    drafts = []
    for other in parsed.others:
        name = _clip(other.heading, _NAME)
        lines = [line for line in (_clip(x, _LONG) for x in other.lines) if line][:30]
        if name and lines:
            drafts.append({"section": bank_section.custom, "title": name, "section_name": name, "bullets": lines})
    return drafts



def _valid(raw: dict) -> DraftEntry | None:
    if not raw.get("title"):
        return None
    try:
        return DraftEntry.model_validate(raw)
    except ValidationError:
        # Dates that do not fit together (an end before the start) are the
        # likely cause; the student can add them back in the editor. An
        # award's date goes too: kept, a bad one dropped the whole award.
        undated = {**raw, "start_month": None, "end_month": None, "end_kind": None, "award_date": None}
        try:
            return DraftEntry.model_validate(undated)
        except ValidationError:
            return None


def draft_entries(parsed: ParsedResume, today: datetime.date | None = None) -> list[DraftEntry]:
    """Draft entries in section order, each section in the resume's order."""
    today = today or datetime.datetime.now(datetime.UTC).date()
    return [d for d in (_valid(raw) for raw in _raw_drafts(parsed, today)) if d is not None]


def parsed_skills(parsed: ParsedResume) -> list[tuple[str, str | None]]:
    """The parser's skills as (name, group) pairs, for `draft_skills`, then
    the tools named beside each role and project ("Intern| C++, Python",
    "Robot | C++, Python") that the skills section left out, with no group."""
    pairs: list[tuple[str, str | None]] = [(s.skill_name, s.category) for s in parsed.skills]
    beside = [*parsed.experience, *parsed.projects, *parsed.leadership]
    return pairs + [(tool, None) for item in beside for tool in item.technologies]


def skill_pairs(skills: list[tuple[str, str | None]]) -> list[tuple[str, str | None]]:
    """(name, group) pairs clipped to the field limits, keeping only the
    skills the catalog knows (`skill_catalog`, KAN-369), in the resume's
    spelling, one per catalog skill ("ReactJS" and "React" are one)."""
    seen: set[str] = set()
    out: list[tuple[str, str | None]] = []
    for raw_name, group in skills:
        name = _clip(raw_name, _NAME)
        if not name or not_a_skill(name) or (known := skill_catalog.canonical(name)) is None or known in seen:
            continue
        seen.add(known)
        out.append((name, _clip(group, _NAME)))
    return out


def read(raw_text: str | None) -> tuple[list[DraftEntry], list[tuple[str, str | None]]]:
    """The parser's entries and skills from an upload's stored text. A text
    the parser cannot read, or a parser crash, reads as nothing: an upload
    never fails because of its reading."""
    try:
        parsed = parse_resume(raw_text) if raw_text else None
    except Exception:
        logger.exception("Resume parsing failed")
        parsed = None
    if parsed is None:
        return [], []
    return tidy_drafts(draft_entries(parsed)), skill_pairs(parsed_skills(parsed))


_BAR_RE = re.compile(r"\s*\|\s*")


def tidy_drafts(drafts: list[DraftEntry]) -> list[DraftEntry]:
    """Both readings' last step: a "|" in a title or organization spaced on
    both sides ("thinkwell (Pulp) |AI Communications Platform"), as the
    resume beside it writes it, and an entry the reading holds twice word
    for word kept once (a PDF editor left a resume's whole text in it
    twice, and every entry was saved twice)."""
    kept: list[DraftEntry] = []
    seen: set[str] = set()
    for draft in drafts:
        for field in ("title", "organization"):
            value = getattr(draft, field)
            if value and "|" in value:
                setattr(draft, field, _BAR_RE.sub(" | ", value).strip())
        key = draft.model_dump_json()
        if key not in seen:
            seen.add(key)
            kept.append(draft)
    return kept


# --- Model parsing (KAN-222) ---------------------------------------------------

# One frozen string, so providers can cache it as a prefix; the resume text
# goes in a message after it. Wording still open: tune it against a fixed
# set of resumes before a provider switch.
MODEL_PROMPT = """\
You read a student's resume and copy it into resume entries. Answer with JSON \
only: {"entries": [...], "skills": [{"name": ..., "group": ...}]}.

The truth rule: copy only what the resume says, in its own words. Never \
invent, reword or improve a title, organization, date, number, tool or \
result. Leave a field null (or "" for the title) when the resume does not \
say it. Copy names, places, degrees and skills exactly as written: "B.S." \
stays "B.S.", "NYC" stays "NYC".

Entries, in the resume's order:
- section is one of "education", "experience", "projects", "leadership" \
(clubs, activities, volunteering), "awards", "certifications". \
A publication or paper is "projects", with its whole citation as the title.
- title: the role, school, project, award or certification name. \
organization: the company or group, and for an award the group that gives \
it. Education: the school is the title.
- Months are "YYYY-MM". end_kind is "month" (ended), "present" (still going, \
no end_month) or "expected" (an expected end, such as graduation).
- bullets: the resume's bullet lines for that entry, one per item, unchanged.
- Education only: degree, field_of_study, gpa, gpa_scale, coursework, honors. \
field_of_study is the major, with any minor after it as the resume writes it \
("Computer Science, minor in Writing & Rhetoric"). \
Projects only: tools, the list of tools the resume names for the project, \
after its name, in parentheses or on a line of their own under it \
("Next.js, TypeScript, FastAPI"), each as written. A line that only lists \
tools is never a bullet, and the tools are never part of the title. \
Certifications only: issuer. Awards only: award_date, in place of start and \
end. Leave other sections' fields empty.
- skills: each skill the resume lists, with its group ("Languages", "Tools") \
when the resume gives one.

Text like [name], [email], [phone] or [link] stands for something removed for \
privacy. Never copy it into an entry.
"""

# The model sees at most this much of the resume: two full pages and more.
MAX_RESUME_CHARS = 20_000

def _withheld(value: object) -> bool:
    return isinstance(value, str) and bool(placeholders_in(value))


async def read_with_model(raw_text: str, llm: LLM, *, identity: Identity) -> ModelReading:
    """The model's reading of the resume text. The seam removes identity data
    from every message first. Raises `ScoutUnavailable` (or its
    `InvalidReply`) when no model answers or the answer fails the schema."""
    prompt = [
        {"role": "system", "content": MODEL_PROMPT},
        {"role": "user", "content": raw_text[:MAX_RESUME_CHARS]},
    ]
    return await llm.complete_json(prompt, ModelReading, identity=identity)


def model_drafts(reading: ModelReading, text: str | None = None) -> list[DraftEntry]:
    """The model's entries as drafts, each checked against the entry schema:
    a field holding a placeholder is emptied, text is clipped, an entry with
    no title is dropped, and dates that do not fit together are dropped.
    Given the resume's `text`, a field the text does not back goes too
    (`_backed_fields`), and an entry whose title goes with it."""
    words = set(_words(text)) if text else None
    drafts: list[DraftEntry] = []
    for entry in reading.entries:
        raw = entry.model_dump()
        # A citation that ends in its URL ("... arXiv preprint, [link]") lost
        # its whole title to the placeholder, so the paper was dropped. The
        # link is the parser's (`with_links`); the title keeps the rest.
        raw["title"] = _LINK_TAIL_RE.sub("", raw["title"] or "")
        raw = {k: None if _withheld(v) else v for k, v in raw.items()}
        for field in ("title", "organization", "location", "degree", "field_of_study", "issuer"):
            raw[field] = _clip(raw[field])
        # The school as its own organization ("Stony Brook University" twice):
        # the parser leaves out an organization that repeats the title.
        if raw["organization"] and raw["title"] and _title_key(raw["organization"]) == _title_key(raw["title"]):
            raw["organization"] = None
        # "Computer Science | Minor in Writing & Rhetoric", copied as written,
        # reads as the parser writes it: "Computer Science, minor in ...".
        if raw["field_of_study"] and not _MINOR_AS_WRITTEN_RE.search(raw["field_of_study"]):
            raw["field_of_study"] = _MINOR_JOIN_RE.sub(lambda m: f", {m[1].lower()} in ", raw["field_of_study"], count=1)
        raw["honors"] = _clip(raw["honors"], _LONG)
        raw["coursework"] = [c for c in (_clip(x) for x in raw["coursework"] if not _withheld(x)) if c][:40]
        # Only a project holds tools (KAN-738): a role's would fail the
        # entry schema and drop the whole role. They reach the skills
        # through `role_tools`.
        raw["tools"] = _tools([t for t in raw["tools"] if not _withheld(t)]) \
            if raw["section"] is bank_section.projects else []
        # A bullet still holding a placeholder (`with_own_wording` found the
        # parser no match for it) would save "[name]" for good.
        raw["bullets"] = [b for b in (_clip(x, _LONG) for x in raw["bullets"]) if b and not _withheld(b)][:30]
        # "2022 - current": the model sends the year alone, which is no
        # "YYYY-MM", so the entry lost its dates (an award lost itself).
        # A year alone is January of it, as the parser reads it.
        for field in ("start_month", "end_month", "award_date"):
            if isinstance(raw[field], str) and _YEAR_ALONE_RE.fullmatch(raw[field].strip()):
                raw[field] = f"{raw[field].strip()}-01"
        if words is not None:
            raw = _backed_fields(raw, words)
        # A degree only as the resume writes it: "Bachelor's" for "Bachelor
        # of Science" passed the word check ("bachelor" and "s" are both on
        # most resumes), and "B.S." became "BS". Dropped, the parser's
        # reading of it fills the field, word for word.
        if text is not None and raw["degree"] and _degree_key(raw["degree"]) not in _degree_key(text):
            raw["degree"] = None
        if draft := _valid(raw):
            drafts.append(draft)
    return drafts


def role_tools(reading: ModelReading, text: str | None = None) -> list[str]:
    """The tools the model gave an entry that is not a project, which only a
    project holds (KAN-738); given the resume's `text`, only those it backs.
    They become skills, as a role's tools from the parser do."""
    words = set(_words(text)) if text else None
    return [
        tool for entry in reading.entries if entry.section is not bank_section.projects
        for tool in entry.tools if not _withheld(tool) and (words is None or _backed(tool, words))
    ]


def model_skills(reading: ModelReading, text: str | None = None) -> list[tuple[str, str | None]]:
    """The model's skills; given the resume's `text`, only those it backs."""
    words = set(_words(text)) if text else None
    return [
        (s.name, s.group) for s in reading.skills
        if not _withheld(s.name) and (words is None or _backed(s.name, words))
    ]


# --- Every upload read by the model, the parser behind it (KAN-732, ADR 0007) ---

# A reading the model has not finished by then is not waited for: the
# parser's is saved, so an upload never hangs on a provider (the client's own
# timeout is ten minutes).
MODEL_WAIT_SECONDS = 45
# The contact block sits above the first section heading. When that heading
# is this near the top, the model gets the text from it on, so a name the
# resume spells unlike the profile never reaches it: the seam removes only
# the profile's own name, and any email, phone or link.
_TOP_LINES = 12
# Too common to show that a field is the resume's own words.
_COMMON = frozenset({"a", "an", "and", "the", "of", "in", "on", "at", "for", "to", "with", "by", "as", "or", "from"})
_TEXT_FIELDS = ("title", "organization", "location", "degree", "field_of_study", "issuer", "honors")


@dataclass
class Reading:
    """One reading of an upload: what goes into the bank, and who read it."""

    entries: list[DraftEntry]
    skills: list[tuple[str, str | None]]
    read_by: Literal["parser", "model"] = "parser"


async def read_resume(raw_text: str | None, llm: LLM | None = None, identity: Identity | None = None) -> Reading:
    """An upload's reading: the model's, checked against the text, with the
    tools taken out of its titles, an award's giver in its organization and
    the parser's project links, combined with what the parser read that the
    model left out (`with_parsers_reading`) and the parser's skills; else the
    parser's. The parser's when no
    model is given (no AI reading left today) or there is no text, and when
    the model fails, answers in the wrong shape, runs past
    MODEL_WAIT_SECONDS or keeps no entry the text backs. Never raises: an
    upload never fails because of its reading."""
    entries, skills = read(raw_text)
    parsed = Reading(entries, skills)
    if llm is None or identity is None or not raw_text:
        return parsed
    # "Chick-ﬁl-A": the PDF's ligatures and other compatibility characters,
    # which the parser's clean-up fixes, would be copied by the model as is.
    text = unicodedata.normalize("NFKC", fix_symbols(raw_text))
    try:
        async with asyncio.timeout(MODEL_WAIT_SECONDS):
            reading = await read_with_model(_from_first_heading(text), llm, identity=identity)
    except Exception as exc:
        # ScoutUnavailable (down, out of quota, the wrong shape), the wait
        # running out, or anything else: the parser's reading still stands.
        logger.warning("The model could not read a resume, so the parser's reading is saved: %r", exc)
        return parsed
    drafts = model_drafts(with_own_wording(reading, entries), text)
    if not drafts:
        return parsed
    drafts, tools = with_tools_split(drafts)
    drafts = with_parsers_reading(with_links(with_award_givers(drafts), entries), entries)
    # The model's skills first, so its groups win; then each project's
    # tools, and the parser's skills, which the catalog already passed, so
    # a skill the model left out is kept.
    beside = tools + [tool for draft in drafts for tool in draft.tools] + role_tools(reading, text)
    found = model_skills(reading, text) + [(tool, None) for tool in beside] + skills
    return Reading(tidy_drafts(drafts), skill_pairs(found), "model")


def with_tools_split(drafts: list[DraftEntry]) -> tuple[list[DraftEntry], list[str]]:
    """Each role and project title less the tools the model copied into it,
    which become skills, as the parser splits them: "Budget Buddy (React,
    Firebase)" and "Robot | C++, Python" keep only the name. The truth rule
    has the model copy a title whole, so without this the tools stayed in it
    (KAN-369's glued titles, back). A project also keeps them as its own
    tools when the model gave it none (KAN-738), and so does a project
    whose first bullets only list tools: the model copied the stack line as
    a bullet, which the parser reads as tools (`is_tools_line`)."""
    tools: list[str] = []
    for draft in drafts:
        if draft.section not in (bank_section.experience, bank_section.leadership, bank_section.projects):
            continue
        name, found = title_and_tools(draft.title)
        if found and name:
            draft.title, tools = name, tools + found
            if draft.section is bank_section.projects and not draft.tools:
                draft.tools = _tools(found)
        while draft.section is bank_section.projects and draft.bullets and is_tools_line(draft.bullets[0]):
            line = draft.bullets.pop(0)
            draft.tools = draft.tools or _tools(tool_items(line))
    return drafts, tools


def title_and_tools(title: str) -> tuple[str, list[str]]:
    """A title's tools: a list after its last "|" (`split_tools`), or a
    comma list in parentheses at its end. "(Pulp)" holds no list and stays."""
    name, tools = split_tools(title)
    paren = re.search(r"\s*\((.*?)\)\s*$", name)
    if paren and "," in paren.group(1):
        tools = tools or [t.strip() for t in paren.group(1).split(",") if t.strip()]
        name = name[:paren.start()].strip()
    return name, tools


_GIVER_RE = re.compile(r"^(?P<award>.+?)\s+[–—|-]\s+(?P<giver>[^–—|]+)$")


def with_award_givers(drafts: list[DraftEntry]) -> list[DraftEntry]:
    """An award with no organization whose title ends in " – Giver": the
    giver goes to the organization, as the parser reads "Award – Issuer".
    The model copied "Dean's List – Riverside State University" whole."""
    for draft in drafts:
        if draft.section is not bank_section.awards or not (m := _GIVER_RE.match(draft.title)):
            continue
        giver = m["giver"].strip()
        # The model may fill the organization and keep it in the title too.
        if not draft.organization or _title_key(draft.organization) == _title_key(giver):
            draft.title, draft.organization = m["award"].strip(), draft.organization or giver
    return drafts


def with_parsers_reading(drafts: list[DraftEntry], parsed: list[DraftEntry]) -> list[DraftEntry]:
    """Both readings as one: the model's entries, and what the parser read
    that they lack. Each parser entry is matched to the model's entry for the
    same thing (`_twin`, in any section: the two file a Resident Assistant
    differently). With no twin it is added whole: the model left out both
    papers under "Publications" (2026-11-08). With one, it fills the twin's
    empty fields (`_fill_blanks`) and adds the bullets no model entry holds.
    The model's value always wins where both have one: it read the layout,
    and the parser fails on the layouts the model is for."""
    out = list(drafts)
    # What the model's reading already says: its bullets, and each entry's
    # name, since the parser saves a line it misreads ("Stony Brook
    # University" under a project) as a bullet.
    held = [_bullet_words(b) for d in drafts for b in d.bullets] + [_name_words(d) for d in drafts]
    for entry in parsed:
        twin = _twin(entry, drafts)
        if twin is None:
            out.append(entry)
            held += [_bullet_words(b) for b in entry.bullets]
            continue
        _fill_blanks(twin, entry)
        for bullet in entry.bullets:
            words = _bullet_words(bullet)
            # A line of tools ("Next.js, TypeScript, FastAPI") is no bullet: the
            # model rightly leaves it out, and it reaches the skills instead.
            if not words or is_tools_line(bullet) or len(twin.bullets) >= 30:
                continue
            if any(len(words & theirs) * 4 >= len(words) * 3 for theirs in held):
                continue
            twin.bullets.append(bullet)
            held.append(words)
    return out


def _bullet_words(text: str) -> set[str]:
    return set(_words(text)) - _COMMON


def _name_words(entry: DraftEntry) -> set[str]:
    return set(_words(f"{entry.title} {entry.organization or ''}")) - _COMMON


def _twin(entry: DraftEntry, drafts: list[DraftEntry]) -> DraftEntry | None:
    """The model's entry for the same thing as the parser's `entry`: at least
    two words of its title and organization shared, and three in four of the
    shorter one's. The shorter, since the parser's title can hold the whole
    line on a layout it misreads ("Robotics Club - Software Lead" is the
    model's "Robotics Club"). "Cashier, Target" and "Cashier, Walmart" share
    one word, and are two jobs. The most words shared wins, then the same
    section."""
    own = _name_words(entry)
    best: tuple[int, bool] = (0, False)
    twin = None
    for draft in drafts:
        theirs = _name_words(draft)
        shared = len(own & theirs)
        if shared < 2 or shared * 4 < min(len(own), len(theirs)) * 3:
            continue
        score = (shared, draft.section is entry.section)
        if score > best:
            best, twin = score, draft
    return twin


_BLANKS = ("location", "link", "degree", "field_of_study", "issuer", "honors")
_SECTION_ONLY = {f for fields in SECTION_FIELDS.values() for f in fields}


def _fill_blanks(twin: DraftEntry, entry: DraftEntry) -> None:
    """The twin's empty fields from the parser's entry, never one the model
    filled: the dates when the model gave none (a paper's year), a start the
    model left out of the same span, the award date, the location, link,
    degree, field, GPA and courses. A fill that breaks the entry's rules (an
    end before the start) is skipped. Never the title or organization: on a
    layout the parser misreads, those are where its mistakes are."""
    fill: dict = {f: getattr(entry, f) for f in _BLANKS if not getattr(twin, f) and getattr(entry, f)}
    if twin.gpa is None and entry.gpa is not None:
        fill.update(gpa=entry.gpa, gpa_scale=entry.gpa_scale)
    if not twin.coursework and entry.coursework:
        fill["coursework"] = entry.coursework
    if not twin.tools and entry.tools:
        fill["tools"] = entry.tools
    if twin.award_date is None and entry.award_date is not None:
        fill["award_date"] = entry.award_date
    if twin.start_month is None and twin.end_month is None and twin.end_kind is None:
        if entry.start_month or entry.end_month or entry.end_kind:
            fill.update(start_month=entry.start_month, end_month=entry.end_month, end_kind=entry.end_kind)
    elif twin.start_month is None and entry.start_month and twin.end_month == entry.end_month:
        fill["start_month"] = entry.start_month
    # A twin in another section takes only the fields its section holds.
    foreign = _SECTION_ONLY - set(SECTION_FIELDS.get(twin.section, ()))
    fill = {f: v for f, v in fill.items() if f not in foreign}
    if not fill:
        return
    try:
        filled = DraftEntry.model_validate({**twin.model_dump(), **fill})
    except ValidationError:
        return
    for field in fill:
        setattr(twin, field, getattr(filled, field))


def with_own_wording(reading: ModelReading, parsed: list[DraftEntry]) -> ModelReading:
    """The model's bullets that hold a placeholder, each in the words of the
    parser's bullet it matches (three in four of its other words). The seam
    removes every part of the student's name, in any case, even where it is
    a common word ("user flow" for a Test User, "landing page" for a Page),
    so the model echoes "[name]" where the resume has a word. The parser read
    the resume itself, so its bullet holds the resume's words; this swaps in
    a line of the resume, never a value for the placeholder. A bullet with
    no match keeps its placeholder, and `model_drafts` drops it."""
    own = [(set(_words(b)) - _COMMON, b) for entry in parsed for b in entry.bullets]
    for entry in reading.entries:
        entry.bullets = [_own_bullet(b, own) if placeholders_in(b) else b for b in entry.bullets]
    return reading


def _own_bullet(bullet: str, own: list[tuple[set[str], str]]) -> str:
    stripped = bullet
    for placeholder in PLACEHOLDERS:
        stripped = stripped.replace(placeholder, " ")
    words = set(_words(stripped)) - _COMMON
    if not words or not own:
        return bullet
    found, line = max(((len(words & theirs), line) for theirs, line in own), key=lambda pair: pair[0])
    return line if found * 4 >= len(words) * 3 else bullet


def _from_first_heading(text: str) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines[:_TOP_LINES]):
        if section_of(line):
            return "\n".join(lines[i:])
    return text


def _words(text: str) -> list[str]:
    """Lower-case words and numbers: "3.62" is "3" and "62", "C++" is "c"."""
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", text).casefold())


def _backed(value: str, words: set[str]) -> bool:
    """Whether the resume's words back a field the model wrote: every number
    in it is on the resume, and so is every word of a short one (three words
    or fewer, common words aside) and three in four of a longer one, so a
    word the PDF broke in two still passes."""
    own = [w for w in _words(value) if w not in _COMMON]
    if any(w.isdigit() and w not in words for w in own):
        return False
    found = sum(w in words for w in own)
    return found == len(own) if len(own) <= 3 else found * 4 >= len(own) * 3


def _number_backed(value: float, words: set[str]) -> bool:
    # 3.8 may be "3.8" or "3.80" on the resume
    return any(_backed(form, words) for form in (f"{value:g}", f"{value:.1f}", f"{value:.2f}"))


def _backed_fields(raw: dict, words: set[str]) -> dict:
    """The model's entry less what the resume's words do not back: a title,
    organization, location, bullet or course, all of the entry's dates when
    one names a year the resume lacks, and a GPA it lacks with its scale."""
    raw = {**raw}
    for field in _TEXT_FIELDS:
        if raw[field] and not _backed(raw[field], words):
            raw[field] = None
    raw["bullets"] = [b for b in raw["bullets"] if _backed(b, words)]
    raw["coursework"] = [c for c in raw["coursework"] if _backed(c, words)]
    raw["tools"] = [t for t in raw["tools"] if _backed(t, words)]
    if any(raw[f] and raw[f][:4] not in words for f in ("start_month", "end_month", "award_date")):
        raw.update(start_month=None, end_month=None, end_kind=None, award_date=None)
    if raw["gpa"] is not None and not _number_backed(raw["gpa"], words):
        raw.update(gpa=None, gpa_scale=None)
    return raw


def _degree_key(value: str) -> str:
    return _DEGREE_FORM_RE.sub(" ", value.replace("’", "'")).strip().lower()


def _title_key(title: str) -> str:
    return " ".join(_words(title))


def with_links(drafts: list[DraftEntry], parsed: list[DraftEntry]) -> list[DraftEntry]:
    """The model's projects with the links the parser read, since the model
    sees every URL as [link]: a project takes the link of the parser's
    project with its title, word for word or, two words or more, as the
    first words of the other's ("Line Robot" and "Line Robot | Robotics
    Club"; one word alone, "Line", is too little to tell)."""
    def starts(longer: str, shorter: str) -> bool:
        return " " in shorter and longer.startswith(f"{shorter} ")

    links = {_title_key(p.title): p.link for p in parsed if p.section is bank_section.projects and p.link}
    for draft in drafts:
        if draft.section is not bank_section.projects or draft.link:
            continue
        key = _title_key(draft.title)
        draft.link = links.get(key) or next(
            (link for k, link in links.items() if starts(k, key) or starts(key, k)), None
        )
    return drafts
