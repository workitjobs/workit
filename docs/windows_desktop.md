# WorkIt Auto Apply on Windows

**Status (2026-11-21, KAN-929):** a plan. P1 to P4 are built; the rest is not. This note lists what
stops Apply on Windows, one problem per section, in the order to solve
them. It expands F4 and W4's "Found on the way" list in
`desktop_application_auto_apply.md`. Line numbers are at commit
`4ce8cf43`. If a line moved, search for the function's name. Paths without
a folder are under `apply-agent/src/apply/`.

## 1. Two goals

- **A Windows developer** runs Apply from a checkout (`uv run apply ...`)
  and runs its tests.
- **A Windows user** downloads WorkIt Auto Apply and runs it.

The developer goal is part of the user goal. Every problem that stops a
developer also stops a user. The user goal adds two things: the seed in
Google Chrome, and a Windows package. So the developer goal comes first.
A Windows developer can then build and test the rest, since each problem
here needs Windows to check.

These already work on Windows (W4, KAN-850): the Chrome finder
(`chrome_finder.py:42-50`), showing a folder (`plain/seed_setup.py:141-151`),
the clipboard (pyperclip), the keychain (`keyring` on Credential Manager),
a Worker's background start (`plain/launcher.py:452-455`), and the window's
build and tests (KAN-867).

## 2. How a plain Worker works

This is the background for the problems in section 4.

```
Apply process: the Bridge (plain/bridge.py)
   |  the channel: a Unix socket file, workers.sock (a named pipe on Windows), checked both ways (P4)
   v
the host (plain/host.py): a small relay program that Chrome starts, one per Worker (P5)
   |  native messaging: Chrome joins the extension to the host's stdin and stdout
   v
the Worker extension, in Worker k's Chrome, on profile APPLY_PROFILES/plain-<k>
   |  extension APIs and the debugger
   v
the job posting's page
```

- **A Worker** is one Chrome process on its own profile folder,
  `APPLY_PROFILES/plain-<k>`. Apply starts it (`PlainWorkers.launch`,
  `plain/launcher.py:307-358`) and stops it by its PID. There are two
  Workers by default, one to three (D24). One Worker can hold more than one
  application, each in its own window.
- **The Worker extension** does the work in the Worker's Chrome. It opens
  tabs, runs the Fill engine, types, and keeps the guards on.
- **The host** is how the extension talks to Apply. The extension calls
  `connectNative`. Chrome then starts the host program and joins the
  extension to it. The host relays each message to Apply over the channel,
  and tells Apply which Worker it is.
- **The host file** is the native messaging manifest. It tells Chrome
  which program is the host. Today it is a JSON file in each Worker
  profile's `NativeMessagingHosts` folder, beside a shell-script wrapper
  (`PlainWorkers.install_host`, `plain/launcher.py:289-305`).

CDP Workers (`browsers.WorkerBrowsers`) are the other kind. Playwright
drives a Chrome through its debugging port, with no extension, host or
seed. Lever, SmartRecruiters and Workable block them. So
`worker_mode: protected`, the default, sends those hosts to plain Workers
(`apply-agent/policies.default.yaml:184-193`).

### How Apply keeps track of its processes

A PID alone never names a process for long: the OS gives a dead process's
PID to a new process later. So Apply keeps each PID with something that
proves which process it is, or it holds the live process object.

| What | Where Apply keeps it | Why there |
|---|---|---|
| The Workers this Apply started | In memory: `PlainWorkers.running` and `_starting`, each with its `Popen` (on the Mac, a `launcher.Chrome`, which keeps the `psutil.Process` it started with) | `stop` and `stop_all` stop exactly those |
| A Worker's Chrome that outlives its Apply | On disk: `apply-owner.json` in its profile, with Apply's PID and start time (`launcher.own`, KAN-885) | Workers keep running after a crash. The next run stops one whose Apply is gone (`reclaim`) |
| Which Chrome holds a profile | macOS and Linux: Chrome's own `SingletonLock`, which Chrome writes, not Apply. Windows: the process whose arguments name the profile (P3) | It covers any Chrome on the profile, also one that Apply didn't start |
| The open Apply windows | On disk: a note for each window in `APPLY_PROFILES/windows/` | `apply ask` and `--into` find them from another process (`into.windows`) |

- **To check that a process runs:** `psutil.pid_exists` (P2). It says only
  that some process has that PID.
- **To check that it is Apply's:** its start time (`_owner_alive`), or its
  command line: `browsers.chrome_pid` takes a lock's PID only while that
  process is a browser whose `--user-data-dir` is the profile, and
  `orphan`, `in_use` and the seed wizard all ask `chrome_pid`.
