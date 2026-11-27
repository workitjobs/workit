# WorkIt Auto Apply on Windows

**Status (KAN-929):** being built. P1 to P5, P7 to P9 and P11 to P13 are
built and tested on the Mac. Nothing has run on Windows yet: section 7's
check list is next. This note takes F4 and W4's "Found on the way" list
(`desktop_application_auto_apply.md`) one problem at a time. Paths
without a folder are under `apply-agent/src/apply/`.

## 1. Goals

- **A Windows developer** runs Apply from a checkout (`uv run apply ...`)
  and runs its tests.
- **A Windows user** downloads WorkIt Auto Apply and runs it.

Every problem that stops a developer also stops a user, so the developer
goal comes first. The user goal adds the seed in Google Chrome and a
Windows package. These already work on Windows (W4, KAN-850): the Chrome
finder, showing a folder, the clipboard, the keychain (Credential
Manager), a Worker's background start, and the window's build (KAN-867).

## 2. How a plain Worker works

```
Apply process: the Bridge (plain/bridge.py)
   |  the channel (plain/channel.py, P4)
   v
the host (plain/host.py): a relay that Chrome starts, one per Worker (P5)
   |  native messaging: Chrome joins the extension to the host's stdin and stdout
   v
the Worker extension, in Worker k's Chrome, on profile APPLY_PROFILES/plain-<k>
```

- **A Worker** is one Chrome process on its own profile. Apply starts it
  (`PlainWorkers.launch`) and stops it by its PID. One to three Workers
  (D24).
- **The host file** is the native messaging manifest that tells Chrome
  which program is the host. Today `PlainWorkers.install_host` writes it,
  with a `#!/bin/sh` wrapper, into each Worker profile's
  `NativeMessagingHosts/`.
- **CDP Workers** (`browsers.WorkerBrowsers`) need no extension, host or
  seed. Lever, SmartRecruiters and Workable block them, so
  `worker_mode: protected` sends those hosts to plain Workers.

### How Apply knows its processes

The OS gives a dead process's PID to a new process. So Apply keeps each
PID with proof of which process it is, or keeps the live process object.

| What | Kept where | The proof |
|---|---|---|
| The Workers this Apply started | Memory: `PlainWorkers.running` and `_starting` | The `Popen`, or on the Mac `launcher.Chrome`'s `psutil.Process` |
| A Worker that outlived its Apply | `apply-owner.json` in its profile (`launcher.own`, KAN-885) | Apply's PID and start time (`_owner_alive`) |
| The Chrome that has a profile open | `browsers.chrome_pid` (P3) | A browser whose `--user-data-dir` is the profile |
| The open Apply windows | `APPLY_PROFILES/windows/` (`into.windows`) | `psutil.pid_exists` |

Apply stops a process only through an object that remembers it (`Popen`,
`psutil.Process`): psutil refuses to signal a reused PID. P7 is how to
stop a Chrome cleanly on Windows.

## 3. Why Workers copy a WorkIt-only seed

Decided (2026-11-21): each Worker has its own profile, a copy of the
seed. The seed (`APPLY_PROFILES/plain-seed`) is a WorkIt-only profile in
which the student adds the Worker extension once (`apply plain seed`).
Apply never uses or copies the student's own profile:

- Apply must start the Chrome process itself. Its switches
  (`launcher.FLAGS`) work only at start, and a profile is open in one
  Chrome at a time. Workers run side by side, so each needs its own.
- Google Chrome ignores `--load-extension`, and Chrome 136 and later
  ignore the debugging port on the default profile.
- A copy of the student's profile has no Worker extension either. It
  needs the same Windows fixes (P3 to P5). It also brings Chrome Sync,
  every sign-in, the student's own extensions (which change form
  fields), gigabytes for each copy, and cookies whose key may not move
  with the copy.
- "Sign in with Google" gives an app a token, not a browser profile. The
  student signs in to Google once in the seed, and each copy has it.

