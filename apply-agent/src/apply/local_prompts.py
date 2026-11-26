"""A Developer checkout's own copy of WorkIt's Model route prompts (D5), so `claude -p` can answer a kind on the
developer's own Claude plan (`apply app --max-plan`) without WorkIt's Usage cap.

The prompts stay where WorkIt keeps them, in this checkout's backend (backend/app/apply_prompts): this builds a
kind's prompt from there exactly as POST /apply-app/ask does, and names the Claude model its size runs on. Never
in the Student build (apply.build.DEVELOPER): the Student app has no backend beside it.
"""

import sys
from pathlib import Path

from apply.adapters import SetupError

BACKEND = Path(__file__).resolve().parents[3] / "backend"
VERSION = 1  # the version WorkItAsk sends
MODELS = {"large": "sonnet", "small": "haiku"}  # Apply's Sonnet and Haiku calls (backend apply_prompts.kind.Kind)
BEST = "opus"  # the Best model (GLOSSARY): every large kind, and BEST_SMALL
BEST_SMALL = {"presubmit.review"}  # the last read of a form before it is sent


def model(kind: str, size: str, best: bool) -> str:
    """The Claude model `kind`, of `size`, runs on: with `best`, a large kind and BEST_SMALL run on the Best model."""
    return BEST if best and (size == "large" or kind in BEST_SMALL) else MODELS[size]


def build(kind: str, data: dict, backend: Path = BACKEND, best: bool = False):
    """`(model, built)` for `kind` and `data`: built's system, prompt and schema, said as the applicant when the
    kind is. With `best`, a large kind and the Pre-submit review run on the Best model. Raises SetupError when this checkout has no backend or no such kind; pydantic's ValidationError
    when `data` is not the kind's."""
    if not (backend / "app" / "apply_prompts").is_dir():
        raise SetupError(f"--max-plan builds WorkIt's prompts from this checkout's backend: none at {backend}")
    if str(backend) not in sys.path:
        sys.path.append(str(backend))
    from app.apply_prompts import KINDS, said

    if (found := KINDS.get((kind, VERSION))) is None:
        raise SetupError(f"WorkIt's prompts have no kind {kind!r} version {VERSION}: update this checkout")
    given = found.data.model_validate(data)
    built = found.build(given)
    return model(kind, found.size, best), (said(built, given) if found.applicant else built)
