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

from app.apply_prompts import KINDS, said, writing
from app.apply_prompts.kind import NAME

DRAFTS = {"q1": "I built a scheduling tool.", "q2": "Dear team, ..."}
SOURCES = "<story_bank>\nAt HackSBU 2025 I led a team of four.\n</story_bank>"

# One sample of each kind's data: a new kind adds its own.
SAMPLES = {
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
