"""
WorkIt Auto Apply's prompts built on the server (KAN-723, app/apply_prompts/):
every kind builds a valid schema from sample data, a build reads only its
own data, and each call is said as the applicant. No test checks a
prompt's wording: the team reads a prompt when it changes it. The route
that sends a build to the model is tests/test_apply_app.py.
"""

import json

import pytest
from jsonschema import Draft202012Validator

from app.apply_prompts import KINDS, essays, said, writing
from app.apply_prompts.guides import load
from app.apply_prompts.kind import NAME

DRAFTS = {"q1": "I built a scheduling tool.", "q2": "Dear team, ..."}
SOURCES = "<story_bank>\nAt HackSBU 2025 I led a team of four.\n</story_bank>"

WHY = {"label": "Why Acme?", "kind": "textarea", "required": True, "type": "why-company"}
LETTER = {"label": "Cover letter", "kind": "textarea", "type": "cover-letter"}
AREA = {"label": "Which area? Select up to 2", "kind": "multi_select", "options": ["Backend", "ML", "Backend"]}
PLANNED = {"type": "why-company", "parts": ["why"], "story": "HackSBU", "slots": {"why": ["I led a team of four"]}}

# One sample of each kind's data: a new kind adds its own.
SAMPLES = {
    ("essays.plan", 1): {"sources": SOURCES, "posting": "<posting>Acme</posting>", "questions": {"q1": WHY, "q2": LETTER}},
    ("essays.write", 1): {"sources": SOURCES, "posting": "<posting>Acme</posting>", "questions": {"q1": WHY, "q2": LETTER},
                          "plans": {"q1": PLANNED, "q2": PLANNED | {"type": "cover-letter"}},
                          "short_questions": {"d1": AREA}},
    ("writing.check", 1): {"drafts": DRAFTS, "sources": SOURCES},
    ("writing.edit", 1): {"drafts": DRAFTS, "sources": SOURCES, "style_card": "Short sentences.",
                          "flagged": {"q1": ["a sentence over 30 words"]}, "questions": {"q1": "Why us?"},
                          "lengths": {"q2": "70-120 words"}},
}


def _built(key):
    kind = KINDS[key]
    data = kind.data.model_validate(SAMPLES[key])
    return said(kind.build(data), data)


def test_every_kind_has_a_sample():
    assert set(SAMPLES) == set(KINDS)


@pytest.mark.parametrize("key", sorted(KINDS))
def test_every_kind_builds_a_valid_schema_for_an_object(key):
    schema = _built(key).schema
    Draft202012Validator.check_schema(schema)
    assert schema["type"] == "object"


@pytest.mark.parametrize(("key", "field"), [(("writing.check", 1), "unsupported"), (("writing.edit", 1), "edited")])
def test_a_writing_answer_has_one_field_for_each_draft(key, field):
    answer = _built(key).schema["properties"][field]
    assert answer["required"] == list(DRAFTS) and set(answer["properties"]) == set(DRAFTS)


def test_the_edit_sends_only_the_questions_and_lengths_of_its_own_drafts():
    data = writing.Edited.model_validate({**SAMPLES["writing.edit", 1], "drafts": {"q1": "I built X."},
                                          "questions": {"q1": "Why us?", "q9": "Other form's question"}})
    prompt = writing.edit(data).prompt
    assert "Why us?" in prompt and "Other form's question" not in prompt
    assert "<lengths>" not in prompt  # q2's length goes with q2's draft only


def test_a_call_is_said_as_the_applicant_and_keeps_the_name_a_placeholder():
    data = writing.Checked.model_validate({**SAMPLES["writing.check", 1], "school": 'Stony "Brook"',
                                           "pronouns": "she/her/hers"})
    built = said(writing.Built(f"{NAME} at @SCHOOL@", "@SCHOOL@ prompt", {"description": "at @SCHOOL@"}), data)
    assert built.system.startswith(f'{NAME} at Stony "Brook"') and "she/her/hers" in built.system
    assert built.prompt == 'Stony "Brook" prompt'
    assert built.schema == {"description": 'at Stony "Brook"'}
    json.dumps(built.schema)


def test_a_plan_has_an_entry_for_each_question_and_lists_only_the_asked_types():
    built = _built(("essays.plan", 1))
    entries = built.schema["properties"]["plan"]["properties"]
    assert set(entries) == {"q1", "q2"} and entries["q1"]["properties"]["type"]["enum"] == list(load())
    assert "- why-company (company link" in built.system and "- failure (company link" not in built.system


def test_a_cover_letter_is_written_in_its_slots_and_a_choice_from_its_options():
    schema = _built(("essays.write", 1)).schema["properties"]
    assert set(schema["essays"]["properties"]["q2"]["properties"]) >= {"opening", "proof", "closing"}
    area = schema["drafts"]["properties"]["d1"]["properties"]["answer"]
    assert area == {"type": "array", "items": {"type": "string", "enum": ["Backend", "ML"]}, "maxItems": 2}


@pytest.mark.parametrize("change", [
    {"questions": {"q1": WHY | {"type": "write-my-homework"}}, "plans": {"q1": PLANNED}},
    {"plans": {"q1": PLANNED}},  # q2 has no plan
    {"short_questions": {"q1": AREA}},  # one key for an essay and a one-off question
    {"questions": {}, "plans": {}, "short_questions": {}},
])
def test_write_data_that_doesnt_hold_together_is_refused(change):
    with pytest.raises(ValueError):
        essays.WriteData.model_validate(SAMPLES["essays.write", 1] | change)
