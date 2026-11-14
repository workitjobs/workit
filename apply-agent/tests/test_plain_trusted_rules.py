"""The worker extension's debugger sends only what ops/typing.js and ops/cdp.js allow (KAN-716,
KAN-839). No browser: in CI.

A plain Worker types text trusted through its own chrome.debugger. That is a key and click path, so
these rules are checked on the source: three files use the debugger. ops/debug.js holds the one
attachment per tab and sends nothing. ops/typing.js sends every input, through its `send`, which
names only text, Backspace/Delete, a plain left click (for a radio, checkbox or option only) and
focus emulation. ops/cdp.js runs page code (KAN-839) through its own `send`, whose list names no
input, no emulation and no domain that a page can notice turned on (Runtime, Debugger, Console)."""

import re
from pathlib import Path

from apply.plain import extension, launcher

EXT = Path(extension.__file__).resolve().parents[3] / "worker-extension"
TYPING = EXT / "ops" / "typing.js"
CDP = EXT / "ops" / "cdp.js"
DEBUG = EXT / "ops" / "debug.js"


def sources() -> dict[Path, str]:
    return {p: p.read_text() for p in sorted(EXT.rglob("*.js")) if "vendor" not in p.parts}


def _send_of(text: str, head: str) -> str:
    send = text[text.index(head):]
    return send[:send.index("\n}\n")]


def test_only_typing_and_cdp_send_debugger_commands_and_each_only_through_its_send():
    users = [p.relative_to(EXT).as_posix() for p, text in sources().items() if "chrome.debugger" in text]
    assert users == ["ops/cdp.js", "ops/debug.js", "ops/typing.js"]
    attach = DEBUG.read_text()
    assert "sendCommand" not in attach  # the attachment only: it sends nothing
    assert set(re.findall(r"chrome\.debugger\??\.(\w+)", attach)) <= {"attach", "detach", "onDetach", "onEvent"}
    for path, head in ((TYPING, "export function send("), (CDP, "function send(")):
        text = path.read_text()
        assert text.count("chrome.debugger.sendCommand") == 1, path.name
        assert "chrome.debugger.sendCommand" in _send_of(text, head), path.name
        assert set(re.findall(r"chrome\.debugger\.(\w+)", text)) <= {"sendCommand"}, path.name  # attaching is debug.js's


def test_cdp_sends_page_code_never_input_and_turns_on_nothing_a_page_can_notice():
    text = CDP.read_text()
    allowed = text[text.index("const ALLOWED = new Set(["):]
    allowed = set(re.findall(r'"(\w+\.\w+)"', allowed[:allowed.index("]);")]))
    assert allowed == {
        "Runtime.evaluate", "Runtime.callFunctionOn", "Runtime.releaseObject", "Runtime.runIfWaitingForDebugger",
        "DOM.getFrameOwner", "DOM.describeNode", "DOM.resolveNode",
        "Page.enable", "Page.getFrameTree", "Page.addScriptToEvaluateOnNewDocument", "Page.removeScriptToEvaluateOnNewDocument",
        "Target.setAutoAttach"}
    assert not {m for m in allowed if m.startswith(("Input.", "Emulation.", "Debugger.", "Console."))}
    assert "Runtime.enable" not in allowed  # with Runtime on, a page can tell (tests/test_plain_debugger.py)
    assert "if (!ALLOWED.has(method))" in _send_of(text, "function send(")


def test_send_names_only_text_backspace_delete_a_click_and_focus():
    text = TYPING.read_text()
    rules = text[text.index("function allowed("):]
    rules = rules[:rules.index("\n}\n")]
    assert set(re.findall(r'"((?:Input|Emulation|[A-Z]\w+)\.\w+)"', rules)) == {
        "Input.insertText", "Input.dispatchKeyEvent", "Input.dispatchMouseEvent", "Emulation.setFocusEmulationEnabled"}
    assert "!/[\\r\\n]/.test(params.text)" in rules  # never a line break: a lone one is an Enter to a one-line box
    keys = text[text.index("const KEYS = {"):]
    keys = keys[:keys.index("};")]
    assert re.findall(r"^\s+(\w+): \{", keys, re.MULTILINE) == ["Backspace", "Delete"]  # never Enter, Space or a character
    assert 'exactly(params, ["type", "key", "code", "windowsVirtualKeyCode", "commands"])' in rules  # no modifiers, no text
    mouse = text[text.index("const MOUSE = "):].split("\n", 1)[0]
    assert set(re.findall(r'"(\w+)"', mouse)) == {"mousePressed", "mouseReleased"}  # no move first, no wheel, no drag
    assert 'exactly(params, ["type", "x", "y", "button", "clickCount", "buttons"])' in rules
    assert 'params.button === "left"' in rules and "params.clickCount === 1" in rules


