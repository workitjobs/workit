"""
Make the made-up resume scoring set (KAN-900): `data/reading_set/`, one
resume file and its answer key per person. By hand, never in CI; its output
is committed, so scoring needs none of its tools.

    uv run python -m app.scripts.make_reading_set
    uv run python -m app.scripts.make_reading_set --chrome /path/to/chrome

Every person is made up: names, schools, companies, phones (555), emails
(example.com) and links. Each person is drawn from the pools below with a
fixed seed, so a run makes the same set, and printed in one of eleven layouts
through the tools students' resumes come from: LaTeX (Tectonic, as Jake's
Resume and Overleaf templates are), a browser's Save as PDF (Chrome, as
Google Docs, Canva and resume sites print), and Word (python-docx). A layout
prints exactly what the answer key holds, in its own date form, heading
names and line shapes, so the key is right by construction; the layouts
differ where real resumes differ, which is where readings fail.

The answer key is the person's entries as WorkIt's bank holds them
(`app.scripts.reading_score` has the format). A new layout or pool item
changes every file the seed draws after it: make the set again, commit the
files with the change, and score `main` again before comparing.
"""

import argparse
import html
import json
import random
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.shared import Inches, Pt

OUT = Path(__file__).resolve().parents[2] / "data" / "reading_set"
TODAY = (2026, 11)

# --- Pools ------------------------------------------------------------------

PEOPLE = [
    ("Priya Raman", "priyaraman"), ("Marcus Bell", "mbell"), ("Sofia Alvarez", "salvarez"),
    ("Daniel Okafor", "dokafor"), ("Hannah Kim", "hannahkim"), ("Ethan Novak", "enovak"),
    ("Aisha Rahman", "aisharahman"), ("Lucas Ferreira", "lferreira"), ("Grace Liu", "graceliu"),
    ("Owen Patel", "owenpatel"), ("Zoe Martin", "zmartin"), ("Kevin Tran", "kevintran"),
    ("Nadia Haddad", "nhaddad"), ("Ben Carter", "bencarter"), ("Elena Petrova", "epetrova"),
    ("Jamal Wright", "jwright"), ("Mei Tanaka", "meitanaka"), ("Ryan Walsh", "rwalsh"),
    ("Leila Ahmadi", "lahmadi"), ("Victor Huang", "vhuang"),
]

SCHOOLS = [
    ("Riverside State University", "Riverside, CA"),
    ("Lakeshore Institute of Technology", "Chicago, IL"),
    ("Northfield College", "Northfield, MN"),
    ("University of Cedar Falls", "Cedar Falls, IA"),
    ("Harbor City University", "Baltimore, MD"),
    ("Westbrook University", "Austin, TX"),
    ("Pinecrest State University", "Flagstaff, AZ"),
    ("Eastgate College", "Albany, NY"),
]

DEGREES = [
    ("B.S.", "Bachelor of Science", "Computer Science"),
    ("B.S.", "Bachelor of Science", "Computer Engineering"),
    ("B.A.", "Bachelor of Arts", "Economics"),
    ("B.S.", "Bachelor of Science", "Data Science"),
    ("B.A.", "Bachelor of Arts", "Cognitive Science"),
    ("B.S.", "Bachelor of Science", "Mechanical Engineering"),
    ("B.S.", "Bachelor of Science", "Information Systems"),
    ("B.A.", "Bachelor of Arts", "Mathematics"),
]

COURSES = [
    "Data Structures", "Algorithms", "Operating Systems", "Computer Networks", "Databases",
    "Machine Learning", "Linear Algebra", "Probability and Statistics", "Software Engineering",
    "Computer Architecture", "Econometrics", "Human-Computer Interaction", "Thermodynamics",
    "Discrete Mathematics", "Corporate Finance",
]

