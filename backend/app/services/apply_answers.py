"""
Apply's Answer bank entries as WorkIt keeps them (`applicant_profiles.fill_answers`,
models/CLAUDE.md, "The Fill engine's profile"): one rule for the one-time
import (scripts/import_apply_profile.py) and for any later way in, so an answer
means the same whichever way it came.

- **Only the student's own words are `own`.** As in Apply (answer_bank.py,
  `LISUL`), an entry is theirs only with `source: lisul`. A Claude draft
  (`source: claude`) stays their Claude's even once reviewed, so it passes
  Claude's checks and a form that bans AI text never takes it. An entry
  marked `reviewed: false` is never own, whatever its source says: an
  unreviewed answer is not the student's word yet.
- **A choice** (an entry with options, or a list answer: the options ticked)
  is `choice`, and skips the writing checks.
"""

import datetime
from collections.abc import Iterable
from typing import Any

LISUL = "lisul"


def is_own(source: Any, reviewed: Any) -> bool:
    """The student's own words: Apply's `source: lisul`, never one marked unreviewed."""
    return source == LISUL and reviewed is not False


def brought(
    answer: Any, *, options: Iterable[Any] = (), source: Any = None, reviewed: Any = None,
    company: Any = None, edited_at: datetime.datetime | None = None,
) -> dict | None:
    """One Answer bank entry as `fill_answers` holds it, or None for an entry
    with no answer (an empty one, or a multi-select's "none of these")."""
    if answer in (None, "", []):
        return None
    answer = [str(a) for a in answer] if isinstance(answer, list) else str(answer)
    value = {
        "answer": answer, "own": is_own(source, reviewed),
        "choice": isinstance(answer, list) or bool(list(options or ())),
        "company": str(company or "").strip() or None,
    }
    if edited_at is not None:
        value["edited_at"] = edited_at.astimezone(datetime.UTC).isoformat()
    return value


def from_bank(entries: dict) -> dict:
    """A whole answer-bank.yaml, as the import brings it: {question: entry}."""
    kept = {}
    for filed, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        first = entry.get("first_seen") if isinstance(entry.get("first_seen"), dict) else {}
        value = brought(entry.get("answer"), options=entry.get("options") or (), source=entry.get("source"),
                        reviewed=entry.get("reviewed"), company=first.get("company"),
                        edited_at=_time(entry.get("edited_at")))
        if value is not None:
            kept[str(entry.get("question") or filed).strip()] = value
    return kept


def _time(value: Any) -> datetime.datetime | None:
    if isinstance(value, datetime.datetime):
        return value if value.tzinfo else value.replace(tzinfo=datetime.UTC)
    try:
        parsed = datetime.datetime.fromisoformat(str(value)) if value else None
    except ValueError:
        return None
    return parsed if parsed is None or parsed.tzinfo else parsed.replace(tzinfo=datetime.UTC)
