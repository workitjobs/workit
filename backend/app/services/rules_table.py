"""
The Fill engine's Rules table (KAN-745), as the API serves it (KAN-756):
the engine's own bundled table, read from the JSON its build writes into the
submodule (`autofiller_extension/fill-engine/dist/rules-table.json`, which
the engine's CI keeps equal to `bundledRules()`). Never a copy kept here: a
copy drifts from the engine the extension ships.

Read once at start (`load`, from app/main.py's lifespan) and again on the
first use if that failed, so the app still starts without the submodule
(backend/CLAUDE.md, "The app starts with no credentials"); the image always
has it (Dockerfile). The table is handed on as data: nothing here names its
version or its fields beyond `answers` and `systems`, so the engine's next
schema version is a data change (a submodule bump), not a change here.
"""

import copy
import json
import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

_table: dict[str, Any] | None = None


class NoRulesTable(Exception):
    """The engine's table is not on this computer (the submodule isn't checked out or built)."""


def load() -> dict[str, Any] | None:
    """Reads the engine's table into memory; None, logged, when it isn't there."""
    global _table
    path = get_settings().rules_table_path
    try:
        _table = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("No Fill engine Rules table at %s: /extension/rules answers 503 (git submodule update --init)", path)
        return None
    return _table


def bundled() -> dict[str, Any]:
    """The whole table as the engine bundles it. NoRulesTable when it isn't there."""
    table = _table if _table is not None else load()
    if table is None:
        raise NoRulesTable
    return table


def sites() -> set[str]:
    """The job systems the engine's table has data for."""
    return set(bundled().get("systems") or {})


def for_site(site: str) -> dict[str, Any]:
    """
    What one job system's fill loads: the whole table with `systems` cut to
    that site, a fresh copy the caller may change. The engine's `loadRules`
    replaces everything on each load, so the answer rules always come along.
    """
    table = copy.deepcopy(bundled())
    table["systems"] = {site: table.get("systems", {})[site]}
    return table
