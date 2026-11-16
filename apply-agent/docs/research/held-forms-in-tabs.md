# Held forms in tabs of a CDP Worker

**Status (2026-11-15):** Research only, nothing built. KAN-865. **The measurements are not run yet.** Chrome for Testing aborts as it starts inside the Sandcastle sandbox (below), so the tables have no numbers. The helper `tools/held_forms_tabs.py` is written and passes ruff; run it on a Mac outside the sandbox and fill in the tables. Section 4 (reading the code) is done.

Tried on a Mac with macOS 26.6.2 (arm64), Chrome for Testing 156.0.8078.4 from Playwright (`chromium-1248`), on branch `sandcastle/sequential-reviewer/1794787673834`.

**The idea.** A CDP Worker starts a new Chrome for each Application (`WorkerBrowsers.open`) and keeps it until the form is done. A held form keeps its Worker until its window is closed (`rehearsal.py`), so with two Workers, two held forms stop the run. Plain Workers already keep a held form in one tab and fill the next form in another. Can CDP Workers do the same?

## Why nothing was measured

Each start of Chrome for Testing, headed, with `WorkerBrowsers.launch_options` (channel None, `chromium_sandbox: True`), ended at once:

```
[ERROR:third_party/crashpad/crashpad/util/mac/xattr.cc:41] getxattr size org.chromium.crashpad.database.initialized on file /Users/<user>/Library/Application Support/Google/Chrome for Testing/Crashpad: Operation not permitted (1)
Received signal 6
<process did exit: exitCode=null, signal=SIGABRT>
```

The sandbox lets no process write to `~/Library/Application Support`, and Chrome aborts. The issue says not to work around the sandbox, so the run stopped here.

## How to run the helper

From `apply-agent/`, with `git submodule update --init` and `uv run playwright install chromium` done once:

```
uv run python tools/held_forms_tabs.py ticks                 # section 1's frames, ticks and screencast, no form
uv run python tools/held_forms_tabs.py fill --form lever-immuta   # section 2
uv run python tools/held_forms_tabs.py memory --held 5       # section 3
```

Each case starts its own Chrome on a scratch profile under the temp folder and closes it after. The saved form is served on 127.0.0.1 by `plain.demo.replay`, which refuses every POST, and is filled as Test Person. Nothing presses Submit.

**Playwright's own flags.** Playwright adds `--disable-background-timer-throttling`, `--disable-renderer-backgrounding` and `--disable-backgrounding-occluded-windows` to every Chrome it launches (seen in its launch line), so a CDP Worker runs with all three today. The helper's "Chrome defaults" cases take them out with `ignore_default_args`; the last case keeps them, as Workers run.

## 1. Does a background tab keep running and drawing?

A page that counts animation frames (`requestAnimationFrame`) and timer ticks (`setInterval`, every 0.1 s), 3 s each, with the held form's tab in front. Screencast: `Page.startScreencast` frames from the page behind while a box on it changes every 50 ms.

| Case | Frames behind | Ticks behind | `visibilityState` | Screencast frames |
|---|---|---|---|---|
| Chrome defaults, tab | not run | not run | not run | not run |
| Chrome defaults + no-throttle flags, tab | not run | not run | not run | not run |
| Chrome defaults, window | not run | not run | not run | not run |
| As Workers run (Playwright flags), tab | not run | not run | not run | not run |

## 2. Does a form fill correctly behind?

`lever-immuta` filled in front, then the same form filled in a second tab or window behind it.

| Case | Answered | Shown on the page | `readback_problems` | Seconds |
|---|---|---|---|---|
| In front (each case's first form) | not run | not run | not run | not run |
| Chrome defaults, tab | not run | not run | not run | not run |
| Chrome defaults + no-throttle flags, tab | not run | not run | not run | not run |
| Chrome defaults, window | not run | not run | not run | not run |
| As Workers run (Playwright flags), tab | not run | not run | not run | not run |

## 3. What each held form costs in memory

One Worker's Chrome, as Workers run; after each filled form, the total resident memory of its browser process and every child (`psutil`).

| Held forms | Total resident memory | Processes |
|---|---|---|
| 0 (one blank tab) | not run | not run |
| 1 | not run | not run |
| 2 | not run | not run |
| 3 | not run | not run |
| 4 | not run | not run |
| 5 | not run | not run |

## 4. How plain Workers do it, and whether CDP Workers can copy it

Read from the code, 2026-11-15.

| | Plain Worker | CDP Worker today |
|---|---|---|
| Chrome per Worker | One, started on the first form and kept (`PlainSite`) | One per Application: `open()` launches a persistent context and closes it after (`WorkerBrowsers.open`) |
| Next form while one is held | A new tab in the same Chrome. `_open[worker]` holds each tab a form holds now; only blank tabs close (`PlainSite.open`, `_leave_blank`) | Not possible: the profile is open in the held form's Chrome, and `open()` refuses a profile in use (`ProfileInUse`) |
| Background flags | `--disable-backgrounding-occluded-windows` only (`launcher.FLAGS`), so a covered window keeps painting | All three of Playwright's, above |
| Guards | Reset only when no other form is open in the Worker (`guards.reset` if not `others`) | Per page: `submit_guard.on_open(page)` before the first load |

**Can CDP Workers copy it?** Yes, in shape. `WorkerBrowsers` would keep each Worker's `BrowserContext` open across Applications and give the next form `context.new_page()`, with a set of held tabs per Worker as `PlainSite._open` has. The guard needs no change: it is set per page. Two points need care. Playwright's sync API is bound to the thread that started it, while each form runs on a thread of its own today, so the kept context needs one owner thread. And `trace.watch(context)`, `_ENDPOINTS` and the focus keeper's watch are per context today, and would move to per page. Whether a form behind fills as well as one in front is section 2's question, still open.

## Verdict

Not known yet. The code allows tabs in a kept Chrome, and CDP Workers already run with Playwright's three no-throttle flags. Sections 1 to 3 must be run outside the sandbox before anyone builds it.
