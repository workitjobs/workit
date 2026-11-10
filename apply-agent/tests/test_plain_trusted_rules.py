"""The worker extension's debugger sends only what ops/typing.js allows (KAN-716). No browser: in CI.

A plain Worker types text trusted through its own chrome.debugger. That is a key and click path, so
these rules are checked on the source: one file uses the debugger, every command goes through its
`send`, and `send` names only text, Backspace/Delete, a plain left click (for a radio, checkbox or
option only) and focus emulation."""

import re
from pathlib import Path

from apply.plain import extension, launcher

EXT = Path(extension.__file__).resolve().parents[3] / "worker-extension"
TYPING = EXT / "ops" / "typing.js"


def sources() -> dict[Path, str]:
    return {p: p.read_text() for p in sorted(EXT.rglob("*.js")) if "vendor" not in p.parts}


def test_only_ops_typing_uses_the_debugger_and_only_through_send():
    users = [p.relative_to(EXT).as_posix() for p, text in sources().items() if "chrome.debugger" in text]
    assert users == ["ops/typing.js"]
    text = TYPING.read_text()
    assert text.count("chrome.debugger.sendCommand") == 1
    send = text[text.index("export function send("):]
    send = send[:send.index("\n}\n")]
    assert "chrome.debugger.sendCommand" in send
    calls = re.findall(r"chrome\.debugger\.(\w+)", text)
    assert set(calls) <= {"attach", "detach", "sendCommand", "onDetach"}


def test_send_names_only_text_backspace_delete_and_focus():
    text = TYPING.read_text()
    send = text[text.index("export function send("):]
    send = send[:send.index("\n}\n")]
    assert set(re.findall(r'"((?:Input|Emulation|[A-Z]\w+)\.\w+)"', send)) == {
        "Input.insertText", "Input.dispatchKeyEvent", "Input.dispatchMouseEvent", "Emulation.setFocusEmulationEnabled"}
    keys = text[text.index("const KEYS = {"):]
    keys = keys[:keys.index("};")]
    assert re.findall(r"^\s+(\w+): \{", keys, re.MULTILINE) == ["Backspace", "Delete"]  # never Enter, Space or a character
    mouse = text[text.index("const MOUSE = "):].split("\n", 1)[0]
    assert set(re.findall(r'"(\w+)"', mouse)) == {"mouseMoved", "mousePressed", "mouseReleased"}  # no wheel, no drag
    assert 'params.button === (params.type === "mouseMoved" ? "none" : "left")' in send  # a left click only
    assert "(params.clickCount ?? 0) <= 1" in send and "!params.modifiers" in send


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
