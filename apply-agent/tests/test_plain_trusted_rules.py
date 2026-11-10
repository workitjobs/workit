"""The worker extension's debugger sends only what ops/typing.js allows (KAN-716). No browser: in CI.

A plain Worker types text trusted through its own chrome.debugger. That is a key and click path, so
these rules are checked on the source: one file uses the debugger, every command goes through its
`send`, and `send` names only text, Backspace/Delete and focus emulation."""

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
        "Input.insertText", "Input.dispatchKeyEvent", "Emulation.setFocusEmulationEnabled"}
    keys = text[text.index("const KEYS = {"):]
    keys = keys[:keys.index("};")]
    assert re.findall(r"^\s+(\w+): \{", keys, re.MULTILINE) == ["Backspace", "Delete"]  # never Enter, Space or a character
    assert "dispatchMouseEvent" not in text


def test_workers_start_with_the_debugger_bar_hidden_and_the_permission_asked():
    assert "--silent-debugger-extension-api" in launcher.FLAGS
    assert '"debugger"' in (EXT / "manifest.json").read_text()
    assert not any(flag.startswith(launcher.NEVER) for flag in launcher.FLAGS)
