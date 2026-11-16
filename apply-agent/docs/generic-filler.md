# The generic Filler (KAN-861)

Reference for Apply, reached from `apply-agent/CLAUDE.md`. Paths are relative to `apply-agent/`. A change in this
area updates this file in the same PR. The design is W2 of `../docs/desktop_application_auto_apply.md` (D13: in v1
no model drives the browser).

The generic Filler fills a form on a job system that has no Filler of its own. Code reads the form and does every
click; a model only picks.

## Reading the form (`form_tree.py`)

- **The accessibility tree, as Playwright's ARIA snapshot reads it** (`locator("body").aria_snapshot()`). The same
  call works on a CDP Worker and a plain Worker, since `plain/page.py` runs Playwright's own injected script. Chrome's
  raw tree (`Accessibility.getFullAXTree`) is CDP's only, and a plain Worker has no op for it.
- **Each control by role and name.** A text box is a text question; a `<select>`, a combobox, a list box or a radio
  group is a select with its options; a set of checkboxes is a multi-select; a lone checkbox is a Yes or No, as
  the engine asks Greenhouse's "Current role". A lone box of three words or fewer under a question ("I
  Understand", Lever's) is that question's one option.
- **What the tree leaves out comes from the element** (`FACTS`): the required mark, a text area, a `<select>`'s
  placeholder option, a radio's group, a placeholder. A label that ends in a star is required too. File inputs
  are not in the tree as such: they are read by `input[type=file]` (`FILES`), hidden ones too, each named by its
  label or by the nearest short words around it that are not an upload button's own ("Attach").
- **A label is the control's own name**, unless the name only asks for input: none, its placeholder, "Select...",
  or Lever's "Type your response". Then the words just before the control in the same part of the page name it.
  Words just before it that end in a required mark win too when the name doesn't hold them (Lever's "Name of
  School ✱" over a box named by its choice). On Lever's six saved forms, before this rule, 21 of the 174
  questions took "Type your response" as their label.
- **Found again by role, name and place** (`locate`): `get_by_role(role, name=..., exact=True).nth(n)`. A nameless
  control's place is among every control of its role, as `get_by_role(role).nth(n)` counts them. Counted among
  the nameless only, a box's facts came from another box.
- **A dropdown with no options in the tree is opened, read and closed** (`steps._options_of`, Claude fill's
  reader). Options that say they open more options (`aria-haspopup`, `aria-expanded`) make it a two-level list,
  asked as text. A box with no options until one types is a search box, asked as text.
- **The top frame only.** An embedded form is opened in its own page first (`embedded.form_behind`).
- **A list a combobox opens is that combobox's** (its `aria-controls` or `aria-owns`), never a question of its own.
  A dropdown the first read left open was read again as a nameless list, labelled by the words before it.
- **Each field is found again by its key**: its role (a file input: "file"), its label and its place, never how it
  fills. A read that opens no dropdown can't tell a two-level list or a search box from a dropdown, so the step's
  quick read takes those from the Question set's read.

**Measured** (2026-11-15) on the Fill engine's saved Lever forms, whose questions the engine reads off the served
page with no network: the reader finds 164 of the engine's 174 questions, nearly all of the same kind. The rest are
a self-ID survey the page keeps collapsed and a signature's two parts. Greenhouse's and Ashby's saved forms read
their questions from their APIs, which the saved form's server doesn't answer.

## Filling (`generic_fill.py`)

`GenericFiller` has the Filler shape (`fillers.py`). Its form stays open from its Question set to its last step, so
`orchestrator.by_filler` runs it on `OnePage`. In the Student build it takes the place of `ForTheStudent` (KAN-855),
which held a form with no Filler unfilled. A Developer checkout keeps Claude fill.

