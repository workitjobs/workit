'''
How a view's fields read as resume text, shared by the PDF templates and the
Word file so the two always say the same thing. Plain text out: each layout
escapes or styles it itself. Stdlib only, like the rest of this package.
'''

import datetime
import re
from dataclasses import dataclass
from decimal import Decimal

from app.services.resume_view import ViewEntry

SECTION_LABELS = {
    "education": "Education",
    "experience": "Experience",
    "projects": "Projects",
    "leadership": "Leadership & Activities",
    "awards": "Awards",
    "certifications": "Certifications",
}
SKILLS_LABEL = "Technical Skills"
# What the header prints when My Profile's U.S. Citizen box is checked
US_CITIZEN = "U.S. Citizen"
# Jake's own spelling of months: "Aug. 2018", "June 2020", "Sep. 2018"
_MONTHS = ("Jan.", "Feb.", "Mar.", "Apr.", "May", "June", "July", "Aug.", "Sep.", "Oct.", "Nov.", "Dec.")
_FULL_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
# Sections whose heading is two rows (title and place, then subtitle and
# dates); the rest are one row, title and a tag, with the dates at the right.
TWO_ROW = {"education", "experience", "leadership"}


def month(day: datetime.date, date_format: str = "short") -> str:
    '''A month in `DATE_FORMATS`' terms: "Aug. 2018", "August 2018", "2018" or
    "08/2018".'''
    if date_format == "long":
        return f"{_FULL_MONTHS[day.month - 1]} {day.year}"
    if date_format == "year":
        return str(day.year)
    if date_format == "numeric":
        return f"{day.month:02}/{day.year}"
    return f"{_MONTHS[day.month - 1]} {day.year}"


def dates(entry: ViewEntry, date_format: str = "short") -> str:
    '''"Aug. 2018 – May 2021", "June 2020 – Present", "Expected May 2027",
    or "" when the entry has no dates.'''
    if entry.section == "awards":
        return month(entry.award_date, date_format) if entry.award_date else ""
    if entry.end_kind == "present":
        end = "Present"
    elif entry.end_month:
        end = ("Expected " if entry.end_kind == "expected" else "") + month(entry.end_month, date_format)
    else:
        end = ""
    start = month(entry.start_month, date_format) if entry.start_month else ""
    # One month, or one year in the year format, names it once: "June 2024
    # – June 2024" and "2020 – 2020" read as a slip
    if start and end in (start, f"Expected {start}"):
        return end
    return f"{start} – {end}" if start and end else start or end


def _number(value: Decimal) -> str:
    # 3.80 -> "3.8", 4.00 -> "4.0", 3.85 -> "3.85"; a whole number of ten or
    # more as written: 90 -> "90" and 100 -> "100". Zeros came off the end
    # of a number with no decimal point too, so "GPA: 90/100" printed
    # "GPA: 9/100", and 85.0 from the database printed "85.0/100.0"
    # a float from the editor's copy reads as the decimal it was typed as
    value = value if isinstance(value, Decimal) else Decimal(str(value))
    if value == value.to_integral_value() and value >= 10:
        return f"{value:.0f}"
    text = f"{value:f}"
    if "." not in text:
        return text + ".0"
    text = text.rstrip("0")
    return text + "0" if text.endswith(".") else text


def _grade(value: Decimal) -> str:
    # Under ten, two decimals: "3.80", "4.00", "8.50"; ten or more as
    # `_number` reads it: "90", "92.5"
    value = value if isinstance(value, Decimal) else Decimal(str(value))
    return f"{value:.2f}" if value < 10 else _number(value)


def gpa(entry: ViewEntry) -> str | None:
    '''"GPA: 3.80/4.00": a GPA under ten with two decimals, as career
    centers ask ("to two decimal points") and a transcript prints it, and a
    scale under ten the same; "90/100" and "8.50/10" stay whole. The
    database keeps two decimals and nothing of how many were typed, so
    "3.80/4.00" printed "3.8/4.0" until KAN-813.'''
    if entry.gpa is None:
        return None
    scale = f"/{_grade(entry.gpa_scale)}" if entry.gpa_scale is not None else ""
    return f"GPA: {_grade(entry.gpa)}{scale}"


@dataclass(frozen=True)
class Heading:
    '''An entry's heading. Two-row sections use all four slots; one-row
    sections show `title` and `tag` on the left and `right` at the right,
    and a project with tools shows them as `subtitle`, a line of their own
    under it (KAN-738).'''

    title: str
    right: str = ""
    subtitle: str = ""
    subright: str = ""
    tag: str = ""


def _degree_line(entry: ViewEntry) -> str:
    # A field the degree already names prints once: "B.S. in Computer
    # Science" with "Computer Science" read "in Computer Science in Computer
    # Science"
    field = entry.field_of_study
    if field and entry.degree and field.lower() in entry.degree.lower():
        field = None
    degree = " in ".join(x for x in (entry.degree, field) if x)
    return ", ".join(x for x in (degree, entry.organization) if x)