The first design filled in the student's everyday Chrome, and the team
dropped it (`apply-agent/docs/research/everyday-chrome-fill-design.md`).
Chrome for Testing (`plain_chrome: testing`) needs no seed, and the store
copy (W6) makes the seed one "Add to Chrome". The profiles are in
`home.APP_FOLDER/profiles/`: on Windows
`%LOCALAPPDATA%\WorkIt Auto Apply\profiles\`, the local AppData, as
Chrome's own. Remove All My Data deletes them.

## 4. The problems

Each problem that is not built says what breaks, whom it stops, the fix,
and when it is done. Section 5 gives each fix's kind, section 6 its
test, and section 7 the order.

### P1. File locks: built

`import fcntl` stopped every command on Windows. Every lock goes through
`apply.locks` (`held`, `tried`) now, on portalocker. Its docstring has the
rules. What the code doesn't say:

- **portalocker, not filelock:** filelock opens its lock file with
  `O_TRUNC`, which empties it. portalocker uses `fcntl.flock` on macOS and
  Linux, so the Mac's locks act as before.
- **Every lock is exclusive:** portalocker has no shared lock on Windows
  without pywin32. On Windows a lock also blocks reads of the locked
  file, so the Answer bank locks `answer-bank.lock`, not its YAML.
- **A wait on Windows gives up after about 10 s,** and `held` tries again.
- **Two jobs in one folder need two lock files:** a second lock on a file
  that this process holds waits for good. So the Repair's one-at-a-time
  lock is `repairs/.running.lock` (`repairer.RUNNING`).
- **Unix-only calls that are left** fail only when they run: in a
  developer-only module, `os.getuid()` in `schedule.Launchctl` (the Mac's
  scheduled runs, which D10 drops). `claude_cli.stream_claude`
  (`ask_model: claude`) stopped claude with `os.killpg`, which raised on
  each stop on Windows: `claude_cli.kill_tree` kills the tree through
  psutil there (2026-11-27).

### P2. "Is it still running?": built

On Windows `os.kill(pid, 0)` is no check: signal 0 is `CTRL_C_EVENT`, and
any other signal ends the process. Every check is `psutil.pid_exists`
now. On macOS and Linux it calls `os.kill(pid, 0)` itself, and another
user's process counts as running. So "it runs" never proves "it is
Apply's": `chrome_pid` checks the arguments (P3), and `_owner_alive` the
start time.

### P3. Which Chrome has a profile open: built

Chrome writes `SingletonLock`, which holds the PID, on macOS and Linux
only. Windows' `lockfile` holds no PID. `browsers.chrome_pid(profile,
system)` has an entry for each OS, and both end in one check
(`_browser_on`): a browser (no `--type=`) whose `--user-data-dir` is the
profile. On Windows it scans every process's arguments, with no filter
by program name: the check proves the Chrome, and the tests' stand-in
browser is a Python process. The scan takes 8–16 ms over 600 processes
on a Mac. Apply asks a few times for each Worker start, and once a second
during the seed's setup.

**Still open (Windows):** does the browser process carry
`--user-data-dir` as Apply starts it, and how long does the scan take?

### P4. The channel between Apply and the hosts: built

Python on Windows has no `AF_UNIX` and no `os.getuid`. `plain/channel.py`
is the one channel for the Bridge, the host, `tools.py` and `mcp.py`: a
Unix socket on macOS and Linux, a named pipe on Windows, and on every OS
a check in both directions before any message. Its docstring has the
design, and `apply-agent/docs/plain-workers/PROTOCOL.md` has the wire
format.

- **Decided (2026-11-24): a named pipe, not a port.** Every program on
  the computer, and every web page in a browser on it, can send to a
  local port: Zoom's local server let web pages start calls until 2019.
  Chrome and VS Code use named pipes on Windows. `multiprocessing
  .connection` makes and opens the pipe, so no `pywin32`.
- **Two Windows traps, read in Python's source:** a close stops a blocked
  pipe read only with `RuntimeError("shouldn't get here")`, so `Messages`
  counts every failed read as closed. And a blocked `accept` never wakes
  when the listener closes. So `close` connects once to wake it, and
  waits till it gave its pipe back: else the same process can't make
  that pipe again (`Busy`).
- **The security review (2026-11-26)** found no way past the check. Below
  its bar: Python opens the pipe with no limit on impersonation, and lets
  remote clients connect, with read access only.
- **Still open (Windows):** a close cancels a blocked read, the wake
  frees a real pipe's accept, and a second Apply gets `BridgeBusy`.

**After a pull of P1 or P4, restart every running Apply.** An old Apply
locks `answer-bank.yaml` and a new one `answer-bank.lock`. And an old
Bridge sends no challenge, so a new host waits 5 s and gives up.

### P5. The host file (native messaging manifest and wrapper): built

- **What broke.** Chrome on Windows finds a host only through the
  registry (Chromium's `launch_context_win.cc`, read 2026-11-26): the
  default value of
  `HKEY_CURRENT_USER\Software\Google\Chrome\NativeMessagingHosts\<name>`
  (then `HKLM`) is the manifest's path (`chrome_host.KEY`). Every build
  reads this key, Chrome for Testing too. And Windows can't run a
  `#!/bin/sh` wrapper.
