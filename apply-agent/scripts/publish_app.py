"""Sign a release of WorkIt Auto Apply for Sparkle and write the feed that offers it (KAN-941, W8 step 4 of
../docs/desktop_application_auto_apply.md).

    SPARKLE_PRIVATE_KEY=<the update key> python3 scripts/publish_app.py     (from apply-agent/, after --release)

../.github/workflows/publish-app.yml runs it on a GitHub Mac, after build_app.py --release, with the key from the
auto-apply-desktop environment: no person's computer holds the key. It writes build/out/publish/: the DMG under its
build's own name, signed with the update key (Sparkle's sign_update), and appcast.xml, the feed every installed app
reads, with one item: this build. The workflow uploads both. It refuses a test build, a DMG Apple hasn't notarized
(scripts/notarize_app.py), which macOS would block on every student's Mac, and a key whose signature the app's public
half rejects: every app would download that update and refuse it.
"""

import os
import plistlib
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from email.utils import formatdate

import build_app as build  # the app's paths and settings, kept in one place
import notarize_app as notarize

PUBLISH = build.OUT / "publish"
SIGN_UPDATE = build.SPARKLE / "bin" / "sign_update"
SPARKLE = "{http://www.andymatuschak.org/xml-namespaces/sparkle}"  # the feed's sparkle: names, as ElementTree reads them
APPCAST = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle">
  <channel>
    <title>{name}</title>
    <item>
      <title>{shown} ({number})</title>
      <pubDate>{date}</pubDate>
      <sparkle:version>{number}</sparkle:version>
      <sparkle:shortVersionString>{shown}</sparkle:shortVersionString>
      <sparkle:minimumSystemVersion>{minimum}</sparkle:minimumSystemVersion>
      <enclosure url="{url}" type="application/octet-stream" sparkle:edSignature="{signature}" length="{length}" />
    </item>
  </channel>
</rss>
"""
# The check an installed app makes: an Ed25519 signature of the whole DMG, under the app's public half. Run on the
# build's own Python, which has cryptography (Apply's own dependency).
VERIFY = r"""
import base64, sys
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
key, signature, dmg = sys.argv[1:]
Ed25519PublicKey.from_public_bytes(base64.b64decode(key)).verify(base64.b64decode(signature), Path(dmg).read_bytes())
"""


def main() -> None:
    # Out of the environment, so no program this script starts (the build's Python below) inherits it.
    key = os.environ.pop("SPARKLE_PRIVATE_KEY", "").strip()
    if not key:
        sys.exit("SPARKLE_PRIVATE_KEY is empty: publish-app.yml reads it from the auto-apply-desktop environment "
                 "(docs/secrets.md, workit-prod/auto-apply-desktop).")
    if not build.DMG.is_file():
        sys.exit(f"Build a release first: python3 scripts/build_app.py --release (there is no {build.DMG}).")
    plist = plistlib.loads((build.APP / "Contents" / "Info.plist").read_bytes())
    number, shown = plist["CFBundleVersion"], plist["CFBundleShortVersionString"]
    if not plist.get(build.RELEASE_KEY):
        sys.exit("That's a test build: publish only a release (python3 scripts/build_app.py --release).")
    if not notarize.stapled(build.DMG):
        sys.exit("The DMG carries no notarization ticket, so macOS would block it on every student's Mac: "
                 "notarize it first (scripts/notarize_app.py).")
    shutil.rmtree(PUBLISH, ignore_errors=True)
    PUBLISH.mkdir()
    dmg = PUBLISH / f"WorkIt-Auto-Apply-{number}.dmg"  # one name per build: an app may be downloading the last one
    shutil.copyfile(build.DMG, dmg)
    # The key goes in on stdin ("-"), never in a file or the command line. -p prints the signature alone.
    try:
        signature = subprocess.run([SIGN_UPDATE, "--ed-key-file", "-", "-p", dmg], input=key, check=True,
                                   capture_output=True, text=True).stdout.strip()
    except subprocess.CalledProcessError:
        # Never print what sign_update said: its error repeats the key it was given, into the run's log.
        sys.exit("sign_update couldn't read SPARKLE_PRIVATE_KEY: it must be the one line of base64 that "
                 "generate_keys -x wrote (docs/secrets.md, workit-prod/auto-apply-desktop).")
    try:
        build.venv_python(VERIFY, plist["SUPublicEDKey"], signature, dmg)
    except subprocess.CalledProcessError:
        sys.exit("SPARKLE_PRIVATE_KEY isn't the app's update key: every app would download this update and refuse "
                 "it. Put the team's key back in Infisical (docs/secrets.md); never make a new one.")
    url, length = f"{build.FEED.rsplit('/', 1)[0]}/{dmg.name}", str(dmg.stat().st_size)
    feed = PUBLISH / "appcast.xml"
    feed.write_text(APPCAST.format(name=build.NAME, shown=shown, number=number, date=formatdate(usegmt=True),
                                   signature=signature, length=length, minimum=plist["LSMinimumSystemVersion"],
                                   url=url))
    # Read back as Sparkle reads it: with a feed it can't read (a "&" in new text), every app's check fails with no
    # message, while the run passes.
    try:
        [item] = ET.parse(feed).getroot().findall("channel/item")
        enclosure = item.find("enclosure")
        offered = (item.findtext(f"{SPARKLE}version"), enclosure.get("url"), enclosure.get(f"{SPARKLE}edSignature"),
                   enclosure.get("length"))
    except (ET.ParseError, ValueError, AttributeError) as error:
        sys.exit(f"appcast.xml isn't a feed Sparkle can read ({error}): fix APPCAST in scripts/publish_app.py.")
    if offered != (number, url, signature, length):
        sys.exit(f"appcast.xml doesn't offer this build: {offered}. Fix APPCAST in scripts/publish_app.py.")
    print(f"Signed build {number} ({shown}) for Sparkle: {PUBLISH}")


if __name__ == "__main__":
    main()
