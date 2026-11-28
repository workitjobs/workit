"""The Safety level (apply.safety): one choice that sets several policies, under the applicant's own keys."""

import json

import pytest

from apply import auto_submit, build, profile, safety


@pytest.fixture
def mine(tmp_path, monkeypatch):
    """The data folder's policies.yaml and app.json, both empty at first."""
    policies, state = tmp_path / "policies.yaml", tmp_path / "app.json"
    monkeypatch.setattr(profile, "OVERRIDE", policies)
    monkeypatch.setattr(safety, "STATE", state)
    return policies, state


# Fault: a level changing what an applicant who never chose one gets.
def test_no_level_is_careful_and_changes_nothing(mine):
    rules = profile.load_policies()
    assert rules["safety_level"] == "careful"
    assert (rules["calibration_run"], rules["high_stakes_job_systems"], rules["auto_submit"]) == (10, ["ashby"], False)
    assert not any(rules[key] for key in ("tick_arbitration", "tick_attestations", "sign_self_id",
                                          "answer_opinion_questions", "auto_submit_essays"))
    assert rules["willing_to_undergo_checks"] is None


# Fault: full_auto left a review-only hold on, or a key the applicant set lost to the level.
def test_full_auto_lifts_the_holds_under_the_applicants_own_keys(mine):
    policies, _ = mine
    policies.write_text("safety_level: full_auto\ncalibration_run: 3\n")
    rules = profile.load_policies()
    assert rules["auto_submit"] is rules["auto_submit_essays"] is rules["sign_self_id"] is True
    assert (rules["high_stakes_job_systems"], rules["hold_high_stakes_essays"]) == ([], False)
    assert rules["calibration_run"] == 3


# Fault: full_auto holding a certification or consent box for the applicant, or balanced ticking one (Lisul, 2026-11-27).
def test_only_full_auto_ticks_every_agreement(mine):
    policies, _ = mine
    for level, ticks in (("careful", False), ("balanced", False), ("full_auto", True)):
        policies.write_text(f"safety_level: {level}\n")
        rules = profile.load_policies()
        assert rules["tick_attestations"] is ticks
        assert rules["willing_to_undergo_checks"] is (True if ticks else None)
    policies.write_text("safety_level: full_auto\ntick_attestations: false\nwilling_to_undergo_checks: false\n")
    rules = profile.load_policies()
    assert rules["tick_attestations"] is rules["willing_to_undergo_checks"] is False


# Fault: the window's choice (app.json) ignored, or put over the level the applicant wrote in policies.yaml.
def test_policies_yaml_beats_the_windows_choice(mine):
    policies, state = mine
    state.write_text(json.dumps({"safety_level": "balanced"}))
    assert profile.load_policies()["tick_arbitration"] is True
    assert profile.load_policies()["sign_self_id"] is False
    policies.write_text("safety_level: careful\n")
    assert profile.load_policies()["tick_arbitration"] is False


# Fault: a misspelt level taken as some other level's policies.
def test_an_unknown_level_is_careful(mine):
    mine[0].write_text("safety_level: yolo\n")
    assert profile.load_policies()["safety_level"] == "careful"


# Fault: a level lifting a hard guard (the caps, captchas, live runs), whatever the applicant chose.
def test_no_level_sets_a_hard_guard():
    keys = {level: set(rules) for level, rules in safety.LEVELS.items()}
    assert all(not rules & safety.HARD_GUARDS for rules in keys.values())
    assert len({frozenset(rules) for rules in keys.values()}) == 1  # each level sets every key it names


# Fault: the Student build reading a level from a policies.yaml, or auto-submitting at full_auto.
def test_the_student_build_keeps_its_level_in_app_json(mine, monkeypatch, tmp_path):
    policies, state = mine
    monkeypatch.setattr(build, "STUDENT", True)
    policies.write_text("safety_level: full_auto\n")
    assert profile.load_policies()["safety_level"] == "careful"
    state.write_text(json.dumps({"safety_level": "full_auto"}))
    rules = profile.load_policies()
    assert rules["sign_self_id"] is True
    applicant = tmp_path / "applicant-profile.yaml"
    applicant.write_text("identity: {}\n")
    assert auto_submit.on(profile.ApplicantProfile.load(applicant)) is False
