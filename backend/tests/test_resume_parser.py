"""Regression tests for the heuristic resume parser.

Each fixture is the extracted text of a real resume in a layout that once broke
the parser, cut to start at the first section header so no contact details are
stored.

When a new layout breaks parsing: extract its text, add it as a fixture, write
down what it *should* parse to here, then fix the parser until every case passes.
"""
from pathlib import Path

import pytest

from app.utils import resume_parser
from app.utils.resume_parser import count_sections, parse_resume, section_of

FIXTURES = Path(__file__).parent / "fixtures"

# education: (institution, degree, field_of_study, gpa, end_date)
# experience and leadership: (organization, title, location, start_date, end_date, bullet_count)
# awards: (title, issuer, date)
# A fixture without "leadership" or "awards" keys expects those sections empty.
EXPECTED = {
    # Google Docs export: pipes in the school line, a second role with no company line
    "google_docs_single_column.txt": {
        "education": [
            # the minor follows the major: an entry has no field of its own for it
            ("Stony Brook University", "B.S.", "Computer Science, minor in Writing & Rhetoric", None, "2026-12-01"),
        ],
        "experience": [
            ("Pulp Internet Corporation (Seed-Stage AI Startup)", "Product Designer & Engineer",
             None, "2025-10-01", "2026-08-01", 3),
            ("Pulp Internet Corporation (Seed-Stage AI Startup)", "Product & Operations Lead Intern",
             None, "2025-01-01", "2025-08-01", 3),
        ],
        "projects": [
            "thinkwell (Pulp) |AI Communications Intelligence Platform",
            "pulp101.com (Pulp) | Editorial & Discussion Platform",
            "AI Pitch Room (Pulp) |Interactive Investor Experience",
        ],
        "skill_count": 25,
    },
    # Company+Dates / Title+Location; "Intern Brooklyn, NY" must not become the location
    "react_pdf_single_column.txt": {
        "education": [
            ("Stony Brook University", "B.S.", "Computer Science Honors", 3.86, "2027-05-01"),
        ],
        "experience": [
            ("Washington University Summer Engineering Fellowship (WUSEF) – CyanoAgent",
             "AI Research Fellow", "St. Louis, MO", "2026-05-01", "2026-08-01", 4),
            ("Stony Brook University Computer Science Department – Operations & Data",
             "Software Engineer and IT Support", "Stony Brook, NY", "2025-01-01", "2026-05-01", 4),
            ("Pulp Corporation", "Software Engineer Intern", "Brooklyn, NY", "2025-01-01", "2025-08-01", 3),
            ("Stony Brook University Campus Residences", "Resident Assistant", "Stony Brook, NY",
             "2024-08-01", None, 3),
        ],
        "projects": ["Academic Advising Bot", "Playlister"],
        "skill_count": 27,
    },
    # Title / Company / Dates+Location, "current" end dates, bullets drawn as shapes
    "two_column_no_bullet_glyphs.txt": {
        "education": [
            ("The Harker School", "High School Diploma", None, None, "2018-01-01"),
        ],
        "experience": [
            ("Panda Express", "Cashier", "San Jose, CA", "2022-01-01", None, 4),
            ("Chick-fil-A", "Retail Sales Associate", "San Jose, CA", "2020-01-01", "2022-01-01", 4),
            ("The Table", "Dishwasher", "San Jose, CA", "2018-01-01", "2020-01-01", 4),
        ],
        "projects": [],
        "skill_count": 9,
    },
    # Title | Company / Location | Dates, and everything on one line
    "word_pipe_layout.txt": {
        "education": [
            ("Stony Brook University", "B.S.", "Computer Science Honors", 3.86, "2027-05-01"),
        ],
        "experience": [
            ("Washington University Summer Engineering Fellowship", "AI Researcher", "St. Louis, MO",
             "2026-05-01", "2026-08-01", 3),
            ("Stony Brook University Operations & Data", "Software Engineer and IT Analyst",
             "Stony Brook, NY", "2025-01-01", "2026-05-01", 3),
            ("Pulp Corporation", "Software Engineer Intern", "Brooklyn, NY", "2025-01-01", "2025-08-01", 3),
            ("Stony Brook University Campus Residences", "Resident Assistant", "Stony Brook, NY",
             "2024-08-01", None, 3),
        ],
        "projects": ["WorkIt | Full Stack Recruiting Platform", "Stony Brook Academic Advising Bot"],
        "skill_count": 18,
    },
    # KAN-263: "Leadership Activities", two heading words with no "&", was no
    # heading, so its clubs joined the project above. Made-up text in the
    # layout of the resume the ticket names: Organization + Dates, then
    # Role + Location, then bullets.
    "leadership_activities_heading.txt": {
        "education": [
            ("Lakeview State University", "Bachelor of Science", "Computer Science", None, "2027-05-01"),
        ],
        "experience": [
            ("Northwind Data", "Software Engineering Intern", "Albany, NY", "2025-06-01", "2025-08-01", 2),
        ],
        "leadership": [
            ("Lakeview State University Residence Life", "Resident Assistant", "Albany, NY", "2024-08-01", None, 2),
            ("Lakeview Robotics Club", "Outreach Lead", "Albany, NY", "2023-09-01", "2024-05-01", 1),
        ],
        "projects": ["Course Planner Bot"],
        "skill_count": 5,
    },
    # Leadership & Activities in the Company+Dates / Title+Location layout;
    # Awards one per line as "Award – Issuer  Date", one with a year only
    "leadership_and_awards_single_column.txt": {
        "education": [
            ("Riverside State University", "B.S.", "Mechanical Engineering", 3.62, "2027-05-01"),
        ],
        "experience": [
            ("Harbor Robotics", "Mechanical Engineering Intern", "Portland, OR", "2026-06-01", "2026-08-01", 2),
        ],
        "leadership": [
            ("Society of Women Engineers", "Vice President", "Riverside, CA", "2025-09-01", None, 2),
            ("Formula SAE Racing Team", "Suspension Lead", "Riverside, CA", "2024-09-01", "2025-05-01", 1),
        ],
        "awards": [
            ("Dean's List", "Riverside State University", "2025-12-01"),
            ("First Place, Regional Design Competition", "ASME", "2025-04-01"),
            ("Merit Scholarship", None, "2024-01-01"),
        ],
        "projects": [],
        "skill_count": 6,
    },
    # "LEADERSHIP EXPERIENCE" is not Experience; "HONORS & AWARDS" as bullets
    # split by "|"
    "pipe_layout_leadership_honors.txt": {
        "education": [
            ("Northfield University", "Bachelor of Science", "Computer Science", None, "2027-12-01"),
        ],
        "experience": [],
        "leadership": [
            ("Coding Club", "President", "Chicago, IL", "2025-08-01", None, 2),
            ("Northfield University Learning Center", "Peer Tutor", "Chicago, IL", "2025-01-01", "2025-05-01", 1),
        ],
        "awards": [
            ("Hackathon Winner, Best Use of Data", "HackNorth", "2025-10-01"),
            ("President's Scholarship", "Northfield University", "2025-08-01"),
        ],
        "projects": ["Budget Buddy"],
        "skill_count": 3,
    },
    # Jake's Resume from LaTeX: "Expected Graduation:" beside the school, a
    # wrapped coursework bullet, undated "Name| tools" projects, a wrapped
    # skills line, and PDF gaps after bold phrases
    "jakes_undated_projects.txt": {
        "education": [
            ("Lakeview University", "Bachelor of Science", "Computer Science", 3.62, "2027-05-01"),
        ],
        "experience": [
            ("Harbor Transit", "Software Engineer Intern", None, "2025-06-01", "2025-08-01", 2),
            ("Riverside Robotics Lab", "Undergraduate Researcher", None, "2024-12-01", "2025-05-01", 1),
        ],
        "projects": ["Line Following Robot", "Plant Disease Classifier", "Arm Control Demo"],
        "skill_count": 11,
    },
    # KAN-348: "Research Experience" and "Publications" once joined Education,
    # so a lab and a paper read as schools. Lab roles are jobs; papers are
    # projects, one per citation, wrapped lines and all
    "research_and_publications.txt": {
        "education": [
            ("Hillcrest State University", "B.S.", "Computer Science", 3.71, "2027-05-01"),
        ],
        "experience": [
            ("Northwind Analytics", "Data Science Intern", "Boston, MA", "2025-06-01", "2025-08-01", 1),
            ("Computational Systems Lab", "Undergraduate Researcher", "Hillcrest, NY", "2025-01-01", None, 2),
            ("Vision and Learning Group", "Research Assistant", "Hillcrest, NY", "2024-09-01", "2024-12-01", 1),
        ],
        "projects": [
            ("Lee, R., Ortiz, M. (2025). Faster Cache Simulation with Sampled Traces. Proceedings "
             "of the Workshop on Systems Research."),
            "Ortiz, M., Lee, R. (2024). A Benchmark for Small-Object Detection. arXiv preprint",
        ],
        "skill_count": 5,
    },
    # Apply's sample resume: "Company - Title - Dates" on one line, dates as
    # "Jun-Aug 2026", and the school's line in dash fields. Before, the
    # title held the company and dates, the second job took the first one's
    # company, and the school had no graduation date.
    "dash_separated_one_line.txt": {
        "education": [
            ("Illinois State University", "B.S.", "Computer Science, minor in Mathematics", 3.7, "2028-05-01"),
        ],
        "experience": [
            ("Example Logistics", "Software Engineering Intern", None, "2026-06-01", "2026-08-01", 2),
            ("Illinois State University Library", "Student Developer", None, "2025-09-01", None, 1),
        ],
        "projects": ["Robotics Club - Software Lead"],
        "skill_count": 10,
    },
}


