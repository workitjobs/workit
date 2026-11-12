'''
The renderer's tests (KAN-204, KAN-207, spec seam 3): render a fixed view of
Jake's sample with real Tectonic, read the PDF's text back with pdfminer, and
check what a hiring system would read, the page count, and the missing-character
warning. CI installs Tectonic, and where `CI` is set these tests fail rather than
skip when it is missing.
'''

import datetime
import hashlib
import io
import os
import shutil
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import get_args

import pytest
from pdfminer.high_level import extract_pages, extract_text
from pdfminer.pdfpage import PDFPage
from pdfminer.pdftypes import resolve1
from pdfminer.psparser import literal_name

from app.schemas.built_resume import PageSettings as ApiPageSettings
from app.services import resume_render
from app.services.resume_render import (
    ALIGNMENTS,
    BODY_SIZES,
    DATE_FORMATS,
    DEFAULT_PAGE,
    EDUCATION_FIRST,
    FONT_FAMILIES,
    FONT_SIZES,
    HEADER_FIELDS,
    HEADING_SIZES,
    LINE_SPACINGS,
    MARGINS,
    NAME_SIZES,
    TEMPLATE,
    TITLE_SIZES,
    WRAPPED_LINE,
    PageSettings,
    TectonicUnavailable,
    box_lines,
    compile_pdf,
    escape,
    jakes_document,
    render,
    shown_header,
)
from app.services.resume_render.fields import (
    dates,
    degree_leads,
    gpa,
    heading,
    heading_fields,
    one_row,
    phone_text,
    skill_lines,
)
from app.services.resume_render.jakes import body as jakes_body
from app.services.resume_render.sample import IDENTITY, VIEW
from app.services.resume_view import (
    ResumeView,
    ViewBullet,
    ViewEntry,
    ViewSection,
    ViewSkill,
)

# jakes.tex from the KAN-176 prototype, byte for byte. A change here is a
# change to Jake's template itself: don't
JAKES_TEX_SHA256 = "c673cb35b525347452428b710a0acb4c17858cade15f6b673c8b70784d08b60b"


def _tectonic_or_skip() -> None:
    try:
        compile_pdf(jakes_document("x"))
    except TectonicUnavailable as exc:
        if os.environ.get("CI"):
            raise
        pytest.skip(f"tectonic not set up ({exc}); run python3 scripts/fetch_tectonic.py")


def _text(pdf: bytes) -> str:
    # Plain text, no layout: the PDF is untagged (ADR 0002)
    return " ".join(extract_text(io.BytesIO(pdf)).split())


def _pages(pdf: bytes) -> int:
    return sum(1 for _ in PDFPage.get_pages(io.BytesIO(pdf)))


def test_jakes_preamble_is_byte_for_byte() -> None:
    assert hashlib.sha256(TEMPLATE.read_bytes()).hexdigest() == JAKES_TEX_SHA256
    preamble = TEMPLATE.read_text(encoding="utf-8").split("%%BODY%%")[0]
    assert jakes_document(r"\section{X}").startswith(preamble)


def test_jakes_sample_renders_as_one_page_with_its_text() -> None:
    _tectonic_or_skip()
    rendered = render(VIEW, IDENTITY, "jakes")

    assert rendered.page_count == 1
    assert _pages(rendered.pdf) == 1
    assert rendered.missing_characters == ()
    text = _text(rendered.pdf)
    # pdfminer reads the right-hand column (places, dates) as its own block,
    # so each field is checked alone, not a whole row
    for expected in (
        "Jake Ryan",
        "123-456-7890 | jake@su.edu | linkedin.com/in/jake | github.com/jake",
        "Education",
        "Southwestern University",
        "Bachelor of Arts in Computer Science, Minor in Business",
        "Aug. 2018 – May 2021",
        "GPA: 3.80/4.00",
        "Undergraduate Research Assistant",
        "June 2020 – Present",
        "Texas A&M University",
        "College Station, TX",
        "Developed a REST API using FastAPI and PostgreSQL to store data from learning management systems",
        "Gitlytics | Python, Flask, React, PostgreSQL, Docker",
        "Implemented GitHub OAuth to get data from user’s repositories",
        "Technical Skills",
        "Languages: Java, Python, C/C++, SQL (Postgres), JavaScript, HTML/CSS, R",
        "Libraries: pandas, NumPy, Matplotlib",
    ):
        assert expected in text


def _with_entries(view: ResumeView, *entries: ViewEntry) -> ResumeView:
    return replace(view, sections=(*view.sections, ViewSection("leadership", entries)))


def test_a_resume_past_one_page_reports_its_page_count() -> None:
    _tectonic_or_skip()
    bullets = tuple(ViewBullet(uuid.uuid4(), f"Led weekly meeting number {i} for the robotics club") for i in range(30))
    long = _with_entries(VIEW, ViewEntry(uuid.uuid4(), "leadership", "President", organization="Robotics Club",
                                         bullets=bullets))

    rendered = render(long, IDENTITY, "jakes")
    assert rendered.page_count == 2
    assert _pages(rendered.pdf) == 2
    assert "Leadership & Activities" in _text(rendered.pdf)


def test_characters_the_font_lacks_are_reported_once_each() -> None:
    _tectonic_or_skip()
    view = _with_entries(VIEW, ViewEntry(uuid.uuid4(), "leadership", "Президент клуба 中文", organization="José"))

    rendered = render(view, replace(IDENTITY, name="Jake Ryan 中"), "jakes")
    # In the order the page meets them: the name, then the entry
    assert rendered.missing_characters == (
        "中", "П", "р", "е", "з", "и", "д", "н", "т", "к", "л", "у", "б", "а", "文",
    )
    # Accented Latin is in the font
    assert "é" not in rendered.missing_characters


def _link_targets(pdf: bytes) -> list[str]:
    from pypdf import PdfReader

    page = PdfReader(io.BytesIO(pdf)).pages[0]
    return [a.get_object()["/A"]["/URI"] for a in page.get("/Annots", []) if "/A" in a.get_object()]


def test_header_links_with_underscores_and_tildes_stay_clickable() -> None:
    _tectonic_or_skip()
    links = ("https://github.com/john_doe", "https://cs.example.edu/~jdoe/a%20b#top")
    identity = replace(IDENTITY, email="john_doe@example.com",
                       links=(("github_url", links[0]), ("other_url", links[1])))

    pdf = render(VIEW, identity, "jakes").pdf

    assert set(_link_targets(pdf)) >= {"mailto:john_doe@example.com", *links}
    assert "github.com/john_doe" in _text(pdf)
    assert "cs.example.edu/~jdoe" in _text(pdf)


def test_an_unknown_template_is_refused() -> None:
    with pytest.raises(ValueError):
        render(VIEW, IDENTITY, "no-such-template")


def test_escaped_text_prints_literally_and_runs_nothing() -> None:
    _tectonic_or_skip()
    hostile = "\\input{/etc/passwd}\n\nR&D 100% $5 #1 snake_case ~ ^ <b> a|b"
    pdf = compile_pdf(jakes_document(escape(hostile)))

    text = _text(pdf)
    assert "\\input{/etc/passwd} R&D 100% $5 #1 snake_case ~ ^ <b> a|b" in text
    assert "root:" not in text