- **Who.** Both, for plain Workers. A developer, for the accounts host.
- **Built: the host finds its Worker from its Chrome, on every OS.** The
  key is one per Windows user, so one wrapper serves every Worker and
  every profiles folder, and can name neither a Worker nor a channel.
  - The host takes the nearest browser above it (`host.browser_of`):
    Chrome starts a `.bat` host through `cmd.exe /d /s /c`, so its parent
    is no Chrome. That browser's `--user-data-dir`, `plain-<k>`, gives
    the Worker, and the folder above it the channel
    (`channel.socket_path`).
  - So a Bridge listens only there: `PlainWorkers` takes no Bridge of its
    own. The long-path fallback is always `/tmp`, never `$TMPDIR`: the
    host runs in its Chrome's environment, launchd's on the Mac.
  - The host imports psutil (decided 2026-11-26): the standard library
    can't read another process's arguments on Windows.
  - The tile takes the same browser (`window_capture.chrome_of`), for its
    check that a connection is its Worker's own (`tile._foreign_to`).
- **Built: the key and a `.bat` for the Workers' host** (`chrome_host`).
  - The manifest and the `.bat` go in one fixed folder,
    `APP_FOLDER/native-hosts`, never a profile: a key that named a test's
    temporary folder would name a deleted file once that test ended.
  - The `.bat` starts with `@echo off`, or cmd.exe writes the command into
    Chrome's pipe. Each part is quoted with each `%` doubled, then `%*`
    passes on Chrome's arguments. It is UTF-8, and its `chcp 65001 >nul`
    makes cmd.exe read it so: the OEM code page (437 on US Windows) can't
    hold a path such as `C:\Users\Łukasz`, and every Worker's start failed
    (found in review, 2026-11-26).
  - A file is written only when its text changes: on Windows a file that
    Chrome or cmd.exe has open can't be replaced.
  - The student's everyday Chrome sees the key too. That is safe: only
    the Worker extension may call the host (`allowed_origins`), and the
    host connects only from a `plain-<k>` profile. The seed's extension
    tries every 2 s, so during the seed's setup a host starts and exits
    every 2 s.
  - A checkout and the installed app on one Windows user share the key:
    the last one that starts a Worker owns it. Either one's host serves
    the other's Workers while their channel code is the same.
  - The package can use its own `.exe`, which starts through cmd.exe
    too, unless the `NativeHostsExecutablesLaunchDirectly` policy is on.
- **Built: the accounts host** (`native_host.install`, `apply
  chrome-passwords`) takes the same key and `.bat`, whose `set` line
  gives the host its data folder (`APPLY_HOME`). `doctor` reads the
  manifest that the key names (`chrome_host.found`), and its test of
  that runs on the Mac and in CI (`Machine.system`).