| Control | Plain code |
|---|---|
| Text box, text area | `fill`, then `blur` as a person leaves the box; a box left empty (a mask, BambooHR's date) is typed key by key once |
| Native `<select>` | `select_option` by the option the plan fitted (fit.ts, in the planner) |
| Radio group | `check` the radio of the planned option |
| One checkbox | `set_checked` for Yes or No |
| Checkboxes | `set_checked` on each, ticked if planned |
| File | The résumé by `attach.attach_resume`; any other by `upload_origin.give` |

- **Every field is read back right after its fill**, from its own element: a box's value, a select's chosen text,
  which radio or box is checked, a file input's file name, a dropdown's shown choice. One that doesn't show its
  answer raises a `FillError` that names its label (colons taken out: the Worker reads the field up to the first
  colon). The Worker drops it, and in the Student build it is a Needs-you item whose box starts with the planned
  answer (`docs/held-forms.md`, KAN-855). A text box that read back wrong is emptied, so no wrong answer stays on
  the page.
- **After the student's Resume**, `resumed` keeps as theirs each value they changed in a field Apply had filled.

### The model's pick

- **Code matches first.** An option of the answer's exact words, then its words in another case or spacing, then
  the one the Fill engine's `shows` reads as the answer. Only then the model.
- **The model's question is `generic_fill.pick`** through the Model route (`ask_kind`; the prompt and schema are the
  server's, `../backend/app/apply_prompts/generic_fill.py`): the field's question, the planned answer and its
  options, numbered. It answers `{"choice": <number> | null}`, and the schema bounds the number by the list.
  About a hundred tokens. A list of more than 60 options, a null, or a failed call is no pick: the field is the
  student's. The call goes through `applicant.as_applicant`, so the student's private values go as placeholders
  (D8). At the Usage cap the call raises `UsageLimitHit`, and the run pauses.

### Dropdowns, search boxes and two-level lists

| Control | Plain code | The model's question, when code can't match |
|---|---|---|
| Dropdown | Click it, read the options it lists, click the planned one | Which option is the answer |
| List box (always open) | Click its own option | Which option is the answer |
| Search box | Click, type the answer, read what it lists, click one | Which listed choice is the answer |
| Two-level list | Open it; a group opens its own options | Which group holds the answer, then which option |

An option is clicked only as an `option` in the dropdown's own list box (`aria-controls`, `aria-owns`), else among
the options that showed as it opened: never a button or link of the page's. Its read-back is the choice the field
shows on a line of its own, else its tree value.

## Next and the steps

- **The step's Next is found by Claude fill's words** (`steps.NEXT`, never one that says it sends, `SENDS`, or goes
  back, `BACK`), among the tree's buttons. Plain code presses it with `steps.press_step`, through the guards, as
  Claude fill's Next is pressed: its own check refuses a button or page that may send. Two that could go on ("Save
  and continue later" beside "Continue"): `generic_fill.next` asks which goes on without sending; null is a Handoff.
- **The last step is the one that shows a button that sends and no Next.** The fill returns there; only the student
  presses Submit. `submit` raises `SetupError`.
- **A field no question names yet** (the next step's, or one an answer showed) is read with its dropdowns opened and
  raised as `MoreQuestions`, for the Worker to plan.
- **A posting page with no field** opens its form by its one Apply link on the page's own site (followed with no
  click; one to another site is a Handoff, since the Filler would fill and give files to that site) or button
  (pressed through the guards), whose whole name is an opener's (`OPENS`: "Apply for This Job", BambooHR's). None, two, a
  button in a `<form>` (its press would send that form: opening a form never needs one sent) or one with a frame
  inside is a Handoff.

## What goes to the student

Each is a Handoff whose words say what Apply saw, then "press Fix here and ... on the form in this window"
(`FIX_HERE`, which moved here from the Orchestrator).

- A page in a state the fill didn't expect: an alert with an error's words that wasn't there before the fill, a
  pop-up it can't close (`attach.clear_pop_up`), a field that went blank or changed once filled.
- A widget the tree doesn't show: a drawing area (a signature pad, a canvas date picker) or a drag and drop.
- A step whose end isn't clear: no Next and no button that sends; two Nexts the model can't tell apart; more than
  20 steps.
- A required attestation on a step with a Next: the student's own to tick (KAN-676, `fill_engine.tick_ask`).
- Anything the guards stopped while code pressed.
- A captcha's challenge, or its box on the last step, is the captcha wait (`model.Captcha`), as for Claude fill.

## The guards (KAN-666)

The generic Filler's clicks are new click paths. It fills under the rehearsal's guard and drives under its own drive
guard (`submit_guard.DriveGuard`), so a click that would send is blocked even where the page dresses a Submit as an
option. The drive guard is armed (`arm`) as the Question set's read starts, before its first click (a dropdown
opened, a pop-up's Close), and as each fill starts and after each Next, and rests when the code stops, so the
student's own clicks go through on the held page. Armed only once the fill started, the read ran unguarded on a page
a live run opens with the guard lifted (`on_open`), and a pop-up's Close that was the form's submit sent it (the
adversarial review, 2026-11-15).

