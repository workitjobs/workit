"""
How WorkIt reads Apply's Answer bank entries (answer-bank.yaml, as the
import brings it, scripts/import_apply_profile.py) and matches a question's
wording, so an answer means the same whichever way it came.

- **Only the student's own words are their own** (`is_own`). As in Apply,
  an entry is theirs only with `source: lisul`. A Claude draft
  (`source: claude`) stays their Claude's even once reviewed, so it passes
  Claude's checks and a form that bans AI text never takes it. An entry
  marked `reviewed: false` is never their own, whatever its source says:
  an unreviewed answer is not the student's word yet.
"""

from typing import Any

LISUL = "lisul"


def is_own(source: Any, reviewed: Any) -> bool:
    """The student's own words: Apply's `source: lisul`, never one marked unreviewed."""
    return source == LISUL and reviewed is not False


def wording(question: str) -> str:
    """A question's wording as the Fill engine's Answer bank matches it (fit.ts,
    `norm`): case, spacing, curly quotes and a required field's asterisk don't count."""
    text = question.lower().replace("’", "'").replace("“", '"').replace("”", '"')
    return " ".join(text.split()).strip(" *")