def _iso(d):
    return d.isoformat() if d else None


def _bullet_count(description):
    return len(description.splitlines()) if description else 0


@pytest.mark.parametrize("fixture", EXPECTED)
def test_parses_fixture(fixture):
    expected = EXPECTED[fixture]
    parsed = parse_resume((FIXTURES / fixture).read_text(encoding="utf-8"))

    assert [
        (e.institution, e.degree, e.field_of_study, e.gpa, _iso(e.end_date))
        for e in parsed.education
    ] == expected["education"]
    assert [
        (e.company_name, e.title, e.location, _iso(e.start_date), _iso(e.end_date),
         _bullet_count(e.description))
        for e in parsed.experience
    ] == expected["experience"]
    assert [
        (e.company_name, e.title, e.location, _iso(e.start_date), _iso(e.end_date),
         _bullet_count(e.description))
        for e in parsed.leadership
    ] == expected.get("leadership", [])
    assert [(a.title, a.issuer, _iso(a.date)) for a in parsed.awards] == expected.get("awards", [])
    assert [p.project_name for p in parsed.projects] == expected["projects"]
    assert len(parsed.skills) == expected["skill_count"]


def test_every_fixture_has_expectations():
    # A fixture dropped in without expectations would silently test nothing
    assert {p.name for p in FIXTURES.glob("*.txt")} == set(EXPECTED)