def test_the_pdf_is_titled_with_the_name_and_the_name_runs_nothing() -> None:
    # KAN-317: with no Title, a viewer showed the blob: link's random id
    _tectonic_or_skip()
    from pypdf import PdfReader

    def title(name: str) -> str:
        pdf = render(VIEW, replace(IDENTITY, name=name), "jakes").pdf
        return PdfReader(io.BytesIO(pdf)).metadata["/Title"]

    assert title("José O'Brien") == "José O'Brien Resume"
    assert title("\\input{/etc/passwd} (a) >> <b>") == "\\input{/etc/passwd} (a) >> <b> Resume"
    assert title("  ") == "Resume"
    # The Overleaf source stays Jake's own: pdfLaTeX would warn on the special
    assert "pdf:docinfo" not in resume_render.latex(VIEW, IDENTITY, "jakes")

def _content_streams(pdf: bytes) -> list[bytes]:
    from pypdf import PdfReader

    return [page.get_contents().get_data() for page in PdfReader(io.BytesIO(pdf)).pages]


def _long_view() -> ResumeView:
    bullets = tuple(ViewBullet(uuid.uuid4(), f"Led weekly meeting number {i} for the robotics club") for i in range(30))
    return _with_entries(VIEW, ViewEntry(uuid.uuid4(), "leadership", "President", organization="Robotics Club",
                                         location="Georgetown, TX", bullets=bullets))


def _tools_view() -> ResumeView:
    '''Jake's sample with a project that keeps its stack as tools (KAN-738),
    as an upload now reads "workitjobs.ai | AI Job Search Platform" over a
    line of tools.'''
    project = ViewEntry(uuid.uuid4(), "projects", "workitjobs.ai", organization="AI Job Search Platform",
                        tools=("Next.js", "TypeScript", "Tailwind CSS", "FastAPI", "PostgreSQL"),
                        bullets=(ViewBullet(uuid.uuid4(), "Lead design and front-end on a 5-person team"),))
    sections = tuple(replace(s, entries=(project, *s.entries)) if s.section == "projects" else s
                     for s in VIEW.sections)
    return replace(VIEW, sections=sections)


def _one_row_view() -> ResumeView:
    '''Jake's sample with a school that has no degree line and a job with no
    organization (KAN-503): each heading has nothing at the left of its
    second row.'''
    lab = ViewEntry(uuid.uuid4(), "education", "Signal Processing Lab", location="Hillcrest, NY",
                    end_month=datetime.date(2025, 5, 1), end_kind="month",
                    bullets=(ViewBullet(uuid.uuid4(), "Built a search index for lab notes"),))
    job = ViewEntry(uuid.uuid4(), "experience", "Freelance Web Developer", location="Remote",
                    start_month=datetime.date(2024, 6, 1), end_kind="present",
                    bullets=(ViewBullet(uuid.uuid4(), "Built sites for three local businesses"),))
    sections = tuple(
        replace(s, entries=(lab, *s.entries)) if s.section == "education"
        else replace(s, entries=(job, *s.entries)) if s.section == "experience"
        else s
        for s in VIEW.sections)
    return replace(VIEW, sections=sections)


def test_a_heading_with_an_empty_second_row_is_one_row_place_then_dates() -> None:
    # KAN-503: the second row's right side sat alone on a line. One row
    # shows the place, then the dates, whichever row each came from
    lab, job = (s.entries[0] for s in _one_row_view().sections[:2])
    for entry in (lab, job):
        h = heading(entry)
        rights = one_row(h, heading_fields(entry.section))
        assert [heading_fields(entry.section)[name] for name in rights] == ["location", "dates"]
    # With no place, the dates alone
    bare = replace(lab, location=None)
    assert one_row(heading(bare), heading_fields("education")) == ["subright"]
    # A second row with words at its left stays two rows
    school = VIEW.sections[0].entries[0]
    assert one_row(heading(school), heading_fields("education")) is None


def test_a_school_with_no_degree_prints_its_heading_on_one_row() -> None:
    _tectonic_or_skip()
    view = _one_row_view()
    rendered = render(view, IDENTITY, "jakes")
    boxes = {(b.item_id, b.kind): b for b in rendered.boxes}
    for entry in (view.sections[0].entries[0], view.sections[1].entries[0]):
        title, place, when = (boxes[(str(entry.id), kind)] for kind in ("title", "location", "dates"))
        # One row: the place and the dates sit on the title's line, the
        # dates at the right edge, after the place
        assert abs(place.y1 - title.y1) < 2 and abs(when.y1 - title.y1) < 2
        assert title.x1 < place.x0 < place.x1 < when.x0
        # and the first bullet follows at once, with no line between
        bullet = boxes[(str(entry.bullets[0].id), "bullet")]
        assert 0 <= bullet.y0 - title.y1 < 8
    assert (str(view.sections[0].entries[0].id), "degree") not in boxes
    lines = _text_lines(rendered.pdf)
    assert any("Hillcrest, NY | May 2025" in t for t, _, _ in lines)


def test_the_word_file_prints_an_empty_second_row_heading_on_one_row() -> None:
    from docx import Document

    from app.services.resume_render.word import render_docx

    texts = [p.text for p in Document(io.BytesIO(render_docx(_one_row_view(), IDENTITY))).paragraphs]
    at = texts.index("Signal Processing Lab\tHillcrest, NY | May 2025")
    assert texts[at + 1] == "Built a search index for lab notes"
    at = texts.index("Freelance Web Developer\tRemote | June 2024 – Present")
    assert texts[at + 1] == "Built sites for three local businesses"


@pytest.mark.parametrize("view", [VIEW, _long_view(), _tools_view(), _one_row_view()],
                         ids=["one page", "two pages", "tools", "one row"])
def test_position_markers_leave_the_page_unchanged(view) -> None:
    # The preview must be the file that downloads (ADR 0002): the markers
    # that place the editor's click targets may not move one glyph
    from app.services.resume_render import compile_document, jakes

    _tectonic_or_skip()
    marked = compile_document(jakes_document(jakes.body(view, IDENTITY)))
    plain = compile_document(jakes_document(jakes.body(view, IDENTITY, marks=False)))

    assert marked.boxes and not plain.boxes
    assert _content_streams(marked.pdf) == _content_streams(plain.pdf)


def _text_lines(pdf: bytes) -> list[tuple[str, int, tuple[float, float, float, float]]]:
    '''Each text line pdfminer finds: (text, page, (x0, top, x1, bottom)) in
    PDF points from the page's top left, like a box.'''
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTChar, LTTextContainer, LTTextLine

    lines = []
    for number, page in enumerate(extract_pages(io.BytesIO(pdf)), start=1):
        for element in page:
            if isinstance(element, LTTextContainer):
                for line in element:
                    # The list's bullet glyph is the template's, not the line's
                    chars = [c for c in line if isinstance(c, LTChar) and c.get_text() not in "• "] \
                        if isinstance(line, LTTextLine) else []
                    if chars:
                        x0, x1 = min(c.x0 for c in chars), max(c.x1 for c in chars)
                        y0, y1 = min(c.y0 for c in chars), max(c.y1 for c in chars)
                        text = line.get_text().strip().removeprefix("• ")
                        lines.append((text, number, (x0, page.height - y1, x1, page.height - y0)))
    return lines


