# Building and testing WorkIt Auto Apply

How to build the app, change what goes into it, and test the built app on a
Mac (KAN-833, W8 of `../../docs/desktop_application_auto_apply.md`). The
rules and their reasons are in `../CLAUDE.md`, "Building the app".

## Build

From `apply-agent/`, on an Apple Silicon Mac with Xcode's Command Line Tools
and uv:

| Command | What it builds | Time |
|---|---|---|
| `python3 scripts/build_app.py` | A test build from the working tree, uncommitted changes too | About 1.5 minutes with a warm compile cache, 6 to 7 from cold |
| `python3 scripts/build_app.py --release` | A build for students, from the current commit's files only, with complete notices and no ccache. It refuses to start while `scripts/build_app.py` has uncommitted changes | 6 to 7 minutes, as a cold test build (it compiles every C file) |

Both write `build/out/WorkIt Auto Apply.app` (about 223 MB) and
`build/out/WorkIt Auto Apply.dmg` (about 80 MB), and replace the last ones.
`build/` is git-ignored. Each app names its commit in `Info.plist`
(`WorkItCommit`; `+changes` on a test build of a changed working tree) and
whether it is a release (`WorkItRelease`):
`plutil -p "build/out/WorkIt Auto Apply.app/Contents/Info.plist"`.

A failed check stops the build with one sentence that says what to fix.
Nuitka's report, `build/out/report.xml`, lists every module it compiled and
why.

## What goes into the app, and how to change it

Three lists decide what the app holds. Change only these:

| To | Change | Then |
|---|---|---|
| Ship, or stop shipping, a file or folder that the app reads beside its program (`home.CODE`) | `INPUTS` in `scripts/build_app.py` | Launch the built app (below). |
| Keep out a file that would come in by itself: Apply's package data (any non-Python file in `src/apply`) or a library's data | `LEAVE_OUT` in `scripts/build_app.py` | The build refuses an app that still holds it. |
| Keep a Python module out of the compile | `DEVELOPER` in `src/apply/build.py` | `tests/test_student_build.py` fails while the Student path still imports it. |

- **A module is compiled only when the Student path imports it**, from
  `scripts/app_entry.py`. A module nothing imports stays out with no list.
- **A non-Python file in `src/apply` ships by itself**, as package data. A
  file outside `src/apply` ships only through `INPUTS`.
- **Remove a file from `INPUTS` only after the code stops reading it.** The
  build doesn't check what the code reads: a missing input crashes the built
  app when it runs. `worker-extension/` is read by the Worker setup (until
  W6 uses the Chrome Web Store copy). `sample/` left the app on
  2026-11-24, ahead of the code: until W11 stops `student.app` from
  copying it, a built app whose data folder has no Applicant profile stops
  at launch.
- **A release sees only committed files.** Commit a change before a
  `--release` build.
- A new rule about what ships goes in `../CLAUDE.md`, "Building the app", in
  the same change.

## Launch and test the built app

`open "build/out/WorkIt Auto Apply.app"` starts it as a student starts it:
the compiled Student build, with no uv, Python or source code. After a code
change, build again before you test: `uv run apply app` runs the checkout's
source instead, with `STUDENT = False` and the data folder `~/.config/apply`.

- **Its data folder** is `~/Library/Application Support/WorkIt Auto Apply`.
  For a first run from the start, quit the app and move that folder aside.
  Never read the files in it raw (`../CLAUDE.md`, "The data folder").
- **Its WorkIt session** is the Keychain item `apply-workit`, which a
  checkout uses too. Signing out in one signs out the other. The first time,
  macOS may ask whether the app may use the item: Always Allow.
- **First run** asks, one step at a time: Google Chrome, the disclosure and
  license, Screen Recording, then the Worker setup (`docs/apply-window.md`).
  - Screen Recording: with today's ad-hoc signature, macOS forgets the
    permission after each build. Turn it on again in System Settings and
    reopen the app; remove an old entry with "-" first.
  - Worker setup: Chrome opens a new tab (Chrome 157 opens no `chrome://`
    page from its command line). Paste `chrome://extensions` from the
    clipboard into the address bar, turn on Developer mode, then Load
    unpacked the folder the app puts on the clipboard. It ends when a real
    Worker says hello through the app's relay.
- **Sign-in:** Settings, Sign Out, then Sign In with WorkIt. The browser
  asks to open WorkIt Auto Apply; the app comes to the front, signed in. A
  checkout's sign-in helper also claims `workit-auto-apply://`. If the link
  goes to it, unregister it (`lsregister -u ~/.config/apply/"WorkIt Auto
  Apply Sign-In.app"`, the full `lsregister` path is in
  `src/apply/sign_in_link.py`); a checkout's next sign-in registers it
  again. `lsregister -dump URLSchemeBinding | grep workit-auto-apply`
  names the app that gets the link.
- **To see what it prints**, start its program directly instead of with
  `open`: `"build/out/WorkIt Auto Apply.app/Contents/MacOS/WorkIt Auto
  Apply"`. `APPLY_HOME=<folder>` gives it another data folder, never under
  a temp folder for a run (`home.temp_state`).