def test_jakes_layout_details():
    parsed = parse_resume((FIXTURES / "jakes_undated_projects.txt").read_text(encoding="utf-8"))
    school = parsed.education[0]
    assert school.gpa_scale == 4.0
    # the wrapped second line of coursework stays with the first
    assert school.description == (
        "Relevant Coursework: Data Structures & Algorithms, Discrete Mathematics, Graph Theory, "
        "Linear Algebra, Operating Systems, Compilers, Probability & Statistics"
    )
    assert [p.technologies for p in parsed.projects] == [
        ["C++", "CMake", "Raspberry Pi"], ["Python", "PyTorch"], ["C++", "CUDA"],
    ]
    # a PDF gap after a bold phrase is one space; a missing-glyph tilde is "~"
    assert parsed.projects[0].description.splitlines()[0].startswith("Programmed a Raspberry Pi to")
    # set apart from the word before it, as the PDF shows it (math spacing)
    assert "from ~90ms" in parsed.projects[2].description
    # the wrapped "Concepts" line keeps its group
    assert [(s.skill_name, s.category) for s in parsed.skills[-2:]] == [
        ("Machine Learning", "Concepts"), ("Agile", "Concepts"),
    ]


# Section headings from career-center guides (KAN-348). A heading the parser
# does not know is no section: its text joins the section above it.
HEADINGS = [
    # formats: a colon, a rule, a dash, a symbol, a number, spaced letters, a slash
    ("Education:", "education"),
    ("LEADERSHIP EXPERIENCE:", "leadership"),
    ("EXPERIENCE ______", "experience"),
    ("— Experience —", "experience"),
    ("| Experience |", "experience"),
    ("■ Experience", "experience"),
    ("# Projects", "projects"),
    ("01 Experience", "experience"),
    ("E X P E R I E N C E", "experience"),
    ("W O R K  E X P E R I E N C E", "experience"),
    ("Honors / Awards", "awards"),
    ("Skills/Tools", "skills"),
    # Experience
    ("Relevant Experience", "experience"),
    ("Career Related Experience", "experience"),
    ("Additional Experience", "experience"),
    ("Internship Experience", "experience"),
    ("Internships", "experience"),
    ("Employment History", "experience"),
    ("Work History", "experience"),
    ("Professional Background", "experience"),
    ("Experiences", "experience"),
    ("Teaching Experience", "experience"),
    ("Academic Experience", "experience"),
    ("Work & Research Experience", "experience"),
    # Leadership: clubs, activities and volunteering
    ("Volunteer Experience", "leadership"),
    ("Volunteering", "leadership"),
    ("Community Service", "leadership"),
    ("Community Involvement", "leadership"),
    ("Professional Affiliations", "leadership"),
    ("Memberships", "leadership"),
    ("Student Organizations", "leadership"),
    ("Athletics", "leadership"),
    ("Leadership and Community Involvement", "leadership"),
    # KAN-263: leadership words side by side, with no "&" or "and"
    ("Leadership Activities", "leadership"),
    ("LEADERSHIP ACTIVITIES", "leadership"),
    ("Leadership Roles", "leadership"),
    ("Leadership Positions", "leadership"),
    ("Leadership & Involvement", "leadership"),
    ("Campus Leadership", "leadership"),
    ("Student Leadership", "leadership"),
    # Education
    ("Education and Training", "education"),
    ("Educational Background", "education"),
    ("Academic Background", "education"),
    ("Relevant Coursework", "education"),
    # Skills
    ("Technical Proficiencies", "skills"),
    ("Core Competencies", "skills"),
    ("Programming Languages", "skills"),
    ("Languages & Technologies", "skills"),
    ("Tools", "skills"),
    ("Skills Summary", "skills"),
    # Projects, and papers as projects
    ("Technical Projects", "projects"),
    ("Related Course Projects", "projects"),
    ("Research Projects", "projects"),
    ("Portfolio", "projects"),
    ("Hackathons", "projects"),
    ("Papers", "publications"),
    ("Publications & Presentations", "publications"),
    ("Conference Presentations", "publications"),
    ("Patents", "publications"),
    # Awards and Certifications
    ("Achievements", "awards"),
    ("Scholarships", "awards"),
    ("Awards & Achievements", "awards"),
    ("Certificates", "certifications"),
    ("Licenses and Certifications", "certifications"),
    # the first part of a combined heading decides
    ("Experience & Leadership", "experience"),
    ("Education & Certifications", "education"),
    ("Projects & Research", "projects"),
    ("Honors and Activities", "awards"),
    ("Activities and Honors", "leadership"),
    # learned labels (app/utils/learned_headings.json), as reviewed
    ("Co-op Experience", "experience"),
    ("Greek Life", "leadership"),
    ("Tech Stack:", "skills"),
    ("CAPSTONE PROJECT", "projects"),
    ("Courses", "education"),
    ("Online Courses", "certifications"),
    ("Personal Statement", "personal statement"),
    # found but not saved, so their text joins no other section
    ("Professional Summary", "professional summary"),
    ("Summary of Qualifications", "summary of qualifications"),
    ("About Me", "about me"),
    ("Additional Information", "additional information"),
    ("Hobbies", "hobbies"),
    ("References", "references"),
]


