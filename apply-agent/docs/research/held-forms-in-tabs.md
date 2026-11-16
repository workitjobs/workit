# Held forms in tabs of a CDP Worker

**Status (2026-11-16):** Research only, nothing built. KAN-865 (sections 1 to 5), then KAN-876 (sections 6 to 9: every saved form, Workday's steps, the keep-alive and memory behind a tab and behind a window). Measured on a Mac (one run, 2026-11-15) and in a Linux container (2026-11-16). The helper `tools/held_forms_tabs.py` repeats every measurement.

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

One thing is still open. On the saved form (an `http://127.0.0.1` page, not the plain `data:` page of section 1), a tab behind drew few animation frames after a few seconds: 55, then 3, in two 3 s counts with no fill; 12 after a fill. A window behind drew 181. Its timers ran at full speed, it stayed visible, the fill was the same, and the tile still got 60 frames, since a screencast makes Chrome draw. The cause was not found. Section 7 found what it costs: Playwright clicks only an element stable over two animation frames, so each click in a tab behind waits about 2 s.

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

## 6. Every saved form, behind a held form

`sweep`, container, 2026-11-16, as Workers run (Playwright's flags). For each saved form with a `page.har`, one Worker's Chrome fills it in front, where it then stays as the held form. Then the same form fills in a new tab behind it, then in a new window behind it, and last, the control, in a new tab in front of them. The fill is section 3's. For each case the table gives: answered, shown on the page, read-back problems, left (a field the engine could not fill and was dropped), seconds. Questions are the same in every case. The Fill engine's fixtures held 29 such forms at this commit; the issue counted 31.

| Saved form | Questions | Front | Tab behind | Window behind | Again, in front |
|---|---|---|---|---|---|
| `ashby-amplify` | | not filled in front: NoForm | | | |
| `ashby-cohere` | | not filled in front: NoForm | | | |
| `ashby-harvey` | | not filled in front: NoForm | | | |
| `ashby-patreon` | | not filled in front: NoForm | | | |
| `ashby-semgrep` | | not filled in front: NoForm | | | |
| `ashby-skydio` | | not filled in front: NoForm | | | |
| `ashby-snowflake` | | not filled in front: NoForm | | | |
| `bamboohr-lunaroutpost` | | not filled in front: no Filler | | | |
| `eightfold-lockheed` | | not filled in front: the form never showed | | | |
| `eightfold-netflix` | | not filled in front: the form never showed | | | |
| `greenhouse-anduril` | 26 | 21, 21, 0, 2, 13.3 | 21, 21, 0, 2, 13.3 | 21, 21, 0, 2, 13.3 | 21, 21, 0, 2, 13.3 |
| `greenhouse-arc` | 23 | 15, 15, 0, 4, 33.0 | 15, 15, 0, 4, 33.1 | 15, 15, 0, 4, 33.0 | 15, 15, 0, 4, 33.0 |
| `greenhouse-coinbase` | 54 | 34, 34, 0, 3, 23.7 | 34, 34, 0, 3, 23.7 | 34, 34, 0, 3, 23.6 | 34, 34, 0, 3, 23.7 |
| `greenhouse-datacor` | 21 | 16, 16, 0, 1, 2.7 | 16, 16, 0, 1, 2.5 | 16, 16, 0, 1, 2.8 | 16, 16, 0, 1, 2.8 |
| `greenhouse-purestorage` | 31 | 23, 23, 0, 3, 23.3 | 23, 23, 0, 3, 23.4 | 23, 23, 0, 3, 23.4 | 23, 23, 0, 3, 23.3 |
| `greenhouse-uberfreight` | 17 | 6, 3, 3, 1, 39.2 | 6, 3, 3, 1, 39.3 | 6, 3, 3, 1, 39.2 | 6, 3, 3, 1, 39.3 |
| `lever-belvedere` | 35 | 25, 25, 0, 1, 0.8 | 25, 25, 0, 1, 0.8 | 25, 25, 0, 1, 0.8 | 25, 25, 0, 1, 0.8 |
| `lever-hermeus` | 35 | 22, 22, 0, 1, 0.7 | 22, 22, 0, 1, 0.7 | 22, 22, 0, 1, 0.7 | 22, 22, 0, 1, 0.7 |
| `lever-immuta` | 21 | 14, 14, 0, 1, 0.7 | 14, 14, 0, 1, 0.7 | 14, 14, 0, 1, 0.7 | 14, 14, 0, 1, 0.7 |
| `lever-rhombus` | 18 | 16, 16, 0, 1, 0.8 | 16, 16, 0, 1, 0.8 | 16, 16, 0, 1, 0.8 | 16, 16, 0, 1, 0.8 |
| `lever-shieldai` | 43 | 27, 27, 0, 1, 0.8 | 27, 27, 0, 1, 0.8 | 27, 27, 0, 1, 0.8 | 27, 27, 0, 1, 0.8 |
| `lever-xcimer` | 22 | 16, 16, 0, 1, 0.7 | 16, 16, 0, 1, 0.7 | 16, 16, 0, 1, 0.7 | 16, 16, 0, 1, 0.7 |
| `oracle-macys` | | not filled in front: the engine has no parser for oracle | | | |
| `waymo-depotautomation` | | not filled in front: the engine has no parser for waymo | | | |
| `workable-enfos` | 13 | 10, 10, 0, 1, 30.7 | 10, 10, 0, 1, 30.4 | 10, 10, 0, 1, 30.3 | 10, 10, 0, 1, 30.4 |
| `workable-perryhomes` | 60 | 29, 29, 0, 3, 31.6 | 29, 14, 15, 3, 30.4 | 29, 14, 15, 3, 30.4 | 29, 14, 15, 3, 30.4 |
| `workable-scout` | 19 | 14, 14, 0, 1, 30.7 | 14, 14, 0, 1, 30.4 | 14, 14, 0, 1, 30.4 | 14, 14, 0, 1, 30.4 |
| `workday-caci` | | step by step: section 7 | | | |
| `workday-xcel` | | step by step: section 7 | | | |

Each page was visible behind (`visibilityState`), in a tab and in a window. 15 forms filled on one page, and section 7 fills the 2 Workday forms step by step. The other 12 could not be filled even in front and were skipped, as the issue says:

- **Ashby (7):** the page draws its form from Ashby's GraphQL, which is a POST. The replay refuses every POST, so the page says "Application submission is unavailable" and the engine finds no form.
- **Eightfold (2):** the page loads its questions with a POST (`/api/application/v2/questions`), refused the same way. The form never shows.
- **BambooHR, Oracle, Waymo (3):** the Fill engine has no Filler for them (the BambooHR fixture's README says so). Oracle's form is used in section 8 for the keep-alive only.
- **Workday (2):** the one-page fill stops at the posting ("showed no step name"); a Workday form fills step by step after a sign-in. Section 7 does that.

Every form that filled, filled the same in front, behind a tab and behind a window, except `workable-perryhomes`, below. The seconds match too, to a tenth. `greenhouse-uberfreight`'s 3 problems and the fields left are the saved forms' own: they are the same in front. About one Greenhouse load in three left the page unhydrated, in front as well as behind; the helper loads it again once (`tried`), and that happened in front and behind alike.

### `workable-perryhomes`: Workable's saved draft, not the tab behind

The form filled in front with no problem, then showed 15 read-back problems in the tab behind, the window behind and the control in front: every field of the Work Experience and Education entries read back empty. The control in front failed too, so being behind is not the cause. Workable keeps a draft of each posting in the page's `localStorage` (`evergreen-persistence-<id>`). The second load of the same posting in the same Chrome profile restores the first fill's entries, and the engine's fill of the entries no longer lands. With the first page closed and the draft cleared, a second fill in the same Chrome gave 29 shown and 0 problems again. Clearing the draft while the first page is still open does not help: that page writes it again.

For held forms this matters only when one Worker fills the same Workable posting twice (Fill again, or a second form for the same posting). A CDP Worker's profile already keeps its `localStorage` across Applications today, so this is not new with tabs.

## 7. Workday's steps behind

`workday`, container, 2026-11-16, two runs. Each saved Workday posting is filled step by step by the Workday Filler (`WorkdayFiller`), as Apply does: the sign-in (an account made on the fake Workday, `tests/fake_workday.py`), then each step's questions, Save and Continue, and the wait for the next step's names (shown 1.5 s late, as Workday's are live), to Review. The fake Workday is routed in the page only. The one stop is the Filler's handoff for the terms box, which Apply never ticks: the helper ticks it as the applicant would, and goes on. Nothing was submitted (`submissions` 0 in every case).

| Form, case | Sign-in (s), run 1 / run 2 | Steps (s each), run 2 | Questions, answered, shown, problems | All (s), run 2 |
|---|---|---|---|---|
| `workday-caci`, front | 4.3 / 3.7 | 4.9, 1.9, 2.6, 1.7, 3.3, 1.9 | 21, 21, 21, 0 | 20.1 |
| `workday-caci`, tab behind | **15.0 / 15.1** | 4.9, 1.9, 2.7, 1.8, 3.3, 1.9 | 21, 21, 21, 0 | 31.5 |
| `workday-caci`, window behind | 3.7 / 3.7 | 4.9, 1.9, 2.7, 1.7, 3.3, 1.9 | 21, 21, 21, 0 | 20.0 |
| `workday-caci`, again, in front | 3.7 / 3.7 | 4.9, 1.9, 2.6, 1.7, 3.3, 1.9 | 21, 21, 21, 0 | 20.0 |
| `workday-xcel`, front | 4.3 / 3.7 | 4.9, 1.9, 2.7, 1.7, 3.3, 1.9 | 21, 21, 21, 0 | 20.1 |
| `workday-xcel`, tab behind | **21.2 / 23.3** | 4.9, 1.9, 2.7, 1.7, 3.3, 1.9 | 21, 21, 21, 0 | 39.7 |
| `workday-xcel`, window behind | 3.7 / 3.7 | 4.9, 1.9, 2.7, 1.8, 3.3, 1.9 | 21, 21, 21, 0 | 20.2 |
| `workday-xcel`, again, in front | 3.7 / 3.8 | 4.9, 1.9, 2.6, 1.7, 3.3, 1.9 | 21, 21, 21, 0 | 20.1 |

**Next and each step's wait work behind as in front.** All six steps loaded in order (`step loads` 1 to 6), every step took the same time to a tenth, and the read-back is the same. **The sign-in was 4 to 6 times slower in a tab behind**, in both runs, and not in a window.

The cause is section 3's open item. Playwright clicks only an element that is "stable", the same box over two animation frames. A tab behind a held form, on a saved form's page, drew 3 animation frames in 3 s, where the same page in front or in a window drew 181. Ten trial clicks (`click(trial=True)`: every check, no click) on the same button took 20.1 s in the tab behind, 0.36 s in front and 0.35 s in a window. The sign-in makes several Playwright clicks (Apply, Sign in with email, the view switch, the send), so it pays about 2 s for each. The Fill engine fills by page script and makes no Playwright click, so a fill behind (section 6) did not slow down. Why the steps after sign-in did not slow down was not found; they may have drawn frames while their routed pages loaded.

## 8. The keep-alive behind

`keepalive`, container, 2026-11-16: `oracle-macys` held behind a tab and behind a window of one Worker's Chrome, with a third tab in front, each held page with its own `keepalive.Keeper` for 10 minutes, `PING_S` cut from 240 s to 30 s. On 127.0.0.1 the Keeper uses the generic rules (`ANY`): a mouse move and a GET of the page's own URL each ping. At 5 minutes each held page showed a session dialog in the generic rules' words, with a "Continue session" button.

| | Behind a tab | Behind a window |
|---|---|---|
| Pings | 19 | 19 |
| Each ping's GET reached the server | 19 of 19 (200) | 19 of 19 (200) |
| Each ping's mouse move reached the page (a window `mousemove` listener) | 9 of 9 before the stay press | 9 of 9 before the stay press |
| Mouse moves after the stay press | none, as the Keeper intends (`_quiet`) | none |
| Stay press | pressed "Continue session"; the page's button heard it and closed the dialog | the same |
| `visibilityState` at every ping | visible | visible |
| Keeper's hold after the press | "Apply pressed this site's 'Continue session'…" | the same |

Everything the Keeper does reaches a page behind a tab and behind a window. The page heard 1 trusted mouse move in the tab and 2 in the window beside the 9 synthetic ones: the stay press is a Playwright click, which moves the mouse.

**`ceSessionExpire` could not be checked on the saved form.** It stayed `[]` in both cases. Oracle's page code (`main-minimal.js`) writes it in `updateExpiredTime`, which returns at once when the page has no candidate `tokenId`; the token comes only after a candidate verifies their email, which the saved form never does. Oracle's handler is a `mousemove` listener on `window`, the same as the helper's own listener, which heard every one of the Keeper's moves. So the moves reach the place Oracle listens; that its stored time moves forward needs a signed-in Oracle form, live.

## 9. Memory for windows

`memory --windows`, container, 2026-11-16, `lever-immuta`, each held form in a window of its own; then `memory` in tabs, in the same container, for the comparison. Resident (as section 4) and unique memory (USS: the pages only that process holds, so nothing counts twice; it leaves out the shared pages, so the true cost is between the two).

| Held forms | Windows: resident | Windows: unique | Tabs: resident | Tabs: unique | Processes |
|---|---|---|---|---|---|
| 0 (one blank tab) | 920 MiB | 194 MiB | 922 MiB | 196 MiB | |
| 1 | 1513 MiB | 420 MiB | 1516 MiB | 424 MiB | 12 |
| 2 | 1803 MiB | 537 MiB | 1770 MiB | 518 MiB | 13 |
| 3 | 2087 MiB | 659 MiB | 2020 MiB | 616 MiB | 14 |
| 4 | 2378 MiB | 794 MiB | 2246 MiB | 701 MiB | 15 |
| 5 | 2637 MiB | 897 MiB | 2456 MiB | 768 MiB | 16 |

Each held form after the first adds one renderer process either way. In a window it adds about 105 to 135 MiB of unique memory (260 to 290 MiB resident); in a tab about 70 to 100 MiB (210 to 255 MiB resident). A window costs about 30 MiB more per held form: its own compositor and surfaces.

## Verdict

**Use a window for each form, in one kept Chrome per CDP Worker.** Under Playwright, every saved form that fills in front fills the same behind a held form, in a tab or in a window: 17 forms of 4 hiring systems (Greenhouse, Lever, Workable, and Workday step by step), the same answers, read-back and time (sections 6, 7). The one difference in the sweep, `workable-perryhomes`, is Workable's saved draft of a posting loaded twice in one profile, and it shows in front too. The keep-alive's pings, mouse moves and stay press reach a page behind a tab and behind a window alike (section 8). The reason to choose the window: a tab behind on a real hiring system's page draws about 1 animation frame a second, so each Playwright click there waits about 2 s, and Workday's sign-in took 4 to 6 times as long in a tab behind (section 7). Claude fill, Rescue, Next and every sign-in click through Playwright. A window behind draws in full, and costs about 30 MiB more per held form (section 9). Playwright's focus emulation is still what keeps either one visible (section 2), so the plan holds only while Playwright drives each page.

**A cap of 4 held forms per Worker on an 8 GB laptop with two Workers**, with the form being filled as the fifth window. One Worker's Chrome with 5 forms in windows held 0.9 GB of unique memory (2.6 GB resident, which counts shared pages more than once); two such Workers take about 1.8 to 2 GB, which leaves room beside macOS and the student's own Chrome on 8 GB. The base Chrome (about 420 MiB unique with its first form) is paid once per Worker, where a new Chrome per form pays it again for each. `lever-immuta` is a light page; a Greenhouse or Workday page holds more, so measure the cap again on the Mac with those before it is built.

Not tested: the Mac's window cover in the container (`--disable-backgrounding-occluded-windows` is on in every Worker), Ashby and Eightfold behind (their saved forms need a live API even in front), and Oracle's own session time moving forward (section 8).