- **To stop it:** only a process that is Apply's, and only through an
  object that remembers it: a `Popen`, or a `psutil.Process`, whose
  `terminate` and `kill` refuse a reused PID (`_raise_if_pid_reused`, read
  in psutil's source). How to stop a Chrome cleanly on Windows is P7.
- **`launcher.Chrome` held a bare PID** (found in review, 2026-11-24). A
  Worker's Chrome that had ended, the student's quit or a crash, could have
  its PID given to another program, which `_stop` then sent SIGTERM and
  SIGKILL. It now keeps the `psutil.Process` and polls and signals through
  it. Test: `tests/test_each_os.py`,
  `test_a_chrome_whose_pid_went_to_another_program_is_never_signalled`
  (fault: a bare PID).

## 3. Why Workers have their own profiles, and what the seed is

### Why not the student's own Chrome profile

A Chrome profile is a folder on the computer. It holds cookies, extensions
and settings. Apply gives each Worker its own folder, for four reasons.

1. **Apply must start the Chrome process itself.** The Worker's switches
   (`launcher.FLAGS`, `plain/launcher.py:82-83`) work only when a Chrome
   process starts. One profile folder is open in only one Chrome process at
   a time. If the student's Chrome runs, a start on its folder only opens a
   new window in that Chrome, and Chrome ignores the switches. Apply then
   also can't stop it by its PID.
2. **Workers run side by side.** Each Worker is its own Chrome process, so
   each needs its own folder.
3. **The student's Chrome stays theirs.** A Worker holds the Worker
   extension, its submit guards, the host, and windows that Apply opens and
   closes. The student's own extensions (a password manager, an ad blocker)
   could change a form. The first design filled in the student's everyday
   Chrome. The team rejected it because it lost live tiles, Fix here,
   parallel background Workers, screenshots, Claude fill and Rescue
   (`apply-agent/docs/research/everyday-chrome-fill-design.md:7`).
4. **Chrome refuses part of this on the everyday profile.** Google Chrome
   ignores `--load-extension` (`plain/launcher.py:13`). Chrome 136 and later
   also ignore the debugging port on the default profile folder, so CDP
   Workers need their own folder too.

**Google sign-in can't give Apply a profile.** "Sign in with Google" gives
an app a token for a Google account. It gives no browser folder, no
cookies and no extension. This does work: the student signs in to Google
once, by hand, in the seed. Each Worker is a copy of the seed, so each
Worker is signed in too, and a job site's "Sign in with Google" works there
(`apply-agent/docs/sign-in.md:73`).

### What the seed is

The seed is a profile folder, `APPLY_PROFILES/plain-seed` (`launcher.SEED`,
`plain/launcher.py:71`). It is a template. It is not a process, and it
starts nothing.

- Once, the student opens it in Google Chrome and adds the Worker extension
  (Developer mode, then Load unpacked), guided by `apply plain seed`
  (`plain/seed_setup.py`).
- When a Worker starts and its folder doesn't exist yet, Apply copies the
  seed to that folder (`plain/launcher.py:317-318`). Then Apply starts
  Chrome on the copy. Later runs use the same copy again.
- So the student clicks once, not once for each Worker.
- Chrome for Testing (`plain_chrome: testing`) needs no seed. It takes
  `--load-extension`, so Apply loads the extension itself
  (`plain/launcher.py:200-202`).
- The Chrome Web Store copy (W6) changes the clicks to one "Add to Chrome",
  with no Developer mode. The seed stays
  (`apply-agent/docs/plain-workers/worker-extension-todo.md:65-74`).

### Why not copy the student's own profile instead of the seed

Apply could copy the student's everyday profile, as it copies the seed. It
doesn't. The copy doesn't remove the seed's blocker, and it brings
problems of its own.

1. **The copy has no Worker extension.** The seed exists only to hold the
   Worker extension. The student's own profile doesn't have it, so a copy
   of that profile doesn't either. A person must still add the extension
   somewhere. A copy carries it only if the student adds the extension to
   their everyday Chrome. That puts an extension with the debugger and
   access to every site in their everyday browsing, against "nothing of
   theirs changes" (`desktop_application_auto_apply.md:166-169`). On
   Windows, that Chrome would also find the host's registry key (P5).
2. **It needs the same Windows fixes.** Chrome writes its databases while
   it runs, so a copy is safe only while that profile's Chrome is closed.
   Apply already copies only profiles that no Chrome has open
   (`browsers.py:120-124`). To know that on Windows, Apply needs P3, the
   same fix the seed needs. The Workers still need P4 and P5. So the copy
   avoids none of the Windows problems.
3. **Chrome Sync.** If the student has sync on, each copy is signed in to
   sync as them. What a Worker does (its history, its settings, a store
   extension) then syncs back to the student's Chrome on each of their
   devices.
4. **The student's whole identity comes along.** Their email, bank and
   social sign-ins would sit in browsers that Apply's code drives. Apply
   leaves saved passwords out of every copy on purpose (`browsers.NOT_COPIED`
   skips `Login Data`, `browsers.py:61-62`), and turns off Chrome's offer
   to save one (`_no_saved_passwords`, `browsers.py:311`).
5. **The student's extensions come along.** A password manager or a
   writing helper changes form fields, and the Fill engine then reads back
   values that it did not write.
6. **Size.** An everyday profile can be several gigabytes, and three
   Workers make three copies. The seed is small.
7. **Sign-ins may not carry.** Chrome encrypts cookies with a key that is
   outside the profile folder (`Local State`, and the OS's keychain or
   DPAPI). Nobody has checked whether a copy can still read them on
   Windows.

What a student wants from their own profile is mostly their Google
sign-in. The seed already carries it: they sign in to Google once in the
seed (above).

These remove or shrink the seed's blocker:

- **Fix P3, P7 and P8.** The seed then works on Windows. P3 is needed in
  any case, so this is the next step.
- **The store copy (W6):** one "Add to Chrome", with no Developer mode, on
  every OS.
- **Chrome for Testing for students:** no seed at all. This is an open
  question (section 8).

### Where the profiles live, and who can see them

- Apply makes every profile in its own data folder (`home.APP_FOLDER`,
  `home.py:31`), under `profiles/` (`browsers.PROFILES`, `browsers.py:39`):
  - macOS: `~/Library/Application Support/WorkIt Auto Apply/profiles/`
  - Windows: `%LOCALAPPDATA%\WorkIt Auto Apply\profiles\`. This is the
    local AppData, not the roaming one, since Chrome keeps its own
    profiles there too.
  - Linux: `~/.local/share/WorkIt Auto Apply/profiles/`
- The folder belongs to the student. It is in their own user account, and
  they can open it. Apply doesn't encrypt it or lock it.
- The student doesn't find it by chance: by default, Finder hides
  `~/Library` and File Explorer hides `AppData`. Nothing else hides it.
- It doesn't show in the student's own Chrome profile list.
- The student sees the seed's Chrome window once, at first run, and each
  Worker's Chrome window while that Worker runs.
- Settings' Remove All My Data deletes the whole folder (D25).

## 4. The problems

Each problem says what it is, where it is, what breaks on Windows, whom it
stops, how to fix it, and how to know it is done. Section 5 gives the rules
for each fix, section 6 the tests, and section 7 the order.

### P1. File locks (`fcntl`): built

- **What it is.** Two Apply processes can write Apply's data files at the
  same time: a run, the window, `apply ask`. The files are the Tracker,
  Records, the Answer bank and its queue, the open-forms list and the
  WorkIt login. A lock file stops two writes at once (`fcntl.flock`, for
  example `tracker.py:211`).
- **Where it was** (line numbers before the fix). `import fcntl` at the top of 10 modules: `tracker.py:9`,
  `records.py:5`, `batch.py:14`, `answer_bank.py:18`, `answer_sync.py:24`,
  `verify.py:11`, `workit.py:49`, and the developer-only `repair.py:13`,
  `repairer.py:30` and `sheet.py:10`.
- **What breaks.** Windows has no `fcntl` module. The import fails, so no
  command starts, and the app window doesn't either. This was checked on a
  Mac with `fcntl` blocked: `apply.cli`, `apply.first_run` and
  `apply.plain.seed_setup` all fail to import, through `tracker.py:9`.
- **Who.** Both.
- **The fix (KAN-929).** `apply.locks` (`apply-agent/src/apply/locks.py`)
  is the one way Apply locks a file. `held(path)` waits for the lock.
  `tried(path)` takes it only if it is free, as `apply repair` needs.
  Every one of the 10 modules uses it. It runs on `portalocker`.
  - **A lock file is never emptied.** `held` and `tried` open the lock
    file to append. Three lock files were opened with `"w"`, which empties
    a file: the Answer bank queue's (`answer_sync.py`), and the WorkIt
    login's and the WorkIt queue's (`workit.py`). They append now.
  - **Each data file has its own lock file beside it**, `<name>.lock`,
    which holds nothing. The Sheet shares the Tracker's lock on purpose
    (`sheet.locked`), so that their writes never interleave.
  - **The Answer bank has its own lock file now**, `answer-bank.lock`.
    Before, it locked `answer-bank.yaml` itself. On Windows a lock also
    stops every other handle from reading the locked bytes, so the bank's
    own read would fail.
  - **Every lock is exclusive.** portalocker's Windows lock is exclusive
    only: a shared one needs pywin32. The Answer bank's read took a shared
    lock. It takes the exclusive one now, so two reads wait for each
    other. A read is short.
  - **A wait never gives up on Windows.** portalocker's Windows lock tries
    for about 10 s, then raises `AlreadyLocked`, and `held` tries again.
  - **Why portalocker, not filelock.** filelock opens its lock file with
    `O_TRUNC`, which empties it (read in its `_unix.py` and
    `_windows.py`). portalocker locks a file that Apply opens itself, in
    the mode that Apply picks. On macOS and Linux it uses `fcntl.flock`,
    as Apply did, so the Mac's locks work as before. It has no required
    dependency, and its license is BSD-3-Clause.
  - **After a pull, restart every Apply process.** An older process and a
    newer one on the same data folder still exclude each other on every
    lock file except two: the Answer bank's (the older one locks
    `answer-bank.yaml`, the newer one `answer-bank.lock`) and the
    Repair's one-at-a-time lock (below).
  - **Two jobs in one folder need two lock files** (found in review,
    2026-11-21). A second lock on a file that the same process already
    holds waits for good. The one-at-a-time Repair lock and the Repair
    requests' lock were both `HOME/repairs/.lock`, since `repair.FOLDER`
    and `repairer.WORKTREES` are one folder. So the first save inside a
    Repair never returned, after Claude had done the work. This bug was
    older than P1: the `fcntl` code used the same paths. The
    one-at-a-time lock is `repairs/.running.lock` now
    (`repairer.RUNNING`). Test: `tests/test_repairer.py`,
    `test_a_repair_saves_its_request_in_the_folder_it_runs_in`, the only
    repair test with the real layout (fault: one lock file for both).
- **Tests**, in the fast list. Each test went red with its fault in.
  - `tests/test_locks.py`: another process holds the Tracker's lock
    between its read and its save. This process's write waits, `tried`
    sees the lock, and then both writes land. Fault: the lock does
    nothing.
  - `tests/test_each_os.py` (moved there with P2): no module of Apply
    imports `fcntl`. Fault: a module imports it again. The test reads
    the source. An import with `fcntl` blocked can't work as a test,
    because portalocker itself imports `fcntl` on macOS and Linux.
- **Where lock files live.** Apply makes each lock file the first time it
  locks that data file: `held` and `tried` make the folder, and opening
  the file to append makes an empty one. Every lock file is in the data
  folder, beside its data file. None is in the app's package: a signed Mac
  app and Windows' `Program Files` are read-only, and each data folder
  needs its own. Remove All My Data deletes them with the folder, and the
  next run makes them again.
- **After a crash.** The OS releases a lock when the process that held it
  ends. So a crash leaves no stale lock, only an empty file, and the next
  process takes the lock at once. On Windows the release can take a
  moment, and `held` waits for it.
- **Is `fcntl` gone completely?** Yes, from Apply's start (checked
  2026-11-21):
  - No file in `apply-agent/` imports it: not the source, the tests, the
    tools or the scripts.
  - No installed library imports it at its top. portalocker imports it
    only on macOS and Linux.
  - `uv.lock` has no OS limit, and it holds Windows' own packages
    (pywebview's `pythonnet` and `clr-loader`), so `uv sync` resolves on
    Windows.
  - A scan found no module that imports another Unix-only module (`pwd`,
    `termios`, `resource`, `readline` and the like), and none that calls
    a Unix-only function at its top level.
  - Not proven: nothing has run on Windows yet. The first Windows run, or
    the Windows CI job (section 6), proves it.
- **Unix-only calls that are left.** These fail only when they run, not
  at import, and each one belongs to another problem: SIGTERM (P7).
  P2's `os.kill(pid, 0)`, P3's `SingletonLock` and P4's Unix sockets are
  fixed. Two more are in developer-only modules (`build.DEVELOPER`),
  so they stop only a Windows developer's command that runs them:
  - `os.killpg` in `claude_cli.stream_claude` (`claude_cli.py:154`), used
    with `ask_model: claude`.
  - `os.getuid()` in `schedule.Launchctl` (`schedule.py:133`): the Mac's
    scheduled runs, which D10 drops.

### P2. "Is it still running?" (`os.kill(pid, 0)`): built

- **What it is.** Apply asks whether a process still runs: a Worker's
  Chrome, or an Apply window. On macOS and Linux, signal 0 checks and sends
  nothing.
- **Where it was** (line numbers before the fix):
  - `browsers.py:104`, in `chrome_pid`: is a profile's Chrome running?
    Both kinds of Worker use it.
  - `into.py:43`, in `windows`: which Apply windows are still open?
  - `plain/launcher.py:420`, in `Chrome.poll`: the Mac's Chrome that `open`
    started.
  - `dashboard.py:2318`, in `_quit`: the Chrome app window's quit, on the
    Mac.
  - The developer-only `cli.py:513` (`apply ask`) and `dock_app.py:131`
    (the Dock keeper).
  - Also the tests' Chrome reaper (`tests/chrome_reaper.py`) and three
    plain Worker tests.
- **What broke.** On Windows, `os.kill` is not a check. Signal 0 is
  `CTRL_C_EVENT` there, which tries to send a Ctrl-C to a console process
  group. Any other signal ends the process at once. Neither tells whether
  a process runs.
- **Who.** Both.
- **The fix (KAN-929).** Each place asks `psutil.pid_exists(pid)`. psutil
  was already a dependency, and the code is the same on every OS.
  - **On macOS and Linux, nothing changes.** psutil's `pid_exists` calls
    `os.kill(pid, 0)` there itself (read in its `_psposix.py`). No such
    process gives False. A process of another user (`PermissionError`)
    gives True: it exists, but Apply may not signal it.
  - **On Windows, it asks the OS** whether a process with that PID exists,
    and it sends nothing.
  - **Another user's process** (found in review, 2026-11-21). The old
    check in `chrome_pid` counted another user's process as gone, since
    it caught `PermissionError` with every `OSError`; `pid_exists`
    counts it as running. A Chrome that crashed leaves its lock, and the
    OS can give its PID to a root process. Then the Worker stayed in use
    for good: `reclaim` can't read a root process's arguments either.
    Reproduced on a Mac with root's PID 329. The fix is the identity half
    of P3: `chrome_pid` now takes the lock's PID only while that process
    is a browser (no `--type=`) whose `--user-data-dir` is this profile,
    and an `AccessDenied` counts as no browser. `orphan` and
    `Desk.chrome` had copies of that check; both ask `chrome_pid` now.
    Playwright starts a CDP Worker's Chrome with `--user-data-dir` too
    (read in its driver), so CDP Workers pass the check.
  - `into.windows` also counts another user's process as running now.
    There a wrong answer lists a window that is gone, and its first call
    fails with `NoWindow`, as for any closed window. `Chrome.poll` used
    to raise on such a process; it now says "running".
  - Tests for the review's fix, in the fast list: a lock that names
    another program (`tests/test_plain_seed_setup.py`, the Desk test:
    fault, `chrome_pid` trusts any live PID), and one whose process
    Apply may not read (`tests/test_each_os.py`: fault, the same, or an
    `AccessDenied` that escapes). Tests that need a browser to have a
    profile open start a stand-in process whose command line names the
    profile (`conftest.browser_on`), since a lock that names the test's
    own process no longer counts.
- **Tests**, in the fast list:
  - `tests/test_each_os.py`,
    `test_no_module_of_apply_makes_a_call_that_stops_windows`: no module
    checks a process with `os.kill(pid, 0)`. Fault: a module does again.
    It went red with the fault in. It reads the source, because on macOS
    and Linux the old call works. The same test also checks P1's `fcntl`
    imports: that check moved there from `tests/test_locks.py`.
  - A live process and a gone one: the tests that already held them pass.
    `tests/test_into.py` holds a window that lists itself and a note with
    a gone PID. The plain Worker tests stop a Worker and check that its
    Chrome is gone, and `tests/test_reopen.py` waits for a Chrome to quit.
    `tests/test_apply_window_on_the_mac.py`'s fake Mac now fakes
    `psutil.pid_exists`.
- **Still open.** Run it on Windows (the Windows CI job, section 6). The
  tests' Chrome reaper still stops a Chrome with SIGTERM and SIGKILL (P7).

### P3. Which Chrome has a profile open (`SingletonLock`): built

- **What it is.** Apply finds the PID of the Chrome that has a profile
  open. With it, Apply knows that a profile is in use, stops an orphan
  Chrome, brings a Worker forward, and, in the seed wizard, sees that the
  seed's Chrome is open.
- **Where it was** (line numbers before the fix). `browsers.chrome_pid` (`browsers.py:100-107`) reads the
  profile's `SingletonLock` link. The end of the link's target is the PID.
  Its callers: `in_use` (`browsers.py:95-97`), `browsers.py:210`, `:275`,
  `:280`, `PlainWorkers.idle` (`plain/launcher.py:176-178`), `launch`
  (`:313`), `start_in_background` (`:461`), `orphan` (`:493`), and
  `Desk.chrome` (`plain/seed_setup.py:156`).
- **What broke.** Chrome makes `SingletonLock` on macOS and Linux only.
  On Windows a profile has a `lockfile`, with no PID in it. So `chrome_pid`
  always returns None. Every profile looks free, no orphan is ever found,
  and the seed wizard thinks Chrome never opened.
- **Who.** Both.
- **The fix (KAN-929).** `chrome_pid(profile, system)` has an entry for
  each OS. Both entries end in one check, `_browser_on`: a browser (no
  `--type=`) whose `--user-data-dir` is this profile.
  - **macOS and Linux:** the PID that `SingletonLock` names, checked so
    (the identity half, from P2's review). It reads one link and one
    process, so it stays: 0.02 ms on this Mac.
  - **Windows:** every process's arguments, through
    `psutil.process_iter(["cmdline"], ad_value=None)`. psutil gives a
    process that Apply may not read, or a zombie, no arguments (None),
    and skips one that ends during the scan (read in psutil 7.2.2's
    source). So the scan never raises, and a process of another user is
    never the profile's Chrome.
  - **No filter by program name.** Every process is checked, not only
    `chrome.exe`. The check is what proves the Chrome, and the tests'
    stand-in browser (`conftest.browser_on`) is a Python process.
  - **Cost.** The same scan takes 8–16 ms over 596 processes on this Mac.
    Apply asks seldom: once per Worker start, profile check or tile that
    starts filming, and once a second during the seed's setup. Not
    measured on Windows (section 8).
- **Tests**, in the fast list: `tests/test_each_os.py`,
  `test_on_windows_the_profiles_chrome_is_found_by_its_arguments`. Its
  scan holds a helper of the profile's Chrome, another profile's browser,
  a process Apply may not read, and the profile's own browser, which it
  must find; after that Chrome quits, it must find none. Four faults each
  went red: no Windows entry, a helper counts, a process with no
  arguments crashes the scan, and any profile's browser counts. The
  macOS and Linux entry keeps its tests (P2's review fix), and the real
  plain Worker tests pass on the Mac.
- **Still open.** Run it on Windows: whether Windows Chrome's browser
  process carries `--user-data-dir` in its arguments as Apply starts it,
  and how long the scan takes there.

### P4. The channel between Apply and the hosts (Unix socket): built

- **What it is.** Apply's Bridge listens on a socket file, `workers.sock`,
  that only the user can read (0600). Each Worker's host connects to it
  and relays the extension's messages. The MCP tools use sockets the same
  way.
- **Where.** `plain/bridge.py:265` and `:273` (the Bridge),
  `plain/host.py:46` (the host), `plain/mcp.py:48`, `plain/tools.py:447`.
  The socket folders use `os.getuid()`: `plain/bridge.py:98` when the
  socket's path is too long, and `plain/tools.py:73` always, under `/tmp`,
  which Windows doesn't have either.
- **What breaks.** Python on Windows has no `socket.AF_UNIX`, and `os` has
  no `getuid`. So no plain Worker can talk to Apply.
- **Who.** Both, for plain Workers. CDP Workers don't use the channel.
- **Decided (2026-11-24): a named pipe on Windows only, with a check in
  both directions on every OS.** macOS and Linux keep today's Unix socket.
  - **Not a port.** A port on `127.0.0.1` would open nothing to the
    network, and the OS would pick a free number, so it couldn't collide
    with a developer's ports. But every program on the computer, and every
    web page in a browser on it, can send bytes to a local port: Zoom's
    local server on the Mac (port 19421) let web pages start calls until
    2019. Desktop apps (Chrome, VS Code) talk between their own processes
    through named pipes on Windows and Unix sockets on the Mac, and no
    firewall or antivirus asks about a pipe.
  - **Not `pywin32`:** a new dependency for one job. Python's own
    `multiprocessing.connection` makes and opens named pipes on Windows,
    the same code that `multiprocessing` itself uses there.
- **The design (built).** One module, `plain/channel.py`, standard
  library only, holds the channel for the Bridge, the host, `tools.py` and
  `mcp.py`, with an entry for each OS:
  - **macOS and Linux:** the Unix socket, as today: `workers.sock` in the
    profiles folder (`socket_path`), mode 0600, with `/tmp/apply-<uid>/`
    for a path that is too long.
  - **Windows:** a named pipe, `\\.\pipe\workit-apply-<16 hex>`, the hash of
    the same path. So one profiles folder always gives the same pipe, and
    two folders never share one. Windows refuses to make a pipe a second
    time (`FILE_FLAG_FIRST_PIPE_INSTANCE`, which Python sets), so a second
    Apply on the same folder gets `BridgeBusy`, as today.
  - **The Windows adapter.** The pipe sends whole messages, and the Bridge
    reads a stream of bytes. A small class gives the pipe the calls the
    Bridge and `tools.py` use: `sendall`, `recv`, `shutdown`, `close`,
    `settimeout` and `makefile`. Two facts from Python's source shape it.
    A close cancels a pending send but not a pending receive: a reader
    blocked on another thread wakes only when Windows cancels its read,
    and Python then raises `RuntimeError("shouldn't get here")`, so every
    failure of a read counts as "closed". And a blocked `accept` doesn't
    wake when the listener closes, so `close` first connects once to its
    own pipe: else the pipe stays, and the next Bridge in the same process
    (a run after the seed's setup) can't make it again. The Bridge already
    sends under a lock, which the pipe needs: it refuses two sends at once.
  - **The check in both directions.** When a channel starts, it writes a
    new random secret, 32 bytes, beside its address (`workers.key` beside
    `workers.sock`): only after it holds the address, so a second Apply
    never overwrites the first one's secret. Then each new connection:
    the listener sends a random challenge, the connecting side answers
    `HMAC(secret, "client" + challenge)` and its own random challenge, and
    the listener answers `HMAC(secret, "server" + that)`. Each side checks
    with `hmac.compare_digest` and closes on a wrong answer, before any
    other message. A stranger can't connect, a stranger can't pass for
    Apply to a host whose Apply has gone, and an old answer fails a new
    challenge. It runs on the Mac too, so one handshake serves every OS.
  - **The host stays standard-library only.** It loads its neighbour
    `channel.py` by its file path, and reads the address and the secret
    from its `--socket` argument, as today. This prepares P5 too: on
    Windows, one wrapper serves every Worker, and the host can find the
    profiles folder from its parent Chrome's `--user-data-dir`.
  - **`tools.py` and `mcp.py`** (Claude's drive, developer only) use the
    same module. `/tmp` and `os.getuid()` stay in the macOS and Linux
    entry only.
- **Tests** (built), in the fast list. Each went red with its fault in.
  - `tests/test_plain_channel.py` runs each test on the entries its OS has.
    On macOS and Linux, "connections" runs the Windows entry's own classes
    (`ConnectionListener`, `Messages`) over `multiprocessing` connections on
    a Unix socket in place of the pipe, so all but the pipe's own calls run
    in CI. One test for each fault: a frame both ways, read head then body
    as the Bridge reads it, one over 1 MB too (fault: `Messages` drops
    what a read didn't take); a client without the secret is refused and
    told nothing; a client that says nothing is dropped (fault: the pipe's
    reads take no timeout); a listener without the secret is refused by
    the client; an old answer fails a new challenge; a drive reads its
    lines through `makefile`; a close wakes a blocked reader (the socket
    and the pipe); a closed channel listens again in the same process; and
    `close` wakes an accept that closing the listener leaves blocked, with
    a fake listener that plays the pipe (macOS wakes a blocked accept by
    itself, so only a fake shows the fault there).
  - `tests/test_each_os.py`: a Windows path makes a named pipe, one for
    each folder, and never reaches `os.getuid`; its source test fails on a
    Unix socket made outside the channel.
  - The tests that played a host on a raw Unix socket
    (`tests/test_plain_bridge.py`, `tests/test_plain_claude.py`) connect
    through the channel. The Bridge's permission test covers the secret.
  - The Mac's real plain Worker tests pass: a Worker's start, an
    extension's reload (a new host, checked again), a reused Worker, the
    reopen after Apply is killed (a new secret), and a drive's tools.
- **Still open.** The pipe's own calls run only on Windows: that a close
  there cancels a blocked read, that `close`'s own connection wakes a
  real pipe's accept, and that a second Apply gets `Busy`. They wait for
  the Windows CI job (later) or the teammate's run.
- **Review.** The check guards the line that can drive a Worker's Chrome,
  so it gets a security review before the PR merges, in the spirit of
  the guards' adversarial review (root `CLAUDE.md`).
- **Done when.** A plain Worker on Chrome for Testing says hello on
  Windows. That needs P5 too.

### P5. The host file (native messaging manifest and wrapper)

- **What it is.** Chrome starts a host only if a manifest names it. The
  manifest gives the program's path and the extension IDs that may call it.
  Today each Worker profile has its own manifest and its own wrapper
  script. The wrapper tells the host its socket and its Worker number
  (`--socket <path> --worker <k>`).
- **Where.** `PlainWorkers.install_host` (`plain/launcher.py:289-305`): a
  `#!/bin/sh` wrapper (`:294-296`) and a manifest in
  `<profile>/NativeMessagingHosts/`. Also the accounts host for the
  student's own Chrome (`native_host.install`, `native_host.py:124-132`),
  which raises `NotImplementedError` on Windows.
- **What breaks.** Two things.
  - Chrome on Windows reads no `NativeMessagingHosts` folder. It reads the
    registry key
    `HKEY_CURRENT_USER\Software\Google\Chrome\NativeMessagingHosts\<name>`,
    whose value is the manifest's path (`native_host.WINDOWS_KEY`,
    `native_host.py:50`).
  - Windows can't run a `#!/bin/sh` script.