@pytest.mark.parametrize(("line", "section"), HEADINGS)
def test_heading_names_its_section(line, section):
    assert section_of(line) == section


@pytest.mark.parametrize("line", [
    "• Skills",                              # a bullet, not a heading
    "Languages: Python, C++",                # a skills line
    "Software Engineer Intern",              # a role
    "Undergraduate Researcher",
    "Built the research pipeline.",
    "Acme Corp  Jan 2024 - Present",
])
def test_body_line_is_no_heading(line):
    assert section_of(line) is None


def test_a_learned_heading_names_its_section_after_the_rules(monkeypatch):
    monkeypatch.setattr(resume_parser, "LEARNED", {
        "tech stack": "skills", "personal statement": "other", "a typical day": "none",
        "education": "none",
    })
    assert section_of("TECH STACK:") == "skills"
    assert section_of("Personal Statement") == "personal statement"
    assert section_of("A Typical Day") is None
    # a rule always wins over a learned label
    assert section_of("Education") == "education"
    parsed = parse_resume("Tech Stack\n• Languages: Python, Go\n")
    assert [s.skill_name for s in parsed.skills] == ["Python", "Go"]


def test_every_learned_label_is_known_and_no_rule_names_its_heading():
    # a heading the rules learned to name since is a stale label: drop it
    for heading, label in resume_parser.LEARNED.items():
        assert label in resume_parser.LEARNED_LABELS, heading
        assert not resume_parser.SECTION_RE.fullmatch(heading), heading


