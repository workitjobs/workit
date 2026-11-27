"""
WorkIt Auto Apply's prompts (KAN-723; D5 and W1's "Prompts on the server"
in docs/desktop_application_auto_apply.md). The app sends a call's kind,
its version and its data to POST /apply-app/ask, and the server builds the
system prompt, the prompt and the schema here. A request never carries a
prompt or a schema, so it can't steer the model past the kind's own
instructions or send a schema that attacks the server.

Each module ports one of Apply's modules (apply-agent/src/apply/) and lists
its `KINDS`. A kind's data fields never change in place: a student's app
can be an older copy than the server, so a change is a new version,
registered beside the old one while app copies still send it. The prompt
text may change in any merge. Apply's own copy of a prompt goes once its
call sends the kind.
"""

from app.apply_prompts import (
    brief,
    claude_fill,
    essays,
    generic_fill,
    own_application,
    presubmit,
    probe,
    recording,
    story_map,
    writing,
)
from app.apply_prompts.kind import Built, Kind, said

KINDS: dict[tuple[str, int], Kind] = {(k.name, k.version): k for k in (
    *brief.KINDS, *claude_fill.KINDS, *essays.KINDS, *generic_fill.KINDS, *own_application.KINDS, *presubmit.KINDS, *probe.KINDS, *recording.KINDS,
    *story_map.KINDS, *writing.KINDS,
)}

__all__ = ["KINDS", "Built", "Kind", "said"]