- **A Chrome the app started and left behind** (the setup's, a Worker's):
  stop it with `kill -TERM <pid>`, never `-KILL`, which loses its profile's
  last changes. Kill only processes you started.
- **The DMG:** `open "build/out/WorkIt Auto Apply.dmg"` shows the app, an
  Applications link, `License.txt` and `Third-Party Notices.txt`. Until
  step 2 signs it with a Developer ID, another Mac blocks the downloaded
  app: there, `xattr -dr com.apple.quarantine "/Applications/WorkIt Auto
  Apply.app"` lets it open for a test.

## Publish a release

Every installed app takes a published build at its next check (at launch
and each day) and installs it when the student quits, with no question. So
publish only a release that you launched and tested.

1. On the `main` commit to release, after a pull: `python3
   scripts/build_app.py --release`. Launch it and test it (above).
2. `python3 scripts/publish_app.py`. It signs the DMG with the update key
   in your Keychain (macOS may ask whether `sign_update` may use it:
   Always Allow), writes `build/out/publish/appcast.xml`, and makes the
   draft release `auto-apply-<build number>` with `gh`. No student gets
   anything yet.
3. Run the command it prints: `gh workflow run publish-app.yml --ref main
   -f build=<build number>`. The run copies the DMG and the feed to
   https://downloads.workitjobs.ai and reads them back from there
   (`../../.github/CLAUDE.md`, Publish WorkIt Auto Apply).

**The update key** is in the login Keychain of the Mac that made it
(2026-11-26); its backup is `SPARKLE_PRIVATE_KEY` in Infisical's
`workit-prod/auto-apply-desktop-private-keys` (`../../docs/secrets.md`). To publish from
another Mac, save the backup to a file, run
`build/sparkle-2.10.1/bin/generate_keys -f <file>`, and delete the file.
`generate_keys -p` prints the Keychain key's public half, which must be
`SPARKLE_PUBLIC_KEY`. Never make a new key: every installed app refuses an
update another key signs, so its students would stay on their build for
good.

## Test an update

Sparkle can be tested on one Mac before the real key and feed exist, with a
throwaway key and a local feed. Never commit any of it, and delete the test
build afterwards: it allows plain HTTP.

1. Make a throwaway Ed25519 key with Python's `cryptography`: write the
   private key's 32 raw bytes, base64, to a file, and keep the public key's
   32 bytes, base64. `build/sparkle-2.10.1/bin/sign_update --ed-key-file
   <file>` takes that file; it never touches the Keychain.
2. Build through a small driver that imports `scripts/build_app.py`, sets
   `SPARKLE_PUBLIC_KEY` to the throwaway public key and `FEED` to
   `http://127.0.0.1:8765/appcast.xml`, adds
   `NSAppTransportSecurity: {NSAllowsArbitraryLoads: true}` to the
   Info.plist it writes (macOS refuses plain HTTP without it), and calls
   `main()`. Copy that app aside: it is version N.
3. Build again a minute later (`CFBundleVersion` is the minute): version
   N+1. Sign its DMG (`sign_update --ed-key-file <file> <dmg>` prints the
   enclosure's `sparkle:edSignature` and `length`), write an
   `appcast.xml` with one `<item>` for it, and serve the folder with
   `python3 -m http.server 8765 --bind 127.0.0.1`.
4. So that N checks at once instead of in a day: `defaults write
   ai.workitjobs.autoapply SUHasLaunchedBefore -bool true` and `defaults
   write ai.workitjobs.autoapply SULastCheckTime -date "2020-01-01 00:00:00
   +0000"`. Start N with `APPLY_HOME` set to a data folder that has a
   profile. Within 30 s it fetches the feed and the DMG. Quit it
   (`kill -TERM`): N+1 replaces it in place.
5. To see a refusal, offer a higher version signed with another key: it is
   downloaded and never installed.
6. Clean up: stop the server, delete every `SU*` key from the
   `ai.workitjobs.autoapply` defaults, and delete the test app and DMG.

## Still open

- Step 2: Developer ID signing with the hardened runtime and the
  entitlements for Node (JIT) and Apple events, then notarizing the app
  and the DMG.
- Step 3: a beta channel for testers is not built. Sparkle and the update
  key are in every build (2026-11-26).
- Step 4: publishing (above) waits on Infisical's `/auto-apply-desktop`
  sync (`../../docs/secrets.md`, Still open), and nothing is published
  yet. The website's `DOWNLOAD_URL`
  (`frontend/src/app/(seeker)/auto-apply-desktop/page.tsx`) stays null
  until step 2, since until then the DMG opens on no other Mac; then it is
  `https://downloads.workitjobs.ai/WorkIt-Auto-Apply.dmg`.
- `worker-extension/` leaves `INPUTS` with W6.
- W11: `student.app` still copies the Test Person sample, which the app no
  longer ships, into a data folder with no Applicant profile, so such a
  first launch stops until the student's profile comes from WorkIt.
- CDP Workers' Chrome is started by Playwright inside the app, so macOS may
  blame the app for Chrome's updater ("prevented from modifying apps")
  during a run on a host outside `plain_worker_hosts`.
- The app doesn't yet check that it runs from Applications; Sparkle can't
  update a copy that macOS runs from a translocated, read-only folder.