# (title, organization, location or None, bullets, skills it suggests)
JOBS = [
    ("Software Engineering Intern", "Acme Robotics", "Boston, MA", [
        "Built a Python service that schedules charging for 40 warehouse robots, cutting idle time by 18%",
        "Wrote integration tests in pytest for the fleet API, raising coverage from 52% to 81%",
        "Moved three nightly batch jobs to Docker containers on AWS ECS",
    ], ["Python", "Docker", "AWS"]),
    ("Data Analyst Intern", "Lakeside Labs", "Chicago, IL", [
        "Cleaned and joined 2.3 million loan records in SQL to find causes of late payments",
        "Built a Tableau dashboard that the credit team now reviews every Monday",
        "Presented churn findings to the VP of Product, leading to a new reminder email",
    ], ["SQL", "Tableau", "Excel"]),
    ("Frontend Developer Intern", "Brightline Health", "New York, NY", [
        "Rebuilt the patient intake form in React and TypeScript, reducing drop-off by 12%",
        "Added accessibility checks to CI and fixed 60 WCAG issues across 14 pages",
        "Worked with two designers in Figma to ship a new appointment calendar",
    ], ["React", "TypeScript", "Figma"]),
    ("Research Assistant", "Riverside Vision Lab", None, [
        "Trained PyTorch models to segment crop rows in drone images with 0.87 mean IoU",
        "Labeled 4,000 images and wrote a script that checks labels for overlaps",
        "Co-wrote a workshop paper on low-cost field imaging",
    ], ["PyTorch", "Python", "Linux"]),
    ("Teaching Assistant", "Department of Computer Science", None, [
        "Led two weekly lab sections of 30 students for Introduction to Programming in Java",
        "Held office hours and graded assignments with a rubric shared by six TAs",
    ], ["Java"]),
    ("Backend Engineer Intern", "Quillstack", "San Francisco, CA", [
        "Designed a GraphQL endpoint for invoice search that serves 3,000 requests a minute",
        "Cut p95 latency from 900 ms to 240 ms by adding Redis caching to account lookups",
        "Reviewed pull requests and wrote the runbook for the billing on-call rotation",
    ], ["GraphQL", "Redis", "Node.js"]),
    ("IT Support Technician", "Campus Technology Services", "Riverside, CA", [
        "Resolved about 25 hardware and network tickets a week for students and staff",
        "Imaged and deployed 150 laptops for the fall semester",
        "Wrote a how-to guide for the campus VPN that cut related tickets by a third",
    ], ["Linux", "Bash"]),
    ("Machine Learning Intern", "Northwind Analytics", "Seattle, WA", [
        "Built a demand forecasting model in scikit-learn that beat the old baseline by 9% MAPE",
        "Set up Airflow jobs to retrain the model weekly on fresh sales data",
        "Wrote a feature store notebook used by four other analysts",
    ], ["scikit-learn", "Airflow", "pandas"]),
    ("Product Design Intern", "Fernway", "Remote", [
        "Ran 12 user interviews and turned findings into three journey maps",
        "Designed and tested a new onboarding flow in Figma that raised activation by 7%",
        "Kept the component library in sync with engineering each sprint",
    ], ["Figma"]),
    ("Financial Analyst Intern", "Granite Peak Capital", "Denver, CO", [
        "Built a three-statement model in Excel for a $40M acquisition target",
        "Prepared weekly market summaries for the investment committee",
        "Checked comparable company data in a database of 300 firms",
    ], ["Excel"]),
    ("Mechanical Engineering Co-op", "Torrent Pumps", "Milwaukee, WI", [
        "Redesigned a pump housing in SolidWorks, cutting its weight by 14%",
        "Ran tolerance stack-ups and wrote test plans for two new impellers",
        "Worked with the machine shop to reduce scrap on one part from 6% to 2%",
    ], ["SolidWorks", "MATLAB"]),
    ("Sales Associate", "Target", "Austin, TX", [
        "Helped about 80 customers a shift and kept the electronics section stocked",
        "Trained four new associates on the register and returns process",
    ], []),
    ("Full Stack Developer Intern", "Orchard Learning", "Atlanta, GA", [
        "Built a Django and PostgreSQL feature that lets teachers share lesson plans",
        "Wrote Jest tests for the React gradebook and fixed 23 bugs before launch",
        "Automated deploys to Heroku with GitHub Actions",
    ], ["Django", "PostgreSQL", "React", "Jest"]),
    ("Undergraduate Researcher", "Systems and Networks Lab", "Albany, NY", [
        "Measured tail latency of three key-value stores under mixed workloads",
        "Wrote a Go load generator that replays production traces at 50,000 operations per second",
    ], ["Go", "Linux"]),
    ("Data Engineering Intern", "Bluefin Logistics", "Miami, FL", [
        "Built Spark jobs that load 40 GB of shipment events into Snowflake each night",
        "Wrote data quality checks that caught a broken vendor feed within an hour",
    ], ["Spark", "Snowflake", "Python"]),
    ("iOS Developer Intern", "Pocketwise", "Los Angeles, CA", [
        "Shipped a budgeting widget in Swift and SwiftUI used by 20,000 people in its first month",
        "Fixed memory leaks that caused crashes on older iPhones",
    ], ["Swift"]),
    ("Peer Tutor", "Academic Success Center", None, [
        "Tutored 15 students a week in calculus, statistics and introductory economics",
        "Created practice sets that the center now gives every new tutor",
    ], []),
    ("Cloud Infrastructure Intern", "Stratus Bank", "Charlotte, NC", [
        "Wrote Terraform modules for 30 internal services on Azure",
        "Cut monthly cloud spend by $11,000 by right-sizing idle virtual machines",
    ], ["Terraform", "Azure"]),
]