def degree_leads(entry: ViewEntry, education_first: str) -> bool:
    '''Whether this entry prints its degree line over its school: an entry
    with no degree line keeps the school on top, or that row would print empty.'''
    return education_first == "degree" and entry.section == "education" and bool(_degree_line(entry))


def heading(entry: ViewEntry, date_format: str = "short", education_first: str = "school") -> Heading:
    when = dates(entry, date_format)
    if entry.section == "education":
        if degree_leads(entry, education_first):
            return Heading(_degree_line(entry), entry.location or "", entry.title, when)
        return Heading(entry.title, entry.location or "", _degree_line(entry), when)
    if entry.section in TWO_ROW:
        return Heading(entry.title, when, entry.organization or "", entry.location or "")
    if entry.section == "certifications":
        tag = entry.issuer or entry.organization or ""
    else:  # projects, awards, and a custom section's entries (KAN-498)
        # the link as the header prints one ("github.com/jd/robot"), not its
        # whole address; the PDF makes it clickable (`jakes._entry`)
        tag = " | ".join(x for x in (entry.organization, entry.link and link_text(entry.link)) if x)
    return Heading(entry.title, when, tag=tag, subtitle=tools(entry))


def one_row(h: Heading, kinds: dict[str, str]) -> list[str] | None:
    '''A two-row heading with nothing at the left of its second row (a school
    with no degree line, a job with no organization) prints as one row
    (KAN-503): drawn as two, the second row's place or dates sat alone on a
    line of their own. Answers the right slots that row shows, the place
    first and then the dates, so the dates keep the right edge every other
    entry's dates sit on; each slot only when it has text. None while the
    second row has words at its left, so the heading stays two rows.'''
    if h.subtitle:
        return None
    names = sorted(("right", "subright"), key=lambda name: kinds[name] != "location")
    return [name for name in names if getattr(h, name)]


def tools(entry: ViewEntry) -> str:
    '''A project's tools line, "Next.js, TypeScript", or "".'''
    return ", ".join(entry.tools)


def heading_fields(section: str, degree_first: bool = False) -> dict[str, str]:
    '''Which entry field each of heading()'s slots shows, by slot name: the
    `kind` of the slot's click target in the editor (KAN-209). Education's
    subtitle is the degree line, which also names the school; `degree_first`
    swaps the two rows (`degree_leads`).'''
    if section == "education":
        top, under = ("degree", "title") if degree_first else ("title", "degree")
        return {"title": top, "right": "location", "subtitle": under, "subright": "dates"}
    if section in TWO_ROW:
        return {"title": "title", "right": "dates", "subtitle": "organization", "subright": "location"}
    return {"title": "title", "tag": "organization", "right": "dates", "subtitle": "tools"}


def details(entry: ViewEntry) -> list[tuple[str, str]]:
    '''(kind, line) for each line shown above an entry's bullets:
    Education's GPA, coursework and honors.'''
    lines = []
    if score := gpa(entry):
        lines.append(("gpa", score))
    if entry.coursework:
        lines.append(("coursework", "Relevant Coursework: " + ", ".join(entry.coursework)))
    if entry.honors:
        lines.append(("honors", "Honors: " + entry.honors))
    return lines


def skill_lines(skills) -> list[tuple[str, tuple]]:
    '''(label, skills) per group, in the order groups first appear; a layout
    joins the names with ", ". Ungrouped skills are "Other" beside groups,
    or unlabeled ("") alone.'''
    groups: dict[str | None, list] = {}
    for skill in skills:
        groups.setdefault(skill.group, []).append(skill)
    if list(groups) == [None]:
        return [("", tuple(groups[None]))]
    return [(group or "Other", tuple(members)) for group, members in groups.items()]


def phone_text(phone: str) -> str:
    '''How a phone number prints, as the Profile shows it (the web app's
    `phoneText`, frontend/src/lib/profile-links.ts): a U.S. number of 10
    digits, or 11 starting with 1, as "+1 646-555-0142" however it was
    typed; any other as typed. The profile keeps what was typed, and the
    resume printed it bare ("16465550142"), unlike the profile beside it.'''
    digits = re.sub(r"\D", "", phone)
    us = digits[1:] if len(digits) == 11 and digits.startswith("1") else digits
    if len(us) != 10 or re.search(r"[^\d\s()+.-]", phone):
        return phone
    return f"+1 {us[:3]}-{us[3:6]}-{us[6:]}"


def link_text(url: str) -> str:
    '''How a link prints: no scheme, no "www.", no trailing slash.'''
    for prefix in ("https://", "http://", "mailto:"):
        if url.lower().startswith(prefix):
            url = url[len(prefix):]
    if url.lower().startswith("www."):
        url = url[4:]
    return url.rstrip("/")