- **Who.** Both, for plain Workers.
- **Fix.**
  - Write the registry key with `winreg` (standard library), and write a
    `.bat` wrapper. The package can use its own `.exe` instead.
  - **A design change.** The registry key is one per Windows user, for
    every Chrome profile, not one per Worker profile. So one wrapper serves
    every Worker, and it can't carry the Worker number. The host must find
    its Worker another way. For example, its parent Chrome's
    `--user-data-dir` (psutil) names `plain-<k>`.
  - The student's everyday Chrome also sees the key. That is safe: only
    the Worker extension's IDs may call the host (`allowed_origins`), and
    the everyday Chrome doesn't have that extension.
  - **Check the host's parent.** The tile proves a connection is its
    Worker's own by comparing the host's parent (`chrome_of`) with the
    Worker's Chrome (`tile._foreign_to`). Chrome on Windows may start a
    host through `cmd.exe` (recalled from Chromium; its source was not
    read). Then the parent is `cmd.exe`, and every tile counts as
    foreign. If so, accept the Worker's Chrome anywhere among the host's
    ancestors (`psutil.Process(host_pid).parents()`).
- **Done when.** The same check as P4: a plain Worker says hello on
  Windows.

### P6. A Worker with no window at start (`--no-startup-window`)

- **What it is.** A Worker's Chrome starts with no window, so it takes no
  focus. The extension opens the window, unfocused, after its hello
  (`plain/launcher.py:203-205`).
