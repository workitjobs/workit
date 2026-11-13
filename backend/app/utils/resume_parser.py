import itertools
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import ftfy  # fix broken unicode

from app.models.dto import (
    Award,
    Certification,
    Education,
    Experience,
    OtherSection,
    ParsedResume,
    Project,
    Skill,
)

# Constants
MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# "Aug. 2024" as well as "Aug 2024": Jake's template, and so WorkIt's own
# PDFs, end a short month in a period, and without it a re-uploaded WorkIt
# resume read "Acme Corp Aug." as the company and January as the month
MONTH = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?'

YEAR = r'(\d{4})'

# REGEX
DATE_RANGE_RE = re.compile(
    rf'(?:({MONTH})\s+)?{YEAR}\s*(?:[–\-—]|\bto\b)\s*(Present|Current|Now|(?:({MONTH})\s+)?{YEAR})',
    re.IGNORECASE,
)
# "Expected May 2027", "Expected Graduation: May 2027", "Anticipated Grad Date May 2027"
EXPECTED_RE = re.compile(
    rf'(?:Expected|Anticipated)(?:\s+(?:Graduation|Grad\.?)(?:\s+Date)?)?\s*:?\s*({MONTH})\s+{YEAR}',
    re.IGNORECASE,
)
# Bare "Month Year" ending a line or a "|" field — no range, no "Expected"
BARE_DATE_RE = re.compile(rf'({MONTH})\s+{YEAR}\s*(?=\||$)', re.IGNORECASE | re.MULTILINE)
# "Jun-Aug 2026": two months, one year. Whole month names only, so
# "Marketing - May 2026" is no range.
_MONTH_NAME = (r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|'
               r'Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?')
_SAME_YEAR_RANGE_RE = re.compile(rf'\b({_MONTH_NAME})\s*[–\-—]\s*({_MONTH_NAME})\s+(\d{{4}})\b', re.IGNORECASE)
# " - " between fields: "Company - Title - Dates" on one line
DASH_FIELDS_RE = re.compile(r'\s+[–—-]\s+')
# "Minor in Writing & Rhetoric", "Minor: Mathematics", ending at a field's end
MINOR_RE = re.compile(r'\bMinors?\s*(?:in\b|:)\s*(.+?)(?=\s{2,}|\s*\||\s*;|\s+[–—-]\s|\s*\bGPA\b|\n|$)', re.IGNORECASE)

# Section headings, from career-center guides (KAN-348). One term is one
# section's name; a heading is terms joined by "&" or "and", and may end in
# any one word ("Skills & Abilities"). The first term decides the section
# (`_section_name`). A heading the parser does not know is no section: its
# text joins the section above it, which made a lab and a paper read as
# schools.
_PREFIX = (
    r'(?:Work|Professional|Research|Relevant|Related|Career\s+Related|Additional|Other|'
    r'Internship|Technical|Engineering|Industry|Teaching|Clinical|Freelance|Academic|'
    r'Volunteer|Leadership|Management|Software|Previous|Selected)'
)
_TERM = (
    r'(?:'
    # jobs and lab roles
    rf'(?:{_PREFIX}\s+(?:&|and)\s+)?(?:{_PREFIX}\s+)?Experiences?|'
    r'Internships?|Employment(?:\s+History)?|Work\s+History|Professional\s+Background|Research|'
    # papers, which import keeps as projects
    r'(?:Research\s+)?Publications?|Papers|(?:Conference\s+)?Presentations|Patents|'
    # clubs, activities and volunteering; "Leadership Activities" has no "&"
    # between its words, and was no heading until KAN-263
    r'(?:(?:Campus|Student|Community)\s+)?Leadership'
    r'(?:\s+(?:Activities|Roles?|Positions?|Involvement))?|'
    r'Extracurricular\s+Activities|Extracurriculars|'
    r'(?:Campus|Community|Athletic)\s+Involvement|Involvement|Activities|'
    r'Volunteer(?:ing|\s+Work)?|Community\s+(?:Service|Engagement)|'
    r'(?:Professional\s+)?(?:Affiliations|Memberships)|(?:Student\s+)?Organizations|Athletics|'
    r'Education|Educational\s+(?:Background|Qualifications)|Academic\s+Background|'
    r'(?:Professional\s+)?Training|(?:Relevant\s+)?Coursework|Relevant\s+Courses|'
    r'(?:(?:Personal|Academic|Technical|Engineering|University|Course|Related\s+Course|'
    r'Selected|Side|Research|Software|Independent|Class)\s+)?Projects?|Portfolio|Hackathons|'
    r'(?:Technical\s+|Core\s+)?Skills(?:\s+Summary)?|Technologies|Technical\s+Proficiencies|'
    r'(?:Core\s+)?Competencies|(?:Programming\s+)?Languages|Tools|'
    r'(?:Professional\s+)?Certifications?|Certificates|Licenses|'
    r'Awards?|Honors?|Achievements|Scholarships|Recognition|'
    # found but not saved
    r'(?:Professional\s+)?Summary|Summary\s+of\s+Qualifications|Qualifications|'
    r'(?:Career\s+)?Objective|Profile|About\s+Me|Interests|Hobbies|'
    r'Additional\s+Information|References|Other'
    r')'
)
SECTION_RE = re.compile(rf'{_TERM}(?:\s+(?:&|and)\s+{_TERM})*(?:\s+(?:&|and)\s+\w+)?', re.IGNORECASE)
COURSEWORK_RE = re.compile(r'(?:Relevant\s+)?(?:Coursework|Courses)\b', re.IGNORECASE)
# "E X P E R I E N C E": one letter at a time, words two spaces apart
_SPACED_RE = re.compile(r'[A-Za-z](?: [A-Za-z&])+(?:\s{2,}[A-Za-z](?: [A-Za-z&])+)*')