def test_count_sections_reads_every_format():
    assert count_sections("EDUCATION:\nSchool\nE X P E R I E N C E\nJob\nSkills/Tools\nGo\n") == 3


def test_an_unsaved_section_stops_its_text_joining_the_one_above():
    parsed = parse_resume(
        "Experience\nAcme Corp  Jan 2024 - Present\nSoftware Engineer Intern\n• Built an API.\n"
        "Hobbies\nChess, hiking\n"
    )
    assert parsed.experience[0].description == "Built an API."


@pytest.mark.parametrize("heading", ["Relevant Coursework:", "COURSES"])
def test_a_coursework_heading_joins_the_school_above(heading):
    parsed = parse_resume(
        "Education\nHillcrest State University  May 2027\nB.S. in Computer Science\n"
        f"{heading}\nData Structures, Algorithms, Operating Systems\n"
    )
    assert [e.institution for e in parsed.education] == ["Hillcrest State University"]
    assert parsed.education[0].description == (
        f"{heading.rstrip(':')}: Data Structures, Algorithms, Operating Systems"
    )


def test_a_publication_keeps_its_year_and_link():
    parsed = parse_resume((FIXTURES / "research_and_publications.txt").read_text(encoding="utf-8"))
    assert [(_iso(p.end_date), p.url, p.description) for p in parsed.projects] == [
        ("2025-01-01", None, None),
        ("2024-01-01", "https://arxiv.org/abs/2409.01234", None),
    ]


def test_a_publication_dated_by_month_drops_the_date_from_its_name():
    parsed = parse_resume("Publications\nA Paper Title, Systems Conference  May 2025\n")
    assert [(p.project_name, _iso(p.end_date)) for p in parsed.projects] == [
        ("A Paper Title, Systems Conference", "2025-05-01"),
    ]


def test_a_lone_research_header_is_experience():
    parsed = parse_resume(
        "Education\nHillcrest State University  May 2027\n"
        "Research\nComputational Systems Lab  Jan 2025 - Present\nUndergraduate Researcher\n"
    )
    assert [e.institution for e in parsed.education] == ["Hillcrest State University"]
    assert [(e.company_name, e.title) for e in parsed.experience] == [
        ("Computational Systems Lab", "Undergraduate Researcher"),
    ]


def test_project_subtitle_after_bar_stays_in_the_name():
    parsed = parse_resume("Projects\nWorkIt | Recruiting Platform\n• Built it.\n")
    assert [(p.project_name, p.technologies) for p in parsed.projects] == [
        ("WorkIt | Recruiting Platform", []),
    ]


def test_leading_minus_sign_is_not_a_bullet_marker():
    # KAN-224: the four lines once parsed to one, "20% churn ..."
    parsed = parse_resume(
        "EXPERIENCE\n"
        "Software Engineering Intern\n"
        "Acme Corp, New York, NY\n"
        "June 2025 - August 2025\n"
        "Built a REST API in FastAPI that served 10,000 daily requests.\n"
        "Cut page load time by 40% by caching job search results in Redis.\n"
        "Wrote 120 unit tests and raised coverage from 55% to 85%.\n"
        "-20% churn after redesigning the onboarding flow.\n"
    )
    assert parsed.experience[0].description.splitlines() == [
        "Built a REST API in FastAPI that served 10,000 daily requests.",
        "Cut page load time by 40% by caching job search results in Redis.",
        "Wrote 120 unit tests and raised coverage from 55% to 85%.",
        "-20% churn after redesigning the onboarding flow.",
    ]


