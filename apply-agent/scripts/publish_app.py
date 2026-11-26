"""Hand a release of WorkIt Auto Apply to the workflow that publishes it (KAN-941, W8 step 4 of
../docs/desktop_application_auto_apply.md).

    python3 scripts/publish_app.py      (from apply-agent/, after python3 scripts/build_app.py --release)

It signs build/out's DMG with the update key in this Mac's Keychain (Sparkle's sign_update), writes the feed that
offers it to every installed app (appcast.xml, one item: the newest build), and puts both on a draft GitHub Release,
auto-apply-<build number>. No student gets anything yet: ../.github/workflows/publish-app.yml copies the two to R2,
the DMG first, when it runs from main with that build number. It refuses a test build, a build whose commit isn't on
main, and a Keychain key that isn't the app's: every app would download that update and refuse it.
"""

import plistlib
import re
import shutil
import subprocess
import sys
from email.utils import formatdate

import build_app as build  # the app's paths and settings, kept in one place

PUBLISH = build.OUT / "publish"
TOOLS = build.SPARKLE / "bin"
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
      <enclosure url="{url}" type="application/octet-stream" {signature} />
    </item>
  </channel>
</rss>
"""


def output(*command: object) -> str:
    return subprocess.run([str(part) for part in command], check=True, capture_output=True, text=True).stdout.strip()


def main() -> None:
    if not build.DMG.is_file():
        sys.exit(f"Build a release first: python3 scripts/build_app.py --release (there is no {build.DMG}).")
    plist = plistlib.loads((build.APP / "Contents" / "Info.plist").read_bytes())
    number, shown, commit = plist["CFBundleVersion"], plist["CFBundleShortVersionString"], plist[build.COMMIT_KEY]
    if not plist.get(build.RELEASE_KEY):
        sys.exit("That's a test build: publish only a release (python3 scripts/build_app.py --release).")
    # Only the public half: sign_update reads the private half from the Keychain itself, below.
    keychain = subprocess.run([TOOLS / "generate_keys", "-p"], capture_output=True, text=True, check=False)
    if keychain.returncode or keychain.stdout.strip() != plist["SUPublicEDKey"]:
        sys.exit("This computer's Keychain has no update key, or another one than the app's, which every app would "
                 "refuse. Import the team's key from Infisical (docs/app-build.md, Publish a release).")
    build.git("fetch", "--quiet", "origin", "main")
    if subprocess.run(["git", "-C", str(build.ROOT), "merge-base", "--is-ancestor", commit, "origin/main"],
                      check=False).returncode:
        sys.exit(f"Commit {commit[:12]} isn't on main: merge it first, so students get only reviewed code.")
    shutil.rmtree(PUBLISH, ignore_errors=True)
    PUBLISH.mkdir()
    dmg = PUBLISH / f"WorkIt-Auto-Apply-{number}.dmg"  # one name per build: an app may be downloading the last one
    shutil.copyfile(build.DMG, dmg)
    # sign_update reads the private key from this user's login Keychain: this script never sees it.
    signature = output(TOOLS / "sign_update", dmg)  # the enclosure's sparkle:edSignature and length
    if not re.fullmatch(r'sparkle:edSignature="[A-Za-z0-9+/]+=*" length="\d+"', signature):
        sys.exit(f"sign_update printed no signature: {signature}")
    appcast = PUBLISH / "appcast.xml"
    appcast.write_text(APPCAST.format(name=build.NAME, shown=shown, number=number, date=formatdate(usegmt=True),
                                      minimum=plist["LSMinimumSystemVersion"], signature=signature,
                                      url=f"{build.FEED.rsplit('/', 1)[0]}/{dmg.name}"))
    tag = f"auto-apply-{number}"
    build.run(["gh", "release", "create", tag, "--draft", "--target", commit, "--title",
               f"{build.NAME} {shown} ({number})", "--notes",
               f"Built from {commit}. Publish it: gh workflow run publish-app.yml --ref main -f build={number}",
               dmg, appcast])
    print(f"Draft release {tag} is ready, and no student has it yet. To publish it to every app and the website:\n"
          f"  gh workflow run publish-app.yml --ref main -f build={number}")


if __name__ == "__main__":
    main()