def _inside(inner, box, slack=1.5) -> bool:
    x0, top, x1, bottom = inner
    return (box.x0 - slack <= x0 and x1 <= box.x1 + slack
            and box.y0 - slack <= top and bottom <= box.y1 + slack)


def _line(lines, text):
    return next((page, bbox) for t, page, bbox in lines if t.startswith(text))


def test_render_gives_a_box_for_each_line_the_editor_can_select() -> None:
    _tectonic_or_skip()
    rendered = render(VIEW, IDENTITY, "jakes")
    boxes = {(b.item_id, b.kind): b for b in rendered.boxes}
    assert len(boxes) == len(rendered.boxes)  # one box for each

    school = VIEW.sections[0].entries[0]
    assert {kind for item, kind in boxes if item == str(school.id)} == {"title", "location", "degree", "dates", "gpa"}
    job = VIEW.sections[1].entries[0]
    assert {kind for item, kind in boxes if item == str(job.id)} == {"title", "organization", "location", "dates"}
    project = VIEW.sections[2].entries[0]
    assert {kind for item, kind in boxes if item == str(project.id)} == {"title", "organization", "dates"}
    every_bullet = {str(b.id) for s in VIEW.sections for e in s.entries for b in e.bullets}
    assert {item for item, kind in boxes if kind == "bullet"} == every_bullet
    assert {item for item, kind in boxes if kind == "skill"} == {str(s.id) for s in VIEW.skills}
    assert all(b.page == 1 and 0 <= b.x0 < b.x1 <= 612 and 0 <= b.y0 < b.y1 <= 792 for b in rendered.boxes)

    # Each box covers its text where pdfminer, reading the PDF on its own,
    # finds it. Places and dates are pdfminer's own lines
    lines = _text_lines(rendered.pdf)
    _, bbox = _line(lines, "Southwestern University")
    assert _inside(bbox, boxes[(str(school.id), "title")])
    _, bbox = _line(lines, "Georgetown, TX")
    assert _inside(bbox, boxes[(str(school.id), "location")])
    _, bbox = _line(lines, "June 2020 – Present")
    assert _inside(bbox, boxes[(str(job.id), "dates")])
    first = job.bullets[0]
    _, bbox = _line(lines, first.text[:30])
    assert _inside(bbox, boxes[(str(first.id), "bullet")])


def test_a_projects_tools_print_on_their_own_line_under_its_heading() -> None:
    # KAN-738: the heading's first line stays as it was (name, organization,
    # dates), and the tools take a line of their own, as the student's own
    # resume prints them; the editor gets a "tools" box for that line
    _tectonic_or_skip()
    view = _tools_view()
    rendered = render(view, IDENTITY, "jakes")
    project = view.sections[2].entries[0]
    boxes = {(b.item_id, b.kind): b for b in rendered.boxes}

    assert rendered.missing_characters == ()
    assert {kind for item, kind in boxes if item == str(project.id)} == {"title", "organization", "tools"}
    tools = boxes[(str(project.id), "tools")]
    assert tools.text == "Next.js, TypeScript, Tailwind CSS, FastAPI, PostgreSQL"
    title, bullet = boxes[(str(project.id), "title")], boxes[(str(project.bullets[0].id), "bullet")]
    assert title.y1 <= tools.y0 and tools.y1 <= bullet.y0
    assert abs(tools.x0 - title.x0) < 1  # under the name, not indented

    lines = _text_lines(rendered.pdf)
    assert any(t.startswith("workitjobs.ai | AI Job Search Platform") for t, _, _ in lines)
    _, bbox = _line(lines, "Next.js, TypeScript")
    assert _inside(bbox, tools)
    # A project with no tools keeps one line, as before
    gitlytics = view.sections[2].entries[1]
    assert (str(gitlytics.id), "tools") not in boxes


def test_the_header_gives_a_box_for_each_profile_field() -> None:
    _tectonic_or_skip()
    rendered = render(VIEW, IDENTITY, "jakes")
    boxes = {b.kind: b for b in rendered.boxes if b.item_id == "header"}

    assert set(boxes) == {"full_name", "phone_number", "email", "linkedin_url", "github_url"}
    lines = _text_lines(rendered.pdf)
    for kind, text in [("full_name", "Jake Ryan"), ("phone_number", "123-456-7890"),
                       ("email", "jake@su.edu"), ("github_url", "github.com/jake")]:
        bbox = next(bbox for t, _, bbox in lines if text in t)
        box = boxes[kind]
        if kind == "full_name":
            assert _inside(bbox, box)
        else:
            # The contact line is one pdfminer line, its "|" taller than the
            # text, so a field's box sits inside it rather than around it
            assert box.y0 < bbox[3] and bbox[1] < box.y1
            assert bbox[0] - 1.5 <= box.x0 and box.x1 <= bbox[2] + 1.5


def test_the_header_says_us_citizen_only_when_checked() -> None:
    assert "U.S. Citizen" not in jakes_body(VIEW, IDENTITY)
    # First on the contact line, before the phone
    assert r"\small U.S. Citizen $|$ +1 123-456-7890 $|$ " in jakes_body(
        VIEW, replace(IDENTITY, us_citizen=True), marks=False)
    _tectonic_or_skip()
    rendered = render(VIEW, replace(IDENTITY, us_citizen=True), "jakes")
    assert any("U.S. Citizen" in t for t, _, _ in _text_lines(rendered.pdf))
    # No box: the editor cannot type it
    assert {b.kind for b in rendered.boxes if b.item_id == "header"} == {
        "full_name", "phone_number", "email", "linkedin_url", "github_url"}


def test_the_header_prints_the_location_after_the_email() -> None:
    # KAN-436: U.S. Citizen | phone | email | location | links
    identity = replace(IDENTITY, location="Stony Brook, NY")
    assert r"\underline{jake@su.edu}} $|$ Stony Brook, NY $|$ \href{https://linkedin.com/in/jake}" in jakes_body(
        VIEW, identity, marks=False)
    _tectonic_or_skip()
    rendered = render(VIEW, identity, "jakes")
    box = next(b for b in rendered.boxes if b.item_id == "header" and b.kind == "location")
    assert box.text == "Stony Brook, NY"


def test_a_hidden_header_field_does_not_print_on_that_resume() -> None:
    identity = replace(IDENTITY, location="Stony Brook, NY")
    page = PageSettings(hidden_header=("location", "phone_number", "github_url"))
    tex = jakes_body(VIEW, shown_header(identity, page), marks=False)
    assert "Stony Brook" not in tex and "123-456-7890" not in tex and "github.com/jake" not in tex
    assert "jake@su.edu" in tex and "linkedin.com/in/jake" in tex
    # render() and latex() hide them with no help from the caller
    assert "Stony Brook" not in resume_render.latex(VIEW, identity, "jakes", page)
    assert "Stony Brook" in resume_render.latex(VIEW, identity, "jakes")


