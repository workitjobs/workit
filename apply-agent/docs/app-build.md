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
| `python3 scripts/build_app.py --release` | A build for students, from the current commit's files only, with complete notices and no ccache | 6 to 7 minutes, as a cold test build (it compiles every C file) |

Both write `build/out/WorkIt Auto Apply.app` (about 223 MB) and
`build/out/WorkIt Auto Apply.dmg` (about 80 MB), and replace the last ones.
`build/` is git-ignored. Each app names its commit in `Info.plist`
(`WorkItCommit`; `+changes` on a test build of a changed working tree):
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
  app when it runs. `sample/` is read by `student.app` (the Test Person
  copy, until W11 brings the student's profile from WorkIt), and
  `worker-extension/` by the Worker setup (until W6 uses the Chrome Web
  Store copy).
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

## Still open

- Step 2: Developer ID signing with the hardened runtime and the
  entitlements for Node (JIT) and Apple events, then notarizing the app
  and the DMG.
- Step 3: Sparkle, its EdDSA key, and the feed on R2.
- Step 4: the DMG's upload and `DOWNLOAD_URL`, after W0, W6 and W7.
- `sample/` leaves `INPUTS` with W11; `worker-extension/` with W6.
- CDP Workers' Chrome is started by Playwright inside the app, so macOS may
  blame the app for Chrome's updater ("prevented from modifying apps")
  during a run on a host outside `plain_worker_hosts`.
- The app doesn't yet check that it runs from Applications; Sparkle can't
  update a copy that macOS runs from a translocated, read-only folder.
