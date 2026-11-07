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
from app.schemas.bank import DraftEntry, ModelReading
from app.services import skill_catalog
from app.utils.resume_parser import parse_resume, section_of

_SHORT, _LONG, _NAME = 200, 500, 60
_COURSEWORK_RE = re.compile(r"^(?:Relevant\s+)?(?:Coursework|Courses)\s*:?\s*", re.IGNORECASE)
_GPA_LINE_RE = re.compile(r"^GPA\b", re.IGNORECASE)
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
    return drafts


def _valid(raw: dict) -> DraftEntry | None:
    if not raw.get("title"):
        return None
    try:
        return DraftEntry.model_validate(raw)
    except ValidationError:
        # Dates that do not fit together (an end before the start) are the
        # likely cause; the student can add them back in the editor.
        undated = {**raw, "start_month": None, "end_month": None, "end_kind": None}
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
    return draft_entries(parsed), skill_pairs(parsed_skills(parsed))


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
(clubs, activities, volunteering), "awards", "certifications".
- title: the role, school, project, award or certification name. \
organization: the company or group. Education: the school is the title.
- Months are "YYYY-MM". end_kind is "month" (ended), "present" (still going, \
no end_month) or "expected" (an expected end, such as graduation).
- bullets: the resume's bullet lines for that entry, one per item, unchanged.
- Education only: degree, field_of_study, gpa, gpa_scale, coursework, honors. \
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
        raw = {k: None if _withheld(v) else v for k, v in entry.model_dump().items()}
        for field in ("title", "organization", "location", "degree", "field_of_study", "issuer"):
            raw[field] = _clip(raw[field])
        raw["honors"] = _clip(raw["honors"], _LONG)
        raw["coursework"] = [c for c in (_clip(x) for x in raw["coursework"] if not _withheld(x)) if c][:40]
        # A bullet still holding a placeholder (`with_own_wording` found the
        # parser no match for it) would save "[name]" for good.
        raw["bullets"] = [b for b in (_clip(x, _LONG) for x in raw["bullets"]) if b and not _withheld(b)][:30]
        if words is not None:
            raw = _backed_fields(raw, words)
        if draft := _valid(raw):
            drafts.append(draft)
    return drafts


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
    """An upload's reading: the model's, checked against the text and with
    the parser's project links, else the parser's. The parser's when no
    model is given (no AI reading left today) or there is no text, and when
    the model fails, answers in the wrong shape, runs past
    MODEL_WAIT_SECONDS or keeps no entry the text backs. Never raises: an
    upload never fails because of its reading."""
    entries, skills = read(raw_text)
    parsed = Reading(entries, skills)
    if llm is None or identity is None or not raw_text:
        return parsed
    try:
        async with asyncio.timeout(MODEL_WAIT_SECONDS):
            reading = await read_with_model(_from_first_heading(raw_text), llm, identity=identity)
    except Exception as exc:
        # ScoutUnavailable (down, out of quota, the wrong shape), the wait
        # running out, or anything else: the parser's reading still stands.
        logger.warning("The model could not read a resume, so the parser's reading is saved: %r", exc)
        return parsed
    drafts = model_drafts(with_own_wording(reading, entries), raw_text)
    if not drafts:
        return parsed
    return Reading(with_links(drafts, entries), skill_pairs(model_skills(reading, raw_text)), "model")


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
    if any(raw[f] and raw[f][:4] not in words for f in ("start_month", "end_month", "award_date")):
        raw.update(start_month=None, end_month=None, end_kind=None, award_date=None)
    if raw["gpa"] is not None and not _number_backed(raw["gpa"], words):
        raw.update(gpa=None, gpa_scale=None)
    return raw


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