- **What breaks.** Not checked on Windows. On Linux, such a Chrome quits
  at once (`apply-agent/docs/research/held-forms-after-a-crash.md:20`).
- **Who.** Both, for plain Workers.
- **Fix.** Measure first, once P4 and P5 work. If Chrome quits, start it
  with a window and let the OS keep that window behind.
- **Done when.** It is measured, and the result is written here.

### P7. Stopping a Chrome cleanly (signals)

- **What it is.** Apply stops a Chrome with SIGTERM, then SIGKILL after
  10 s. SIGTERM lets Chrome save. SIGKILL loses what Chrome has not saved
  yet (measured on the Mac).
- **Where.** `Desk.terminate` (`plain/seed_setup.py:165-169`), the Mac's
  `launcher.Chrome` (`plain/launcher.py:412-440`), and `_stop`
  (`plain/launcher.py:524-532`). `launcher.Chrome` now signals through
  psutil (section 2), which on Windows takes SIGTERM as TerminateProcess:
  still no clean exit there.
- **What breaks.** On Windows, `os.kill(pid, SIGTERM)` and
  `Popen.terminate()` both end the process at once, with no save.
  - For a Worker, that loses the session cookies that
    `--restore-last-session` keeps, so the job sites' sign-ins go (KAN-718).
  - For the seed, that loses Developer mode and Load unpacked.
