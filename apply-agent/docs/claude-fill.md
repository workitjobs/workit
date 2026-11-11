# Claude fill and form pages

Reference for Apply, reached from `apply-agent/CLAUDE.md`. Paths are relative to `apply-agent/`. A change in this area updates this file in the same PR.

## Claude fill

- Claude fill stops at the form's last step and names the button that
  sends; it never clicks it. A PreToolUse hook (`apply.send_click`, passed
  with `--settings` in `claude_cli.drive`) refuses a click Claude names as
  that button, with word to stop. A click the drive guard still blocked on
  the button Claude then names as the submit leaves the form filled
  (`claude_fill._only_its_submit`); any other block is a Handoff.
- Claude's stop for a captcha holds the fill only when Apply's own check
  sees the challenge or its box showing to a person (`captcha.shows`,
  `captcha.unsolved`; KAN-760, `docs/captchas-and-bot-blocks.md`). Else
  Claude is told that no challenge is open (`NO_CAPTCHA`) and drives once
  more, and a second such stop is a Handoff (`UNSEEN_CAPTCHA`). The rules
  tell Claude that an invisible captcha's frame or its words in the
  snapshot ("Please try again", "Verify") don't stop it.
- Claude's "blocked" on a page that shows a provider sign-in ("Sign in using Google" and the like) is
  a Needs sign-in Handoff, read by plain code, never Claude's free-text reason (KAN-763,
  `docs/sign-in.md`). Its pause goes on by itself once Lisul signs in.
- Only what the drive guard blocked during that drive stops it. A block of
  an earlier drive was its Handoff already: after Lisul's Resume, the next
  read or fill goes on (LinkedIn's SmartRecruiters page posts a form of its
  own while Claude reads it).
- A careers page that embeds a Greenhouse form goes to the Greenhouse Filler
  (`greenhouse.board_behind`): by `?gh_jid=`, or by a job id in its path
  that the job API says is shown on that same host (Roblox). Failing that,
  `embedded.form_behind` opens a page of no known job system, reads its
  frames (after one click on its Apply button outside any form) and sends an
  embedded Greenhouse, Lever or Ashby form to that system's Filler. Claude
  fill is only the fallback.
