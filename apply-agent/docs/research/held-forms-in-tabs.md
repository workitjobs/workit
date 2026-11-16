# Held forms in tabs of a CDP Worker

**Status (2026-11-17):** Research only, nothing built. KAN-865 (sections 1 to 5), then KAN-876 (sections 6 to 9: every saved form, Workday's steps, the keep-alive and memory behind a tab and behind a window). Measured on a Mac (one run, 2026-11-15) and in a Linux container (2026-11-16 and 2026-11-17). The helper `tools/held_forms_tabs.py` repeats every measurement.

Two machines, both with Chrome for Testing 156.0.8078.4 from Playwright 1.64.0 (`chromium-1248`), headed, with the CDP Workers' launch options (`WorkerBrowsers.launch_options`):

- **Mac:** macOS 26.6.2, arm64, outside the Sandcastle sandbox. Its display draws at 120 Hz, so a page in front counts about 360 frames in 3 s.
- **Container:** Sandcastle's `sandcastle-browser` image, Debian 12, Linux arm64, 14 cores, 7.7 GiB, a virtual screen (Xvfb on `DISPLAY=:99`) at 60 Hz, so about 180 frames in 3 s. Chrome's own process sandbox can't start there (no user namespaces: `No usable sandbox!`), so these runs pass `--no-chrome-sandbox`, which turns `chromium_sandbox` off. That is the one change from the Workers' options. Linux has no macOS window cover, so what `--disable-backgrounding-occluded-windows` does on the Mac is not tested in the container.

**The idea.** A CDP Worker starts a new Chrome for each Application (`WorkerBrowsers.open`) and keeps it until the form is done. A held form keeps its Worker until its window is closed (`rehearsal.py`), so with two Workers, two held forms stop the run. Plain Workers already keep a held form in one tab and fill the next form in another. Can CDP Workers do the same?

## How to run the helper

From `apply-agent/`, with `git submodule update --init` and `uv run playwright install chromium` done once:

```
uv run python tools/held_forms_tabs.py ticks                 # section 1, under Playwright
uv run python tools/held_forms_tabs.py raw                   # section 2, Chrome with no Playwright
uv run python tools/held_forms_tabs.py fill --form lever-immuta   # section 3
uv run python tools/held_forms_tabs.py memory --held 5       # section 4 (add --windows for section 9)
uv run python tools/held_forms_tabs.py sweep --out rows.jsonl     # section 6, every saved form
uv run python tools/held_forms_tabs.py workday                    # section 7
uv run python tools/held_forms_tabs.py keepalive                  # section 8, 10 minutes
```

Add `--no-chrome-sandbox` in a container with no user namespaces. Each case starts its own Chrome on a scratch profile under the temp folder and closes it after. The saved form is served on 127.0.0.1 by `plain.demo.replay`, which refuses every POST, and is filled as Test Person. Nothing presses Submit.

**Playwright's own flags.** Playwright adds `--disable-background-timer-throttling`, `--disable-renderer-backgrounding` and `--disable-backgrounding-occluded-windows` to every Chrome it launches, so a CDP Worker runs with all three today. The "Chrome defaults" cases take them out with `ignore_default_args`; the last case keeps them, as Workers run.

**A bug fixed in the helper (2026-11-16).** The first Mac run counted 3 screencast frames in 3 s, in front too. Playwright's sync API delivers a CDP event (`Page.screencastFrame`) only while the script is inside a Playwright call, and the helper waited with `time.sleep`, so frames were neither delivered nor acknowledged. It now waits with `page.wait_for_timeout`, and a page in front gives 60 frames in 3 s. The Mac's screencast numbers are left out below.

## 1. Does a page behind keep running and drawing, under Playwright?

A plain page that counts animation frames (`requestAnimationFrame`) and timer ticks (`setInterval`, every 0.1 s), 3 s each, with the front page's tab or window in front. Screencast: `Page.startScreencast` frames from the page behind while a box on it changes every 50 ms. In front, every case gave about 180 frames, 30 ticks and 60 screencast frames (container).

| Case | Machine | Frames behind | Ticks behind | `visibilityState` | Screencast frames behind |
|---|---|---|---|---|---|
| Chrome defaults, tab | Mac | about 360 | 30 | visible | (bug, above) |
| Chrome defaults, tab | Container | 180 | 30 | visible | 60 |
| Chrome defaults + no-throttle flags, tab | Mac | about 360 | 30 | visible | (bug) |
| Chrome defaults + no-throttle flags, tab | Container | 182 | 30 | visible | 60 |
| Chrome defaults, window | Mac | about 360 | 30 | visible | (bug) |
| Chrome defaults, window | Container | 181 | 30 | visible | 60 |
| As Workers run (Playwright flags), tab | Mac | about 360 | 30 | visible | (bug) |
| As Workers run (Playwright flags), tab | Container | 182 | 30 | visible | 60 |

Under Playwright, a page behind runs, draws and streams to a tile as one in front does, with or without the flags.

## 2. Why a page behind says "visible": Playwright's focus emulation

Playwright sends `Emulation.setFocusEmulationEnabled {enabled: true}` to every page it attaches to (`crPage.ts`, skipped only for its internal `noDefaults` connections). That one call makes Chrome treat the tab as shown. `raw` starts the same Chrome with two tabs and no CDP client, and reads each page's own counts from its title through `/json/list`, which attaches to nothing. Then it attaches Playwright (`connect_over_cdp`). Container, 3 s each:

| Case | Tab behind, no client | Tab behind, Playwright attached |
|---|---|---|
| Chrome defaults | hidden, 0 frames, 3 ticks | visible, 178 frames, 30 ticks |
| `--disable-background-timer-throttling` `--disable-renderer-backgrounding` | hidden, 0 frames, 30 ticks | visible, 180 frames, 30 ticks |

A one-off check with raw CDP (no Playwright, Node's `WebSocket`) named the call: `Runtime.enable` on the tab behind left it hidden; `Emulation.setFocusEmulationEnabled {enabled: true}` alone made it visible with full frames, and `{enabled: false}` made it hidden again. With the tab hidden, `Page.startScreencast` sent 1 frame in 7 s. A second CDP session can't turn it off while Playwright's own session keeps it on: `{enabled: false}` from `new_cdp_session` left the page visible.

**For CDP Workers:** the result holds. They run under Playwright (`launch_persistent_context`), and each page they open gets focus emulation. A tab behind stays visible, runs its timers, draws, and gives the tile its live view. **Outside Playwright**, a Worker's tab behind is hidden, draws nothing and sends the tile nothing; the no-throttle flags bring back its timers only. A tab of a plain Worker gets focus emulation only while the Worker extension's typing attachment holds it (`worker-extension/ops/typing.js`, `attach`); otherwise it is such a tab.

## 3. Does a form fill correctly behind?

`lever-immuta` filled in front, then the same form filled in a second tab or window behind it. In every case, on both machines, in front and behind alike: 21 questions, 14 answered, 14 shown on the page, 0 `readback_problems`, 1 left (Lever's location search, which needs Lever's live API), 0.7 s.

| Case | Machine | Form behind: `visibilityState` while filling | Frames behind after the fill | Ticks | Screencast frames |
|---|---|---|---|---|---|
| Chrome defaults, tab | Container | visible | 12 | 30 | 60 |
| Chrome defaults + no-throttle flags, tab | Container | visible | 12 | 30 | 61 |
| Chrome defaults, window | Container | visible | 181 | 30 | 61 |
| As Workers run (Playwright flags), tab | Container | visible | 12 | 30 | 61 |

One thing is still open. On the saved form (an `http://127.0.0.1` page, not the plain `data:` page of section 1), a tab behind drew few animation frames after a few seconds: 55, then 3, in two 3 s counts with no fill; 12 after a fill. A window behind drew 181. Its timers ran at full speed, it stayed visible, the fill was the same, and the tile still got 60 frames, since a screencast makes Chrome draw. The cause was not found. A page whose script waits on animation frames could run slower in a tab behind than in a window.

## 4. What each held form costs in memory

One Worker's Chrome, as Workers run; after each filled `lever-immuta`, the total resident memory of its browser process and every child (`psutil`). Resident memory counts shared pages in each process, so the totals are higher than the memory really used; the steps between rows are the useful number.

| Held forms | Mac | Mac processes | Container | Container processes |
|---|---|---|---|---|
| 0 (one blank tab) | 926 MiB | | 906 MiB | |
| 1 | 1446 MiB | 10 | 1463 MiB | 12 |
| 2 | 1511 MiB | 11 | 1717 MiB | 13 |
| 3 | 1807 MiB | 12 | 1965 MiB | 14 |
| 4 | 2028 MiB | 13 | 2195 MiB | 15 |
| 5 | 2208 MiB | 14 | 2421 MiB | 16 |

Each held form after the first adds one renderer process and about 190 to 250 MiB. The first form costs about 550 MiB over a blank Chrome (it starts the network and GPU work too). A new Chrome per form, as CDP Workers do today, costs the 906 to 926 MiB base again for each.

## 5. How plain Workers do it, and whether CDP Workers can copy it

Read from the code, 2026-11-15.

| | Plain Worker | CDP Worker today |
|---|---|---|
| Chrome per Worker | One, started on the first form and kept (`PlainSite`) | One per Application: `open()` launches a persistent context and closes it after (`WorkerBrowsers.open`) |
| Next form while one is held | A new tab in the same Chrome. `_open[worker]` holds each tab a form holds now; only blank tabs close (`PlainSite.open`, `_leave_blank`) | Not possible: the profile is open in the held form's Chrome, and `open()` refuses a profile in use (`ProfileInUse`) |
| Background flags | `--disable-backgrounding-occluded-windows` only (`launcher.FLAGS`), so a covered window keeps painting | All three of Playwright's, above, and focus emulation on each page (section 2) |
| Guards | Reset only when no other form is open in the Worker (`guards.reset` if not `others`) | Per page: `submit_guard.on_open(page)` before the first load |

**Can CDP Workers copy it?** Yes. `WorkerBrowsers` would keep each Worker's `BrowserContext` open across Applications and give the next form `context.new_page()`, with a set of held tabs per Worker as `PlainSite._open` has. The guard needs no change: it is set per page. Two points need care. Playwright's sync API is bound to the thread that started it, while each form runs on a thread of its own today, so the kept context needs one owner thread. And `trace.watch(context)`, `_ENDPOINTS` and the focus keeper's watch are per context today, and would move to per page.

## Verdict

**It works, in tabs, with the flags CDP Workers have today.** Under Playwright, a form fills behind a held form exactly as in front (the same answers, no read-back problems, the same time), its timers run, and the tile's live view gets every frame, with or without the no-throttle flags. The reason is Playwright's focus emulation, not the flags: it keeps every page it drives visible. So the plan holds only while Playwright (or another CDP client that turns focus emulation on) drives each tab; a tab with no such client goes hidden and stops drawing. Tabs and windows fill the same; a window behind also keeps full animation frames, which a tab behind on the saved form did not (section 3, cause not found), so a window is the safer choice if a form's script waits on animation frames. Each held form costs about 200 to 250 MiB in a kept Chrome, against about 900 MiB for a new Chrome per form. Not tested: the Mac's window cover in the container, and a form other than `lever-immuta`.