- **Still open (Windows):** Chrome runs the `.bat` and the host says
  hello; a venv's `python.exe`, a launcher, finds psutil under `-I`;
  `chcp 65001` in the hidden cmd.exe that Chrome starts, with a user
  folder such as `C:\Users\Łukasz`.
- **Done when.** A plain Worker on Chrome for Testing says hello on
  Windows.

### P6. A Worker with no window at start (`--no-startup-window`)

- **What it is.** A Worker's Chrome starts with no window, so it takes no
  focus. The extension opens the window, unfocused, after its hello.
- **What breaks.** Not checked on Windows. On Linux, such a Chrome quits
  at once (`apply-agent/docs/research/held-forms-after-a-crash.md`).
- **Fix.** Measure first, once P4 and P5 work. If Chrome quits, start it
  with a window and let the OS keep that window behind.
- **Done when.** It is measured, and the result is written here.

### P7. Stopping a Chrome cleanly: built from the Mac

- **What broke.** Apply stopped a Chrome with SIGTERM, then SIGKILL after
  10 s. SIGTERM lets Chrome save. On Windows, SIGTERM, `Popen.terminate()`
  and psutil's `terminate` all end the process at once, with no save. A
  Worker lost the session cookies that `--restore-last-session` keeps, so
  its job-site sign-ins went (KAN-718). The seed lost Developer mode and
  Load unpacked.
- **Built.** `launcher.ask_to_quit` is the one ask, for a Worker
  (`_stop`, `reclaim`) and the seed (`Desk.terminate`): SIGTERM on macOS
  and Linux, and on Windows `taskkill /PID <pid>` with no `/F`, which asks
  the windows to close, as a click on X does (with `CREATE_NO_WINDOW`:
  from the app, a console program would flash a console). A Worker that is still up
  after `STOP_WAIT` is killed, as before. The seed is never killed: the
  wizard says what to close, and waits.
- **Still open (Windows):** Chrome saves on that close, and a Worker with
  no window (P6) has nothing to close, so it waits 10 s and is killed.
- **Done when.** On Windows, a setting changed in the seed's Chrome is on
  disk after that Chrome stops.

### P8. The seed wizard on Windows: built from the Mac

- **What it is.** `apply plain seed`, and the app's first-run Seed step,
  which runs the same wizard (`first_run.seed`).
- **What broke.** P5 and P7, and its words were the Mac's: "Finder",
  "Cmd+Shift+G", "Cmd+V", "Return" and "Cmd+Q".
- **Who.** The user. A developer skips the seed (P9).
- **Built.** `seed_setup.WORDS` has each OS's file manager and keys, which
  `instruction` and the `Wizard` pick by `system`. On Windows: File
  Explorer; in the folder picker Ctrl+L, Ctrl+V, Enter, then Select
  Folder; and to quit, Exit in Chrome's three-dot menu.
- **Still open (Windows):** the folder picker takes those keys, and a
  folder dragged from File Explorer loads.
- **Done when.** `uv run apply plain seed` ends with "Setup is done" on
  Windows.

### P9. The developer's way past the seed: built

