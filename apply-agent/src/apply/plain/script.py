"""Page code for the `eval` op: Playwright's evaluate(expression, arg), as one expression.

The wrapped code evaluates `expression`; a function is called with `arg`; a promise is
awaited. It answers {ok: value}, {undef: true}, or {err: {name, message}}, so a page error
comes back as data rather than as the extension's own failure.

With APPLY_PLAIN_EXEC=debugger (KAN-839, the W6 spike), page code goes through the worker
extension's chrome.debugger (`cdp.eval`) instead of chrome.userScripts, and the Fill engine is
handed to the extension's memory once per connection (`cdp.keep`), so `engine.load` runs it
through the debugger, with no file in the extension's folder: what a Chrome Web Store copy of
the extension may do. Off by default until the spike's checks pass.
"""

import hashlib
import json
import os

from apply.plain.bridge import PortError, features

EXEC = "APPLY_PLAIN_EXEC"  # "debugger": page code and the engine through chrome.debugger
DEBUGGER_FROM = 4  # the worker extension's feature level with cdp.eval, cdp.load and cdp.keep

USER_SCRIPTS_OFF = ("the page's CSP blocks eval and this Worker's user scripts are off: turn on Allow User Scripts "
                    "for the Apply Worker extension in the seed profile (`uv run apply plain seed`)")


def wrap(expression: str, arg=None) -> str:
    body = expression.strip().rstrip(";")
    return ("(async () => { try { let __v = (\n" + body + "\n); "
            "if (typeof __v === 'function') __v = __v(" + json.dumps(arg) + "); __v = await __v; "
            "return __v === undefined ? {undef: true} : {ok: __v}; } "
            "catch (e) { return {err: {name: (e && e.name) || 'Error', message: String((e && e.message) || e)}}; } })()")


def unwrap(answer):
    """The value a wrapped expression answered, or its error raised as PortError."""
    if not isinstance(answer, dict):
        raise PortError("EvalError", f"page code gave no answer ({answer!r})")
    if "err" in answer:
        error = answer["err"] or {}
        if error.get("name") == "UserScriptsOff":
            raise PortError("UserScriptsOff", f"{USER_SCRIPTS_OFF} ({error.get('message')})")
        raise PortError("EvalError", f"{error.get('name', 'Error')}: {error.get('message', '')}")
    return None if answer.get("undef") else answer.get("ok")


def through_debugger(connection) -> bool:
    """Whether this Worker's page code goes through its extension's debugger (APPLY_PLAIN_EXEC)."""
    return os.environ.get(EXEC) == "debugger" and features(connection.hello) >= DEBUGGER_FROM


def keep_engine(connection) -> None:
    """The Fill engine's bundle in the extension's memory (`cdp.keep`), once per connection, so its
    `engine.load` runs it through the debugger. Only with through_debugger."""
    from apply import fill_engine

    if not through_debugger(connection) or getattr(connection, "engine_kept", False):
        return
    source = fill_engine.ENGINE.read_text()
    connection.call("cdp.keep", name="engine", source=source, sha256=hashlib.sha256(source.encode()).hexdigest())
    connection.engine_kept = True


def evaluate(connection, tab: int, expression: str, arg=None, frame: int = 0):
    """Playwright's page.evaluate(expression, arg), in the MAIN world of `frame` of `tab`."""
    op = "cdp.eval" if through_debugger(connection) else "eval"
    return unwrap(connection.call(op, tab=tab, frame=frame, code=wrap(expression, arg)))