def test_send_refuses_what_it_does_not_name():
    """The allowlist itself, run in Node when there is one."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        import pytest
        pytest.skip("no node here")
    text = TYPING.read_text()
    rules = text[text.index("const KEYS = {"):text.index("export { available }")] + text[text.index("const exactly"):text.index("// The one place")]
    cases = [
        ("Input.insertText", {"text": "Acme"}, True), ("Input.insertText", {"text": "\n"}, False),
        ("Input.insertText", {"text": "a\nb"}, False), ("Input.insertText", {"text": "\r"}, False),
        ("Input.insertText", {"text": "a", "extra": 1}, False),
        ("Input.dispatchKeyEvent", {"type": "rawKeyDown", "key": "Backspace", "code": "Backspace", "windowsVirtualKeyCode": 8,
                                    "commands": ["deleteBackward"]}, True),
        ("Input.dispatchKeyEvent", {"type": "rawKeyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "commands": []}, False),
        ("Input.dispatchKeyEvent", {"type": "rawKeyDown", "key": "Backspace", "code": "Backspace", "windowsVirtualKeyCode": 8,
                                    "commands": ["deleteBackward"], "modifiers": 4}, False),
        ("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Backspace", "code": "Backspace", "windowsVirtualKeyCode": 8,
                                    "commands": ["deleteBackward"]}, False),
        ("Input.dispatchMouseEvent", {"type": "mousePressed", "x": 1, "y": 2, "button": "left", "clickCount": 1, "buttons": 1}, True),
        ("Input.dispatchMouseEvent", {"type": "mousePressed", "x": 1, "y": 2, "button": "left", "clickCount": 2, "buttons": 1}, False),
        ("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": 1, "y": 2, "button": "none", "clickCount": 0, "buttons": 0}, False),
        ("Input.dispatchMouseEvent", {"type": "mousePressed", "x": 1, "y": 2, "button": "right", "clickCount": 1, "buttons": 2}, False),
        ("Input.dispatchMouseEvent", {"type": "mousePressed", "x": 1, "y": 2, "button": "left", "clickCount": 1, "buttons": 1,
                                      "modifiers": 8}, False),
        ("Emulation.setFocusEmulationEnabled", {"enabled": True}, True), ("Runtime.evaluate", {"expression": "1"}, False),
        ("Input.dispatchKeyEvent", {"type": "rawKeyDown", "key": "Backspace", "code": "Enter", "windowsVirtualKeyCode": 13,
                                    "commands": ["deleteBackward"]}, False),
    ]
    import json
    script = rules + f"\nfor (const [m, p, want] of {json.dumps(cases)}) if (Boolean(allowed(m, p)) !== want) {{ console.log(m, JSON.stringify(p)); process.exitCode = 1; }}\n"
    done = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stdout + done.stderr


def test_a_trusted_click_is_only_for_a_choice_never_a_button_or_a_link():
    dom = (EXT / "page" / "dom.js").read_text()
    choice = re.search(r'const CHOICE = "([^"]+)"', dom)[1]
    presses = re.search(r'const PRESSES = "([^"]+)"', dom)[1]
    assert not re.search(r"\bbutton\b|\ba\[|submit|\blink\b", choice)
    for kind in ("button", "a[href]", "input[type=submit]", "[role=button]", "[role=link]"):
        assert kind in presses
    assert "window !== window.top" in dom  # the top frame only


def test_workers_start_with_the_debugger_bar_hidden_and_the_permission_asked():
    assert "--silent-debugger-extension-api" in launcher.FLAGS
    assert '"debugger"' in (EXT / "manifest.json").read_text()
    assert not any(flag.startswith(launcher.NEVER) for flag in launcher.FLAGS)