def test_the_additional_line_prints_under_the_contact_line() -> None:
    # KAN-436: its own line, in the contact line's type, with a box the
    # editor types into the profile
    identity = replace(IDENTITY, extra="Secret clearance | Open to relocation")
    tex = jakes_body(VIEW, identity, marks=False)
    assert r"\underline{github.com/jake}} \\" + "\n" + r"\small Secret clearance \textbar{} Open to relocation" in tex
    assert "Secret clearance" not in jakes_body(
        VIEW, shown_header(identity, PageSettings(hidden_header=("resume_header_extra",))), marks=False)
    # With no contact line it stands alone, with no empty line above it
    bare = replace(identity, phone=None, email=None, links=())
    assert r"\vspace{1pt}" + "\n" + r"\small Secret" in jakes_body(VIEW, bare, marks=False)
    _tectonic_or_skip()
    rendered = render(VIEW, identity, "jakes")
    box = next(b for b in rendered.boxes if b.item_id == "header" and b.kind == "resume_header_extra")
    contact = next(b for b in rendered.boxes if b.item_id == "header" and b.kind == "phone_number")
    assert box.text == "Secret clearance | Open to relocation"
    assert box.y0 >= contact.y1 - 1
    assert rendered.page_count == 1 and rendered.missing_characters == ()


def test_the_hidden_header_fields_are_kept_in_one_order_and_checked() -> None:
    assert PageSettings(hidden_header=["github_url", "phone_number"]).hidden_header == ("phone_number", "github_url")
    with pytest.raises(ValueError):
        PageSettings(hidden_header=("full_name",))
    fields = ApiPageSettings.model_fields
    assert set(get_args(get_args(fields["hidden_header"].annotation)[0])) == set(HEADER_FIELDS)
    with pytest.raises(ValueError):
        ApiPageSettings(hidden_header=["us_citizen"])


def test_a_wrapped_bullet_box_covers_both_lines() -> None:
    _tectonic_or_skip()
    long = ViewBullet(uuid.uuid4(), "Mentored twelve first-year students in data structures and algorithms each "
                                    "week, and wrote practice problems that the course staff later adopted for exams")
    view = _with_entries(VIEW, ViewEntry(uuid.uuid4(), "leadership", "Tutor", organization="Learning Center",
                                         bullets=(long,)))
    rendered = render(view, IDENTITY, "jakes")
    (box,) = [b for b in rendered.boxes if b.item_id == str(long.id)]

    lines = _text_lines(rendered.pdf)
    _, first = _line(lines, "Mentored twelve")
    second = next(bbox for text, _, bbox in lines if "course staff" in text or "for exams" in text)
    assert second[1] > first[1]  # it did wrap
    assert _inside(first, box) and _inside(second, box)


def test_boxes_on_the_second_page_say_so() -> None:
    _tectonic_or_skip()
    view = _long_view()
    rendered = render(view, IDENTITY, "jakes")

    last = view.sections[-1].entries[0].bullets[-1]
    (box,) = [b for b in rendered.boxes if b.item_id == str(last.id)]
    assert box.page == 2
    _, bbox = next((p, bbox) for t, p, bbox in _text_lines(rendered.pdf) if t == last.text and p == 2)
    assert _inside(bbox, box)


@pytest.fixture
def read_only_vendor(tmp_path, monkeypatch):
    '''A vendored binary without its execute bit and a cache the process
    cannot write, as in a Vercel Function, with /tmp under tmp_path.'''
    vendor = tmp_path / "vendor"
    (vendor / "cache" / "fonts").mkdir(parents=True)
    for i in range(50):
        (vendor / "cache" / "fonts" / f"{i}.otf").write_bytes(os.urandom(4096))
    binary = vendor / resume_render.binary_name()  # tectonic.exe on Windows
    binary.write_bytes(b"#!/bin/sh\n")
    binary.chmod(0o644)
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    monkeypatch.setattr(resume_render, "VENDOR", vendor)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp))
    real_access = os.access
    monkeypatch.setattr(
        resume_render.os, "access",
        lambda path, mode: False if Path(path).parent == vendor else real_access(path, mode),
    )
    return vendor, tmp


def test_concurrent_renders_share_one_complete_cache_copy(read_only_vendor) -> None:
    vendor, tmp = read_only_vendor
    with ThreadPoolExecutor(8) as pool:
        copies = list(pool.map(lambda _: resume_render._cache(), range(16)))
    assert set(copies) == {tmp / "workit-tectonic-cache"}
    assert sorted(p.name for p in (copies[0] / "fonts").iterdir()) == sorted(
        p.name for p in (vendor / "cache" / "fonts").iterdir()
    )
    # No staging folder is left behind
    assert [p.name for p in tmp.iterdir()] == ["workit-tectonic-cache"]


def test_a_failed_cache_copy_leaves_nothing_and_the_next_one_works(read_only_vendor, monkeypatch) -> None:
    _, tmp = read_only_vendor
    real_copytree = shutil.copytree

    def dies_partway(src, dst, **kwargs):
        Path(dst).mkdir()
        (Path(dst) / "half").write_text("x")
        raise OSError("disk full")

    monkeypatch.setattr(resume_render.shutil, "copytree", dies_partway)
    with pytest.raises(TectonicUnavailable):
        resume_render._cache()
    assert list(tmp.iterdir()) == []

    monkeypatch.setattr(resume_render.shutil, "copytree", real_copytree)
    assert (resume_render._cache() / "fonts").is_dir()


def test_a_binary_without_its_execute_bit_runs_from_an_executable_copy(read_only_vendor) -> None:
    _, tmp = read_only_vendor
    with ThreadPoolExecutor(8) as pool:
        copies = set(pool.map(lambda _: resume_render._binary(), range(16)))
    assert copies == {tmp / "workit-tectonic"}
    assert os.access(tmp / "workit-tectonic", os.X_OK)


def test_the_word_file_says_us_citizen_when_checked() -> None:
    from docx import Document

    from app.services.resume_render.word import render_docx

    doc = Document(io.BytesIO(render_docx(VIEW, replace(IDENTITY, us_citizen=True))))
    assert doc.paragraphs[1].text == (
        "U.S. Citizen | +1 123-456-7890 | jake@su.edu | linkedin.com/in/jake | github.com/jake")