def test_hyphen_glued_to_a_word_is_still_a_bullet_marker():
    parsed = parse_resume(
        "EXPERIENCE\n"
        "Software Engineering Intern\n"
        "Acme Corp, New York, NY\n"
        "June 2025 - August 2025\n"
        "-Built a REST API in FastAPI\n"
        "-Wrote 120 unit tests\n"
    )
    assert parsed.experience[0].description.splitlines() == [
        "Built a REST API in FastAPI",
        "Wrote 120 unit tests",
    ]


def test_lines_before_the_first_marker_are_kept():
    parsed = parse_resume(
        "EXPERIENCE\n"
        "Software Engineering Intern\n"
        "Acme Corp, New York, NY\n"
        "June 2025 - August 2025\n"
        "Built a REST API in FastAPI.\n"
        "- Wrote 120 unit tests.\n"
    )
    assert parsed.experience[0].description.splitlines() == [
        "Built a REST API in FastAPI.",
        "Wrote 120 unit tests.",
    ]


def test_a_range_in_one_year_names_the_year_once():
    parsed = parse_resume("EXPERIENCE\nAcme Corp\nSoftware Engineering Intern  Jun-Aug 2026\n- Built a tool\n")
    job = parsed.experience[0]
    assert (_iso(job.start_date), _iso(job.end_date)) == ("2026-06-01", "2026-08-01")


def test_a_word_starting_with_a_month_is_no_range():
    # "Marketing" starts with "Mar": only whole month names make a range
    parsed = parse_resume("EXPERIENCE\nAcme Corp\nProduct Marketing - May 2026\n- Ran a launch\n")
    assert _iso(parsed.experience[0].start_date) is None


def test_a_dash_with_a_role_on_both_sides_stays_one_title():
    parsed = parse_resume("EXPERIENCE\nSoftware Engineer - Backend Lead  Jan 2024 - Present\n- Built a tool\n")
    assert parsed.experience[0].title == "Software Engineer - Backend Lead"


def test_a_school_name_with_a_dash_keeps_both_parts():
    parsed = parse_resume(
        "EDUCATION\nUniversity of Wisconsin - Madison - B.S. in Computer Science - May 2027\n"
    )
    school = parsed.education[0]
    assert (school.institution, _iso(school.end_date)) == ("University of Wisconsin - Madison", "2027-05-01")


def test_a_projects_tools_on_their_own_line_are_its_technologies():
    parsed = parse_resume(
        "PROJECTS\nThe Papyr | AI News App  March 2026 - Present\n"
        "Next.js, TypeScript, Supabase (PostgreSQL), Gemini API\n"
        "• Designed a daily briefing that ends on a finish line\n"
        "Robot Arm  Jan 2025 - May 2025\nTech Stack: C++, ROS, OpenCV\n"
        "• Built a pick-and-place arm\n"
    )
    assert [(p.technologies, _bullet_count(p.description)) for p in parsed.projects] == [
        (["Next.js", "TypeScript", "Supabase (PostgreSQL)", "Gemini API"], 1),
        (["C++", "ROS", "OpenCV"], 1),
    ]


def test_a_bullet_with_commas_is_not_a_tools_line():
    from app.utils.resume_parser import is_tools_line

    assert not is_tools_line("Ran interviews, turning user pain points into prioritized roadmaps, plans and specs")
    assert not is_tools_line("Python, SQL")  # two items: too few to tell
    assert is_tools_line("Figma, Next.js, TypeScript, Tailwind CSS")


def test_a_minor_follows_the_major():
    parsed = parse_resume("EDUCATION\nHillcrest State University  May 2027\nB.S. in Biology, Minor: Chemistry\n")
    assert parsed.education[0].field_of_study == "Biology, minor in Chemistry"


# --- Text the parser read wrong in real uploads (2026-11-12 audit) ----------
# Each layout below is a real resume's, retyped with made-up names.

