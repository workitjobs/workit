# Held forms after a Worker's Chrome crash

**Status (2026-11-16):** Research only, nothing built. KAN-866, beside KAN-865 (`held-forms-in-tabs.md`). The helper is `tools/held_forms_crash.py`.

Tested in the Sandcastle container: Linux arm64 (Docker), Chrome for Testing 156.0.8078.4 (Playwright 1.64.0, `chromium-1248`), headed on a virtual screen (Xvfb, `DISPLAY=:99`). On branch `sandcastle/sequential-reviewer/1794789423560`.

**The idea.** KAN-865 asks whether a Worker's Chrome can keep several filled forms in tabs, each waiting for the student's Submit. Then one Chrome crash ends every held form in it. This note measures what comes back today, and what Apply's own recovery brings back.

**Not tested: the Mac.** Chrome's session restore is the same code on every OS. But a Mac's quit and kill differ in ways the container can't show: the Dock, an app that stays open with no windows, a macOS restart that quits apps. Run the helper on a Mac before a decision that rests on a quit.

## How the cases ran

Two saved forms (the Fill engine's fixtures `lever-immuta` and `lever-shieldai`, each served on 127.0.0.1 by `plain.demo.replay`, which refuses every POST), each filled as Test Person in its own tab of one Worker. Nothing pressed a Submit. The helper then waited 5 s (`--settle`), ended the Worker's Chrome and started it again on the same profile as Apply starts it:

- **Plain Worker:** `PlainWorkers(kind="testing")` (`plain/launcher.py`): Chrome for Testing with `--load-extension`, `--restore-last-session` and `--no-startup-window`. Ended by SIGKILL of its browser process (a crash), or by `PlainWorkers.stop` (Apply's own stop: SIGTERM, a normal quit). Started again by `PlainWorkers.launch(0)`.
- **CDP Worker:** Playwright's `launch_persistent_context` with `WorkerBrowsers.launch_options` (`browsers.py`), as `WorkerBrowsers.open` starts it. Ended by SIGKILL of the Chrome that holds the profile, or by `context.close()` (Apply's own end of a CDP Worker). Started again the same way.

"Values back" counts each field that held a value before the end (text, list, box; never a file) and has the same value after it.

**Two switches only for the container** (`held_forms_crash.LINUX`): `--no-sandbox`, since the container has no user namespaces for Chrome's sandbox; and `--keep-alive-for-test`. Without the second, Chrome on Linux started with `--no-startup-window` exits at once with code 0, before the worker extension says hello: a plain Worker can't start on Linux at all. A Mac keeps a Chrome with no window running. **This is a finding for F4 (Windows and Linux):** plain Workers as they start today don't run on Linux.

## 1. A crash (SIGKILL): which tabs come back, and their values

| Worker | Tabs after the restart | `lever-immuta` (14 values) | `lever-shieldai` (27 or 28 values) |
|---|---|---|---|
| Plain | one blank tab (the window `launch` makes) | not back | not back |
| CDP | `about:blank` | not back | not back |

Neither Worker brings back a tab. The plain Worker's `--no-startup-window` opens no tab of the last session: by design, so no job page loads before Apply guards it (`docs/restart-recovery.md`). A CDP Worker starts with no session restore.

## 2. A normal quit, for comparison

| Worker | Tabs after the restart | `lever-immuta` | `lever-shieldai` |
|---|---|---|---|
| Plain (SIGTERM) | one blank tab | not back | not back |
| CDP (`context.close()`) | `about:blank` | not back | not back |

The same as a crash. Only the plain Worker's cookies come back across a quit (`--restore-last-session`, KAN-718), and across a crash for both Workers when they were written (below).

## 3. What Chrome itself kept

Not what Apply does: the helper's `--restore` option starts the Worker again with Chrome's own session restore on (a plain Worker without `--no-startup-window`; a CDP Worker with `--restore-last-session` added). This shows what a recovery could get from Chrome.

| Worker | End | Wait before the end | Tabs back | `lever-immuta` values | `lever-shieldai` values |
|---|---|---|---|---|---|
| Plain | quit | 5 s | both | 14 of 14 | 28 of 28 |
| CDP | quit | 5 s | both | 13 of 13 | 27 of 27 |
| Plain | kill | 1 s | both | 14 of 14 | 0 of 28 |
| Plain | kill | 3 s | both | 14 of 14 | 0 of 28 |
| Plain | kill | 5 s | both | 14 of 14 | 28 of 28 |
| Plain | kill | 10 s, 20 s | both | 14 of 14 | 28 of 28 |
| CDP | kill | 1 s, 3 s, 5 s | none | 0 | 0 |
| CDP | kill | 10 s, 20 s | both | 13 of 13 | 27 of 27 |

- Chrome keeps each tab's URL and its form values (the page state) in the profile's session file, and puts both back when it restores the session.
- A quit writes the session file at once. A crash keeps only what Chrome last wrote on its timer: the values of a form filled less than about 5 to 10 s before the crash are lost, or the whole tab with it. The plain Worker's first form was filled about 10 s before its second, so it was always kept.
- A restored tab is a job page that loads at once, before Apply guards it, and on its own server's terms: a form whose page wipes itself on load, or whose session ended, loses its values anyway. A saved form on 127.0.0.1 doesn't.

## 4. Apply's own recovery: `apply reopen` (KAN-720)

Tried with `tests/test_reopen.py -k killed` (two fake Greenhouse forms held in one plain Worker; Apply killed; `apply reopen` on the same profiles folder), through `held_forms_crash.py reopen`. The test ends the Worker's Chrome with SIGTERM; the helper's kill case sends SIGKILL instead.

In both cases Apply itself is killed (SIGKILL) first, as in the test. Two fixes were needed before the test could run here:

- `tests/reopen_child.py` (the Apply process the test kills) had no Question types since they moved to WorkIt (65e8156e), so both forms failed at setup ("Apply has no Question types yet"). It now copies the tests' `question-types.json` as `conftest.py` does. This failure is on `main` too: the test needs Chrome for Testing, and CI doesn't run it.
- The container's PID 1 (`sleep`) reaps no orphan, so a killed Chrome stayed a zombie, and the test's `os.kill(pid, 0)` took it for running. The helper makes itself the subreaper (`prctl`) and reaps them. A Mac has no such problem.

| End of the Worker's Chrome | Result |
|---|---|
| Quit (SIGTERM, as the test does) | Passed: both forms back held in one Worker, under their guards, with the planted answer from the Record, nothing sent |
| Crash (SIGKILL) | Passed: the same |

What each part restores, read from the code (`batch.py`, `rehearsal.Reopening`, `docs/restart-recovery.md`):

| | `apply reopen` | Chrome's session restore (section 3) |
|---|---|---|
| The page | Opened again from the posting's link, under the guards, in the Worker that held it | Its tab, loaded at once with no guard |
| The answers | Each answer the page showed when the Record was last saved (`batch.draft`); the rest are planned and filled again | Every value Chrome last wrote, the student's own edits too |
| A file (the resume) | Attached again by the fill | Never |
| An attestation, consent or signature | Left for the student (`send_click.ATTEST`) | Put back as it was |
| The student's edit to a field Apply filled | Lost: the Record keeps a new value only for a field that Needs you asked about (`on_page.Watch`, `_record_again`) | Kept, if Chrome wrote it before the crash |
| The held state | A new tile per form, "Reopened after Apply stopped", held for the student again | None: Apply doesn't know the tab |
| A job site's sign-in | The student signs in on the tile ("needs sign-in") | The cookies Chrome wrote |

The open-forms list (`APPLY_HOME/open-forms.json`) and the Records are Apply's files, so a Chrome crash leaves them whole. `apply reopen` is a command the student runs: nothing starts it when a Worker's Chrome crashes while Apply still runs.

## Verdict

**What a crash costs the student today:** every form held in that Chrome closes, with no tab and no value back, for a plain or a CDP Worker alike. A quit costs the same. With several held forms in tabs, one crash loses all of them at once. `apply reopen` brings each one back held, from its link and its Record, but only when the student runs it, and with the student's own edits to Apply's answers lost.

**What recovery would need to add, for held forms in tabs:**

1. **See the crash.** Apply knows a Worker's Chrome ended (the bridge's connection closes; Playwright's `disconnected`), but nothing reopens its held forms while Apply runs. It would start `apply reopen`'s path for that Worker's forms.
2. **Keep the student's edits.** Save each held form's page values into its Record as they change (the way `on_page.Watch` already does for Needs you fields), not only when the fill ends. Chrome's session file has them, but loses the last 5 to 10 s on a crash and gives them back on an unguarded page.
3. **Keep `--no-startup-window`.** Chrome's own restore brings the values back, but loads each job page before Apply guards it. Reading the session file to fill a guarded page again is possible, but it is Chrome's private format.
4. **For F4:** a plain Worker on Linux needs a way to stay running with no window before it can start there at all.

## How to run the helper

From `apply-agent/`, with `git submodule update --init` and `uv run playwright install chromium` done once:

```
uv run python tools/held_forms_crash.py chrome              # sections 1 and 2: both Workers, kill and quit
uv run python tools/held_forms_crash.py chrome --restore    # section 3 (add --settle 1, 3, 10 ...)
uv run python tools/held_forms_crash.py reopen              # section 4: tests/test_reopen.py -k killed, quit and kill
```

Each case starts its own Chrome on a scratch profile under the temp folder and stops it after. On Linux the helper adds the two container switches itself; for `reopen` it puts a wrapper Chrome for Testing that adds them in a temp `PLAYWRIGHT_BROWSERS_PATH`, so the test's own Workers start too.