def test_the_word_file_prints_the_location_and_leaves_out_hidden_fields() -> None:
    from docx import Document

    from app.services.resume_render.word import render_docx

    identity = replace(IDENTITY, location="Stony Brook, NY")
    doc = Document(io.BytesIO(render_docx(VIEW, identity)))
    assert doc.paragraphs[1].text == (
        "+1 123-456-7890 | jake@su.edu | Stony Brook, NY | linkedin.com/in/jake | github.com/jake")
    page = PageSettings(hidden_header=("email", "linkedin_url"))
    doc = Document(io.BytesIO(render_docx(VIEW, identity, page)))
    assert doc.paragraphs[1].text == "+1 123-456-7890 | Stony Brook, NY | github.com/jake"
    doc = Document(io.BytesIO(render_docx(VIEW, replace(identity, extra="Open to relocation"))))
    assert doc.paragraphs[2].text == "Open to relocation"
    page = PageSettings(hidden_header=("resume_header_extra",))
    doc = Document(io.BytesIO(render_docx(VIEW, replace(identity, extra="Open to relocation"), page)))
    assert "Open to relocation" not in [p.text for p in doc.paragraphs]


def test_the_word_file_prints_a_projects_tools_under_its_heading() -> None:
    from docx import Document

    from app.services.resume_render.word import render_docx

    texts = [p.text for p in Document(io.BytesIO(render_docx(_tools_view(), IDENTITY))).paragraphs]
    heading = next(i for i, t in enumerate(texts) if t.startswith("workitjobs.ai | AI Job Search Platform"))
    assert texts[heading + 1] == "Next.js, TypeScript, Tailwind CSS, FastAPI, PostgreSQL"
    assert texts[heading + 2] == "Lead design and front-end on a 5-person team"
    # A project with no tools goes straight to its bullets
    gitlytics = next(i for i, t in enumerate(texts) if t.startswith("Gitlytics"))
    assert texts[gitlytics + 1].startswith("Developed a full-stack web application")


def test_an_unchecked_header_hashes_as_before_the_check_box() -> None:
    from app.services.sent_resumes import _identity

    # A resume sent before the field existed still matches its repeat
    assert "us_citizen" not in _identity(IDENTITY)
    assert _identity(replace(IDENTITY, us_citizen=True))["us_citizen"] is True


def test_a_bullet_whose_last_line_is_full_has_no_empty_line_after_it():
    # Jake's \resumeItem puts a space after its argument ("{#1 \vspace{-2pt}}").
    # When the last line was full, TeX broke at that space and printed an
    # empty line after the bullet, 14.9 pt where bullets sit 2.9 pt apart
    # (KAN-391). This text fills its last line in the sample view.
    _tectonic_or_skip()
    entry = next(e for s in VIEW.sections for e in s.entries if len(e.bullets) >= 2)
    full = replace(entry.bullets[0], text=(
        "Cut the build from 40 to 9 minutes by caching dependencies and splitting tests across "
        "four workers and more iiiiiiiiii"))
    view = replace(VIEW, sections=tuple(
        replace(s, entries=tuple(
            replace(e, bullets=(full, *e.bullets[1:])) if e.id == entry.id else e for e in s.entries))
        for s in VIEW.sections))

    boxes = [b for b in render(view, IDENTITY, "jakes").boxes if b.kind == "bullet"]
    at = next(i for i, b in enumerate(boxes) if b.item_id == str(full.id))
    assert boxes[at + 1].y0 - boxes[at].y1 < 5


def _long_bullet() -> tuple[ResumeView, str]:
    """The sample with a first bullet that wraps at any setting."""
    entry = next(e for s in VIEW.sections for e in s.entries if e.bullets)
    long = replace(entry.bullets[0], text=" ".join(["Cut the build from forty to nine minutes"] * 8))
    view = replace(VIEW, sections=tuple(
        replace(s, entries=tuple(
            replace(e, bullets=(long, *e.bullets[1:])) if e.id == entry.id else e for e in s.entries))
        for s in VIEW.sections))
    return view, str(long.id)


def test_the_default_page_is_jakes_own() -> None:
    assert jakes_document("x", DEFAULT_PAGE) == jakes_document("x")
    assert jakes_document("x") == TEMPLATE.read_text(encoding="utf-8").replace("\n%%BODY%%\n", "\nx\n", 1)


def test_page_settings_go_after_jakes_preamble_and_only_when_they_differ() -> None:
    tex = jakes_document("x", PageSettings(font_size=12, line_spacing=1.3, side_margin=1.0, top_margin=1.0, alignment="justified"))
    preamble = tex.split("\\begin{document}")[0]
    assert "letterpaper,12pt" in preamble
    assert "\\linespread{1.3}" in preamble and "\\sloppy" in preamble
    assert "\\addtolength{\\textwidth}{-1.0in}" in preamble
    assert "linespread" not in jakes_document("x", PageSettings(font_size=10))


@pytest.mark.parametrize("settings", [
    {"font_family": "Comic Sans"}, {"name_size": 99}, {"heading_size": 99}, {"title_size": 99}, {"body_size": 99},
    {"body_size": 10.25}, {"body_size": 7.5}, {"body_size": float("nan")}, {"body_size": "10"},
    {"date_format": "roman"}, {"education_first": "gpa"},
    {"font_size": 13}, {"line_spacing": 2.0}, {"side_margin": 0.1}, {"top_margin": 2.0}, {"alignment": r"\\input{/etc/passwd}"},
])
def test_a_page_setting_off_the_lists_never_reaches_the_latex(settings) -> None:
    with pytest.raises(ValueError):
        PageSettings(**settings)


@pytest.mark.parametrize("page", [
    *(PageSettings(font_size=size) for size in FONT_SIZES),
    *(PageSettings(font_family=family) for family in FONT_FAMILIES),
    PageSettings(name_size=NAME_SIZES[0], heading_size=HEADING_SIZES[0], title_size=TITLE_SIZES[0], body_size=BODY_SIZES[0]),
    PageSettings(name_size=NAME_SIZES[-1], heading_size=HEADING_SIZES[-1], title_size=TITLE_SIZES[-1], body_size=BODY_SIZES[-1]),
    PageSettings(name_size=31.5, heading_size=15.5, title_size=13.5, body_size=8.5),
    *(PageSettings(date_format=date_format) for date_format in DATE_FORMATS),
    PageSettings(education_first="degree"),
    *(PageSettings(line_spacing=spacing) for spacing in LINE_SPACINGS),
    *(PageSettings(side_margin=margin, top_margin=margin) for margin in MARGINS),
    *(PageSettings(alignment=alignment) for alignment in ALIGNMENTS),
    PageSettings(font_size=12, line_spacing=1.3, side_margin=1.0, top_margin=1.0, alignment="justified"),
    PageSettings(font_size=10, line_spacing=1.15, side_margin=0.75, top_margin=0.75, alignment="justified"),
], ids=repr)
def test_each_page_setting_compiles_offline_and_its_boxes_read_as_lines(page) -> None:
    _tectonic_or_skip()
    view, long_id = _long_bullet()
    rendered = render(view, IDENTITY, "jakes", page)
    assert rendered.wrapped_line == page.wrapped_line
    box = next(b for b in rendered.boxes if b.item_id == long_id)
    # A wrapped line runs to the text's right edge, inside the page's margin
    assert box.x1 == pytest.approx(612 - page.side_margin * 72, abs=1)
    assert box.x0 >= page.side_margin * 72
    assert box_lines(box, rendered.wrapped_line) >= 3
    # The box is as many lines tall as the bullet prints
    height = box.y1 - box.y0 - resume_render.ASCENT - resume_render.DESCENT
    assert height / (box_lines(box, rendered.wrapped_line) - 1) == pytest.approx(page.wrapped_line, abs=0.3)


