"""The truth check (apply.truth, KAN-748) is WorkIt's own: the same file,
byte for byte, as backend/app/auto_apply/truth.py, so the two run one check.
Its behaviour is tested there (backend/tests/test_truth_check.py); Apply's
holds are tested in test_claude_answers.py."""

from pathlib import Path

from apply import truth

BACKEND = Path(__file__).resolve().parents[2] / "backend" / "app" / "auto_apply" / "truth.py"


def test_apply_runs_the_backends_truth_check_unchanged():
    assert Path(truth.__file__).read_bytes() == BACKEND.read_bytes(), (
        "apply-agent/src/apply/truth.py differs from backend/app/auto_apply/truth.py: copy the backend's file here.")


def test_a_made_up_number_and_outcome_are_claims_and_a_clean_answer_has_none():
    own = "Micromouse (IEEE student branch): placed 2nd of 15+ teams at MIT."
    assert [(c.kind, c.text) for c in truth.unsupported("We placed 2nd at MIT, and 47 clubs adopted it.", own)] == [
        ("number", "47"), ("outcome", "adopted")]
    assert truth.unsupported("We placed 2nd of 15+ teams at MIT.", own) == []