- **Who.** Mostly the user, since the seed is in Google Chrome and a
  developer on Chrome for Testing has no seed. A developer's Workers still
  lose their job-site sign-ins at each stop.
- **Fix: options.**
  - `taskkill /PID <pid>`, with no `/F`, asks the process's windows to
    close, as a click on X does. Measure that Chrome saves.
  - For the seed only: ask the student to close that Chrome window, and
    wait. The wizard already waits for that Chrome to go (`_quit`,
    `plain/seed_setup.py:280-285`). This is the simplest way. It sends no
    signal at all.
  - A Worker that started with no window (P6) may have no window to close.
    Measure that case too.
- **Done when.** On Windows, a setting changed in the seed's Chrome is on
  disk after the Chrome stops.

### P8. The seed wizard on Windows

- **What it is.** `apply plain seed`, and the app's first-run Seed step,
  which runs the same wizard (`first_run.py:123-128`).
- **What breaks.** After P1, four more problems stop it:
  - P3: the wizard never sees Chrome open. After 20 s it stops with "Chrome
    did not open the seed profile within 20 s" (`plain/seed_setup.py:255-261`).
  - P7: its quit loses the student's clicks.
  - P4 and P5: its last check starts a real Worker, which can't say hello
    (`plain/seed_setup.py:287-303`).
  - Its words are the Mac's: "Finder", "Cmd+Shift+G" and "Cmd+V"
    (`plain/seed_setup.py:94-95`), and "Cmd+Q" (`:283-284`).