def test_justified_lines_end_at_the_margin_and_left_lines_do_not() -> None:
    _tectonic_or_skip()
    view, _ = _long_bullet()

    def wrapped_ends(page: PageSettings) -> list[float]:
        pdf = render(view, IDENTITY, "jakes", page).pdf
        from pdfminer.layout import LTTextContainer, LTTextLine

        ends = []
        for layout in extract_pages(io.BytesIO(pdf)):
            for block in layout:
                if isinstance(block, LTTextContainer):
                    ends += [line.x1 for line in block if isinstance(line, LTTextLine)
                             and "Cut the build" in line.get_text()]
        return ends[:-1]  # a bullet's last line stops where its words do

    assert all(end == pytest.approx(576, abs=0.5) for end in wrapped_ends(PageSettings(alignment="justified")))
    assert any(end < 575 for end in wrapped_ends(DEFAULT_PAGE))


def test_a_bigger_page_setting_can_run_past_one_page() -> None:
    _tectonic_or_skip()
    assert render(VIEW, IDENTITY, "jakes").page_count == 1
    assert render(VIEW, IDENTITY, "jakes", PageSettings(font_size=12, line_spacing=1.3, side_margin=1.0, top_margin=1.0)).page_count == 2


def test_the_latex_file_prints_the_same_page_settings() -> None:
    page = PageSettings(font_size=10, side_margin=0.75)
    tex = resume_render.latex(VIEW, IDENTITY, "jakes", page)
    assert "letterpaper,10pt" in tex and r"\addtolength{\textwidth}{-0.5in}" in tex


STYLED = PageSettings(
    section_spacing=8, entry_spacing=4, accent="#1E3A5F", bullet="dash", show_divider=False, header_alignment="left")


def test_the_style_settings_write_only_what_differs() -> None:
    tex = resume_render.latex(VIEW, IDENTITY, "jakes", STYLED)
    assert r"\definecolor{wiaccent}{rgb}" in tex and r"\textcolor{wiaccent}" in tex
    assert r"\renewcommand{\labelitemii}{--}" in tex
    assert r"\begin{flushleft}" in tex and r"\begin{center}" not in tex
    assert r"\vspace{4pt}\scshape" in tex and "titlerule" not in tex.split("begin{document}")[0].split("wiaccent")[-1]
    assert r"\vspace{-1pt}}" in tex
    plain = resume_render.latex(VIEW, IDENTITY, "jakes")
    assert "wiaccent" not in plain and r"\begin{center}" in plain


@pytest.mark.parametrize("page", [
    STYLED,
    *(PageSettings(accent=accent) for accent in resume_render.ACCENTS),
    PageSettings(header_alignment="right"),
    PageSettings(show_divider=False, section_spacing=12),
    PageSettings(accent="#14532D", section_spacing=4),
    PageSettings(bullet="dash", entry_spacing=6),
    PageSettings(top_margin=1.0),
    PageSettings(side_margin=1.0),
], ids=repr)
def test_each_style_setting_compiles_offline_with_its_text(page) -> None:
    _tectonic_or_skip()
    rendered = render(VIEW, IDENTITY, "jakes", page)
    assert "Jake Ryan" in _text(rendered.pdf)
    assert rendered.boxes


def test_the_dash_bullet_prints_a_dash_and_no_dot() -> None:
    _tectonic_or_skip()
    assert "•" in _text(render(VIEW, IDENTITY, "jakes").pdf)
    dashed = _text(render(VIEW, IDENTITY, "jakes", PageSettings(bullet="dash")).pdf)
    assert "•" not in dashed and "– Developed" in dashed


def test_a_top_margin_moves_the_page_down_and_leaves_its_width() -> None:
    _tectonic_or_skip()
    top = lambda page: min(b.y0 for b in render(VIEW, IDENTITY, "jakes", page).boxes if b.kind == "full_name")
    assert top(PageSettings(top_margin=1.0)) == pytest.approx(top(DEFAULT_PAGE) + 36, abs=1)


def test_header_alignment_moves_the_name() -> None:
    _tectonic_or_skip()
    x = lambda page: next(b.x0 for b in render(VIEW, IDENTITY, "jakes", page).boxes if b.kind == "full_name")
    assert x(PageSettings(header_alignment="left")) < x(DEFAULT_PAGE) < x(PageSettings(header_alignment="right"))


def test_section_order_moves_the_sections_on_the_page() -> None:
    order = ("skills", "projects", "experience", "education", "leadership", "awards", "certifications")
    tex = resume_render.latex(VIEW, IDENTITY, "jakes", PageSettings(section_order=order))
    at = [tex.index(rf"\section{{{name}}}") for name in ("Technical Skills", "Projects", "Experience", "Education")]
    assert at == sorted(at)
    assert resume_render.latex(VIEW, IDENTITY, "jakes") == resume_render.latex(
        VIEW, IDENTITY, "jakes", PageSettings(section_order=list(resume_render.SECTION_ORDER)))


@pytest.mark.parametrize("order", [("skills",), ("skills", "skills"), (*resume_render.SECTION_ORDER, r"\\input")])
def test_a_section_order_must_name_every_section_once(order) -> None:
    with pytest.raises(ValueError):
        PageSettings(section_order=order)


def test_a_moved_section_order_compiles_offline_with_its_boxes() -> None:
    _tectonic_or_skip()
    order = ("skills", *resume_render.SECTION_ORDER[:-1])
    rendered = render(VIEW, IDENTITY, "jakes", PageSettings(section_order=order))
    skill = min(b.y0 for b in rendered.boxes if b.kind == "skill")
    bullet = min(b.y0 for b in rendered.boxes if b.kind == "bullet")
    assert skill < bullet


def _fonts(page: PDFPage) -> list[str]:
    fonts = resolve1(page.resources.get("Font", {}))
    return [literal_name(resolve1(font)["BaseFont"]) for font in fonts.values()]


def test_a_family_goes_after_the_preamble_and_only_under_xetex() -> None:
    tex = jakes_document("x", PageSettings(font_family="tinos"))
    test, regular, end = tex.index(r"\ifdefined\XeTeXversion"), tex.index("Tinos-Regular.ttf"), tex.index(r"\begin{document}")
    assert test < regular < end
    # On Overleaf, whose default is pdfLaTeX, the .tex file keeps Jake's font
    assert tex.index(r"\renewcommand{\rmdefault}{wi}") < tex.index("\n" + r"\fi" + "\n", regular)
    assert "XeTeXversion" not in jakes_document("x", PageSettings(font_size=12))