# "GPA: 3.81/4.00" gives the scale too
GPA_RE = re.compile(r'GPA[:\s]*(\d+(?:\.\d+)?)(?:\s*/\s*(\d+(?:\.\d+)?))?', re.IGNORECASE)
DEGREE_RE = re.compile(
    # A.A./A.S. need the dot, or the word "as" would count as a degree
    r'\b(B\.?S\.?|B\.?A\.?|M\.?S\.?|M\.?A\.?|A\.A\.?|A\.S\.?|Ph\.?D\.?|'
    r'B\.?Sc\.?|M\.?Sc\.?|B\.?Eng\.?|M\.?Eng\.?|B\.?B\.?A\.?|M\.?B\.?A\.?|B\.?F\.?A\.?|M\.?F\.?A\.?|'
    # the whole "Bachelor of Science" or "Bachelor of Computer Science", not
    # just "Bachelor": up to three capitalized words after "of", case
    # sensitive inside, so "in" ends it
    r"(?:Bachelor|Master|Associate)(?:'?s)?(?:\s+of\s+(?-i:[A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*){0,2}))?|"
    r'Doctorate|(?:High\s+School\s+)?Diploma|GED)'
    # not \b: after "B.S." the next character is a space, and a word
    # boundary cannot fall between "." and a space, so the match backed up
    # to "B.S" and every abbreviated degree lost its last period
    r'(?!\w)',
    re.IGNORECASE,
)
INSTITUTION_RE = re.compile(r'\b(?:University|College|School|Institute|Academy)\b', re.IGNORECASE)
DEGREE_FIELD_RE = re.compile(
    r'\b(?:(?P<abbr>B\.?S\.?|B\.?A\.?|M\.?S\.?|M\.?A\.?|A\.A\.?|A\.S\.?|Ph\.?D\.?|B\.?Sc\.?|M\.?Sc\.?|'
    r'B\.?Eng\.?|M\.?Eng\.?|B\.?B\.?A\.?|M\.?B\.?A\.?|B\.?F\.?A\.?|M\.?F\.?A\.?)(?!\w)|'
    r"(?:Bachelor|Master|Associate)(?:'?s)?)"
    r'(?:\s+of\s+(?-i:[A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*){0,2}))?(?:\s+degree)?'
    # "B.S. in X", "B.S., X", "Bachelor's in X", and after an abbreviation
    # the field with nothing between: "B.S. Computer Science"
    r'(?:\s+in\s+|,\s*|(?(abbr)\s+(?=[A-Z])|(?!)))(?P<field>[^|;,\n]+)',
    re.IGNORECASE,
)
# "Specialization in AI/ML", "Concentration: Finance": kept after the major,
# as a minor is
SPECIALIZATION_RE = re.compile(
    r'\b(Specialization|Concentration|Emphasis)\s*(?:in\b|:)\s*(.+?)(?=\s{2,}|\s*\||\s*;|\s+[–—-]\s|\s*\bGPA\b|\n|$)',
    re.IGNORECASE,
)
# catch bullet points; a hyphen before a digit is a minus sign ("-20%"), not one
BULLET_RE = re.compile(r'^\s*(?:[•▪●◦·]|-(?!\d))\s*')
URL_RE = re.compile(r'https?://\S+|github\.com/\S+', re.IGNORECASE)

# ponytail: keyword list — add words as real resumes expose gaps
ROLE_KEYWORDS = re.compile(
    r'\b(?:Engineer|Developer|Intern|Manager|Director|Analyst|Designer|Architect|'
    r'Researcher|Fellow|Assistant|Associate|Lead|Senior|Junior|'
    r'Coordinator|Specialist|Consultant|Administrator|Scientist|'
    r'Officer|President|Head|Chief|Technician|Scribe|Support|'
    r'Advisor|Tutor|Representative|Operator|Strategist|'
    # a club's roles: "Chess Club – Treasurer" splits as "Company - Title"
    r'Treasurer|Secretary|Captain|Chair|Chairperson|Founder|Co-Founder|Mentor|'
    r'Volunteer|Organizer|Ambassador|Editor|Coach|Instructor)\b',
    re.IGNORECASE,
)

