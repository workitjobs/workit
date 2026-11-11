"""A project's tools (KAN-738), pure: no database. The line the editor
types, the sent resume's hash and snapshot, and what the keyword match and
Tailor's truth rule read. The PDF and Word layouts are in
test_resume_render.py; the readings and the API in test_bank_import.py and
test_bank.py."""

import dataclasses
import json
import uuid

from app.services import sent_resumes
from app.services.keywords import _shown_text
from app.services.resume_lines import parse
from app.services.resume_render.sample import IDENTITY, VIEW
from app.services.resume_view import ResumeView, ViewEntry, ViewSection, view_from_json
from app.services.sent_resumes import content_hash
from app.services.tailor import known


def _with_tools(view: ResumeView, tools: tuple[str, ...]) -> ResumeView:
    project = ViewEntry(uuid.UUID(int=99), "projects", "Maze Robot", tools=tools)
    return dataclasses.replace(view, sections=(*view.sections, ViewSection("projects", (project,))))


def test_a_typed_tools_line_is_a_list_split_at_commas_outside_parentheses():
    line = parse("tools", " Next.js, Supabase (PostgreSQL, pgvector) ,, FastAPI ")
    assert (line.target, line.changes) == ("entry", {"tools": ["Next.js", "Supabase (PostgreSQL, pgvector)", "FastAPI"]})
    assert parse("tools", "  ").changes == {"tools": []}


def test_tools_change_the_sent_hash_and_no_tools_keep_the_old_one(monkeypatch):
    plain = _with_tools(VIEW, ())
    assert content_hash(plain, IDENTITY, "jakes") != content_hash(_with_tools(VIEW, ("C++",)), IDENTITY, "jakes")

    # A resume with no project stack hashes as it did before the field, so
    # its repeat still finds the sent resume kept then
    hashed: list[str] = []
    dumps = sent_resumes.json.dumps
    monkeypatch.setattr(sent_resumes.json, "dumps", lambda *a, **k: hashed.append(dumps(*a, **k)) or hashed[-1])
    content_hash(plain, IDENTITY, "jakes")
    assert '"tools"' not in hashed[0]


def test_a_snapshot_from_before_tools_reads_back_with_none():
    view = _with_tools(VIEW, ("C++", "ROS"))
    data = json.loads(json.dumps(dataclasses.asdict(view), default=str))
    assert view_from_json(data) == view
    for section in data["sections"]:
        for entry in section["entries"]:
            del entry["tools"]
    assert all(e.tools == () for s in view_from_json(data).sections for e in s.entries)


def test_the_keyword_match_and_the_truth_rule_read_the_tools_line():
    view = _with_tools(ResumeView(), ("ROS", "Gazebo"))
    assert "Gazebo" in _shown_text(view)
    assert {"ROS", "Gazebo"} <= set(known(view, [], []))
