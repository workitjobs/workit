"""WorkIt Auto Apply's Story bank (W11, services/story_bank.py): built from what WorkIt holds, in the layout Apply's
essays read (apply-agent/sample/story-bank.md). Apply's readers find the student's own writing by its "'s own essays"
heading and a story by its section's heading and bullet."""

from app.services.story_bank import story_bank

JOB = {"section": "experience", "title": "Software Engineering Intern", "organization": "Acme", "copy_group": "g1",
       "start_month": "2026-06", "end_month": "2026-08", "end_kind": "month", "location": "Springfield, IL",
       "tools": ["Python"], "bullets": [{"text": "Cut the report to 20 seconds.", "position": 2},
                                        {"text": "Built the late-delivery flag.", "position": 1}]}
STUDENT = {
    "full_name": "Sam Seeker", "first_name": "Sam",
    "bank": {"entries": [
        JOB, {**JOB, "id": "copy on another resume"},
        {"section": "education", "title": "Stony Brook University", "degree": "B.S.", "field_of_study": "Computer Science",
         "end_month": "2028-05", "end_kind": "expected", "gpa": 3.7, "gpa_scale": 4.0, "coursework": ["Algorithms"]},
        {"section": "projects", "title": "Shelf scanner", "start_month": "2025-09", "end_kind": "present",
         "bullets": [{"text": "Shows a checked-out book within minutes.", "position": 1}]},
    ], "skills": [{"name": "Python", "group": "Languages"}, {"name": "Git", "group": None},
                  {"name": "Go", "group": "Languages"}]},
    "fill": {"profile": {"story_lines": [
        {"section": "## Answers to essay questions\nThe applicant's own answers.", "line": "- Favorite book? Dune"},
        {"section": "## Added context\nWhat they added.", "line": "- For \"Why us?\": boats"},
        {"section": "## Answers to essay questions\nThe applicant's own answers.", "line": "- Hometown? Albany"},
    ]}},
}


def test_the_story_bank_holds_the_students_writing_entries_skills_and_added_lines_in_apples_layout():
    """Fault: an entry on two resumes told twice, a section's bullets out of the student's order, the own writing
    under a heading Apply's readers miss, or an added line lost or split from its section."""
    assert story_bank(STUDENT, ("I built a shelf scanner.", "  The robot drifted left.  ")) == """\
# Story bank: Sam Seeker

## Sam's own essays
I built a shelf scanner.

The robot drifted left.

## Education
- Stony Brook University, B.S. Computer Science, expected May 2028. GPA 3.7/4.0. Coursework: Algorithms.

## Acme: Software Engineering Intern (Jun 2026-Aug 2026, Springfield, IL; Python)
- Built the late-delivery flag.
- Cut the report to 20 seconds.

## Shelf scanner (Sep 2025-present)
- Shows a checked-out book within minutes.

## Skills
- Languages: Python, Go.
- Git.

## Answers to essay questions
The applicant's own answers.
- Favorite book? Dune
- Hometown? Albany

## Added context
What they added.
- For "Why us?": boats
"""


def test_a_student_with_nothing_on_workit_gets_a_story_bank_with_only_its_title():
    assert story_bank({"full_name": "", "bank": None}, ()) == "# Story bank: The applicant\n"