@pytest.mark.parametrize("family", FONT_FAMILIES)
def test_each_family_prints_in_its_own_font(family: str) -> None:
    _tectonic_or_skip()
    pdf = render(VIEW, IDENTITY, "jakes", PageSettings(font_family=family)).pdf
    names = {name.split("+")[-1] for page in PDFPage.get_pages(io.BytesIO(pdf)) for name in _fonts(page)}
    # The file's name, less its style: Tinos, EBGaramond, XCharter
    assert any(name.startswith(FONT_FAMILIES[family][0].split("-")[0]) for name in names), names
    assert not any("LMRoman" in name for name in names), names


def test_a_kind_of_text_takes_its_own_size_and_leaves_the_others() -> None:
    tex = jakes_document("x", PageSettings(body_size=9.5))
    assert r"\renewcommand{\small}{\fontsize{9.5}{11.4}\selectfont}" in tex
    assert r"\renewcommand{\normalsize}" not in tex
    assert PageSettings(body_size=9.5).wrapped_line == pytest.approx(11.4)
    assert PageSettings().wrapped_line == WRAPPED_LINE
    assert r"\fontsize{14}{16.8}\selectfont" in jakes_document("x", PageSettings(heading_size=14))
    assert r"\fontsize{28}" in jakes_body(VIEW, IDENTITY, page=PageSettings(name_size=28))
    assert r"\Huge" in jakes_body(VIEW, IDENTITY, page=PageSettings(body_size=9.5))


def test_every_kind_of_text_changes_the_page_it_prints() -> None:
    _tectonic_or_skip()
    plain = render(VIEW, IDENTITY, "jakes", DEFAULT_PAGE).pdf
    for page in (PageSettings(name_size=20), PageSettings(heading_size=14), PageSettings(title_size=12), PageSettings(body_size=9)):
        assert render(VIEW, IDENTITY, "jakes", page).pdf != plain, page


def test_the_api_takes_exactly_what_the_page_can_print() -> None:
    fields = ApiPageSettings.model_fields
    assert set(get_args(fields["font_family"].annotation)) == {"latin_modern", *FONT_FAMILIES}
    assert set(get_args(fields["date_format"].annotation)) == set(DATE_FORMATS)
    assert set(get_args(fields["education_first"].annotation)) == set(EDUCATION_FIRST)
    scales = {"name_size": NAME_SIZES, "heading_size": HEADING_SIZES, "title_size": TITLE_SIZES, "body_size": BODY_SIZES}
    for field, (low, high) in scales.items():
        for size in (low, low + 0.5, high):
            for settings in (ApiPageSettings, PageSettings):
                assert getattr(settings(**{field: size}), field) == size
        for size in (low - 0.5, low + 0.25, high + 0.5):
            for settings in (ApiPageSettings, PageSettings):
                with pytest.raises(ValueError):
                    settings(**{field: size})