**Plain code never clicks a control that would submit a form** (`form_tree.SUBMITS`): one that is, sits in or holds a
form's submit button (a `<button>` of no type or `type=submit`, an `<input type=submit|image>`), or a label for one
(a click on a label clicks its control). A dropdown or radio
made of one submits its form as it opens or is ticked, and the review found that a GET form's own submit handler
posts the application past both guards: the guard's submit block covers a POST form, or a press it reads as a send.
The reader leaves such a dropdown closed, and the fill makes its field the student's (a `FillError`). The guard's
gap is older than the generic Filler: plain code's Next and Ask Claude's press still reach it, so the review's pages
are tested on the generic Filler alone (`GENERIC_REFUSES`), outside the shared `PAGES`.

**Nor does it press a Next that would submit the form its Submit is in** (`FORM_BUTTONS`): one of type submit whose
form holds another button whose words send, read as a person reads them (its text, value, `aria-label`, title,
`aria-labelledby`, an image's alt or an icon's title). On a GET form that Next sent the application through the same
gap. The step is a Handoff.

**The guard's GET-form gap, closed (KAN-868).** A check the Filler makes before it clicks can be raced: the
review's second round made a dropdown a submit button on its own `pointerdown`, and added a Next's Submit as it was
pressed, and both sent. Only the guard can stop those, and since KAN-868 it blocks a GET form's submit while code
drives a form that holds a button that sends, as it blocks a POST form's. The two pages are now in `GENERIC_REFUSES`.
`tests/test_submit_guard_hostile.py` runs two paths on every hostile page:
"the generic Filler" (the whole fill, every question answered, its model the worst one: it picks the first option
and the first button every time) and "the generic Filler's Apply press". Its two pages: an option that holds the
form's own submit button, and a posting's Apply that is a one-click application's submit.

## Measured

How many of the Fill engine's own planned answers the page shows once each Filler filled it (2026-11-15,
`scripts/generic_fill_measure.py`): each Filler reads and plans the form its own way, then the engine reads the page
back for its own questions, so one ruler scores all three. The six saved Lever forms, as Test Person, on a plain
Worker:

| Form | Planned answers | Lever's own Filler (engine) | Generic Filler, code only | Claude fill |
|---|---|---|---|---|
| lever-belvedere | 26 | 26 | 24 | 26 |
| lever-hermeus | 23 | 23 | 20 | 21 (stopped at its cap) |
| lever-immuta | 15 | 15 | 14 | 15 |
| lever-rhombus | 17 | 17 | 15 | 17 |
| lever-shieldai | 28 | 28 | 26 | 26 (stopped at its cap) |
| lever-xcimer | 17 | 17 | 15 | 17 |
| **All six** | **126** | **126 (100%)** | **114 (90%)** | **122 (97%)** |

Time per form: the generic Filler 3 to 13 s, Claude fill 28 to 63 s and about 40 Haiku turns, the engine under 1 s.
The generic Filler's 12 misses are each a field it left for the student, never a wrong answer typed: Lever's
location search on all six forms (its choices come from Lever's live API, which the saved form's server doesn't
answer, so no model could pick one either), Lever's school list on three, and a self-ID survey the page keeps
collapsed on two. Each is a Needs-you item with its planned answer in a run. The model's picks would add to the
generic Filler's count only where code finds options but no match; on these forms it found none such.

**Tests.** `tests/test_form_tree.py` (no browser, CI): the snapshot parser and how two fields of one label are
asked. `tests/test_generic_filler.py` (Chromium, on a Mac): each kind of control, a box named by its placeholder,
the six saved Lever forms against the engine's own read, the fill of each control and its read-back (on a plain
Worker too), each Handoff, the model's pick on a radio group, a dropdown, a two-level list, a search box, a form in
steps, two possible Nexts, and the Apply press. `tests/test_student_handoffs.py`: the BambooHR fake filled in the
Student build with no model driving. `tests/test_student_build.py` (CI): a job system with no Filler gets the
generic Filler, which never submits. `../backend/tests/test_apply_prompts.py`: the two kinds' schemas.
