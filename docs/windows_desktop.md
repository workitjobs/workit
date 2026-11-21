# WorkIt Auto Apply on Windows

**Status (2026-11-21, KAN-929):** a plan, not built. This note lists what
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
   |  the channel: a Unix socket file, workers.sock (P4)
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

### P1. File locks (`fcntl`)

- **What it is.** Two Apply processes can write Apply's data files at the
  same time: a run, the window, `apply ask`. The files are the Tracker,
  Records, the Answer bank and its queue, the open-forms list and the
  WorkIt login. A lock file stops two writes at once (`fcntl.flock`, for
  example `tracker.py:211`).
- **Where.** `import fcntl` at the top of 10 modules: `tracker.py:9`,
  `records.py:5`, `batch.py:14`, `answer_bank.py:18`, `answer_sync.py:24`,
  `verify.py:11`, `workit.py:49`, and the developer-only `repair.py:13`,
  `repairer.py:30` and `sheet.py:10`.
- **What breaks.** Windows has no `fcntl` module. The import fails, so no
  command starts, and the app window doesn't either. This was checked on a
  Mac with `fcntl` blocked: `apply.cli`, `apply.first_run` and
  `apply.plain.seed_setup` all fail to import, through `tracker.py:9`.
- **Who.** Both.
- **Fix.** One lock helper in one module, on a cross-platform library such
  as `filelock` (W4's rule: a library first). Every module uses the helper.
  The library joins the third-party notices by itself. Three catches:
  - **Never point `filelock` at a data file.** It opens its lock file with
    `O_TRUNC` on macOS, Linux and Windows (read in its `_unix.py` and
    `_windows.py`), which empties the file. Always lock a separate
    `<file>.lock`.
  - **The Answer bank locks its own file** (`answer_bank.py:207`, `:226`:
    "no lock file beside it"). It needs a lock file beside it, for the
    catch above, and because a lock on Windows also stops other processes
    from reading the locked file.
  - **`filelock` has only exclusive locks.** The Answer bank's read takes a
    shared lock (`LOCK_SH`, `answer_bank.py:207`). It takes the exclusive
    lock instead: reads then wait for each other, and a read is short.
    `repairer.py:247`'s try-once lock (`LOCK_NB`) is `filelock`'s
    `timeout=0`.
  - On macOS and Linux, `filelock` waits by polling every 0.05 s, where
    `flock` waited in the kernel. A wait can take that much longer.
- **Done when.** A test imports `apply.cli`, `apply.first_run` and
  `apply.plain.seed_setup` with `fcntl` blocked (its fault: a module
  imports `fcntl` again). It runs in the fast list on Ubuntu, so it guards
  Windows before a Windows job exists. And the new test that writes the
  Tracker from two processes passes (section 6).

### P2. "Is it still running?" (`os.kill(pid, 0)`)

- **What it is.** Apply asks whether a process still runs: a Worker's
  Chrome, or an Apply window. On macOS and Linux, signal 0 checks and sends
  nothing.
- **Where.** `browsers.py:104` (in `chrome_pid`), `into.py:43` (`windows`),
  `plain/launcher.py:420` (`Chrome.poll`), `cli.py:513`, and the
  developer-only `dashboard.py:2318` and `dock_app.py:131`.
- **What breaks.** On Windows, `os.kill` is not a check. Signal 0 is
  `CTRL_C_EVENT` there, which tries to send a Ctrl-C to a console process
  group. Any other signal ends the process at once. Neither tells whether
  a process runs.
- **Who.** Both.
- **Fix.** `psutil.pid_exists(pid)`. psutil is already a dependency. Where
  a reused PID matters, also check that the process is the one Apply means,
  as `orphan` (`plain/launcher.py:489-505`) and `Desk.chrome`
  (`plain/seed_setup.py:153-163`) already do with its `--user-data-dir`.
- **Done when.** No `os.kill(pid, 0)` is left, and `tests/test_each_os.py`
  has a case for each OS.

### P3. Which Chrome has a profile open (`SingletonLock`)

- **What it is.** Apply finds the PID of the Chrome that has a profile
  open. With it, Apply knows that a profile is in use, stops an orphan
  Chrome, brings a Worker forward, and, in the seed wizard, sees that the
  seed's Chrome is open.
- **Where.** `browsers.chrome_pid` (`browsers.py:100-107`) reads the
  profile's `SingletonLock` link. The end of the link's target is the PID.
  Its callers: `in_use` (`browsers.py:95-97`), `browsers.py:210`, `:275`,
  `:280`, `PlainWorkers.idle` (`plain/launcher.py:176-178`), `launch`
  (`:313`), `start_in_background` (`:461`), `orphan` (`:493`), and
  `Desk.chrome` (`plain/seed_setup.py:156`).
- **What breaks.** Chrome makes `SingletonLock` on macOS and Linux only.
  On Windows a profile has a `lockfile`, with no PID in it. So `chrome_pid`
  always returns None. Every profile looks free, no orphan is ever found,
  and the seed wizard thinks Chrome never opened.
- **Who.** Both.
- **Fix.** On every OS, use psutil to find the browser process (no
  `--type=` switch) whose `--user-data-dir` is this profile, as `orphan`
  already checks. This needs no per-OS code. It reads every process's
  arguments, so measure its time with many processes running, and handle
  `AccessDenied` for other users' processes. If the time matters, keep
  `SingletonLock` as the fast path where it exists.
- **Done when.** `in_use` and the seed wizard see a running Chrome on
  Windows, and `tests/test_each_os.py` has a case for each OS.

### P4. The channel between Apply and the hosts (Unix socket)

- **What it is.** Apply's Bridge listens on a socket file, `workers.sock`,
  that only the user can read (0600). Each Worker's host connects to it
  and relays the extension's messages. The MCP tools use sockets the same
  way.
- **Where.** `plain/bridge.py:265` and `:273` (the Bridge),
  `plain/host.py:46` (the host), `plain/mcp.py:48`, `plain/tools.py:447`.
  The fallback folders use `os.getuid()` (`plain/bridge.py:98`,
  `plain/tools.py:73`).
- **What breaks.** Python on Windows has no `socket.AF_UNIX`, and `os` has
  no `getuid`. So no plain Worker can talk to Apply.
- **Who.** Both, for plain Workers. CDP Workers don't use the channel.
- **Fix: options.**
  - `multiprocessing.connection` (standard library): one API that is a
    Unix socket on macOS and Linux and a named pipe on Windows. The host
    uses only the standard library today, and it can stay that way. Its
    messages have their own length header, so the host changes its
    framing to and from Chrome's in one place.
  - A named pipe through `pywin32`, as F4's table says. This is a new
    dependency and Windows-only code.
  - Not a port on `127.0.0.1`: the app opens no port (D11).
  - Whichever you choose, the channel must refuse other users of the
    computer, as the 0600 socket does. A named pipe's default rights let
    every user read it. `multiprocessing.connection`'s `authkey`, or a
    security descriptor on the pipe, closes that.
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
  (`plain/launcher.py:524-532`).
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
| P1 file locks | A library (`filelock`): the same code on every OS |
| P2 "is it still running?" | A library (`psutil.pid_exists`): the same code on every OS |
| P3 profile lock | A library (psutil finds the Chrome): the same code on every OS |
| P4 channel | The standard library (`multiprocessing.connection`): one API, a socket on macOS and Linux and a named pipe on Windows |
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
| P1 | New: two processes write the Tracker at the same time, and both writes are there after. No test checks this today | The lock does nothing | The fast list |
| P1 | New: import `apply.cli`, `apply.first_run` and `apply.plain.seed_setup` with `fcntl` blocked | A module imports `fcntl` again | The fast list, on Ubuntu, before any Windows job |
| P2 | `tests/test_each_os.py`, `tests/test_into.py`: a live PID and a dead PID; the check never stops the process | The check stops a live process, or misses it | The fast list |
| P3 | `tests/test_plain_orphans.py`, `tests/test_each_os.py`: the profile's own Chrome is found; a helper process (`--type=`), another profile's Chrome and a reused PID never count | Another process is taken for the profile's Chrome | The fast list |
| P4 | `tests/test_plain_bridge.py` on the new channel: a hello, a message over 512 KiB, and a client without the key, which is refused | A client that isn't Apply's host gets in | The fast list, on every OS |
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
- **A Windows job in CI.** Add a `windows-latest` job for the fast list
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
| M1 | A developer runs CDP Workers | P1, P2, P3 | `worker_mode: cdp` | Apply starts; every host fills except Lever, SmartRecruiters and Workable |
| M2 | A developer runs plain Workers, with no seed | P4, P5, P6, P9 | `plain_chrome: testing` | Every host fills; a developer never needs the seed |
| M3 | A user runs the app | P7, P8, P10, P11 | the Student build | The download, the seed in Google Chrome, first run |

The store copy (W6) is not Windows work. When it ships, it changes P8's
clicks on every OS.

## 8. Open questions

- **Is Chrome for Testing right for students?** If it is, students need no
  seed at all. D21's reason against it ("Chrome for Testing can't turn on
  Allow User Scripts") has been out of date since KAN-839 removed user
  scripts. Not checked yet: its bot signals on the protected hosts. Also,
  Google builds it for testing, and it doesn't update itself.
- Which registry key does Chrome for Testing read for native hosts? It may
  not be Google Chrome's key.
- Does Chrome save when `taskkill` with no `/F` stops it?
- Does `--no-startup-window` keep Chrome running on Windows?
- How long does it take psutil to find a profile's Chrome when many
  processes run?