`plain_chrome: testing` (or `APPLY_PLAIN_CHROME=testing`,
`launcher.chrome_kind`) runs plain Workers on Chrome for Testing, with no
seed. The app window's first run asked for the seed anyway, so
`uv run apply app` stayed on the Seed step. Now `first_run.seed_problem`
reads `chrome_kind()`, and the Seed step comes only for Google Chrome
(PR #676, 2026-11-26).

- **The Student build keeps Google Chrome (D21):** it reads no
  `policies.yaml`, and `policies.default.yaml` says `plain_chrome:
  chrome`. Only `APPLY_PLAIN_CHROME` changes it.
- **First run's first step still looks for Google Chrome**
  (`chrome_finder.find`), with Chrome for Testing too.
- **Still open (Windows):** `uv run apply app` with `plain_chrome:
  testing` gets past first run with no seed.

### P10. The Windows package

What a user downloads. Today it is a notarized Mac DMG with Sparkle
updates (D17), for Apple Silicon only (D18). Windows needs a Nuitka build
(W8), a code-signing certificate so that SmartScreen doesn't warn, an
installer, updates (WinSparkle or similar), pywebview on WebView2, and
decisions beside D17 and D18.

### P11. Smaller gaps

- **Keep awake: built from the Mac.** Windows could sleep during a run.
  `awake.awake` now calls `SetThreadExecutionState` through `ctypes`
  (system and display on), and sets it back when the run ends. Windows
  clears it when the thread ends, so a crash can't leave it on. No
  `wakepy`: it would be a library for one call. **Still open
  (Windows):** the screen stays on through a long run.
- **Notices: built from the Mac.** `apply run` and the Repairer sent
  each notice to Notification Center through `osascript`, on every OS, so
  on Windows the first notice stopped the run. Off the Mac a notice now
  goes to the terminal (`notify.desktop`, `TerminalNotifier`). A Windows
  toast needs a library: later, if a developer misses it.
- **Not ported, developer-only:** the Repairer (`apply repair`, after a
  run with `repair.max_per_day`) starts `npm` by its bare name, which is
  `npm.cmd` on Windows: `subprocess` finds only an `.exe` so. `claude`
  from npm is `claude.cmd` too; the native installer's `claude.exe` works.
- **Smooth tiles.** The Swift capture helper is the Mac's. Elsewhere a
  tile shows about 2 frames a second until `Page.startScreencast` (W6).
- **Focus.** Off the Mac, the extension's `windows.focus` brings a Worker
  forward. Check that Windows keeps Workers behind the student's apps
  (F4's "Test early").

### P12. A developer's Apply window: built from the Mac

- **What broke.** Every `apply rehearse` and `apply run` opens its Apply
  window (`dashboard.open_window`) with the Dock app and `open -na`,
  finds it with `pgrep`, and raises it with AppleScript. Windows has none
  of them, so each run stopped at its start, and each window's close too.
  Found on the way (2026-11-27): M1 needed it.
- **Built.** Off the Mac the window is Google Chrome itself
  (`_open_elsewhere`), started with `--app` on the window's own profile
  through `launcher.start_in_background`, and found by that profile
  (`browsers.chrome_pid`, then its `--app`). It quits through
  `ask_to_quit`. With no Chrome, the run goes on and prints the address.
  A tile's Show in Finder goes through `seed_setup.reveal`.
- **Still open.** Off the Mac nothing raises the window: `raise_window`
  says False. The button still says "Show in Finder". **Windows:** the
  window opens behind the student's work, and closes when its run ends.

### P13. Text in the OS's encoding: built from the Mac

- **What broke.** 177 text reads and writes named no encoding
  (`read_text`, `write_text`, `open`, and a command's output with
  `text=True`), so they used the OS's own: UTF-8 on a Mac, the code page
  on Windows (cp1252 on US Windows). A UTF-8 file with "Łukasz" in it
  failed to read there, and an answer with "→" failed to write. Chrome's
  Preferences, the profile, the Answer bank and the Fill engine are UTF-8.
  Found on the way (2026-11-27).
- **Built.** Each one names `encoding="utf-8"`, and
  `tests/test_each_os.py` fails on a new one in `src/apply`.
- **Built: the output too.** A pipe or a file takes the code page as
  well, so `apply rehearse ... > run.log` stopped at its first "→".
  `cli.main` makes stdout and stderr UTF-8 on Windows
  (`cli.utf8_streams`). The console is UTF-8 already.
- **Tests on Windows run with `PYTHONUTF8=1`:** the tests' own reads and
  writes name no encoding. The source test covers Apply's.

## 5. Kind of fix

`apply-agent/CLAUDE.md` ("Code that differs by OS") has the rules: a
library first, else one entry for each OS in one function. Two more:
Apply's code has no Windows-only file (only the package's scripts are),
and a Windows-only module (`winreg`, `msvcrt`) is imported inside its
Windows entry, since the Mac has none.

| Problem | Kind of fix |
|---|---|
| P1 to P5, P9 | Built (above) |
| P6 no startup window | Measure first. A Windows entry only if Chrome quits |
| P7 clean quit | Built: `taskkill` with no `/F` in `ask_to_quit`'s Windows entry |
| P8 wizard words | Built: a Windows text in the same function |
| P10 package | Windows-only build, installer and signing scripts, outside Apply's code |
| P11 keep awake | Built: a Windows entry in `awake.awake` |
| P12 Apply window | Built: one entry for the Mac and one for the rest, in each window function |
| P13 encoding | Built: the same code on every OS |

## 6. Tests

Each test names the one fault that it alone turns red (`apply-agent/
CLAUDE.md`, "Every test earns its place"). The built fixes' tests are in
`tests/test_each_os.py`, `tests/test_locks.py` and
`tests/test_plain_channel.py`, all in the fast list.

| Problem | Test, new or extended | The fault it turns red |
|---|---|---|
| P5 | Built: `tests/test_plain_bridge.py`, the real host under a fake Chrome (`tests/fake_chrome.py`), with a process between them as cmd.exe | A host speaks for the wrong Worker or channel |
| P5 | Built: `tests/test_each_os.py`, the tile's `chrome_of` under the same fake | The tile takes cmd.exe for a Worker's Chrome |
| P5 | Built: `tests/test_each_os.py`, with a fake `winreg`: the key names the manifest, the `.bat` passes Chrome's arguments and echoes nothing, and only the Worker extension may call the host | Chrome on Windows finds no host, or the host gets a broken port |
| P5 | Built: `tests/test_each_os.py`, the accounts host's key, `.bat` and `chrome_host.found` | The accounts host can't start on Windows, or reads another data folder |
| P7 | Built: `tests/test_plain_seed_setup.py`, the seed's Chrome is asked with `taskkill` and no `/F`, never killed; `tests/test_each_os.py`, a Worker is asked first and killed only after `STOP_WAIT`, and a reused PID is never asked | A forced stop loses the student's clicks and the Workers' sign-ins |
| P8 | Built: `tests/test_plain_seed_setup.py`, every line the wizard says on Windows | A Windows user is told Finder and Cmd keys |
| P12 | Built: `tests/test_each_os.py`, the window on Windows opens, is found by its profile, isn't opened twice, and an older one is asked to close | A developer's run on Windows stops at its start |
| P13 | Built: `tests/test_each_os.py` reads the source | A text read or write in Windows' code page |
| P9 | Built: `tests/test_first_run.py`: with `plain_chrome: testing`, first run needs no seed | Workers on Chrome for Testing wait on a seed they never use |
| All | A real plain Worker on Chrome for Testing says hello and fills (`test_plain_workers.py`, `test_plain_guards.py`, `test_plain_routing.py`) | A break anywhere between Apply and the extension |

- **A Windows CI job: later** (decided 2026-11-24). A `windows-latest`
  job for the fast list (`apply-fast`'s files), with only the files that
  pass, and more as each fix lands; after M2, the real plain Worker tests
  on Chrome for Testing. Without it, the next Mac-only change breaks
  Windows with no red check. Write it into `.github/CLAUDE.md`.
- **The tests' Chrome reaper does nothing off POSIX**
  (`tests/chrome_reaper.py`): a test run that is killed on Windows leaves
  its Chromes open. Close them in Task Manager.
- **No test checks** P6, whether Chrome saves at P7's stop, or the host
  under a school's managed Chrome. Check them by hand on Windows, and
  write each result in section 8.

## 7. Order

| Step | Goal | Problems | Setting | What works after it |
|---|---|---|---|---|
| M1 | A developer runs CDP Workers | P1, P2, P3, P12 (built) | `worker_mode: cdp` | Every host fills except Lever, SmartRecruiters and Workable |
| M2 | A developer runs plain Workers, with no seed | P4, P5, P9 (built), P6 | `plain_chrome: testing` | Every host fills, with no seed |
| M3 | A user runs the app | P7, P8, P10, P11 | the Student build | The download, the seed in Google Chrome, first run |

**The Windows checks come last** (decided 2026-11-24). Fixes go on from a
Mac until every blocker seems fixed. Then a teammate runs all the checks
on Windows at once: M1 with `worker_mode: cdp`, then plain Workers, then
section 8. Each result goes into this note.

**Next: the Windows checks below.** Every fix that a Mac can make is in.
P6 and the "Still open (Windows)" lines need a Windows computer.

### The Windows checks, in order

On Windows 11 with Google Chrome, Git, Node.js and uv, in PowerShell. Write
each result into this note: under its problem's "Still open (Windows)",
or in section 8. A step that fails stops the steps after it only when it
says so.

1. **Set up.** `git clone --recurse-submodules` the repo, check out the
   branch under test, then in `apply-agent`: `uv sync` and
   `uv run playwright install chromium`.
2. **The per-OS tests.** `$env:PYTHONUTF8 = "1"` (P13), then
   `uv run pytest -q -n auto tests/test_each_os.py tests/test_locks.py
   tests/test_plain_channel.py tests/test_plain_bridge.py
   tests/test_doctor.py tests/test_plain_seed_setup.py
   tests/test_first_run.py`. Then every file of CI's `apply-fast` list
   (`.github/workflows/ci.yml`, its "Fast tests" step), with
   `-m "not nightly"`. Each file that passes goes into the Windows CI job
   later (section 6).
3. **doctor.** `uv run apply doctor` prints a line for each check, and
   none of them crashes.
4. **Sign in.** `uv run apply login`, or the window: `uv run apply app`.
5. **M1, CDP Workers.** `worker_mode: cdp` in
   `%USERPROFILE%\.config\apply\policies.yaml`, then
   `uv run apply rehearse https://job-boards.greenhouse.io/formlabsinternships/jobs/8223362`.
   The Apply window opens behind your work (P12), the form fills and is
   held, and the window closes when you end the run. Then the same
   command with `> run.log 2>&1`: it ends as before (P13).
6. **M2, plain Workers.** `worker_mode: plain` and `plain_chrome: testing`,
   then the same rehearsal. The Worker says hello (P4, P5). If it never
   does, look in Task Manager for a `chrome.exe` with `plain-1` in its
   command line: none means that Chrome quit at its start with no window
   (P6). Then `uv run pytest -q tests/test_plain_workers.py
   tests/test_plain_guards.py tests/test_plain_routing.py`.
7. **P7, a clean stop.** In a plain Worker, sign in to a job site, end the
   run, and rehearse that site again: you are still signed in.
8. **P8, the seed.** `plain_chrome: chrome`, then `uv run apply plain
   seed`. Do each step as it says (Ctrl+L, Ctrl+V and Enter in the folder
   picker; a drag from File Explorer). It ends with "Setup is done", which
   also proves P7's save for the seed.
9. **P9, first run.** `plain_chrome: testing`, then `uv run apply app`:
   first run gets past the Seed step with no seed.
10. **P11, keep awake.** Start a run in the window. In an administrator
    PowerShell, `powercfg /requests` lists `python.exe` under SYSTEM and
    DISPLAY; after the run, it doesn't.
11. **Section 8.** Answer each open question there.

## 8. Open questions

- **Is Chrome for Testing right for students?** Then they need no seed.
  D21's reason against it (Allow User Scripts) is out of date since
  KAN-839 removed user scripts. Not checked: its bot signals on the
  protected hosts. It is built for testing, and doesn't update itself.
- Does Chrome save when `taskkill` with no `/F` stops it?
- Does `--no-startup-window` keep Chrome running on Windows?
- How long does `chrome_pid`'s scan take on Windows (P3)? If it is too
  slow: if Chrome deletes its `lockfile` as it closes (Chromium's source
  seems to say so, not checked), a profile with no `lockfile` has no
  Chrome, and the scan can skip it.