@pytest.mark.parametrize("degree", ["B.S.", "M.S.", "B.A.", "Ph.D.", "B.Sc.", "M.Eng.", "MBA"])
def test_an_abbreviated_degree_keeps_its_last_period(degree):
    # "B.S." was saved as "B.S": a word boundary cannot follow "."
    parsed = parse_resume(f"EDUCATION\nHillcrest State University  May 2027\n{degree} in Biology\n")
    assert (parsed.education[0].degree, parsed.education[0].field_of_study) == (degree, "Biology")


@pytest.mark.parametrize(("line", "degree", "field"), [
    ("B.S. Computer Science, Honors", "B.S.", "Computer Science"),
    ("Bachelor's in Computer Science", "Bachelor's", "Computer Science"),
    ("Bachelor's degree in Economics", "Bachelor's", "Economics"),
    ("Bachelor of Business Administration in Finance", "Bachelor of Business Administration", "Finance"),
    ("Bachelor of Computer Science", "Bachelor of Computer Science", None),
    ("Associate of Arts in Liberal Studies", "Associate of Arts", "Liberal Studies"),
    ("B.S. in Computer Science, Specialization in Artificial Intelligence",
     "B.S.", "Computer Science, specialization in Artificial Intelligence"),
])
def test_the_major_is_kept_in_every_degree_form(line, degree, field):
    parsed = parse_resume(f"EDUCATION\nHillcrest State University  Expected May 2027\n{line}\n")
    assert (parsed.education[0].degree, parsed.education[0].field_of_study) == (degree, field)


def test_a_state_code_is_no_degree():
    # "Boston, MA" read as a master's degree
    parsed = parse_resume("EDUCATION\nNortheast Tech University  Boston, MA\n"
                          "Bachelor of Science in Computer Science  May 2027\n")
    school = parsed.education[0]
    assert (school.institution, school.location, school.degree) == (
        "Northeast Tech University", "Boston, MA", "Bachelor of Science")


@pytest.mark.parametrize("line", ["Hillcrest State University  Hillcrest, NY", "Hillcrest State University | Hillcrest, NY"])
def test_a_schools_place_comes_off_its_name(line):
    parsed = parse_resume(f"EDUCATION\n{line}\nB.S. in Biology  Expected May 2027\n")
    assert (parsed.education[0].institution, parsed.education[0].location) == ("Hillcrest State University", "Hillcrest, NY")


def test_a_second_degree_at_one_school_is_that_school():
    # The B.S. line became a school named "B.S. in Computer Science Honors"
    parsed = parse_resume(
        "EDUCATION\nHillcrest State University  Hillcrest, NY\n"
        "M.S. in Computer Science (Accelerated BS/MS)  Expected May 2028\n"
        "B.S. in Computer Science  Expected May 2027\nGPA: 3.90/4.00\n"
    )
    assert [(e.institution, e.location, e.degree, e.gpa) for e in parsed.education] == [
        ("Hillcrest State University", "Hillcrest, NY", "M.S.", None),
        ("Hillcrest State University", "Hillcrest, NY", "B.S.", 3.9),
    ]


def test_a_school_named_on_its_date_line_keeps_its_name_and_gives_back_the_lines_above():
    # "Intelligence Honors: Dean's List" became the second school's name, the
    # first school's course list stopped at "Artificial", and the second
    # school's own name was lost
    parsed = parse_resume(
        "EDUCATION\nHillcrest State University  Expected Graduation: May 2027\n"
        "Bachelor of Science in Computer Science  GPA: 3.40 / 4.00\n"
        "Relevant Coursework: Machine Learning, Systems Programming, Software Development, Artificial\n"
        "Intelligence Honors: Dean’s List (All Semesters)\n"
        "Lakeside Global Campus  February 2026 – June 2026\n"
        "Bachelor of Science in Computer Science\nRelevant Coursework: Computer Vision\n"
    )
    first, second = parsed.education
    assert second.institution == "Lakeside Global Campus"
    assert first.description.splitlines() == [
        "Relevant Coursework: Machine Learning, Systems Programming, Software Development, Artificial Intelligence",
        "Honors: Dean's List (All Semesters)",
    ]


