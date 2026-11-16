"""The workit-auto-apply:// link WorkIt's sign-in page opens, taken by a Mac app that isn't the built bundle (W5, W8).

macOS hands a link's scheme only to an app bundle that claims it, and `uv run apply app` is a Python process, not a
bundle. So, before the sign-in page opens, `ready` makes a small helper bundle of its own in the data folder (an
AppleScript applet, osacompile's), which claims the scheme and writes the link it is handed to INBOX, readable by
this user alone; the window takes it from there (`take`) and trades its code (app_window.Bridge.take_link). The
student presses Open WorkIt Auto Apply and the window signs in, with nothing to paste.

The helper only carries the link: its code is bound to this sign-in's PKCE challenge, so a link another program wrote
to INBOX trades for nothing (workit.trade). Pasting the code still works where the helper can't be made (not a Mac,
a data folder in a temp folder, where LaunchServices won't look for apps). The built app (W8) claims the scheme in
its own Info.plist and needs no helper.
"""

import subprocess
import sys

from apply.home import HOME, in_temp

SCHEME = "workit-auto-apply"
HELPER = HOME / "WorkIt Auto Apply Sign-In.app"
INBOX = HOME / "sign-in-link"
LSREGISTER = ("/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/"
              "lsregister")
# The applet: one handler, for the link macOS hands it. umask 077: the link's code is the student's.
SCRIPT = """on open location theURL
\tdo shell script "umask 077; printf %s " & quoted form of theURL & " > " & quoted form of "{inbox}"
end open location
"""
# Info.plist's keys: its own id, no Dock icon, and the scheme it claims.
PLIST = (("CFBundleIdentifier", "-string", "ai.workitjobs.autoapply.signin"),
         ("LSUIElement", "-bool", "true"),
         ("CFBundleURLTypes", "-json", f'[{{"CFBundleURLName": "WorkIt Auto Apply sign-in", "CFBundleURLSchemes": ["{SCHEME}"]}}]'))


def ready() -> bool:
    """The helper made (once, or again when its inbox moved) and registered with LaunchServices; False where it
    can't be, and then the student pastes the code."""
    if sys.platform != "darwin" or in_temp(HOME):
        return False
    stamp = HELPER / "Contents" / "inbox"  # which INBOX the applet writes to
    try:
        if not (stamp.is_file() and stamp.read_text() == str(INBOX)):
            HOME.mkdir(parents=True, exist_ok=True)
            subprocess.run(["osacompile", "-o", str(HELPER), "-e", SCRIPT.format(inbox=INBOX)],
                           check=True, capture_output=True, timeout=60)
            plist = HELPER / "Contents" / "Info.plist"
            for key, kind, value in PLIST:
                subprocess.run(["plutil", "-replace", key, kind, value, str(plist)], check=True, capture_output=True)
            # The edit broke osacompile's ad-hoc signature: macOS won't launch it unsigned.
            subprocess.run(["codesign", "--force", "--sign", "-", str(HELPER)], check=True, capture_output=True,
                           timeout=60)
            stamp.write_text(str(INBOX))
        subprocess.run([LSREGISTER, "-f", str(HELPER)], check=True, capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def clear() -> None:
    """Forget a link an earlier sign-in left: its code was for another challenge."""
    INBOX.unlink(missing_ok=True)


def take() -> str | None:
    """The link the helper was handed, once; None till then."""
    try:
        link = INBOX.read_text().strip()
    except OSError:
        return None
    INBOX.unlink(missing_ok=True)
    return link if link.startswith(f"{SCHEME}://") else None