- **Who.** The user. A developer can skip the seed (P9).
- **Fix.** P3, P4, P5 and P7 fix the code. For the words, give `instruction`
  and `_quit` one text for each OS, picked by a `system` argument (W4's
  rule). On Windows: "File Explorer", and in the folder picker, paste the
  path into the address bar (Ctrl+L, Ctrl+V, Enter), then click Select
  Folder. Later, the store copy (W6) removes Developer mode and Load
  unpacked on every OS. The seed stays, with one "Add to Chrome".
- **Done when.** `uv run apply plain seed` ends with "Setup is done" on
  Windows.

### P9. The developer's way past the seed

- **What it is.** A developer can run plain Workers on Chrome for Testing,
  with no seed. Set `plain_chrome: testing` in `policies.yaml`, or
  `APPLY_PLAIN_CHROME=testing` (`launcher.chrome_kind`,
  `plain/launcher.py:112-117`). The doctor then says the seed is "not
  needed" (`doctor.py:237-238`).
- **What breaks.** The app window's first run ignores this setting.
  `seed_problem` makes `PlainWorkers(kind="chrome")` (`first_run.py:119`),
  so `uv run apply app` stays on the Seed step.
- **Who.** The developer.
- **Fix.** Outside the Student build, `seed_problem` reads `chrome_kind()`,
  and the Seed step is done when it is `testing`. The Student build keeps
  Google Chrome (D21).