# US state/territory codes for location detection (US only for now)
US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR", "GU", "VI", "AS", "MP",
}
# Places written out after a PDF gap: "Stony Brook, New York", "Toronto, ON",
# "Incheon, South Korea". Only after the gap, where a right-aligned place
# sits; without one these words could be part of a name.
US_STATE_NAMES = {
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
    "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming", "Puerto Rico",
    "District of Columbia",
}
CA_PROVINCES = {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"}
COUNTRIES = {
    "USA", "United States", "Canada", "Mexico", "Brazil", "Argentina", "Chile", "Colombia", "Peru",
    "United Kingdom", "UK", "England", "Scotland", "Ireland", "France", "Germany", "Spain", "Portugal",
    "Italy", "Netherlands", "Belgium", "Switzerland", "Austria", "Denmark", "Sweden", "Norway",
    "Finland", "Poland", "Greece", "Turkey", "Israel", "United Arab Emirates", "UAE", "Saudi Arabia",
    "Qatar", "Egypt", "Nigeria", "Ghana", "Kenya", "South Africa", "India", "Pakistan", "Bangladesh",
    "Sri Lanka", "Nepal", "China", "Hong Kong", "Taiwan", "Japan", "South Korea", "Korea",
    "Singapore", "Malaysia", "Indonesia", "Philippines", "Thailand", "Vietnam", "Australia",
    "New Zealand",
}
# City is 1-2 words (caps-initial, may contain periods/hyphens), then ", ST"
LOCATION_RE = re.compile(r'([A-Z][\w.\-]*(?:\s+[A-Z][\w.\-]*){0,1},\s*([A-Z]{2}))\s*$')

def parse_resume(raw_text: str) -> ParsedResume | None:
    """
    Split resume into sections and parse each section
    individually with specific parsers
    """
    text = _clean_text(raw_text)
    headings: dict[str, str] = {}
    sections = _split_sections(text, headings)
    if not sections:
        return None
    return ParsedResume(
        education=_parse_education(sections.get("education", "")),
        experience=_parse_experience(sections.get("experience", "")),
        skills=_parse_skills(sections.get("skills", "")),
        # the bank has no Publications section: a paper is a project (KAN-348)
        projects=_parse_projects(sections.get("projects", ""))
        + _parse_publications(sections.get("publications", "")),
        certifications=_parse_certifications(sections.get("certifications", "")),
        # club roles read like jobs: organization, role, dates, bullets
        leadership=_parse_experience(sections.get("leadership", "")),
        awards=_parse_awards(sections.get("awards", "")),
        others=[
            OtherSection(heading=_display_heading(headings[name]), lines=lines)
            for name, body in sections.items()
            if name not in _READ and not name.startswith(_NOT_KEPT) and (lines := _plain_lines(body))
        ],
    )


# The sections parse_resume reads into the bank's own sections; any other
# heading is kept as it stands (KAN-498), but "References" ("available upon
# request"), which says nothing about the student
_READ = {"education", "experience", "skills", "projects", "publications", "certifications", "leadership", "awards"}
_NOT_KEPT = "reference"
# Words a heading keeps in lower case once it is put in title case
_SMALL_WORDS = {"of", "and", "&", "in", "the", "for", "to", "a", "an", "on"}


def _display_heading(heading: str) -> str:
    """A heading as a section's name: "INTERESTS" and "interests" read as
    "Interests", "SUMMARY OF QUALIFICATIONS" as "Summary of Qualifications";
    one in mixed case keeps the resume's own."""
    if heading != heading.upper() and heading != heading.lower():
        return heading
    words = heading.lower().split()
    return " ".join(w if i and w in _SMALL_WORDS else w[:1].upper() + w[1:] for i, w in enumerate(words))


# A line at least this long filled the column, so the next one continues it
_FULL_LINE = 70


def _plain_lines(text: str) -> list[str]:
    """A section with no shape of its own as lines (KAN-498). With bullet
    markers, as `_bullets` reads them. Without, each line is its own unless
    it continues the one above: it starts in lower case, or the line above
    ends in a comma or filled the column, as a wrapped summary does. So a
    paragraph reads as one line and a list of interests as several."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if any(BULLET_RE.match(ln) for ln in lines):
        return (_bullets(lines) or "").splitlines()
    parts: list[str] = []
    above = ""
    for line in lines:
        wrapped = len(above) >= _FULL_LINE and not above.endswith((".", "!", "?"))
        if parts and (line[0].islower() or above.endswith(",") or wrapped):
            parts[-1] += " " + line
        else:
            parts.append(line)
        above = line
    return [re.sub(r"\s{2,}", " ", p) for p in parts]

def count_sections(text: str) -> int:
    """How many section headers sit on lines of their own — the extractor
    uses this to tell which PDF extraction mode kept the structure intact."""
    return sum(1 for line in text.splitlines() if section_of(line))


def section_of(line: str) -> str | None:
    """The section a heading line names ("experience", or the heading itself
    for a section import does not save), or None for a body line. The rules
    decide first; a heading they miss is looked up in the learned labels."""
    s = heading_form(line)
    if not s:
        return None
    if SECTION_RE.fullmatch(s):
        return _section_name(s)
    label = LEARNED.get(learned_key(s))
    if label is None or label == "none":
        return None
    # a section import does not save keeps its own name, as with the rules
    return learned_key(s) if label == "other" else label


def heading_form(line: str) -> str:
    """A line as a heading reads once its format is off, or "" for a bullet."""
    s = line.strip()
    # a bullet is a body line, whatever it says
    if not s or s.startswith("•"):
        return ""
    if _SPACED_RE.fullmatch(s):
        s = " ".join(word.replace(" ", "") for word in re.split(r"\s{2,}", s))
    # "Education:", "EXPERIENCE ____", "— Experience —", "■ Experience", "01 Experience"
    s = re.sub(r"^[^A-Za-z]+|[^A-Za-z]+$", "", s)
    # "Honors / Awards" is "Honors & Awards"
    return re.sub(r"\s*/\s*", " & ", s)


def learned_key(heading: str) -> str:
    return " ".join(heading.casefold().split())


# Headings no rule names, labeled once by a model from a reviewed word list
# (app/scripts/label_resume_headings.py, the scraper's learned headings for
# resumes). A committed file, never a call at upload: ADR 0003 keeps the
# model off a resume the student has not asked it to read.
LEARNED_PATH = Path(__file__).with_name("learned_headings.json")
# the sections import reads, "other" for one it does not save, "none" for no heading
LEARNED_LABELS = (
    "education", "experience", "leadership", "awards", "skills", "projects",
    "certifications", "publications", "other", "none",
)


def _load_learned() -> dict[str, str]:
    if not LEARNED_PATH.exists():
        return {}
    labels = json.loads(LEARNED_PATH.read_text(encoding="utf-8")).get("labels", {})
    return {learned_key(heading): label for heading, label in labels.items() if label in LEARNED_LABELS}


LEARNED = _load_learned()


def fix_symbols(text: str) -> str:
    """Characters a PDF's math or symbol fonts put in a resume's text, as
    the resume means them; the model's reading gets the same text
    (`bank_import.read_resume`). A ring after a number is a degree sign:
    LaTeX's "$^\\circ$" reads as "◦", which became a bullet, so "2.75° to
    1.01°" printed "2.75 • to 1.01 •". U+223C TILDE OPERATOR, which resume
    fonts often lack ("∼120ms"), is a tilde, set apart from the word before
    it, since math spacing put the gap there that text extraction drops
    ("to∼40 ms" read "to~40 ms")."""
    text = re.sub(r'(?<=\d)\s?[◦∘º˚](?![\w])', '°', text)
    text = text.replace('∼', '~')
    return re.sub(r'(?<=[A-Za-z])~(?=\d)', ' ~', text)


# A season where a date goes: in a range ("Spring 2024 – Present"), after
# "Expected", or alone after a PDF gap at a line's end ("Dean's List  Fall
# 2023"). Never inside a sentence: "in Fall 2026, picked 13 of 101" stays.
_SEASON = r'(Spring|Summer|Fall|Autumn|Winter)'
_SEASON_START_RE = re.compile(rf'\b{_SEASON}\s+(\d{{4}})(?=\s*(?:[–\-—]|\bto\b))', re.IGNORECASE)
_SEASON_END_RE = re.compile(
    rf'((?:[–\-—]|\bto\b|\bExpected|\bAnticipated)\s*|\s{{2,}}){_SEASON}\s+(\d{{4}})(?=\s*(?:\||$))',
    re.IGNORECASE | re.MULTILINE,
)
# A season's month: its first as a start, its last as an end (a spring
# graduation is in May). The bank holds months, so the season's word goes.
_SEASON_STARTS = {"spring": "Jan", "summer": "Jun", "fall": "Sep", "autumn": "Sep", "winter": "Dec"}
_SEASON_ENDS = {"spring": "May", "summer": "Aug", "fall": "Dec", "autumn": "Dec", "winter": "Feb"}
# "06/2024": a month and year in numbers
_NUMERIC_MONTH_RE = re.compile(r'\b(0?[1-9]|1[0-2])/(\d{4})\b')
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
# Bullet glyphs from Word's and Docs' symbol fonts (U+F0B7 is Word's
# Symbol-font bullet). Not "■" or "❖", which also mark section headings.
_BULLET_GLYPHS_RE = re.compile(r'[▪●◦·➢►▸➤✓✔\uf0b7\uf0a7\uf076\uf0d8]')


def _clean_text(text: str) -> str:
    # use library to clean up text
    text = ftfy.fix_text(text)
    # before the bullets: a ring after a number is a degree sign
    text = fix_symbols(text)
    text = _BULLET_GLYPHS_RE.sub('•', text)
    # "* Built a ..." (a plain-text resume's bullet)
    text = re.sub(r'^(\s*)\*\s+', r'\1• ', text, flags=re.MULTILINE)
    text = _NUMERIC_MONTH_RE.sub(lambda m: f"{_MONTHS[int(m[1]) - 1]} {m[2]}", text)
    text = _SEASON_START_RE.sub(lambda m: f"{_SEASON_STARTS[m[1].lower()]} {m[2]}", text)
    text = _SEASON_END_RE.sub(lambda m: f"{m[1]}{_SEASON_ENDS[m[2].lower()]} {m[3]}", text)
    # "Jun-Aug 2026" is "Jun 2026 - Aug 2026": a range in one year names it
    # once, and only "Aug 2026" was read, as the end
    text = _SAME_YEAR_RANGE_RE.sub(r'\1 \3 - \2 \3', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# Split sections so each category is parsed individually by its own parser
def _split_sections(text: str, headings: dict[str, str] | None = None) -> dict[str, str]:
    """Each section's text by its name. `headings`, when given, gets each
    name's heading as the resume first wrote it, format off."""
    sections: dict[str, list[str]] = {}             # store text based on sections
    lines: list[str] | None = None                  # text before the first header goes
    for line in text.splitlines():
        name = section_of(line)
        if name:
            if headings is not None:
                headings.setdefault(name, heading_form(line))
            # two headers can name one section (Experience, Research Experience):
            # keep both, or the second replaces the first
            lines = sections.setdefault(name, [])
            # the school's parser finds its courses by this label, and its
            # colon carries the list on the next line onto it
            if COURSEWORK_RE.match(heading_form(line)):
                lines.append(heading_form(line) + ":")
        elif lines is not None:
            lines.append(line)
    return {name: "\n".join(body).strip() for name, body in sections.items()}


# Which section a heading's first term names, checked in this order: each
# word comes before a later one it shares a heading with ("Research
# Projects" are projects, "Leadership Experience" is no job, "Coursework"
# holds "work")
_SECTION_WORDS = [
    ("publications", ("publication", "paper", "presentation", "patent")),
    ("projects", ("project", "portfolio", "hackathon")),
    ("leadership", ("leadership", "activit", "extracurricular", "involvement", "volunteer",
                    "community", "affiliation", "membership", "organization", "athletic")),
    ("awards", ("award", "honor", "achievement", "scholarship", "recognition")),
    ("certifications", ("certif", "license")),
    ("education", ("education", "coursework", "course", "training", "academic background")),
    # a lab role reads like a job: organization, role, dates, bullets
    ("experience", ("experience", "internship", "employment", "work", "background", "research")),
    ("skills", ("skill", "technolog", "proficienc", "competenc", "language", "tool")),
]


def _section_name(heading: str) -> str:
    # the first part decides: "Experience & Leadership" is Experience
    first = re.split(r"\s+(?:&|and)\s+", heading.lower())[0]
    for name, words in _SECTION_WORDS:
        if any(w in first for w in words):
            return name
    # a section import does not save keeps its own name ("hobbies")
    return " ".join(heading.lower().split())


def _month_to_int(month_str: str) -> int:
    return MONTH_MAP.get(month_str[:3].lower(), 1)


def _to_date(year: str, month: str | None) -> date | None:
    return date(int(year), _month_to_int(month) if month else 1, 1)


def _parse_date_range(text: str) -> tuple[date | None, date | None]:
    m = EXPECTED_RE.search(text)
    if m:
        return None, _to_date(m.group(2), m.group(1))
    m = DATE_RANGE_RE.search(text)
    if not m:
        # Bare "Month Year" with no range — treat as end date only
        b = BARE_DATE_RE.search(text)
        if b:
            return None, _to_date(b.group(2), b.group(1))
        return None, None
    start = _to_date(m.group(2), m.group(1))
    # keep present as null
    if m.group(3).lower() in ("present", "current", "now"):
        return start, None
    return start, _to_date(m.group(5), m.group(4))


def _extract_location(text: str) -> tuple[str | None, str]:
    """Extract 'City, ST' from the end of a line. Returns (location, remainder).
    Tries multi-space separator first (common in PDF extraction), then falls
    back to regex-only matching at the end of the line."""
    # Pass 1: multi-space separator (PDF extraction preserves these).
    # City words are single-space separated so the match starts at the last gap.
    ms = re.search(r"\s{2,}([\w.'’-]+(?: [\w.'’-]+)*,\s*([A-Z][A-Za-z]*(?: (?:of )?[A-Z][A-Za-z]*)*))\s*$", text)
    if ms and (ms.group(2) in US_STATES or ms.group(2) in US_STATE_NAMES
               or ms.group(2) in CA_PROVINCES or ms.group(2) in COUNTRIES):
        location = ms.group(1).strip()
        remainder = text[:ms.start()].strip().rstrip("|–—-").strip()
        return location, remainder
    # "Remote" after a PDF gap is the location too
    ms = re.search(r'\s{2,}(Remote|Hybrid)\s*$', text, re.IGNORECASE)
    if ms:
        return ms.group(1), text[:ms.start()].strip().rstrip("|–—-").strip()
    # Pass 2: constrained end-of-line match (1-2 word city)
    m = LOCATION_RE.search(text)
    if m and m.group(2) in US_STATES:
        location = m.group(1).strip()
        remainder = text[:m.start()].strip().rstrip("|–—-").strip()
        return location, remainder
    return None, text


def _is_header_line(line: str) -> bool:
    """A header line (company/org name) starts with an uppercase letter.
    Bullet continuations from PDF line-wrapping start lowercase."""
    stripped = line.strip()
    if not stripped or BULLET_RE.match(stripped):
        return False
    return stripped[0].isupper()


def _has_date(line: str) -> bool:
    return bool(DATE_RANGE_RE.search(line) or EXPECTED_RE.search(line) or BARE_DATE_RE.search(line))


def _strip_dates(line: str) -> str:
    # also drops a "|" left dangling where the dates were ("Title | May 2024")
    return BARE_DATE_RE.sub("", DATE_RANGE_RE.sub("", line)).strip().rstrip(",|–—-").strip()


def split_tools(text: str) -> tuple[str, list[str]]:
    """"Name | C++, Python": a list after the last bar is the tools, and the
    name keeps what comes before it ("Robot | Club| C++, Go" keeps "Robot |
    Club"). A single phrase there is a subtitle ("WorkIt | Recruiting
    Platform") and stays in the name."""
    head, bar, tools = text.rpartition("|")
    if bar and "," in re.sub(r'\(.*?\)', '', tools) and not URL_RE.search(tools):
        return head.strip(), [t.strip() for t in tools.split(",") if t.strip()]
    return text, []


def _split_title_company(text: str) -> tuple[str, str] | None:
    """'Title | Company' or 'Company | Title' — the role keyword decides
    which side is the title; with no keyword on either side, title first."""
    parts = [p.strip() for p in text.split("|")]
    if len(parts) != 2 or not all(parts):
        return None
    if ROLE_KEYWORDS.search(parts[1]) and not ROLE_KEYWORDS.search(parts[0]):
        return parts[1], parts[0]
    return parts[0], parts[1]


_TOOLS_LABEL_RE = re.compile(r'^(?:tech(?:nologies|nology)?(?:\s+stack)?|stack|tools|built\s+with)\s*:\s*', re.IGNORECASE)


def tool_items(text: str) -> list[str]:
    """A tools line's tools: its comma list, less a "Tech Stack:" label, never
    split inside parentheses ("Supabase (PostgreSQL), Gemini API")."""
    rest = _TOOLS_LABEL_RE.sub("", text.strip())
    return [t.strip() for t in re.split(r',(?![^()]*\))', rest) if t.strip()]


def is_tools_line(text: str) -> bool:
    """A line that only lists tools: three or more short comma items ("Next.js,
    TypeScript, Tailwind CSS"), none over four words, and no full stop at the
    end. A bullet's sentence fails on its longer clauses."""
    items = tool_items(text)
    return (len(items) >= 3 and not text.rstrip().endswith(".")
            and all(len(t) <= 40 and len(t.split()) <= 4 for t in items))


def _split_dash_title_company(text: str) -> tuple[str, str] | None:
    """'Company - Title' or 'Title - Company' left of an entry's dates. Only
    when the role keyword is on one side alone: "Software Engineer -
    Backend" names no company, and stays one title."""
    parts = DASH_FIELDS_RE.split(text.strip())
    if len(parts) != 2 or not all(parts):
        return None
    roles = [bool(ROLE_KEYWORDS.search(p)) for p in parts]
    if roles == [True, False]:
        return parts[0], parts[1]
    if roles == [False, True]:
        return parts[1], parts[0]
    return None


def _is_bare_date_line(line: str) -> bool:
    """Only dates, plus maybe a location — the entry's title and company sit
    on the lines above it rather than beside the date."""
    return not _extract_location(_strip_dates(line))[1]


def _header_start(lines: list[str], anchor: int) -> int:
    """First line of the entry whose date line is lines[anchor]. Usually one
    header line (company/org); two when the date line is bare (Title /
    Company / Dates). PDF extraction wraps long bullets into continuation
    lines that lack a bullet marker — looking further back risks pulling
    those fragments in as the company name."""
    start = anchor
    # a dated line above is its own entry, not this one's header
    if anchor > 0 and _is_header_line(lines[anchor - 1]) and not _has_date(lines[anchor - 1]):
        start -= 1
        # a "Title | Company" line already holds both
        if (_is_bare_date_line(lines[anchor]) and start > 0
                and not _split_title_company(lines[start])
                and _is_header_line(lines[start - 1])
                and not lines[start - 1].rstrip().endswith(".")):
            start -= 1
    return start


def _split_entries(text: str) -> list[list[str]]:
    """
    Split a section into entries. Each date-bearing non-bullet line anchors an entry.
    Non-bullet, non-date lines immediately before a date line are that entry's header.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []

    # Find indices of date-bearing lines.
    # Full date ranges (Jan 2024 - Dec 2024) are always anchors.
    # Bare dates (May 2025) need the header check — PDF continuation
    # lines like "completing the rollout by May 2025" are NOT anchors.
    anchors: list[int] = []
    for i, ln in enumerate(lines):
        if BULLET_RE.match(ln):
            continue
        if (DATE_RANGE_RE.search(ln) or EXPECTED_RE.search(ln)
                or (BARE_DATE_RE.search(ln) and _is_header_line(ln))):
            anchors.append(i)

    if not anchors:
        # No dates found — return everything as one entry
        return [lines]

    entries: list[list[str]] = []
    for ai, anchor in enumerate(anchors):
        # everything before the first anchor is its header
        header_start = 0 if ai == 0 else _header_start(lines, anchor)
        # Content: everything after this anchor up to the next entry's header
        if ai + 1 < len(anchors):
            content_end = _header_start(lines, anchors[ai + 1])
        else:
            content_end = len(lines)

        entries.append(lines[header_start:content_end])

    return entries


def _bullets(lines: list[str]) -> str | None:
    """Join bullet lines and their PDF-wrapped continuations."""
    # Some PDFs draw bullets as shapes, so no marker reaches the text. Then a
    # line that opens a new sentence after a full stop starts a new item: any
    # line not starting lowercase, so "-20% churn" or "3 launches" counts.
    has_markers = any(BULLET_RE.match(ln.strip()) for ln in lines if ln.strip())
    parts: list[str] = []
    for ln in lines:
        stripped = ln.strip()
        if not stripped:
            continue
        if BULLET_RE.match(stripped):
            parts.append(BULLET_RE.sub("", stripped).strip())
        elif not has_markers and (not parts or (parts[-1].endswith(".") and not stripped[0].islower())):
            parts.append(stripped)
        elif parts:
            # Continuation of previous bullet (PDF line wrap)
            parts[-1] += " " + stripped
        else:
            # Text before the first marker has nothing to continue: keep it
            parts.append(stripped)
    # a run of spaces inside a line is a PDF gap (after a bold phrase), not wording
    return "\n".join(re.sub(r'\s{2,}', ' ', p) for p in parts) if parts else None


# A label that starts a new line of a school's text inside a wrapped one:
# "..., Artificial Intelligence Honors: Dean's List"
_EDUCATION_LABEL_RE = re.compile(r'\s+(?=(?:Honors|Awards|Activities|Achievements|Distinctions)\s*:)')


def _school_on_date_line(lines: list[str]) -> bool:
    """An entry whose date line names its school ("Lakeside Global
    Campus  February 2026 – June 2026") while the lines above it name no
    school or degree: those lines are the school before's, wrapped or left
    over ("…, Artificial" / "Intelligence Honors: Dean's List")."""
    anchor = next((i for i, ln in enumerate(lines) if _has_date(ln)), 0)
    if anchor == 0:
        return False
    above = lines[:anchor]
    if any(INSTITUTION_RE.search(ln) or DEGREE_RE.search(ln) for ln in above):
        return False
    name = _strip_dates(EXPECTED_RE.sub("", lines[anchor].split("|")[0]))
    return bool(name) and not DEGREE_RE.search(name) and not GPA_RE.search(name)


def _parse_education(text: str) -> list[Education]:
    if not text.strip():
        return []
    entries = _split_entries(text)
    # A school named on its own date line: the lines above it go back to
    # the school before. Before, they became this school's name, and the
    # school's own name was lost (a real resume, 2026-11-12).
    for i in range(1, len(entries)):
        if entries[i] and _school_on_date_line(entries[i]):
            anchor = next(j for j, ln in enumerate(entries[i]) if _has_date(ln))
            entries[i - 1] = entries[i - 1] + entries[i][:anchor]
            entries[i] = entries[i][anchor:]
    results: list[Education] = []
    for lines in entries:
        if not lines:
            continue
        first = lines[0]
        all_text = "\n".join(lines)

        # Institution: usually the first field, but "Degree / School / Dates"
        # and "Degree | Dates | School" put it later — prefer a header line or
        # "|" field naming a school, not a degree
        anchor = next((i for i, ln in enumerate(lines)
                       if _has_date(ln)), 0)
        fields = [f.strip() for ln in lines[:anchor + 1] for f in ln.split("|")]
        named = next((f for f in fields if INSTITUTION_RE.search(f) and not DEGREE_RE.search(f)), None)
        inst_field = named or first.split("|")[0]
        inst = _strip_dates(EXPECTED_RE.sub("", inst_field)) or inst_field.strip()
        # The school's place: after a gap or as its own "|" field. It stayed
        # in the name ("Stony Brook University Stony Brook, NY"), or was lost
        location, rest = _extract_location(inst)
        if location:
            inst = rest
        else:
            location = next((loc for f in fields
                             for loc, left in [_extract_location("  " + _strip_dates(f))] if loc and not left), None)
        # A second degree at the school above ("M.S. ...  Expected May 2028"
        # / "B.S. ...  Expected May 2027" under one name): the same school.
        # Before, the degree line became a school of its own.
        if named is None and DEGREE_RE.search(inst) and results:
            inst, location = results[-1].institution, location or results[-1].location
        # "School - B.S. Computer Science - May 2028 - GPA 3.7" on one line:
        # the school is the dash fields before the degree, so "University of
        # Wisconsin - Madison - B.S." keeps "Madison"
        dash_fields = DASH_FIELDS_RE.split(first)
        if "|" not in first and len(dash_fields) > 2 and DEGREE_RE.search(inst):
            school = list(itertools.takewhile(
                lambda f: not (DEGREE_RE.search(f) or _has_date(f) or GPA_RE.search(f)), dash_fields))
            inst = " - ".join(school).strip() or inst

        # Dates: the start too, which was dropped, so "Aug 2023 - May 2027"
        # printed "May 2027" alone
        start, end = _parse_date_range(all_text)
        if end is None:
            # "... - May 2028 - GPA 3.7": a dash field, not a line's end
            end = next((e for f in dash_fields if (e := _parse_date_range(f.strip())[1])), None)

        # GPA
        gpa_m = GPA_RE.search(all_text)
        gpa = float(gpa_m.group(1)) if gpa_m else None
        gpa_scale = float(gpa_m.group(2)) if gpa_m and gpa_m.group(2) else None

        # Degree, read with each "City, ST" out of the way: "Boston, MA"
        # read as a master's degree
        degree_text = re.sub(r',\s*[A-Z]{2}\b', ',', all_text)
        deg_m = DEGREE_RE.search(degree_text)
        degree = deg_m.group(1) if deg_m else None

        # Field of study: look for "Major(s):" or ": <field>" pattern, or text after degree
        field = None
        for ln in lines[1:]:
            # "Major:", "Majors:", "Majors (B.S.):"
            m = re.search(r'Majors?\s*(?:\([^)]*\))?\s*:\s*(.*?)(?:GPA|$)', ln, re.IGNORECASE)
            if m and m.group(1).strip():
                field = re.sub(r'\s*;.*', '', m.group(1).strip())
                break
        if field is None:
            # "B.S. in Computer Science", "Bachelor of Science in X", "B.S., X"
            m = DEGREE_FIELD_RE.search(degree_text)
            if m and m.group("field").strip():
                # "Computer Science  GPA: 3.81/4.00": the field ends at a PDF gap or the GPA
                field = re.split(r'\s{2,}|\s*\bGPA\b', m.group("field").strip(), flags=re.IGNORECASE)[0].strip()
                # nor a date: "B.S. Expected May 2027" names no field
                field = _strip_dates(EXPECTED_RE.sub("", field)) or None
        # "B.S. in Computer Science | Minor in Writing & Rhetoric": the minor goes
        # after the major, since an entry has no field of its own for it, and it
        # was dropped
        minor = MINOR_RE.search(all_text)
        if field and minor and "minor" not in field.lower():
            field = f"{field}, minor in {minor.group(1).strip()}"
        # a specialization the same way: "Computer Science, specialization in
        # AI/ML" (the comma ended the field, and it was dropped)
        special = SPECIALIZATION_RE.search(all_text)
        if field and special and special.group(1).lower() not in field.lower():
            field = f"{field}, {special.group(1).lower()} in {special.group(2).strip()}"

        # Description: coursework + other non-header lines
        desc_parts: list[str] = []
        for ln in lines[1:]:
            stripped = ln.strip()
            if COURSEWORK_RE.match(stripped):
                desc_parts.append(stripped)
            elif BULLET_RE.match(stripped):
                desc_parts.append(BULLET_RE.sub("", stripped).strip())
            elif desc_parts and (desc_parts[-1].endswith((",", ":")) or stripped[0].islower()
                                 or (COURSEWORK_RE.match(desc_parts[-1]) and len(desc_parts[-1]) >= 60
                                     and not desc_parts[-1].endswith("."))):
                # a PDF-wrapped coursework or bullet line, or the list
                # under a "Relevant Coursework:" heading; a long course list
                # wraps mid-name ("…, Artificial" / "Intelligence")
                desc_parts[-1] += " " + stripped
        # "Honors:" wrapped onto a course list's last line starts its own line
        desc_parts = [part for d in desc_parts for part in _EDUCATION_LABEL_RE.split(d)]
        desc = "\n".join(re.sub(r'\s{2,}', ' ', d) for d in desc_parts) if desc_parts else None

        results.append(Education(
            institution=inst, degree=degree, field_of_study=field, location=location,
            gpa=gpa, gpa_scale=gpa_scale, start_date=start, end_date=end, description=desc,
        ))
    return results


def _parse_experience(text: str) -> list[Experience]:
    if not text.strip():
        return []
    entries = _split_entries(text)
    results: list[Experience] = []
    for lines in entries:
        if not lines:
            continue

        # Find the line with the date range
        date_idx = None
        for i, ln in enumerate(lines):
            if (DATE_RANGE_RE.search(ln) or BARE_DATE_RE.search(ln)) and not BULLET_RE.match(ln):
                date_idx = i
                break
        if date_idx is None:
            continue

        date_line = lines[date_idx]
        start, end = _parse_date_range(date_line)

        # Detect layout: if the line AFTER the date has a role keyword,
        # then date_line = company, next line = title + location.
        # Otherwise: line above = company, date_line = title.
        next_idx = date_idx + 1
        next_line = lines[next_idx].strip() if next_idx < len(lines) else ""
        title_below = bool(next_line
                           and not BULLET_RE.match(next_line)
                           and ROLE_KEYWORDS.search(next_line))
        date_location, date_rest = _extract_location(_strip_dates(date_line))

        if not date_rest and date_idx > 0:
            above_location, above = _extract_location(lines[date_idx - 1].strip())
            two_above = lines[date_idx - 2].strip() if date_idx > 1 else above
            pair = _split_title_company(above)
            if pair:
                # Layout: Title | Company [| Location] / [Location |] Dates / bullets
                title, company = pair
                date_location = date_location or above_location
            else:
                # Layout: Title / Company / Dates+Location / bullets
                title, company = two_above, above
                # Company / Title order instead: the role keyword gives it away
                if ROLE_KEYWORDS.search(above) and not ROLE_KEYWORDS.search(two_above):
                    title, company = above, two_above
            location = date_location
            bullet_start = date_idx + 1
        elif _split_title_company(date_rest):
            # Layout: Title | Company  Location | Dates / bullets
            title, company = _split_title_company(date_rest)
            location = date_location
            bullet_start = date_idx + 1
        elif date_idx == 0 and (pair := _split_dash_title_company(date_rest)):
            # Layout: Company - Title - Dates on one line / bullets. Before,
            # the whole "Company - Title" was the title, and a second such
            # entry took the first one's company.
            title, company = pair
            location = date_location
            bullet_start = date_idx + 1
        elif title_below:
            # Layout: Company+Date / Title+Location / bullets
            company = BARE_DATE_RE.sub("", DATE_RANGE_RE.sub("", date_line)).strip().rstrip(",").rstrip("–—-").strip()
            location, title = _extract_location(next_line)
            title = title.strip() or next_line.strip()
            bullet_start = next_idx + 1
        else:
            # Layout: Company / Title+Date / bullets  (or single-line)
            title = BARE_DATE_RE.sub("", DATE_RANGE_RE.sub("", date_line)).strip().rstrip(",").rstrip("–—-").strip()
            title = re.sub(r'\s*[;,]?\s*\(.*?\)\s*$', '', title).strip()
            if not title:
                title = date_line.strip()

            company = ""
            location = None
            header = lines[date_idx - 1].strip() if date_idx > 0 else ""
            if header:
                location, company = _extract_location(header)
            if date_idx == 0:
                cleaned = DATE_RANGE_RE.sub("", date_line).strip()
                location, company = _extract_location(cleaned)
                if results and ROLE_KEYWORDS.search(company):
                    # A second role at the previous company, listed with no
                    # company line of its own
                    title = company
                    company = results[-1].company_name
                elif not title or title == company:
                    title = company
            bullet_start = date_idx + 1

        # "Role| C++, Python": the role is the title, the tools its skills
        title, technologies = split_tools(title)
        if not company:
            company = title

        desc = _bullets(lines[bullet_start:])

        results.append(Experience(
            company_name=company, title=title, location=location,
            start_date=start, end_date=end, description=desc, technologies=technologies,
        ))
    return results


def _skill_items(text: str) -> list[str]:
    """The names in a skills list: split at commas, semicolons, bars and
    bullets, never inside brackets, and a name with a list in brackets is
    the name and each item ("React (Next.js, Redux)" is three). Split at
    commas alone, "Python | Java | C++" and "Python; Java" read as one
    unknown name each, and "React (Next.js" and "Redux)" both fell out."""
    items, current, depth = [], [], 0
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]" and depth:
            depth -= 1
        if depth == 0 and ch in ",;|•":
            items.append("".join(current))
            current = []
        else:
            current.append(ch)
    items.append("".join(current))
    names: list[str] = []
    for item in (i.strip() for i in items):
        listed = re.fullmatch(r'(.*?)\s*\((.*[,;].*)\)', item)
        if listed:
            names += [listed[1].strip(), *(x.strip() for x in re.split(r'[,;]', listed[2]))]
        else:
            names.append(item)
    return [n for n in names if n]


# "Languages – Python, Java": a short label before a spaced dash, then a list
_DASH_LABEL_RE = re.compile(r'^([A-Za-z][A-Za-z &/+]{1,30}?)\s+[–—-]\s+(.*[,;|].*)$')


def _parse_skills(text: str) -> list[Skill]:
    if not text.strip():
        return []
    results: list[Skill] = []
    category: str | None = None
    wrapped = False  # the line above ended in a comma: this line continues its list
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        dashed = None if ":" in line else _DASH_LABEL_RE.match(BULLET_RE.sub("", line).strip())
        if ":" in line or dashed or (wrapped and category):
            if ":" in line:
                category, rest = line.split(":", 1)
                category = BULLET_RE.sub("", category).strip()
            elif dashed:
                category, rest = dashed[1].strip(), dashed[2]
            else:
                rest = line
            wrapped = line.endswith(",")
            for name in _skill_items(rest):
                results.append(Skill(skill_name=name, category=category))
        else:
            category, wrapped = None, False
            line = BULLET_RE.sub("", line).strip()
            # two-column skill lists put several bullets on one line
            for name in _skill_items(line):
                results.append(Skill(skill_name=name))
    return results


def _parse_projects(text: str) -> list[Project]:
    if not text.strip():
        return []
    entries = [part for entry in _split_entries(text) for part in _split_undated_projects(entry)]
    results: list[Project] = []
    for lines in entries:
        if not lines:
            continue

        # First line has project name + optional tech parens + date
        first = lines[0]
        start, end = _parse_date_range(first)
        name = BARE_DATE_RE.sub("", DATE_RANGE_RE.sub("", first)).strip().rstrip(",").rstrip("–—-").strip()
        technologies: list[str] = []
        name, technologies = split_tools(name)
        # "Name (C++, Python)"
        paren = re.search(r'\s*\((.*?)\)\s*$', name)
        if paren:
            if "," in paren.group(1):
                technologies = technologies or [t.strip() for t in paren.group(1).split(",") if t.strip()]
            name = name[:paren.start()].strip()
        name = re.sub(r'\s{2,}', ' ', name)
        if not name:
            name = first.strip()

        # URL from any line
        url = None
        for ln in lines:
            url_m = URL_RE.search(ln)
            if url_m:
                url = url_m.group(0)
                break

        # a line that is only the link is the url above, not a bullet
        body = [ln for ln in lines[1:] if not URL_RE.fullmatch(ln.strip())]
        # "Next.js, TypeScript, FastAPI" on its own line under the name is the
        # project's tools, as after a "|": before the first bullet, it was saved
        # as one, and its tools never reached the skills
        while body and not BULLET_RE.match(body[0].strip()) and is_tools_line(body[0]):
            technologies = technologies or tool_items(body[0])
            body = body[1:]
        desc = _bullets(body)

        results.append(Project(
            project_name=name, url=url, technologies=technologies,
            start_date=start, end_date=end, description=desc,
        ))
    return results


def _split_undated_projects(lines: list[str]) -> list[list[str]]:
    """Undated projects give `_split_entries` no date to split on, so one
    entry can hold several. Where bullets carry markers, a plain line is a
    new project's name when it holds a "|" ("Robot | C++, Python") or opens
    a new sentence after a finished bullet; a PDF-wrapped bullet line does
    neither."""
    if not any(BULLET_RE.match(ln) for ln in lines):
        return [lines]
    out: list[list[str]] = []
    for i, ln in enumerate(lines):
        starts = i > 0 and not BULLET_RE.match(ln) and _is_header_line(ln) and (
            "|" in ln or lines[i - 1].rstrip().endswith("."))
        if starts and out and any(BULLET_RE.match(x) for x in out[-1]):
            out.append([ln])
        elif out:
            out[-1].append(ln)
        else:
            out.append([ln])
    return out


# A citation's year: "(2025)" or "2025." anywhere in it
CITATION_YEAR_RE = re.compile(r'\b((?:19|20)\d{2})\b')


def _parse_publications(text: str) -> list[Project]:
    """One project per citation, named by the whole citation: no rule tells
    a paper's title from its authors. `_bullets` joins a citation's
    PDF-wrapped lines; its link becomes the project's url, its year the end."""
    results: list[Project] = []
    for item in (_bullets(text.splitlines()) or "").splitlines():
        url_m = URL_RE.search(item)
        name = URL_RE.sub("", item).strip().rstrip(",").strip()
        _, when = _parse_date_range(name)
        year = CITATION_YEAR_RE.search(name)
        if when is None and year:
            when = date(int(year.group(1)), 1, 1)
        # "Paper, Venue  May 2025": the month is the end, not the name
        name = _strip_dates(name) or name
        if name:
            results.append(Project(project_name=name, url=url_m.group(0) if url_m else None, end_date=when))
    return results


def _parse_certifications(text: str) -> list[Certification]:
    if not text.strip():
        return []
    results: list[Certification] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Split on em-dash, en-dash, or " - "
        parts = re.split(r'\s*[–—]\s*|\s+-\s+', line, maxsplit=1)
        cert_name = parts[0].strip()
        issuer = parts[1].strip() if len(parts) > 1 else None
        if cert_name:
            results.append(Certification(cert_name=cert_name, issuer=issuer))
    return results


# A year alone ends an award line ("Merit Scholarship  2024")
YEAR_ONLY_RE = re.compile(r'(?<![\d–\-])\b(\d{4})\s*$')


def _parse_awards(text: str) -> list[Award]:
    """One award per line: "Award – Issuer  Date" or "Award | Issuer | Date";
    the issuer and the date are optional."""
    results: list[Award] = []
    for line in text.splitlines():
        line = BULLET_RE.sub("", line.strip()).strip()
        if not line:
            continue
        _, when = _parse_date_range(line)
        rest = _strip_dates(line)
        year = YEAR_ONLY_RE.search(rest)
        if when is None and year:
            when = date(int(year.group(1)), 1, 1)
        if year:
            rest = rest[:year.start()].strip().rstrip(",|–—-").strip()
        parts = [p.strip() for p in re.split(r'\s*[|–—]\s*|\s+-\s+', rest, maxsplit=1)]
        if parts[0]:
            results.append(Award(title=parts[0], issuer=parts[1] if len(parts) > 1 and parts[1] else None, date=when))
    return results


# --- The header (KAN-436) ---------------------------------------------------
#
# The lines above the first heading: the name, the contact details, and
# whatever else a student put there ("Secret Clearance", "Open to
# relocation"). Read by these rules alone, never by a model (ADR 0007, "The
# contact block stays home"), for upload to fill the profile's empty fields
# (`services/header_fill.py`).

# The header is the contact block: a heading further down than this means
# the resume opens with text that is no header
HEADER_LINES = 12
_HEADER_EMAIL_RE = re.compile(r'(?:mailto:)?([\w.+-]+@[\w-]+(?:\.[\w-]+)+)', re.IGNORECASE)
# A link: a scheme or "www.", or a host with a path, or a bare host on a
# site's usual ending ("janedoe.dev"); the email went first, so no "@" is left
_HEADER_URL_RE = re.compile(
    r'(?:https?://|www\.)[^\s|,;]+'
    r'|(?<![\w@.])[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}/[^\s|,;]*'
    r'|(?<![\w@.])[\w-]+(?:\.[\w-]+)*\.(?:com|dev|io|me|net|org|edu|co|ai|app|site|tech|xyz|page|info)\b(?!\.\w)',
    re.IGNORECASE,
)
# A phone: ten digits in the usual groups, with an optional country code
_HEADER_PHONE_RE = re.compile(
    r'(?<![\w+])(?:\+\d{1,3}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\w)')
# "City, ST" or "City, ST 11790", the whole piece; a street before it is
# taken off first, since an address is never kept
_HEADER_PLACE_RE = re.compile(
    r"([A-Z][A-Za-z.'\-]*(?:\s+[A-Z][A-Za-z.'\-]*){0,3}),\s*([A-Z]{2})(?:\s+\d{5}(?:-\d{4})?)?$")
_HEADER_STREET_RE = re.compile(r'^\d+\s+[\w .\'-]+?,\s*(?=[A-Z])')
# How the pieces of a contact line are set apart
_HEADER_SPLIT_RE = re.compile(r'\s*[|•·◆♦⋄✉☎]\s*|\t|\s{2,}|\s+[–—]\s+')
# A label before a value ("Email: ...", "LinkedIn: ...")
_HEADER_LABEL_RE = re.compile(
    r'^(?:e-?mail|phone|tel|mobile|cell|linkedin|github|portfolio|website|web|address|location|links?)\s*:\s*',
    re.IGNORECASE,
)
# "U.S. Citizen" belongs to Application Questions, which prints it itself
_HEADER_CITIZEN_RE = re.compile(r'^u\.?\s?s\.?\s+citizen(?:ship)?$', re.IGNORECASE)
# Free text kept for the Additional line: a short phrase, never a sentence
_HEADER_TEXT_WORDS = 8
_HEADER_TEXT_CHARS = 60


@dataclass(frozen=True)
class HeaderReading:
    """What a resume's header holds, by the parser's rules (`read_header`).
    `links` are the links that are neither LinkedIn nor GitHub, in order;
    `text` is the free text left once the name and every contact detail
    are taken out, a phrase per item."""

    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    links: tuple[str, ...] = ()
    text: tuple[str, ...] = ()


def header_lines(raw_text: str) -> list[str]:
    """The lines above the first heading, when it is in the first
    HEADER_LINES lines; none when no heading is there."""
    lines = [ln.strip() for ln in _clean_text(raw_text).splitlines() if ln.strip()]
    for at, line in enumerate(lines[:HEADER_LINES + 1]):
        if section_of(line):
            return lines[:at]
    return []


def _link(url: str) -> str:
    url = url.rstrip(".)")
    return url if re.match(r'https?://', url, re.IGNORECASE) else f"https://{url}"


def _phrase(piece: str) -> str | None:
    """A piece of free text worth keeping: short, no sentence, no
    citizenship (Application Questions prints it)."""
    piece = piece.strip(" ,;:-–—|()[]")
    words = piece.split()
    if not words or not re.search(r'[A-Za-z]', piece) or _HEADER_CITIZEN_RE.match(piece):
        return None
    # "Authorized to work in the U.S." ends in an abbreviation, not a sentence
    ends = piece.endswith(("!", "?")) or (piece.endswith(".") and not re.search(r'\b(?:[A-Za-z]\.){1,3}$', piece))
    sentence = ends and len(words) >= 3
    if sentence or len(words) > _HEADER_TEXT_WORDS or len(piece) > _HEADER_TEXT_CHARS:
        return None
    return piece


def read_header(raw_text: str) -> HeaderReading:
    """The resume's header read by rules: the first email and phone, a
    "City, ST" place, the LinkedIn and GitHub links, the other links, and
    the short phrases left (a clearance, "Open to relocation"). The first
    line is the name and is skipped unless it holds a contact detail; a
    sentence (an objective written above the first heading) is never kept."""
    found: dict[str, str] = {}
    links: list[str] = []
    text: list[str] = []
    for at, line in enumerate(header_lines(raw_text)):
        # A line that reads as a sentence is an objective or a summary
        if len(line.split()) > 2 * _HEADER_TEXT_WORDS and not _HEADER_SPLIT_RE.search(line):
            continue
        name_line = at == 0
        for piece in _HEADER_SPLIT_RE.split(line):
            piece = _HEADER_LABEL_RE.sub("", piece.strip())
            for match in _HEADER_EMAIL_RE.finditer(piece):
                found.setdefault("email", match.group(1))
                name_line = False
            piece = _HEADER_EMAIL_RE.sub(" ", piece)
            for match in _HEADER_URL_RE.finditer(piece):
                url = _link(match.group(0))
                host = re.sub(r'^https?://(?:www\.)?', "", url, flags=re.IGNORECASE).lower()
                kind = "linkedin" if host.startswith("linkedin.com") else (
                    "github" if host.startswith("github.com") else None)
                if kind and kind not in found:
                    found[kind] = url
                elif url not in links:
                    links.append(url)
                name_line = False
            piece = _HEADER_URL_RE.sub(" ", piece)
            for match in _HEADER_PHONE_RE.finditer(piece):
                found.setdefault("phone", match.group(0).strip())
                name_line = False
            piece = " ".join(_HEADER_PHONE_RE.sub(" ", piece).split())
            place = _HEADER_PLACE_RE.fullmatch(_HEADER_STREET_RE.sub("", piece))
            if place and place.group(2) in US_STATES:
                found.setdefault("location", f"{place.group(1)}, {place.group(2)}")
                continue
            if name_line or _HEADER_STREET_RE.match(piece):
                continue
            if (phrase := _phrase(piece)) and phrase not in text:
                text.append(phrase)
    return HeaderReading(
        email=found.get("email"), phone=found.get("phone"), location=found.get("location"),
        linkedin=found.get("linkedin"), github=found.get("github"),
        links=tuple(links), text=tuple(text),
    )
