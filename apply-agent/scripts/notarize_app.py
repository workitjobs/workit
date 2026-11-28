"""Notarize a release of WorkIt Auto Apply with Apple and staple the ticket to its DMG (KAN-950, W8 step 2 of
../docs/desktop_application_auto_apply.md).

    APPLE_NOTARY_KEY=<.p8 text> APPLE_NOTARY_KEY_ID=<id> [APPLE_NOTARY_ISSUER_ID=<id>] python3 scripts/notarize_app.py
                         (from apply-agent/, after python3 scripts/build_app.py --release with the Developer ID)

../.github/workflows/publish-app.yml runs it on a GitHub Mac with an App Store Connect API key from the
auto-apply-desktop environment, before scripts/publish_app.py: stapling changes the DMG, and Sparkle's signature
covers every byte of it. Apple checks the DMG and every program in it, and accepts it only when each one has a
Developer ID signature, the hardened runtime and a secure timestamp. The ticket stapled to the DMG lists their
signatures (man stapler), so macOS opens the DMG and the app in it with no warning beyond "downloaded from the
internet".
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import build_app as build  # the app's paths, kept in one place

# notarytool's failures that trying again can't fix, by words in its message (on stderr, as Apple wrote them on
# 2026-11-27), and the fix. Any other failure (a dropped connection) is tried again.
DECLINED = {
    "HTTP status code: 401": "Apple declined the App Store Connect API key. APPLE_NOTARY_KEY, APPLE_NOTARY_KEY_ID and "
                             "APPLE_NOTARY_ISSUER_ID must be one key's: a Team key has an issuer ID, an Individual key "
                             "none (leave it out). A revoked key is declined too: make a new one (docs/secrets.md).",
    "HTTP status code: 403": "Apple refused the key's request: the Account Holder must accept Apple's newest agreement "
                             "(developer.apple.com, Account), and the key needs the Developer role or higher.",
    "invalidPEMDocument": "APPLE_NOTARY_KEY isn't a .p8 file's text: paste the whole file, its BEGIN and END lines too.",
}
TRIES = 3
WAIT = 30  # seconds between tries


def stapled(dmg: Path) -> bool:
    """True when `dmg` carries Apple's ticket, checked against Apple's own copy. Apple notarizes a DMG only when every
    program in it passes, so this also says the app in it is notarized. Not Gatekeeper's spctl: on a Mac with
    Gatekeeper off, as a CI runner can be, it says "override=security disabled" and judges nothing."""
    return subprocess.run(["/usr/bin/xcrun", "stapler", "validate", "-q", dmg], check=False).returncode == 0


def main() -> None:
    # Out of the environment, so no program this script starts inherits it.
    key = os.environ.pop("APPLE_NOTARY_KEY", "").strip()
    key_id = os.environ.get("APPLE_NOTARY_KEY_ID", "").strip()
    issuer = os.environ.get("APPLE_NOTARY_ISSUER_ID", "").strip()  # a Team key's; an Individual key has none
    if not (key and key_id):
        sys.exit("APPLE_NOTARY_KEY or APPLE_NOTARY_KEY_ID is empty: publish-app.yml reads them from the "
                 "auto-apply-desktop environment (docs/secrets.md, workit-prod/auto-apply-desktop).")
    if not build.DMG.is_file():
        sys.exit(f"Build a release first: python3 scripts/build_app.py --release (there is no {build.DMG}).")
    signer = subprocess.run(["/usr/bin/codesign", "--display", "--verbose=2", build.DMG], capture_output=True,
                            text=True, encoding="utf-8", check=False).stderr
    if "Authority=Developer ID Application:" not in signer:
        sys.exit("The DMG has no Developer ID signature, and Apple notarizes nothing without one: the build signs with "
                 "the Developer ID in the Mac's keychains, which only publish-app.yml's run holds.")
    # notarytool reads the key from a file only. The folder is this user's alone (0700) and goes when the block ends.
    with tempfile.TemporaryDirectory() as folder:
        p8 = Path(folder, "notary.p8")
        p8.write_text(key + "\n", encoding="utf-8")
        auth = ["--key", str(p8), "--key-id", key_id, *(["--issuer", issuer] if issuer else [])]
        # Apple's check takes a few minutes, rarely more; the workflow's step bounds the wait. The status decides,
        # never the exit code alone. A try again after a dropped connection may send the DMG twice, which is harmless.
        for attempt in range(1, TRIES + 1):
            done = subprocess.run(["/usr/bin/xcrun", "notarytool", "submit", build.DMG, *auth, "--wait",
                                   "--output-format", "json"], capture_output=True, text=True, encoding="utf-8", check=False)
            try:
                answer = json.loads(done.stdout)
                break
            except json.JSONDecodeError:
                error = (done.stderr or done.stdout).strip()
            if fix := next((fix for words, fix in DECLINED.items() if words in error), ""):
                sys.exit(f"notarytool: {error}\n{fix}")
            if attempt == TRIES:
                sys.exit(f"notarytool failed {TRIES} times: {error}")
            print(f"notarytool failed (try {attempt} of {TRIES}), trying again in {WAIT} s: {error}", flush=True)
            time.sleep(WAIT)
        if answer.get("status") != "Accepted":
            issues = []
            if answer.get("id"):  # Apple's log names each file it refused, and why
                log = subprocess.run(["/usr/bin/xcrun", "notarytool", "log", answer["id"], *auth],
                                     capture_output=True, text=True, encoding="utf-8", check=False).stdout
                try:
                    issues = json.loads(log).get("issues") or []
                except json.JSONDecodeError:
                    pass
            found = "".join(f"\n  {issue.get('path')}: {issue.get('message')}" for issue in issues[:20])
            sys.exit(f"Apple didn't notarize the DMG ({answer.get('status') or answer.get('message')}).{found}")
    # Apple's ticket can reach its servers a little after the check ends: stapler then says "Record not found" and
    # "Error 65".
    for attempt in range(1, TRIES + 1):
        done = subprocess.run(["/usr/bin/xcrun", "stapler", "staple", build.DMG], capture_output=True, text=True,
                              encoding="utf-8", check=False)
        if done.returncode == 0 and stapled(build.DMG):
            break
        error = (done.stderr + done.stdout).strip() or "its ticket doesn't validate"
        if attempt == TRIES:
            sys.exit(f"Apple notarized the DMG, but stapling its ticket failed {TRIES} times: {error}\nStart a new "
                     "run.")
        print(f"Stapling failed (try {attempt} of {TRIES}), trying again in {WAIT} s: {error}", flush=True)
        time.sleep(WAIT)
    print(f"Notarized and stapled: {build.DMG}")


if __name__ == "__main__":
    main()