@pytest.mark.parametrize(("line", "start", "end"), [
    # how WorkIt's own PDF writes a month: "Acme Corp Aug." was the company
    ("Acme Corp  Aug. 2024 – May 2025", "2024-08-01", "2025-05-01"),
    ("Acme Corp  May 2024 to Aug 2024", "2024-05-01", "2024-08-01"),
    ("Acme Corp  06/2024 - 08/2024", "2024-06-01", "2024-08-01"),
    ("Acme Corp  Summer 2024 – Fall 2024", "2024-06-01", "2024-12-01"),
])
def test_a_job_reads_every_common_date_form(line, start, end):
    parsed = parse_resume(f"EXPERIENCE\n{line}\nData Analyst Intern\n• Cleaned survey data\n")
    job = parsed.experience[0]
    assert (job.company_name, _iso(job.start_date), _iso(job.end_date)) == ("Acme Corp", start, end)


def test_a_season_is_read_only_where_a_date_goes():
    parsed = parse_resume(
        "LEADERSHIP\nChess Club – Treasurer  Spring 2024 – Present\n"
        "• Ran the club's budget; in Fall 2026, picked 13 of 101 applicants\n"
    )
    club = parsed.leadership[0]
    assert "Spring" not in club.title and "Spring" not in club.company_name
    assert _iso(club.start_date) == "2024-01-01"
    assert "in Fall 2026, picked 13 of 101 applicants" in club.description


@pytest.mark.parametrize(("place", "kept"), [
    ("Hillcrest, New York", "Hillcrest, New York"),
    ("Toronto, ON", "Toronto, ON"),
    ("Incheon, South Korea", "Incheon, South Korea"),
])
def test_a_written_out_place_after_a_gap_is_the_location(place, kept):
    parsed = parse_resume(f"EXPERIENCE\nSignal Lab  {place}\nResearch Intern  Jan 2025 – May 2025\n• Built a model\n")
    job = parsed.experience[0]
    assert (job.company_name, job.location) == ("Signal Lab", kept)


def test_a_ring_after_a_number_is_a_degree_sign_and_a_math_tilde_keeps_its_space():
    # "2.75° to 1.01°" printed "2.75 • to 1.01 •"
    assert resume_parser.fix_symbols("error 2.75◦ to 1.01◦; latency to∼40 ms") == "error 2.75° to 1.01°; latency to ~40 ms"


@pytest.mark.parametrize("marker", ["➢", "►", "", "*"])
def test_more_bullet_glyphs_are_bullets(marker):
    parsed = parse_resume(f"EXPERIENCE\nAcme Corp  Jan 2025 – May 2025\nAnalyst\n{marker} Built a dashboard\n{marker} Cut costs 10%\n")
    assert parsed.experience[0].description.splitlines() == ["Built a dashboard", "Cut costs 10%"]


@pytest.mark.parametrize(("line", "names"), [
    ("Languages: Python | Java | C++", ["Python", "Java", "C++"]),
    ("Python; Java; C++", ["Python", "Java", "C++"]),
    ("Frameworks: React (Next.js, Redux), Django", ["React", "Next.js", "Redux", "Django"]),
    ("Languages – Python, Java", ["Python", "Java"]),
    ("Certificates: Lean Six Sigma (Green Belt), CompTIA A+", ["Lean Six Sigma (Green Belt)", "CompTIA A+"]),
])
def test_a_skills_line_splits_at_every_common_separator(line, names):
    parsed = parse_resume(f"SKILLS\n{line}\n")
    assert [s.skill_name for s in parsed.skills] == names


def test_a_school_keeps_its_start_date():
    # "Aug 2023 - May 2027" printed "May 2027" alone
    parsed = parse_resume("EDUCATION\nHillcrest State University  Aug 2023 – May 2027\nB.S. in Biology\n")
    school = parsed.education[0]
    assert (_iso(school.start_date), _iso(school.end_date)) == ("2023-08-01", "2027-05-01")


@pytest.mark.parametrize("role", ["Treasurer", "Team Captain", "Founder", "Volunteer"])
def test_a_club_and_its_role_on_one_dashed_line_split(role):
    parsed = parse_resume(f"LEADERSHIP\nChess Club – {role}  Jan 2024 – Present\n• Ran the budget\n")
    club = parsed.leadership[0]
    assert (club.company_name, club.title) == ("Chess Club", role)