- **Done when.** `uv run apply app` with `plain_chrome: testing` goes past
  first run with no seed.

### P10. The Windows package

- **What it is.** What a user downloads. Today it is for the Mac only: a
  notarized DMG with Sparkle updates (D17), for Apple Silicon only (D18).
- **What it needs.** A Nuitka build on Windows (W8), a code-signing
  certificate so that SmartScreen doesn't warn, an installer, updates
  (WinSparkle or similar), and pywebview on WebView2 (F4's table,
  `desktop_application_auto_apply.md:1904-1914`). It also needs new
  decisions beside D17 and D18.
- **Who.** The user.

### P11. Smaller gaps

- **Keep awake.** `awake.command` (`awake.py:17-21`) returns None off the
  Mac, so Windows can sleep during a run. Use `SetThreadExecutionState`
  (through `ctypes`) or a library such as `wakepy`.
- **Smooth tiles.** The Swift helper (`plain/window_capture.swift`) is the
  Mac's. Elsewhere a tile shows about 2 frames a second until
  `Page.startScreencast` (W6).
- **The tile's PID reads: built** (found in review, 2026-11-24). Off the
  Mac, `window_capture.mode` is always "extension", so the tile never
  tries ScreenCaptureKit there, nor its permission note, which names the
  app through `ps`. `window_capture.chrome_of` reads a host's parent with
  psutil, not `ps`. Before, P3 let a Windows tile reach `ps`: each watch
  turn failed without a word, the tile stayed blank, and each turn added
  its handlers again. Tests in `tests/test_each_os.py` (fast list): the
  mode on each OS, and the parent read with `ps` gone.
- **Focus.** FocusKeeper is the Mac's. Elsewhere `focus.KEEPER` is a
  `NoKeeper`, and the extension's `windows.focus` brings a Worker forward
  (`plain/launcher.py:378-391`). Check that Windows keeps Workers behind
  the student's apps (F4's "Test early").
- **Tests and CI.** CI runs on Ubuntu and macOS only. A Windows job, for
  the fast test list at least, stops these fixes from breaking again.

## 5. How to fix: one code for every OS

These rules come from `apply-agent/CLAUDE.md`, "Code that differs by OS".
A fix may change the Mac's code too, when tests cover it (section 6).

- **No Windows-only files in Apply's code.** The only Windows-only files
  are the package's build, installer and signing scripts (P10).
- **A library first.** Where a library works on every OS, the fix replaces
  the Unix-only call on every OS, the Mac too. There is then one code
  path, and the Mac's tests run the same code that Windows runs.
- **Else one entry for each OS, in one function.** Where no library does
  the job, the one function that does the job gets an entry for macOS,
  Windows and Linux, picked by a `system` argument (`sys.platform`).
  `Desk.reveal` and `start_in_background` are the models. Each entry gets
  a case in `tests/test_each_os.py`.
- **Import a Windows-only module inside its Windows entry** (`winreg`,
  `msvcrt`), never at a module's top. The Mac has no such module, so an
  import at the top breaks the Mac.

| Problem | Kind of fix |
|---|---|
| P1 file locks | Built: a library (`portalocker`, only through `apply.locks`), the same code on every OS |
| P2 "is it still running?" | Built: a library (`psutil.pid_exists`), the same code on every OS |
| P3 profile lock | Built: a library (psutil finds the Chrome by its arguments on Windows), one check for every OS |
| P4 channel | Built: a Windows entry, a named pipe (`multiprocessing.connection`); the Unix socket stays on macOS and Linux; one check in both directions on every OS |
| P5 host file | A Windows entry: the registry key (`winreg`) and a `.bat` wrapper. The host finds its Worker the same way on every OS |
| P6 no startup window | Measure first. A Windows entry only if Chrome quits |
| P7 clean quit | For the seed: ask the student to close its window, on every OS or on Windows only. For a Worker: a Windows entry (`taskkill` with no `/F`), after a measurement |
| P8 wizard words | A Windows text in the same function |
| P9 first run | The same code on every OS |
| P10 package | Windows-only build, installer and signing scripts, outside Apply's code |
| P11 keep awake | A Windows entry in `awake.command`, or a library (`wakepy`) |