# (name, tools, bullets, link)
PROJECTS = [
    ("Budget Buddy", ["React", "Firebase"], [
        "Built a shared budgeting app for roommates with real-time expense splitting",
        "Reached 300 users across three campuses in its first semester",
    ], "github.com/{handle}/budget-buddy"),
    ("Trailcast", ["Python", "Flask", "PostgreSQL"], [
        "Made a web app that combines trail reports and weather into one daily hiking score",
        "Scraped 1,200 trail pages and stored them in a normalized schema",
    ], None),
    ("Line Following Robot", ["C++", "Arduino"], [
        "Programmed a PID controller that finished a 10 meter track in 14 seconds",
        "Placed second of 22 teams at the spring robotics showcase",
    ], None),
    ("Course Planner", ["TypeScript", "Next.js", "PostgreSQL"], [
        "Built a planner that checks prerequisites and suggests a four-year course plan",
        "Used by 450 students during registration week",
    ], "courseplanner.example.com"),
    ("Sentiment Tracker", ["Python", "pandas", "scikit-learn"], [
        "Classified 50,000 product reviews by sentiment with 91% accuracy",
        "Charted weekly sentiment for five brands in a small Flask dashboard",
    ], None),
    ("Pixel Chess", ["Java"], [
        "Wrote a chess engine with alpha-beta search that plays at about 1500 Elo",
    ], "github.com/{handle}/pixel-chess"),
    ("Campus Transit Map", ["JavaScript", "Node.js", "MongoDB"], [
        "Mapped live shuttle positions from the transit API for 6,000 daily riders",
        "Added arrival alerts that cut average wait time reported in a survey by 4 minutes",
    ], None),
    ("Wind Turbine Blade Study", ["MATLAB", "SolidWorks"], [
        "Modeled three blade shapes and tested scale versions in the school wind tunnel",
        "Found a shape that raised power output by 6% at low wind speeds",
    ], None),
    ("Portfolio Optimizer", ["Python", "NumPy"], [
        "Built a mean-variance optimizer that rebalances a 20-stock portfolio monthly",
        "Back-tested the strategy over ten years of daily prices",
    ], None),
    ("Study Room Finder", ["Kotlin", "Firebase"], [
        "Made an Android app that shows open library study rooms in real time",
    ], None),
    ("Habit Garden", ["Swift"], [
        "Designed and built an iOS habit tracker that grows a garden as streaks continue",
        "Wrote 40 unit tests and published it to TestFlight for 60 testers",
    ], None),
    ("Election Data Explorer", ["R", "SQL"], [
        "Joined 30 years of county election results with census data in SQL",
        "Built interactive maps in R Shiny for a political science class",
    ], None),
]

# (title, organization, location or None, bullets)
LEADERSHIP = [
    ("President", "Women in Computing", None, [
        "Grew membership from 40 to 110 and organized a hackathon for 200 students",
        "Ran weekly interview prep sessions with alumni from four companies",
    ]),
    ("Treasurer", "Robotics Club", None, [
        "Managed a $12,000 annual budget and wrote two successful grant requests",
    ]),
    ("Resident Assistant", "Office of Residential Life", None, [
        "Supported 45 first-year students on a residence hall floor",
        "Planned monthly events on study skills and wellness",
    ]),
    ("Volunteer Coordinator", "Harbor Food Pantry", "Baltimore, MD", [
        "Scheduled 60 volunteers a month and set up a sign-up sheet that cut no-shows in half",
    ]),
    ("Captain", "Club Soccer", None, [
        "Led practices for 25 players and organized travel to six away games",
    ]),
    ("Mentor", "First-Gen Scholars Program", None, [
        "Met weekly with three first-year students to plan courses and internships",
    ]),
]

AWARDS = [
    ("Dean's List", "{school}"),
    ("Merit Scholarship", "{school}"),
    ("First Place, Spring Hackathon", "Hack Riverside"),
    ("Undergraduate Research Award", "College of Engineering"),
    ("National Merit Finalist", None),
    ("Best Design Award", "Product Design Society"),
]

CERTS = [
    ("AWS Certified Cloud Practitioner", "Amazon Web Services"),
    ("Google Data Analytics Certificate", "Google"),
    ("Certified Associate in Python Programming", "Python Institute"),
    ("Tableau Desktop Specialist", "Tableau"),
]

SKILL_GROUPS = {
    "Languages": ["Python", "Java", "C++", "JavaScript", "TypeScript", "SQL", "Go", "Swift", "Kotlin", "R", "MATLAB"],
    "Frameworks": ["React", "Node.js", "Django", "Flask", "Next.js", "Spring Boot", "PyTorch", "TensorFlow"],
    "Tools": ["Git", "Docker", "AWS", "Linux", "Figma", "Tableau", "PostgreSQL", "Kubernetes", "Excel", "Jira"],
}

INTERESTS = ["Rock climbing, film photography and chess", "Distance running, jazz piano and cooking",
             "Board games, hiking and volunteering at the animal shelter"]
SUMMARIES = [
    "Computer science student who likes building tools people use every day, looking for a summer 2027 software internship.",
    "Data-minded student with internship experience in analytics and a strong base in statistics.",
]

HEADINGS = {
    "education": ["Education"],
    "experience": ["Experience", "Work Experience", "Professional Experience", "Relevant Experience"],
    "projects": ["Projects", "Personal Projects", "Technical Projects"],
    "leadership": ["Leadership", "Leadership & Activities", "Activities", "Campus Involvement"],
    "awards": ["Awards", "Honors & Awards", "Honors"],
    "certifications": ["Certifications", "Licenses & Certifications"],
    "skills": ["Skills", "Technical Skills"],
    "summary": ["Summary"],
    "interests": ["Interests"],
}

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
DOT = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]


# --- People -----------------------------------------------------------------


@dataclass
class Person:
    name: str
    handle: str
    layout: str
    style: dict
    entries: list[dict] = field(default_factory=list)
    skills: dict[str, list[str]] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    headings: dict[str, str] = field(default_factory=dict)

    @property
    def email(self) -> str:
        return f"{self.handle}@example.com"

    @property
    def phone(self) -> str:
        return f"(555) 01{len(self.handle):02d}-{sum(map(ord, self.handle)) % 10000:04d}"

    @property
    def link(self) -> str:
        return f"github.com/{self.handle}"

    def section(self, name: str) -> list[dict]:
        return [e for e in self.entries if e["section"] == name]


