"""The helper that takes WorkIt's sign-in link for a checkout's window (apply.sign_in_link): its inbox, and where it
isn't made. Making and registering the bundle is macOS's (osacompile, LaunchServices), not run here."""

import pytest

from apply import sign_in_link


@pytest.fixture
def inbox(tmp_path, monkeypatch):
    monkeypatch.setattr(sign_in_link, "INBOX", tmp_path / "sign-in-link")
    return tmp_path / "sign-in-link"


def test_the_link_is_taken_once(inbox):
    """Fault: a link read again signs a later sign-in in with a spent code, or never leaves the data folder."""
    assert sign_in_link.take() is None
    inbox.write_text("workit-auto-apply://signed-in?code=abc\n")
    assert sign_in_link.take() == "workit-auto-apply://signed-in?code=abc"
    assert sign_in_link.take() is None and not inbox.exists()


def test_only_a_workit_auto_apply_link_is_taken(inbox):
    """Fault: whatever lands in the inbox is traded as a code."""
    inbox.write_text("https://example.com/?code=abc")
    assert sign_in_link.take() is None and not inbox.exists()


def test_clear_forgets_an_earlier_sign_ins_link(inbox):
    inbox.write_text("workit-auto-apply://signed-in?code=old")
    sign_in_link.clear()
    sign_in_link.clear()  # none left: no error
    assert sign_in_link.take() is None


def test_no_helper_is_made_off_a_mac_or_in_a_temp_folder(tmp_path, monkeypatch):
    """Fault: the helper made where LaunchServices won't find it (a temp folder), or osacompile run off a Mac. The
    window then falls back to the pasted code."""
    made = []
    monkeypatch.setattr(sign_in_link.subprocess, "run", lambda *a, **k: made.append(a))
    monkeypatch.setattr(sign_in_link.sys, "platform", "linux")
    assert sign_in_link.ready() is False
    monkeypatch.setattr(sign_in_link.sys, "platform", "darwin")
    monkeypatch.setattr(sign_in_link, "HOME", tmp_path)
    assert sign_in_link.ready() is False and made == []


def test_the_applet_writes_the_link_it_is_handed_to_the_inbox():
    """Fault: the applet's script quotes the inbox's path wrongly, so a data folder with a space ("Application
    Support") gets no link."""
    script = sign_in_link.SCRIPT.format(inbox="/Users/x/Library/Application Support/WorkIt Auto Apply/sign-in-link")
    assert 'quoted form of "/Users/x/Library/Application Support/WorkIt Auto Apply/sign-in-link"' in script
    assert "on open location theURL" in script and "umask 077" in script


def test_the_built_app_takes_the_link_macos_hands_it_once_with_no_helper(inbox, monkeypatch):
    """Fault: the built app makes the checkout's helper (osacompile, a second bundle claiming the scheme), or takes
    a link macOS handed it twice, or keeps one from an earlier sign-in. Its own Info.plist claims the scheme
    (scripts/build_app.py), and the Apple event's link stays in memory (W8)."""
    monkeypatch.setattr(sign_in_link, "BUNDLED", True)
    monkeypatch.setattr(sign_in_link.subprocess, "run", lambda *a, **k: pytest.fail("made a helper"))
    assert sign_in_link.ready() is True
    sign_in_link.hand("workit-auto-apply://signed-in?code=old")
    sign_in_link.clear()
    assert sign_in_link.take() is None
    sign_in_link.hand("workit-auto-apply://signed-in?code=abc")
    assert sign_in_link.take() == "workit-auto-apply://signed-in?code=abc"
    assert sign_in_link.take() is None and not inbox.exists()
