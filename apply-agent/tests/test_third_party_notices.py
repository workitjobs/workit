"""The third-party notices script (W10): what it keeps from pip-licenses and when a hand entry goes. Its
run with uv and the network is checked by hand (scripts/third_party_notices.py)."""

import importlib.util
from datetime import date
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "third_party_notices.py"
spec = importlib.util.spec_from_file_location("third_party_notices", SCRIPT)
notices = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notices)


def test_a_package_keeps_its_license_and_notice_and_apply_is_left_out():
    rows = [{"Name": "apply", "Version": "0.1.0", "License": "UNKNOWN", "URL": "UNKNOWN"},
            {"Name": "certifi", "Version": "1", "License": "MPL-2.0", "URL": "https://example.org/certifi",
             "LicenseText": "the MPL text", "NoticeText": "UNKNOWN"},
            {"Name": "pyee", "Version": "2", "License": "MIT", "URL": "UNKNOWN", "LicenseText": "the MIT text",
             "NoticeText": "a notice"}]
    certifi, pyee = notices.packages(rows)
    assert (certifi.name, certifi.text, certifi.url) == ("certifi", "the MPL text", "https://example.org/certifi")
    assert (pyee.text, pyee.url) == ("the MIT text\n\na notice", "")
    text = notices.render([certifi, pyee], date(2026, 11, 14))
    assert "  certifi 1: MPL-2.0" in text and "the MPL text" in text and "a notice" in text


def test_a_hand_entry_goes_once_its_package_is_listed(tmp_path):
    (tmp_path / "Sparkle-LICENSE.txt").write_text("Sparkle's text")
    parts, missing = notices.by_hand({"pywebview"}, tmp_path)
    names = [p.name for p in parts]
    assert "pywebview" not in names and "Sparkle" in names
    assert next(p for p in parts if p.name == "Sparkle").text == "Sparkle's text"
    assert "legal/licenses/Sparkle-LICENSE.txt" not in missing
    assert "legal/licenses/Nuitka-LICENSE-RUNTIME.txt" in missing


def test_strict_fails_while_a_license_text_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(notices, "build", lambda: ("notices", ["legal/licenses/Sparkle-LICENSE.txt"]))
    out = tmp_path / "NOTICES.txt"
    assert notices.main(["--out", str(out)]) == 0
    assert notices.main(["--out", str(out), "--strict"]) == 1
    assert out.read_text() == "notices"
