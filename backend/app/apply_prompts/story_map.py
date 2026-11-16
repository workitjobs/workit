"""Apply's Story map tagging (apply-agent/src/apply/story_map.py, `build`), as
a kind the server builds: routing tags for every episode of the Story bank.
Apply checks the tags and keeps the map.
"""

from pydantic import Field

from app.apply_prompts.brief import TAGS as PROBLEM_KINDS
from app.apply_prompts.guides import load
from app.apply_prompts.kind import MAX_SOURCES, Built, Data, Kind

SYSTEM = """You tag a student's experience stories so an essay planner can pick the right one for a company. You add no facts: every tag is either a quote from the story bank or routing.

Make one entry per episode: a single bullet line under the sections from Education to Honors (not the voice sections, Skills or "Not on the one-pager"). A section with several distinct stories gets one entry per bullet that tells a story.
- id: "<section-slug>/<short-name>", lowercase with hyphens, unique.
- anchor: the bullet's opening words, copied exactly (at least 6 words), enough to match that one line.
- types: the question types this story answers well, from the list given.
- problem_kinds: the kinds of problem it is, from the list given; none when none fits.
- skills: the languages, tools and techniques the line names.
- numbers: every number in that line, copied exactly with its unit (e.g. "about 40 ms").
- follow_ups: 2 to 4 questions an interviewer would ask next, each with what the bank says in a few words, or exactly "none" when the bank can't answer it.
- never_claim: what an answer must not claim, from the bank's own "not", "never" and "no" statements about this story.
- related: ids of other entries about the same system or event."""

ENTRY = {"type": "object", "properties": {
    "id": {"type": "string"},
    "anchor": {"type": "string"},
    "types": {"type": "array", "items": {"type": "string"}},
    "problem_kinds": {"type": "array", "items": {"type": "string"}},
    "skills": {"type": "array", "items": {"type": "string"}},
    "numbers": {"type": "array", "items": {"type": "string"}},
    "follow_ups": {"type": "array", "items": {"type": "object", "properties": {
        "q": {"type": "string"}, "bank": {"type": "string"}}, "required": ["q", "bank"]}},
    "never_claim": {"type": "array", "items": {"type": "string"}},
    "related": {"type": "array", "items": {"type": "string"}},
}, "required": ["id", "anchor", "types", "problem_kinds", "skills", "numbers", "follow_ups", "never_claim", "related"]}

SCHEMA = {"type": "object", "properties": {"episodes": {"type": "array", "items": ENTRY}}, "required": ["episodes"]}


class Tagged(Data):
    story_bank: str = Field(min_length=1, max_length=MAX_SOURCES)


def tag(data: Tagged) -> Built:
    prompt = (f"<document>\n<source>story-bank.md</source>\n<document_content>\n{data.story_bank}</document_content>\n</document>\n\n"
              f"Question types: {', '.join(load())}\nProblem kinds: {', '.join(PROBLEM_KINDS)}\n\n"
              "Tag every episode in the story bank.")
    return Built(SYSTEM, prompt, SCHEMA)


# Apply's MODEL is Opus: the large chain.
KINDS = (Kind("story_map.tag", 1, Tagged, "large", tag, applicant=False),)