def ym(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


def future(value: str) -> bool:
    year, month = map(int, value.split("-"))
    return (year, month) > TODAY


def make_person(i: int, layout: str) -> Person:
    rng = random.Random(9000 + i)
    name, handle = PEOPLE[i]
    style = {
        "dates": rng.choice(["short", "long", "dot", "numeric"]),
        "dash": rng.choice([" – ", " - ", " to "]),
        "present": rng.choice(["Present", "Current"]),
        "skills": rng.choice(["groups", "flat", "pipes"]),
        "degree": rng.choice(["short", "long"]),
    }
    p = Person(name, handle, layout, style)

    school, school_place = rng.choice(SCHOOLS)
    short, long_, major = rng.choice(DEGREES)
    grad = rng.choice([2026, 2027, 2027, 2028])
    end = ym(grad, 5)
    edu = {"section": "education", "title": school, "location": school_place,
           "degree": short if style["degree"] == "short" else long_, "field_of_study": major,
           "start": ym(grad - 4, rng.choice([8, 9])), "end": end}
    if future(end):
        edu["expected"] = True
    if rng.random() < 0.7:
        edu["gpa"] = rng.choice([3.42, 3.58, 3.67, 3.71, 3.8, 3.86, 3.92, 3.95])
    if rng.random() < 0.6:
        edu["coursework"] = rng.sample(COURSES, rng.randint(3, 6))
    if rng.random() < 0.35:
        del edu["start"]
    p.entries.append(edu)

    # Jobs: newest first, each span before the last one began.
    jobs = rng.sample(JOBS, rng.randint(2, 3))
    year = min(grad, 2026)
    first = True
    tools: list[str] = []
    for title, org, place, bullets, suggested in jobs:
        if first and rng.random() < 0.4:
            span = {"start": ym(2025, rng.choice([8, 9])), "end": "present"}
            year = 2025
        else:
            year -= 0 if first else 1
            span = {"start": ym(year, rng.choice([5, 6])), "end": ym(year, 8)}
        first = False
        entry = {"section": "experience", "title": title, "organization": org, **span,
                 "bullets": bullets[: rng.randint(2, len(bullets))]}
        if place:
            entry["location"] = place
        p.entries.append(entry)
        tools += suggested

    for pname, ptools, pbullets, link in rng.sample(PROJECTS, rng.randint(1, 3)):
        entry = {"section": "projects", "title": pname, "tools": ptools, "bullets": pbullets}
        when = rng.random()
        if when < 0.4:
            entry |= {"start": ym(2025, 1), "end": ym(2025, 4)}
        elif when < 0.6:
            entry["end"] = str(rng.choice([2023, 2024]))
        if link and rng.random() < 0.7:
            entry["link"] = link.format(handle=handle)
        p.entries.append(entry)
        tools += ptools

    for title, org, place, bullets in rng.sample(LEADERSHIP, rng.choice([0, 1, 1, 2])):
        entry = {"section": "leadership", "title": title, "organization": org,
                 "start": ym(2024, 9), "end": "present", "bullets": bullets}
        if place:
            entry["location"] = place
        p.entries.append(entry)

    for title, giver in rng.sample(AWARDS, rng.choice([0, 1, 2])):
        entry = {"section": "awards", "title": title}
        if giver:
            entry["organization"] = giver.format(school=school)
        entry["date"] = rng.choice(["2024", "2025", ym(2025, 5), ym(2024, 12)])
        p.entries.append(entry)

    for title, issuer in rng.sample(CERTS, rng.choice([0, 0, 1])):
        p.entries.append({"section": "certifications", "title": title, "issuer": issuer})

    if rng.random() < 0.25:
        p.entries.insert(0, {"section": "custom", "title": "Summary", "bullets": [rng.choice(SUMMARIES)]})
    if rng.random() < 0.3:
        p.entries.append({"section": "custom", "title": "Interests", "bullets": [rng.choice(INTERESTS)]})

    pool = list(dict.fromkeys(tools))
    for group, names in SKILL_GROUPS.items():
        extra = [n for n in rng.sample(names, rng.randint(1, 3)) if n not in pool]
        chosen = [n for n in pool if n in names] + extra
        if chosen:
            p.skills[group] = chosen
    leftovers = [n for n in pool if not any(n in v for v in SKILL_GROUPS.values())]
    if leftovers:
        p.skills.setdefault("Tools", []).extend(leftovers)

    # Education first, skills last; some resumes lead with skills, and some
    # put education after the jobs.
    p.order = ["education", "experience", "projects", "leadership", "awards", "certifications", "skills"]
    if rng.random() < 0.3:
        p.order.remove("skills")
        p.order.insert(1, "skills")
    if rng.random() < 0.25:
        p.order.remove("education")
        p.order.insert(p.order.index("experience") + 1, "education")
    p.headings = {k: rng.choice(v) for k, v in HEADINGS.items()}
    return p


def key_of(p: Person, file: str) -> dict:
    skills = [n for names in p.skills.values() for n in names]
    return {
        "file": file,
        "layout": p.layout,
        "person": {"name": p.name, "email": p.email, "phone": p.phone, "links": [p.link]},
        "entries": p.entries,
        "skills": list(dict.fromkeys(skills)),
    }


# --- Printing ---------------------------------------------------------------


def fmt_date(p: Person, value: str | None) -> str:
    if value is None:
        return ""
    if value == "present":
        return p.style["present"]
    if "-" not in value:
        return value
    year, month = map(int, value.split("-"))
    form = p.style["dates"]
    if form == "short":
        return f"{MONTHS[month - 1][:3]} {year}"
    if form == "long":
        return f"{MONTHS[month - 1]} {year}"
    if form == "dot":
        return f"{DOT[month - 1]} {year}"
    return f"{month:02d}/{year}"


def span(p: Person, e: dict) -> str:
    end = fmt_date(p, e.get("end"))
    if e.get("expected"):
        end = f"Expected {end}"
    start = fmt_date(p, e.get("start"))
    return f"{start}{p.style['dash']}{end}" if start and end else start or end


def degree_line(p: Person, e: dict) -> str:
    sep = ", " if p.style["degree"] == "short" and len(e["field_of_study"]) % 2 else " in "
    line = f"{e['degree']}{sep}{e['field_of_study']}"
    if "gpa" in e:
        line += f"; GPA: {e['gpa']:.2f}/4.00" if p.style["dates"] != "numeric" else f", GPA {e['gpa']:.2f}"
    return line


def skills_lines(p: Person) -> list[tuple[str | None, str]]:
    form = p.style["skills"]
    if form == "groups":
        return [(group, ", ".join(names)) for group, names in p.skills.items()]
    every = [n for names in p.skills.values() for n in names]
    return [(None, (" | " if form == "pipes" else ", ").join(every))]


def award_line(p: Person, e: dict) -> tuple[str, str]:
    left = e["title"] + (f" – {e['organization']}" if e.get("organization") else "")
    return left, fmt_date(p, e.get("date"))


def project_head(e: dict) -> str:
    return e["title"] + " | " + ", ".join(e["tools"])


# LaTeX ----------------------------------------------------------------------

_TEX = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", "\\": r"\textbackslash{}"}


def tex(s: str) -> str:
    return "".join(_TEX.get(c, c) for c in s)


TEX_HEAD = r"""\documentclass[letterpaper,11pt]{article}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage[usenames,dvipsnames]{color}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{tabularx}
\usepackage[T1]{fontenc}
\addtolength{\oddsidemargin}{-0.5in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1in}
\addtolength{\topmargin}{-.5in}
\addtolength{\textheight}{1.0in}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}
\pagestyle{empty}
\titleformat{\section}{\vspace{-4pt}\scshape\raggedright\large}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]
\begin{document}
"""


def tex_header(p: Person, center: bool = True) -> str:
    contact = f"{tex(p.phone)} $|$ \\href{{mailto:{p.email}}}{{{tex(p.email)}}} $|$ \\href{{https://{p.link}}}{{{tex(p.link)}}}"
    if center:
        return f"\\begin{{center}}{{\\Huge \\scshape {tex(p.name)}}} \\\\ \\vspace{{1pt}}\\small {contact}\\end{{center}}\n"
    return f"{{\\LARGE \\textbf{{{tex(p.name)}}}}}\\\\\n\\small {contact}\\\\[6pt]\n"


def tex_bullets(items: list[str]) -> str:
    if not items:
        return ""
    body = "".join(f"  \\item {tex(b)}\n" for b in items)
    return f"\\begin{{itemize}}[leftmargin=0.15in,itemsep=-2pt,topsep=2pt]\\small\n{body}\\end{{itemize}}\n"


def tex_row(left: str, right: str, bold: bool = False, italic: bool = False) -> str:
    l = f"\\textbf{{{left}}}" if bold else f"\\textit{{\\small {left}}}" if italic else left
    r = f"\\textit{{\\small {right}}}" if italic else right
    return f"\\begin{{tabular*}}{{\\linewidth}}{{l@{{\\extracolsep{{\\fill}}}}r}}{l} & {r} \\\\\\end{{tabular*}}\\\\\n"


def tex_section(p: Person, name: str, style: str) -> str:
    out = []
    if name == "skills":
        lines = skills_lines(p)
        out.append("\\small " + " \\\\\n".join(
            (f"\\textbf{{{tex(g)}}}: " if g else "") + tex(v) for g, v in lines) + "\\\\\n")
    for e in p.section(name) if name != "skills" else []:
        if name == "education":
            if style == "compact":
                out.append(tex_row(f"\\textbf{{{tex(e['title'])}}}, {tex(e.get('location', ''))}", tex(span(p, e))))
                out.append(tex(degree_line(p, e)) + "\\\\\n")
            else:
                out.append(tex_row(tex(e["title"]), tex(e.get("location", "")), bold=True))
                out.append(tex_row(tex(degree_line(p, e)), tex(span(p, e)), italic=True))
            if e.get("coursework"):
                out.append("\\small Relevant Coursework: " + tex(", ".join(e["coursework"])) + "\\\\\n")
        elif name in ("experience", "leadership"):
            if style == "compact":
                where = f" -- {tex(e['location'])}" if e.get("location") else ""
                out.append(tex_row(f"\\textbf{{{tex(e['title'])}}}, {tex(e['organization'])}{where}", tex(span(p, e))))
            else:
                out.append(tex_row(tex(e["title"]), tex(span(p, e)), bold=True))
                out.append(tex_row(tex(e["organization"]), tex(e.get("location", "")), italic=True))
            out.append(tex_bullets(e["bullets"]))
        elif name == "projects":
            head = f"\\textbf{{{tex(e['title'])}}} $|$ \\emph{{{tex(', '.join(e['tools']))}}}"
            out.append(tex_row(head, tex(span(p, e))))
            if e.get("link"):
                out.append(f"\\small \\href{{https://{e['link']}}}{{{tex(e['link'])}}}\\\\\n")
            out.append(tex_bullets(e["bullets"]))
        elif name in ("awards", "certifications"):
            left, right = award_line(p, e) if name == "awards" else (f"{e['title']} – {e['issuer']}", "")
            out.append(tex_row(tex(left), tex(right)))
        elif name == "custom":
            out.append("\\small " + tex(" ".join(e["bullets"])) + "\\\\\n")
    if not out:
        return ""
    return f"\\section{{{tex(p.headings[name] if name != 'custom' else '')}}}\n" + "".join(out)


def tex_document(p: Person) -> str:
    style = "compact" if p.layout == "latex_compact" else "jakes"
    customs = {e["title"]: e for e in p.section("custom")}
    def custom(title: str) -> str:
        if title not in customs:
            return ""
        return f"\\section{{{title}}}\n\\small {tex(customs[title]['bullets'][0])}\\\\\n"

    if p.layout == "latex_twocol":
        left = [s for s in ("education", "skills", "awards", "certifications")]
        right = [s for s in p.order if s not in left]
        col = lambda names: "".join(tex_section(p, n, "compact") for n in names)
        return (TEX_HEAD + tex_header(p) + custom("Summary")
                + "\\begin{minipage}[t]{0.33\\linewidth}\\raggedright\n" + col(left) + custom("Interests")
                + "\\end{minipage}\\hfill\n\\begin{minipage}[t]{0.63\\linewidth}\n" + col(right)
                + "\\end{minipage}\n\\end{document}\n")
    body = custom("Summary") + "".join(tex_section(p, n, style) for n in p.order) + custom("Interests")
    return TEX_HEAD + tex_header(p, center=p.layout != "latex_left") + body + "\\end{document}\n"


def tectonic() -> str:
    vendored = OUT.parents[1] / "vendor" / "tectonic" / "tectonic"
    found = str(vendored) if vendored.exists() else shutil.which("tectonic")
    if not found:
        raise SystemExit("Tectonic is missing: run python3 scripts/fetch_tectonic.py")
    return found


def write_latex(p: Person, path: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "resume.tex"
        src.write_text(tex_document(p), encoding="utf-8")
        run = subprocess.run([tectonic(), "--chatter", "minimal", "--outdir", tmp, str(src)],
                             capture_output=True, text=True, check=False)
        if run.returncode:
            raise SystemExit(f"{path.name}: Tectonic failed\n{run.stderr[-2000:]}")
        shutil.copy(Path(tmp) / "resume.pdf", path)


# Chrome ---------------------------------------------------------------------

CSS = {
    "html_modern": """
body{font-family:Helvetica,Arial,sans-serif;font-size:10.5pt;margin:0;color:#222}
h1{font-size:22pt;margin:0}.contact{color:#555;margin:2px 0 8px}
h2{font-size:11pt;color:#2b4c9b;border-bottom:1px solid #2b4c9b;margin:10px 0 4px;text-transform:uppercase}
.row{display:flex;justify-content:space-between}.sub{font-style:italic}
ul{margin:2px 0 6px 18px;padding:0}li{margin:0}
""",
    "html_pipe": """
body{font-family:Georgia,serif;font-size:10.5pt;margin:0}
h1{font-size:20pt;text-align:center;margin:0}.contact{text-align:center;margin-bottom:6px}
h2{font-size:11pt;letter-spacing:2px;margin:10px 0 3px;border-bottom:1px solid #000}
ul{margin:2px 0 6px 18px;padding:0}
""",
    "html_twocol": """
body{font-family:Arial,sans-serif;font-size:10pt;margin:0}
h1{font-size:20pt;margin:0}.contact{margin-bottom:8px}
.grid{display:grid;grid-template-columns:30% 66%;gap:4%}
h2{font-size:10.5pt;text-transform:uppercase;color:#0a6e5a;margin:8px 0 3px}
.row{display:flex;justify-content:space-between}.sub{font-style:italic}
ul{margin:2px 0 6px 16px;padding:0}
""",
    "html_dates_left": """
body{font-family:Helvetica,Arial,sans-serif;font-size:10.5pt;margin:0}
h1{font-size:20pt;margin:0}.contact{margin-bottom:8px}
h2{font-size:11pt;border-bottom:2px solid #333;margin:10px 0 4px}
.e{display:grid;grid-template-columns:28% 72%;margin-bottom:4px}.when{color:#444}
ul{margin:2px 0 4px 16px;padding:0}
""",
}


def h(s: str) -> str:
    return html.escape(s)


def html_ul(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{h(b)}</li>" for b in items) + "</ul>" if items else ""


def html_entry(p: Person, name: str, e: dict) -> str:
    lay = p.layout
    if name == "custom":
        return f"<p>{h(e['bullets'][0])}</p>"
    if name in ("awards", "certifications"):
        left, right = award_line(p, e) if name == "awards" else (f"{e['title']} – {e['issuer']}", "")
        if lay == "html_dates_left":
            return f"<div class='e'><div class='when'>{h(right)}</div><div>{h(left)}</div></div>"
        return f"<div class='row'><span>{h(left)}</span><span>{h(right)}</span></div>" if lay != "html_pipe" \
            else f"<div>{h(left)}{' | ' + h(right) if right else ''}</div>"
    if name == "education":
        extra = f"<div>Relevant Coursework: {h(', '.join(e['coursework']))}</div>" if e.get("coursework") else ""
        if lay == "html_pipe":
            return f"<div><b>{h(e['title'])}</b> | {h(e['location'])} | {h(span(p, e))}</div><div>{h(degree_line(p, e))}</div>{extra}"
        if lay == "html_dates_left":
            return (f"<div class='e'><div class='when'>{h(span(p, e))}</div><div><b>{h(e['title'])}</b>, "
                    f"{h(e['location'])}<br>{h(degree_line(p, e))}{extra}</div></div>")
        return (f"<div class='row'><b>{h(e['title'])}</b><span>{h(e['location'])}</span></div>"
                f"<div class='row sub'><span>{h(degree_line(p, e))}</span><span>{h(span(p, e))}</span></div>{extra}")
    if name == "projects":
        link = f"<div>{h(e['link'])}</div>" if e.get("link") else ""
        head = f"<b>{h(e['title'])}</b> | <i>{h(', '.join(e['tools']))}</i>"
        if lay == "html_dates_left":
            return (f"<div class='e'><div class='when'>{h(span(p, e))}</div><div>{head}{link}"
                    f"{html_ul(e['bullets'])}</div></div>")
        when = span(p, e)
        return f"<div class='row'><span>{head}</span><span>{h(when)}</span></div>{link}{html_ul(e['bullets'])}"
    where = e.get("location", "")
    if lay == "html_pipe":
        parts = [f"<b>{h(e['title'])}</b>", h(e["organization"])] + ([h(where)] if where else []) + [h(span(p, e))]
        return f"<div>{' | '.join(parts)}</div>{html_ul(e['bullets'])}"
    if lay == "html_dates_left":
        return (f"<div class='e'><div class='when'>{h(span(p, e))}<br>{h(where)}</div><div><b>{h(e['title'])}</b>, "
                f"{h(e['organization'])}{html_ul(e['bullets'])}</div></div>")
    return (f"<div class='row'><b>{h(e['organization'])}</b><span>{h(where)}</span></div>"
            f"<div class='row sub'><span>{h(e['title'])}</span><span>{h(span(p, e))}</span></div>{html_ul(e['bullets'])}")


def html_section(p: Person, name: str) -> str:
    if name == "skills":
        body = "".join(f"<div>{'<b>' + h(g) + ':</b> ' if g else ''}{h(v)}</div>" for g, v in skills_lines(p))
    else:
        body = "".join(html_entry(p, name, e) for e in p.section(name))
    return f"<h2>{h(p.headings[name])}</h2>{body}" if body else ""


def html_custom(p: Person, title: str) -> str:
    return "".join(f"<h2>{h(title)}</h2>{html_entry(p, 'custom', e)}" for e in p.section("custom") if e["title"] == title)


def html_document(p: Person) -> str:
    head = f"<h1>{h(p.name)}</h1><div class='contact'>{h(p.phone)} | {h(p.email)} | {h(p.link)}</div>"
    if p.layout == "html_twocol":
        left = ("education", "skills", "awards", "certifications")
        body = (html_custom(p, "Summary") + "<div class='grid'><div>" + "".join(html_section(p, n) for n in left)
                + html_custom(p, "Interests") + "</div><div>"
                + "".join(html_section(p, n) for n in p.order if n not in left) + "</div></div>")
    else:
        body = html_custom(p, "Summary") + "".join(html_section(p, n) for n in p.order) + html_custom(p, "Interests")
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>@page{{size:letter;margin:0.5in}}"
            f"{CSS[p.layout]}</style></head><body>{head}{body}</body></html>")


def find_chrome(given: str | None) -> str:
    if given:
        return given
    for pattern in ("Library/Caches/ms-playwright/chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium",
                    "Library/Caches/ms-playwright/chromium-*/chrome-mac*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"):
        found = sorted(Path.home().glob(pattern))
        if found:
            return str(found[-1])
    for app in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",):
        if Path(app).exists():
            return app
    found = shutil.which("google-chrome") or shutil.which("chromium")
    if not found:
        raise SystemExit("No Chrome found: pass --chrome with its path")
    return found


def write_html(p: Person, path: Path, chrome: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "resume.html"
        page.write_text(html_document(p), encoding="utf-8")
        run = subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                              f"--print-to-pdf={path}", page.as_uri()], capture_output=True, text=True, check=False)
        if run.returncode or not path.exists():
            raise SystemExit(f"{path.name}: Chrome failed\n{run.stderr[-2000:]}")


# Word -----------------------------------------------------------------------


def write_docx(p: Person, path: Path) -> None:
    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Inches(0.6)
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10.5)
    width = Inches(7.3)

    def para(text: str = "", bold: bool = False, italic: bool = False, right: str | None = None):
        par = doc.add_paragraph()
        par.paragraph_format.space_after = Pt(0)
        run = par.add_run(text)
        run.bold, run.italic = bold, italic
        if right is not None:
            par.paragraph_format.tab_stops.add_tab_stop(width, WD_TAB_ALIGNMENT.RIGHT)
            par.add_run("\t" + right).italic = italic
        return par

    def bullets(items: list[str]) -> None:
        for b in items:
            if p.layout == "docx_plain":
                para("• " + b)
            else:
                doc.add_paragraph(b, style="List Bullet").paragraph_format.space_after = Pt(0)

    def table_row(left: list[tuple[str, bool]], right: list[str]) -> None:
        t = doc.add_table(rows=1, cols=2)
        lc, rc = t.rows[0].cells
        lc.width, rc.width = Inches(5.3), Inches(2.0)
        lc.text, rc.text = "", ""
        for k, (text, bold) in enumerate(left):
            par = lc.paragraphs[0] if k == 0 else lc.add_paragraph()
            par.add_run(text).bold = bold
        for k, text in enumerate(right):
            par = rc.paragraphs[0] if k == 0 else rc.add_paragraph()
            par.add_run(text)

    def head(e: dict, name: str) -> None:
        where = e.get("location", "")
        if name == "education":
            if p.layout == "docx_table":
                table_row([(e["title"], True), (degree_line(p, e), False)], [where, span(p, e)])
            elif p.layout == "docx_tabs":
                para(e["title"], bold=True, right=where)
                para(degree_line(p, e), italic=True, right=span(p, e))
            else:
                para(f"{e['title']} — {where}", bold=True)
                para(degree_line(p, e))
                para(span(p, e))
            if e.get("coursework"):
                para("Relevant Coursework: " + ", ".join(e["coursework"]))
            return
        if p.layout == "docx_table":
            table_row([(e["organization"], True), (e["title"], False)], [where, span(p, e)])
        elif p.layout == "docx_tabs":
            para(e["organization"], bold=True, right=span(p, e))
            para(e["title"], italic=True, right=where)
        else:
            para(f"{e['title']} — {e['organization']}", bold=True)
            para(" | ".join(x for x in (where, span(p, e)) if x))

    title = doc.add_paragraph()
    title.add_run(p.name).bold = True
    title.runs[0].font.size = Pt(20)
    para(f"{p.email} | {p.phone} | {p.link}")

    def heading(text: str) -> None:
        par = doc.add_paragraph()
        par.paragraph_format.space_before = Pt(8)
        par.paragraph_format.space_after = Pt(2)
        run = par.add_run(text.upper() if p.layout != "docx_plain" else text)
        run.bold = True
        run.font.size = Pt(12)

    def custom(name: str) -> None:
        for e in p.section("custom"):
            if e["title"] == name:
                heading(name)
                para(e["bullets"][0])

    custom("Summary")
    for name in p.order:
        if name == "skills":
            heading(p.headings["skills"])
            for group, value in skills_lines(p):
                par = doc.add_paragraph()
                par.paragraph_format.space_after = Pt(0)
                if group:
                    par.add_run(group + ": ").bold = True
                par.add_run(value)
            continue
        found = p.section(name)
        if not found:
            continue
        heading(p.headings[name])
        for e in found:
            if name in ("education", "experience", "leadership"):
                head(e, name)
                bullets(e.get("bullets", []))
            elif name == "projects":
                para(project_head(e), bold=True, right=span(p, e) or None)
                if e.get("link"):
                    para(e["link"])
                bullets(e["bullets"])
            elif name == "awards":
                left, right = award_line(p, e)
                para(left, right=right or None)
            elif name == "certifications":
                para(f"{e['title']} – {e['issuer']}")
    custom("Interests")
    doc.save(path)


# --- Main -------------------------------------------------------------------

LAYOUTS = ["latex_jakes", "latex_compact", "latex_twocol", "latex_left",
           "html_modern", "html_pipe", "html_twocol", "html_dates_left",
           "docx_table", "docx_tabs", "docx_plain"]


def main(chrome: str | None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.*"):
        if old.suffix in (".pdf", ".docx", ".json"):
            old.unlink()
    browser = None
    for i in range(len(PEOPLE)):
        layout = LAYOUTS[i % len(LAYOUTS)]
        p = make_person(i, layout)
        stem = f"{i + 1:02d}_{layout}"
        ext = ".docx" if layout.startswith("docx") else ".pdf"
        path = OUT / f"{stem}{ext}"
        if layout.startswith("latex"):
            write_latex(p, path)
        elif layout.startswith("html"):
            browser = browser or find_chrome(chrome)
            write_html(p, path, browser)
        else:
            write_docx(p, path)
        (OUT / f"{stem}.json").write_text(json.dumps(key_of(p, path.name), indent=1) + "\n", encoding="utf-8")
        print(f"{path.name}: {len(p.entries)} entries")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--chrome", help="the Chrome or Chromium binary for the browser layouts")
    main(parser.parse_args().chrome)