## 6. Tests

A fix may change the Mac's code when tests cover it. Here "tests cover
it" follows the repo's rule (`apply-agent/CLAUDE.md`, "Every test earns
its place"): each test is one scenario, and its comment names the fault
that it alone turns red. So the goal is a red test for each way that a fix
can break, on each OS. The goal is not a high count of tests.

| Problem | Test, new or extended | The fault it turns red | Where it runs |
|---|---|---|---|
| P1 | Built, `tests/test_locks.py`: two processes write the Tracker at the same time, and both writes are there after | The lock does nothing | The fast list |
| P1 | Built, `tests/test_each_os.py`: no module of Apply imports `fcntl`, read from the source | A module imports `fcntl` again | The fast list, on Ubuntu, before any Windows job |
| P2 | Built: `tests/test_each_os.py` reads the source for `os.kill(pid, 0)`; `tests/test_into.py` holds a live PID and a gone one | A module checks a process with `os.kill(pid, 0)` again; the check misses a live process | The fast list |
| P3 | Built, `tests/test_each_os.py`: on Windows the profile's own Chrome is found by its arguments; a helper (`--type=`), another profile's Chrome and a process Apply may not read never count | Another process is taken for the profile's Chrome, or none is found | The fast list |
| P4 | Built, `tests/test_plain_channel.py` on each entry its OS has, and `tests/test_each_os.py`: frames both ways, the check's refusals, a silent client, lines, close and listen again | A client or a listener that isn't Apply's gets in; a frame comes through cut; a closed pipe can't be made again | The fast list (the pipe itself: Windows) |
| P5 | `tests/test_native_host.py`, `tests/test_each_os.py`, with a fake `winreg`: the key names the manifest, the `.bat` starts the host, and the host finds its Worker from its parent's `--user-data-dir` | A host speaks for the wrong Worker | The fast list |
| P7, P8 | `tests/test_plain_seed_setup.py`, with its fakes: on Windows the wizard never ends the seed's Chrome by force, and it says the Windows words | A forced stop loses the student's clicks | The fast list |
| P9 | `tests/test_first_run.py`: `plain_chrome: testing` passes the Seed step in a Developer checkout; the Student build still needs the seed | The Student build skips the seed | The fast list |
| All, end to end | A real plain Worker on Chrome for Testing says hello and fills: `tests/test_plain_workers.py`, then `tests/test_plain_guards.py` and `tests/test_plain_routing.py` | A break anywhere between Apply and the extension | A Windows runner, and the Mac's `apply` job |

- **The Mac keeps its checks.** A PR that changes P1 to P5 runs the Mac's
  real plain Worker jobs, `apply` and `apply-hostile`
  (`.github/workflows/ci.yml:351` and `:424`). They already run
  `test_plain_guards.py` and `test_plain_routing.py`. Also run the tests
  that the change touches on your Mac, with `-k`, as `apply-agent/CLAUDE.md`
  says.
- **A Windows job in CI: later** (decided 2026-11-24, not built with P4).
  It would run the channel's tests on a real named pipe on every PR. Until
  then the pipe's own calls wait for the teammate's run (section 7). Add a
  `windows-latest` job for the fast list
  (`apply-fast`'s files, `ci.yml:224`). Start it after P1, since no file
  imports on Windows before that. Give it only the files that pass, and
  add files as each fix lands. After M2, add the real plain Worker tests
  on Chrome for Testing. Without this job, the next Mac-only change breaks
  Windows again with no red check. Write the job into `.github/CLAUDE.md`.
- **What a test can't check.** P6, whether Chrome saves at P7's stop, and
  the host under a school's managed Chrome need a real Windows computer.
  Check them by hand, and write each result in section 8.

## 7. Order

| Step | Goal | Problems | Setting | What works after it |
|---|---|---|---|---|
| M1 | A developer runs CDP Workers | P1, P2 and P3 (built) | `worker_mode: cdp` | Apply starts; every host fills except Lever, SmartRecruiters and Workable |
| M2 | A developer runs plain Workers, with no seed | P4 (built), P5, P6, P9 | `plain_chrome: testing` | Every host fills; a developer never needs the seed |
| M3 | A user runs the app | P7, P8, P10, P11 | the Student build | The download, the seed in Google Chrome, first run |

The store copy (W6) is not Windows work. When it ships, it changes P8's
clicks on every OS.

**M1's code is built** (P1 to P3), but nothing has run on Windows yet.

**The Windows checks come last** (decided 2026-11-24). Fixes go on, from
a Mac, until every blocker here seems fixed. Then a teammate on a Windows
computer runs all the checks at once: M1's first run with
`worker_mode: cdp`, then plain Workers, and the open questions in
section 8. Each result goes into this note.

**Next: P5,** the host file. Chrome on Windows can't start a Worker's host
until it finds the host in the registry, through a wrapper Windows can
run. P4 left the host ready for one wrapper: it finds the channel and its
secret from its `--socket` path.

## 8. Open questions

A teammate on Windows checks these after every blocker seems fixed
(section 7).

- **Is Chrome for Testing right for students?** If it is, students need no
  seed at all. D21's reason against it ("Chrome for Testing can't turn on
  Allow User Scripts") has been out of date since KAN-839 removed user
  scripts. Not checked yet: its bot signals on the protected hosts. Also,
  Google builds it for testing, and it doesn't update itself.
- Which registry key does Chrome for Testing read for native hosts? It may
  not be Google Chrome's key.
- Does Chrome save when `taskkill` with no `/F` stops it?
- Does `--no-startup-window` keep Chrome running on Windows?
- How long does `chrome_pid`'s scan take on Windows (P3)? It took 8–16 ms
  over 596 processes on this Mac. If it is too slow, Chrome's `lockfile`
  may skip it for a free profile: if Chrome deletes that file when it
  closes, as Chromium's source seems to say (not checked), a profile with
  no `lockfile` has no Chrome.