def test_a_compile_gets_windows_own_folders_and_no_secret(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SYSTEMROOT", "C:/Windows")
    monkeypatch.setenv("DATABASE_URL", "postgresql://secret")
    monkeypatch.setattr(resume_render.os, "name", "nt")
    env = resume_render._env(tmp_path, "work")
    assert env["SYSTEMROOT"] == "C:/Windows"
    assert "DATABASE_URL" not in env
    # Off Windows the compile gets no Windows folder, even when one is set
    monkeypatch.setattr(resume_render.os, "name", "posix")
    assert "SYSTEMROOT" not in resume_render._env(tmp_path, "work")


def _education():
    return next(s for s in VIEW.sections if s.section == "education").entries[0]


@pytest.mark.parametrize("date_format, expected", [
    ("short", "Aug. 2018 – May 2021"), ("long", "August 2018 – May 2021"),
    ("year", "2018 – 2021"), ("numeric", "08/2018 – 05/2021"),
])
def test_a_date_format_reads_as_it_says(date_format, expected) -> None:
    assert dates(_education(), date_format) == expected


def test_year_only_prints_one_year_once() -> None:
    entry = replace(_education(), end_month=_education().start_month)
    assert dates(entry, "year") == "2018"
    # one month in any format prints once
    assert dates(entry, "short") == "Aug. 2018"


def test_degree_first_swaps_educations_rows_and_their_click_targets() -> None:
    school = _education()
    first = heading(school, "short", "degree")
    assert (first.title, first.subtitle) == (heading(school).subtitle, school.title)
    assert heading_fields("education", degree_leads(school, "degree"))["subtitle"] == "title"

    nothing = replace(school, degree=None, field_of_study=None, organization=None)
    assert heading(nothing, "short", "degree").title == school.title
    assert not degree_leads(nothing, "degree")


def test_degree_first_leaves_every_other_section_alone() -> None:
    job = next(s for s in VIEW.sections if s.section == "experience").entries[0]
    assert heading(job, "short", "degree") == heading(job)


def test_a_box_keeps_its_field_when_degree_first_moves_it() -> None:
    _tectonic_or_skip()
    page = PageSettings(education_first="degree")
    boxes = render(VIEW, IDENTITY, "jakes", page).boxes
    school = _education()
    title = next(b for b in boxes if b.item_id == str(school.id) and b.kind == "title")
    degree = next(b for b in boxes if b.item_id == str(school.id) and b.kind == "degree")
    assert title.text == school.title
    assert degree.y0 < title.y0


def test_the_word_file_follows_the_date_format_and_the_education_order() -> None:
    from docx import Document

    from app.services.resume_render.word import render_docx

    page = PageSettings(date_format="year", education_first="degree")
    rows = [p.text for p in Document(io.BytesIO(render_docx(VIEW, IDENTITY, page))).paragraphs]
    school = next(i for i, row in enumerate(rows) if row.startswith(_education().title))
    assert heading(_education()).subtitle in rows[school - 1]
    assert rows[school].endswith("2018 – 2021")


# --- Text the PDF printed wrong (2026-11-12 audit) ---------------------------

@pytest.mark.parametrize(("typed", "printed"), [
    ("16465550142", "+1 646-555-0142"),
    ("1234567890", "+1 123-456-7890"),
    ("(516)-555-0187", "+1 516-555-0187"),
    ("+44 7911 123456", "+44 7911 123456"),
    ("555-0100 ext 12", "555-0100 ext 12"),
])
def test_a_phone_prints_as_the_profile_shows_it(typed, printed):
    # The resume printed the saved value bare ("16465550142")
    assert phone_text(typed) == printed


@pytest.mark.parametrize(("score", "scale", "printed"), [
    ("90", "100", "GPA: 90/100"),
    ("85.0", "100.0", "GPA: 85/100"),
    ("3.80", "4.00", "GPA: 3.80/4.00"),
    ("3.8", "4.0", "GPA: 3.80/4.00"),
    ("4", "4", "GPA: 4.00/4.00"),
    ("8.5", "10", "GPA: 8.50/10"),
    ("92.5", "100", "GPA: 92.5/100"),
    ("3.81", "4", "GPA: 3.81/4.00"),
])
def test_a_gpa_keeps_its_zeros(score, scale, printed):
    # "90/100" printed "9/100": zeros came off a number with no decimal point
    entry = ViewEntry(uuid.uuid4(), "education", "Riverside State University",
                      gpa=Decimal(score), gpa_scale=Decimal(scale))
    assert gpa(entry) == printed


def test_a_field_the_degree_names_prints_once():
    entry = ViewEntry(uuid.uuid4(), "education", "Riverside State University",
                      degree="B.S. in Computer Science", field_of_study="Computer Science")
    assert heading(entry).subtitle == "B.S. in Computer Science"


def test_typed_quotes_dashes_and_backticks_print_as_typed():
    # TeX's ligatures made "--dry-run" print "–dry-run", "reviews!`" print
    # "reviews¡", and both ends of "smart" closing quotes
    _tectonic_or_skip()
    bullet = 'Ran "smart" --dry-run checks with `git bisect`; reviews!` came back'
    view = _with_entries(VIEW, ViewEntry(uuid.uuid4(), "leadership", "Tutor", organization="Learning Center",
                                         bullets=(ViewBullet(uuid.uuid4(), bullet),)))
    rendered = render(view, IDENTITY, "jakes")
    assert "Ran “smart” --dry-run checks with `git bisect`; reviews!` came back" in _text(rendered.pdf).replace("\n", " ")
    assert rendered.missing_characters == ()


def test_a_projects_link_prints_short_and_clicks_through():
    _tectonic_or_skip()
    project = ViewEntry(uuid.uuid4(), "projects", "Maze Robot", organization="HackSBU",
                        link="https://github.com/jd/maze-robot")
    view = _with_entries(VIEW, project)
    rendered = render(view, IDENTITY, "jakes")
    assert any(t.startswith("Maze Robot | HackSBU | github.com/jd/maze-robot") for t, _, _ in _text_lines(rendered.pdf))
    assert "https://github.com/jd/maze-robot" in _link_targets(rendered.pdf)


def _skills(*pairs: tuple[str, str | None]) -> list[ViewSkill]:
    return [ViewSkill(uuid.uuid4(), name, group) for name, group in pairs]


def test_groups_that_differ_only_in_case_or_and_print_as_one_line():
    # KAN-810: "Frameworks" and "frameworks" printed as two lines, and an
    # upload's lowercase "other" beside the real "Other"
    skills = _skills(("React", "Frameworks"), ("Python", "Languages"), ("Django", "frameworks"),
                     ("Git", "tools and platforms"), ("Docker", "Tools & Platforms"), ("Figma", "other"),
                     ("Excel", None))
    assert [(label, [s.name for s in members]) for label, members in skill_lines(skills)] == [
        ("Frameworks", ["React", "Django"]), ("Languages", ["Python"]),
        ("Tools & Platforms", ["Git", "Docker"]), ("Other", ["Figma", "Excel"])]


def test_a_group_named_only_in_lower_case_prints_in_title_case():
    skills = _skills(("AWS", "cloud and devops"), ("Python", "Languages"))
    assert [label for label, _ in skill_lines(skills)] == ["Cloud and Devops", "Languages"]


def test_a_lone_group_named_other_prints_unlabeled():
    skills = _skills(("Excel", "other"), ("Word", None))
    assert skill_lines(skills) == [("", tuple(skills))]


# --- A long heading wraps before its dates (KAN-807) ---------------------------

def _long_heading_view() -> ResumeView:
    month = datetime.date
    return ResumeView(sections=(
        ViewSection("education", (
            ViewEntry(uuid.uuid4(), "education", "Lakeside Global Campus Signal Processing and Machine Learning Program",
                      location="Lakeside, NY", end_month=month(2025, 8, 1), end_kind="month"),
        )),
        ViewSection("experience", (
            ViewEntry(uuid.uuid4(), "experience",
                      "Undergraduate Research Assistant, Autonomous Systems and Robotics Laboratory",
                      organization="Hillcrest State University", location="Hillcrest, NY",
                      start_month=month(2024, 9, 1), end_kind="present",
                      bullets=(ViewBullet(uuid.uuid4(), "Tuned the PD loop"),)),
        )),
        ViewSection("projects", (
            ViewEntry(uuid.uuid4(), "projects", "Maze Robot: Autonomous Navigation with A* Planning and Sensor Fusion",
                      organization="IEEE Student Branch", start_month=month(2025, 1, 1),
                      end_month=month(2025, 4, 1), end_kind="month"),
        )),
    ), skills=())


def test_a_long_heading_wraps_before_its_dates_and_stays_on_the_page():
    # KAN-807: Jake's `l` column never breaks, so a long title ran under the
    # dates and past the margin ("Present" and "Apr. 2025" were cut off)
    _tectonic_or_skip()
    rendered = render(_long_heading_view(), IDENTITY, "jakes")
    edge = 576  # Jake's text area ends half an inch in from the letter page's 612 pt
    for entry_id in {b.item_id for b in rendered.boxes if b.kind == "title"}:
        boxes = {b.kind: b for b in rendered.boxes if b.item_id == entry_id}
        title = boxes["title"]
        right = min((b for b in boxes.values() if b.x0 > title.x0 and abs(b.y0 - title.y0) < 1), key=lambda b: b.x0)
        # Its words stop short of the right side on the title's first line,
        # and the right side ends inside the text area
        assert title.x1 < right.x0 and right.x1 <= edge + 1
    assert all(t.rstrip() for t, _, _ in _text_lines(rendered.pdf))
    titles = [b for b in rendered.boxes if b.kind == "title"]
    assert sum(1 for b in titles if b.y1 - b.y0 > 20) == 2  # two titles wrap; the project's tag does


def test_a_heading_that_fits_keeps_jake_s_own_table():
    # Only a heading wider than its row wraps: set with a wrapping column,
    # two one-row headings in a row stood 13.5 pt further apart
    _tectonic_or_skip()
    month = datetime.date
    schools = tuple(ViewEntry(uuid.uuid4(), "education", f"Program {n}", location="Lakeside, NY",
                              end_month=month(2025, 8, 1), end_kind="month") for n in (1, 2))
    rendered = render(ResumeView((ViewSection("education", schools),), ()), IDENTITY, "jakes")
    first, second = sorted((b for b in rendered.boxes if b.kind == "title"), key=lambda b: b.y0)
    assert second.y0 - first.y0 < 15
    assert r"\else" + "\n" + r"\vspace{-2pt}\item" in jakes_body(
        ResumeView((ViewSection("education", schools),), ()), IDENTITY, marks=False)


def test_a_date_given_as_a_year_alone_prints_as_the_year():
    # KAN-808: it is January of the year, and printed "Jan. 2019 – Jan. 2023"
    entry = ViewEntry(uuid.uuid4(), "education", "Hillcrest State University",
                      start_month=datetime.date(2019, 1, 1), end_month=datetime.date(2023, 1, 1),
                      end_kind="month", year_only=("start_month", "end_month"))
    assert dates(entry) == "2019 – 2023"
    assert dates(replace(entry, end_kind="expected", year_only=("end_month",))) == "Jan. 2019 – Expected 2023"
    award = ViewEntry(uuid.uuid4(), "awards", "Dean's List", award_date=datetime.date(2024, 1, 1),
                      year_only=("award_date",))
    assert dates(award) == "2024"