- A profile pop-up before the application is never the form's last page
  (KAN-647). When the button Claude names as the one that sends sits in an
  open dialog that is a profile step and nothing more
  (`submit_guard.PROFILE_DIALOG`: titled "Create your profile" or the like,
  naming no application, job or role; no file, essay, box, choice or
  password in it; and no form field of the page's own behind it), and the
  button names no application, plain code presses it
  (Microsoft's names it Submit; `_through_profile_step`) under
  `DriveGuard.let_profile_click()`, which lets that dialog's button through
  the drive and rehearsal guards and nothing else, waits for the dialog to
  go, and the fill goes on to the real form. A button that holds a frame
  is never pressed (`DriveGuard.may_press`, KAN-710).
- A form's Apply button sends, but for a posting's Apply that only opens the application (KAN-725,
  `opens`): TAL.net's posting posts a form of its anti-forgery token alone to `.../opp/<id>/apply/<lang>`.
  Only on a job system proven to open the form there and send nothing: TAL.net alone for now
  (`claude_fill.OPENS_ONLY`, and the guard's own `START_HOSTS`, kept the same; a host joins both only
  once its posting is proven so). Claude fill vouches for the page only at its first drive, on the
  Posting's own URL (`DriveGuard.let_start_click`), in the top frame alone. The vouch is the guards' own
  state (`start`, set by `submit_guard.control` in both guards, cleared by `arm()`), never a `window`
  flag: a page that sets `__applyStartClick`, or sends a control event without the run's token, changes
  nothing (KAN-710). Then Apply's own press of that button (a trusted click, or a plain Worker's marked
  one; never a page script's click) goes through once, while its words name no send, its form holds a
  hidden token (named as one and naming nothing that sends: no `finalSubmitToken`) and buttons and nothing else, bound for its own origin and no final URL, no field on the
  page holds an answer, and the page shows no draft, review or saved-profile apply (`DRAFT` in its text,
  `HEADED` in its title or headings). A key, input or change, a click on anything but that Apply or a
  cookie banner's button, or the page changing its URL by script (the `navigate` event) takes the word
  back. A frame takes back the top page's word by an event of its guard's (`__<key>Unvouch`), which any
  page may send, since it can only take the word away. Once the Apply went through, only that form's own
  submission goes, once, still a token alone: the guard sends its own copy of it (the hidden fields and the
  button's name), and each guard lets that one post leave (`startPost`, at its `navigate` event) only with
  those entries, to that form's target, and only one such post is let go at all (`startSent`), never one
  into a frame (PR 477's second review: the page's own copies, posted into a frame of its own, each went).
  Nothing else is posted to the site (its other subdomains too) from
  that page. A reopened form's and every later page's Apply stay blocked: the word is gone with the
  Posting's document. Elsewhere a posting's Apply may apply at once from a profile the site holds, in any
  words, so it stays blocked there. Without this, Claude's first click on TAL.net's posting was a Handoff
  with no field filled. Still open: an answer typed in another site's frame on the Posting's page can't
  take the word back, since that frame can't reach the top page's guard.
- A POST to a final application URL stays blocked under plain code's Next and profile clicks (KAN-639,
  `postsFinal`). A path ending in `/apply` is final by its name alone, so there a Next goes on only when
  the page says steps remain ("Step 2 of 5", or a list past its `aria-current=step` item) where a person
  sees it (a readable size, on the page, not clipped away: KAN-710), the form has no button that sends
  (KAN-656), and the button plain code pressed sends it: never a script's post or a step list's link.
- Plain code's press (KAN-710): `DriveGuard.let_account_click(element)` arms the account click with the
  element, in that element's frame alone, on a plain Worker too. There the press is the extension's click
  right after its touch on that same element (`page/dom.js`'s `touch`, sent between mouseup and click; PR
  477's second review found a touch on the window, before the pointer events, let a page's pointerdown
  handler click its own button and have that count). A touch on the window only shows the note. It returns False, and plain code hands off unpressed, when the element holds
  a frame. The guard lets a form post only for a press that lands on that element in that frame: the pressed
  button's own submission, the pressed element's own form, or (for a Next in no form) a form that shows a
  field of the step, posted while the click is still dispatched. A form with any button that sends (hidden,
  another language, outside it by `form=`, an input with no value, an icon with a title, a role=button), or
  that had one as the press landed, never posts under it, whatever its submitter says. A form in a shadow
  root never posts as a step. A link's `ping` never leaves a guarded page: the guard takes it off as the link
  is clicked (in a shadow root, or by a script's `click()` on a link in no document, too) and refuses any
  script that sets one.
- The guards' state (KAN-710) is in each guard's closure, never on `window`: lifted, held, paused (an
  emailed code), the account, profile and upload allowances, Ask's, the captcha frame's, the Posting's Apply's vouch (KAN-725). Apply sets it only
  with `submit_guard.control`: an event named with a per-run token (`TOKENS`), sent from a CDP isolated world
  (`Page.createIsolatedWorld`), the worker extension's isolated world (`guard.control`), or an init script
  (`_init`) before any page code. The rehearsal guard tells Apply of Lisul's own presses (his Submit, Fill
  again, Dismiss) by a console line with the token (`TELL_PREFIX`), or on a plain Worker an event the relay
  hears (`TELL_TYPE`): no page can call those, as it could call a binding. Each secret is a random value of its
  own (`TOKENS` for the controls, `TOUCHES`, `TELL`), and the install mark each guard leaves on `window`
  (`MARKS`), which any page can read, names none of them: PR 477's second review found the mark carried the
  control's token, so a page could lift both guards.
- The drive guard in a live run runs before each page's code (PR 477's second review): `on_open`, which a
  Worker calls on every page before its first load, puts its init script on the context there
  (`DRIVE_AT_OPEN`). That copy starts lifted, as no guard, so a Filler's own submit in a live run goes on
  as ever; `DriveGuard` arms it, with Lisul's opt-ins (`optSms`, `optMarketing`), by the control in the
  open document and an init script for each one after (on a plain Worker the drive guard is one
  registration, `drive`, which `DriveGuard`'s armed one replaces). Only Apply's control changes it. In a rehearsal, the rehearsal's guard holds the page from before its code
  (`REHEARSAL_AT_OPEN`) and blocks every send itself, so the drive guard's copy in the open document is the
  full one, as before. Any other page's open document gets a block-only copy (`LATE`): one evaluated after
  the page's code, which may have wrapped `addEventListener` and heard its control event's name, takes no
  lift and no allowance (account, profile, upload, start, Ask's tick, an opt-in), so a send there is left to
  Lisul. A page that replaced a built-in the guard reads with before such a copy came defeats it; every
  Worker page goes through `on_open`. Still open: in a rehearsal, a page that wrapped `addEventListener`
  first can hear the drive guard's control event in its open document and lift it there; the rehearsal's
  guard still blocks every send, but not the drive guard's own blocks (another site's sign-in, a payment). The guard takes every built-in it
  reads with before any page code, and a guard listener that throws blocks what it judged.
- Each form post is judged again as it leaves (KAN-710): at its `navigate` event, with the URL and entries
  it really carries. Entries its own fields don't make (a `formdata` handler's), a final URL, or a form that
  had a Submit, are cancelled there. URLs resolve against the document's base; an empty action or formaction
  is the page's own URL. A sign-in relay is only the top page's own post into itself, once the page loaded.
  fetch makes its request once and sends that one. XHR's and the beacon's bodies are read too: a string,
  URLSearchParams or bytes (an ArrayBuffer or a view of one); a Blob, which can't be read at once, is
  refused in a non-GET to Ashby, whose submit is named only in its body (PR 477's second review). A form
  in another site's frame (a sandboxed one runs no guard) that posts into the top page is beyond the
  guard: the browser fires no `navigate` event for a navigation another site's document starts. A profile pop-up may post to its own page there. A known final URL
  (Lever's, Greenhouse's, a segment with `submit`) never goes, whatever the page says. TAL.net's
  (`/eform/<n>/page/<k>`, `save_page`), Oracle's (`/apply/section/<n>`, `/apply/email`), iCIMS's, Workday's
  (`/apply/applyManually`) and Microsoft's (`/careers/job/<id>`) URLs match no final rule at all
  (`tests/test_submit_guard.py -k every_real_step`). On a plain Worker the declarativeNetRequest rule on
  `/apply` still blocks such a step (it can't read the page), so that Next hands off and nothing is sent.
- Before each Next, plain code checks what the step shows (`cant_be_right`, KAN-652): an address part
  holding a whole address, or a school's start year after this one. It reads every visible box of the
  step (`_on_step`, `STEP_VALUES`), not only the ones Apply filled, so a value an earlier run saved
  is checked too; a label that shows twice (a home and a campus address) is numbered, "#7: City/Town".
  Address line 1 holding a whole address is wrong too when the step asks a part of it (City, State
  or Zip, KAN-684). A bare "Start date" beside school
  fields may be the internship's, so it stops the fill only in a section headed clearly as education
  (`_sections`, `clearly_education`) or at a year past `PLAUSIBLE_YEARS` (KAN-659).
- A question Claude finds on a step (`unlisted`, then MoreQuestions) belongs to that step
  (`_found_at`). Once the fill has gone past it, its answer is never sent to a later step: TAL.net's
  Save and Continue goes on with a required box blank, and Lisul's answer came steps later
  (KAN-687). It is `left_behind` instead. The Worker holds the form for it ("Not filled: ... its
  answer came after the form saved its step without it"). A rehearsal lists it as left blank and,
  once held, fills it on its own step through the window's in-place fill (`docs/held-forms.md`,
  KAN-686). A question the read pass listed has no step of its own and is carried on as before.
- A file that brings on a consent dialog (Microsoft's Eightfold "Data Privacy Notice": I understand /
  Cancel) is the applicant's to let go (KAN-768). Plain code (`attach.attach_resume`, `attach.CONSENT`) gives
  the file, sees the dialog, presses none of its buttons (Cancel drops the file, and Claude's Cancel left the
  Resume empty on 2026-11-10), and raises `attach.Consent`, a Handoff: 'Press "I understand" on the "Data
  Privacy Notice" dialog yourself ..., then press Resume'. On Resume the fill attaches again, and finds the file
  his press let through. A dialog still open is never given another file, and the pop-up clearer
  (`clear_pop_up`) never closes one. A cookie banner is no such dialog. On a plain Worker, Claude's
  `browser_click` refuses any button in such a dialog, and `browser_file_upload` tells Claude to stop when its
  file brought one on (`plain.tools.CONSENT`). `CONSENT` is a fixed function (`plain/fixed.py`): run `apply
  plain prepare` (or seed again) before a plain Worker uses it.
- Eightfold's dropdowns are toggles: a click on the option a list already holds (`aria-selected`) empties the
  field (KAN-767; Microsoft's "worked with Microsoft" and "subsidiary" went blank so in an Ask). On a plain Worker
  `browser_click` makes no click on an option its single-choice list holds already (`plain.tools.PICKED`) and
  tells Claude so. The engine's Eightfold Filler leaves such a dropdown alone too. A CDP Worker's Playwright MCP has
  no such rule yet.
- A label the page shows on more fields than Apply knows is another section's question (KAN-642), but a
  radio or checkbox group is one field, however many of its options the page labels with the question
  (`_labelled_fields`), and a label is named as another section's at most once on a step (`_sectioned`, by
  step and entries added). Claude lists a question it wasn't given to fill again in every round. On
  JPMorgan's Oracle form (2026-11-10), each round named Ethnicity, Gender, Veteran Status and the military
  questions again under new names, about 45 times, till the fill's cap of 300 turns and 6,000,000 tokens
  (KAN-788).
- Each fill session gets every file the plan gives the form, not only that round's (KAN-789): a slot an earlier
  round filled may need its file again, and Claude's upload tool sees only the files passed to it. The résumé that
  plain code attached is never passed, so Claude can't put it in another slot.
- Dropdowns that list their choices only once opened are read and picked
  by plain code (`_with_options`, `_pick_in_comboboxes`). Each one's name is
  read off the very element Playwright clicks (`_comboboxes`), never from a
  page script's own list: the two counted visibility apart on Microsoft's
  profile step, and each question opened its neighbour (KAN-646).
- A text box whose placeholder is a date format ("YYYY-MM") gets that format after its label,
  "(YYYY-MM)", as the planner reads a format (`_with_formats`, KAN-714): Amazon's graduation month box
  says its format only there, and refused "May 2028". (amazon.jobs has its own Filler since KAN-765:
  `docs/fill-engine.md`.)
- A date Claude fills is typed in the box's format and left; one that then shows an error, stays empty or reads
  back another date is picked with its calendar and read back (FILL's date rule, KAN-716). amazon.jobs held no
  typed date and held every date picked from its calendar, which a later page can show a day early: Claude lists
  that in `for_lisul` and never picks another day to make up for it. Workday's dates are the Fill engine's: it
  picks a date its "current value is" line doesn't hold as typed from Workday's Calendar (`docs/fill-engine.md`).
- On a plain Worker (KAN-612; a PortPage, no CDP), `claude_cli.drive` gives
  `claude -p` Apply's own MCP server under the same name, `playwright`
  (`apply.plain.mcp`, a stdio relay, and `apply.plain.tools`, which runs
  each tool on the page through the Worker's port). Its tools are Playwright
  MCP's, by name and input (`apply/plain/mcp_tools.json`, from
  @playwright/mcp@0.0.83's own list), so the prompts, `BROWSER_TOOLS`,
  `NO_BROWSER_TOOLS` and the `send_click` hook don't change. Keep that file
  in step with `PLAYWRIGHT_MCP` when the pin moves. Dialogs are answered as
  they open (`browser_handle_dialog` sets the next answer), and a file is
  attached only to a chooser a click opened and only from the drive's own
  folder. The CDP-only calls and their stand-ins are listed in
  `docs/plain-workers/PROTOCOL.md` ("Ops (S6)"). Test with
  `tests/test_plain_claude.py`; its two real-Haiku tests run only with
  `APPLY_LIVE_CLAUDE=1`.
- A section of jobs or schools is read as "Work Experience (entries)" or "Education (entries)", also one
  that shows entries as cards an old profile on the job site left (Oracle's, Workday's My Experience,
  Amazon's tabs, KAN-762). Its fill gets the profile's jobs and school in an `<entries>` block
  (`entry_history`), and Claude deletes each entry no item names, sets the title and dates of each one an
  item names, and for a job held now ticks its current-job box before the dates and leaves the end empty
  (Oracle refused a start typed after an old end: "Enter a date that's on or before {END_DATE}"). Each
  entry's current-job box comes before its dates in `<fields>` too (the engine's `currentFirst`). An entry
  Claude couldn't delete (`entries_kept`) holds the form: "Verify: Remove this entry, which your profile
  doesn't list: ..." (`ClaudeFill.extra_entries`, `worker.EXTRA_ENTRY`). Verifying holds a section read back
  with more entries than planned too (`docs/held-forms.md`).

## Form pages

- A Filler with a `form_url(url)` method names the page that holds its
  form. The Worker opens that page, not the posting link. Lever's form is
  on `/apply`; a link without it opens the job description.
- A Workday step that Save and Continue refuses ("won't leave its ... step")
  is filled once more, after a second's wait, and saved again; a second
  refusal is the Handoff. ASML's Application Questions showed every pick,
  yet Workday held two of them empty (`WorkdayFiller.fill`).
- Workday may answer Save and Continue with its error page, "Something
  went wrong. Please refresh the page and then try again." That page is
  Workday's React error boundary: the page's own script threw. It is not a
  refused answer, which shows as a "Page Error" banner. The engine's `next`
  names it at once ("showed its error page"). Before, it waited 30 s and
  failed the Application, since the progress bar still named the step
  (NVIDIA's My Experience, 2026-11-10, KAN-758). Apply reloads the page, as
  it asks, and goes on from the step the reload shows. It fills that step
  again if it is the same one. A second error page on the step is the
  Handoff (`WorkdayFiller._save_and_continue`).
