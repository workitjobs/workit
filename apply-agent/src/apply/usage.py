"""Tokens by call kind: what each model call of an Application used, so a
change to a prompt or a cap can be measured stage by stage.

Every `claude -p` call (apply.claude_cli) and every WorkIt Model route call
(apply.ask_model) adds its usage here under its stage: research (a Company
brief's web research), plan, write, check, edit, review, fill (Claude fill,
Rescue, Ask Claude), and the kind's own name for the rest ("probe.typical").
A stage's row keeps its calls, its turns (a research or fill session takes
many; an ask one), its input, output, cache-read and cache-write tokens, and
its calls per model. Like ClaudeCLI.spent, the rows are kept per
thread: a Worker carries one Application at a time on its thread, so the
difference across an Application (since) is its cost. The Record keeps it
as usage.json, and the run's summary line names the biggest stages."""

import threading

# A kind's stage, as the Record and the summary line name it.
STAGES = {
    "essays.plan": "plan", "essays.write": "write", "writing.check": "check", "writing.edit": "edit",
    "presubmit.review": "review", "research": "research", "drive": "fill",
}
# The usage fields of a call, as the Record names them.
FIELDS = {"input_tokens": "input", "output_tokens": "output", "cache_read_input_tokens": "cache_read",
          "cache_creation_input_tokens": "cache_write"}
SHOWN = 4  # stages the summary line names, biggest first

_local = threading.local()


def stage(kind: str) -> str:
    """The stage `kind` counts under."""
    return STAGES.get(kind, kind)


def add(kind: str, model: str, usage: dict | None, tokens: int | None = None, turns: int = 1) -> dict:
    """Count one call of `kind` on `model` with `usage` (its input, output, cache-read and cache-write tokens,
    as the API names them) and `turns` on this thread. `tokens` is its total when the call gave no breakdown
    (WorkIt's Model route). Returns the call's row, for its trace line."""
    usage = usage or {}
    row = {name: int(usage.get(key) or 0) for key, name in FIELDS.items()}
    if tokens and not any(row.values()):
        row["input"] = int(tokens)
    row["turns"] = turns
    rows = _rows()
    kept = rows.setdefault(stage(kind), {"calls": 0, "turns": 0, **dict.fromkeys(FIELDS.values(), 0), "models": {}})
    kept["calls"] += 1
    for name, count in row.items():
        kept[name] += count
    kept["models"][model] = kept["models"].get(model, 0) + 1
    return row | {"kind": kind, "stage": stage(kind), "model": model}


def snapshot() -> dict:
    """This thread's rows so far, a copy."""
    return {name: row | {"models": dict(row["models"])} for name, row in _rows().items()}


def since(before: dict) -> dict:
    """This thread's rows since `before` (snapshot), stages with no new call left out."""
    now, gone = snapshot(), {}
    for name, row in now.items():
        was = before.get(name) or {"calls": 0, "models": {}}
        if (calls := row["calls"] - was["calls"]) <= 0:
            continue
        models = {m: n - was["models"].get(m, 0) for m, n in row["models"].items() if n - was["models"].get(m, 0) > 0}
        gone[name] = {"calls": calls, **{f: row[f] - was.get(f, 0) for f in ("turns", *FIELDS.values())},
                      "models": models}
    return gone


def total(row: dict) -> int:
    """A row's tokens, counted as `spent` counts them: input, output, cache reads and writes at 1x."""
    return sum(row.get(f, 0) for f in FIELDS.values())


def short(rows: dict) -> str:
    """The SHOWN biggest stages of `rows` for a summary line: "research 290k, edit 61k ×2, write 35k"."""
    biggest = sorted(rows.items(), key=lambda item: -total(item[1]))[:SHOWN]
    return ", ".join(f"{name} {_k(total(row))}" + (f" ×{row['calls']}" if row["calls"] > 1 else "") for name, row in biggest)


def _k(tokens: int) -> str:
    return f"{tokens / 1000:.0f}k" if tokens >= 1000 else str(tokens)


def _rows() -> dict:
    if not hasattr(_local, "rows"):
        _local.rows = {}
    return _local.rows
