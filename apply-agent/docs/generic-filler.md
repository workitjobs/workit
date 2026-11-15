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

## What goes to the student

Each is a Handoff whose words say what Apply saw, then "press Fix here and ... on the form in this window"
(`FIX_HERE`, which moved here from the Orchestrator).

- A page in a state the fill didn't expect: an alert with an error's words that wasn't there before the fill, a
  pop-up it can't close (`attach.clear_pop_up`), a field that went blank or changed once filled.
- A widget the tree doesn't show: a drawing area (a signature pad, a canvas date picker) or a drag and drop.
- A form that goes on past its first page (no button that sends on it): for now, the student fills the rest.
- Anything the guards stopped while code pressed.
- A captcha's challenge, or its box on the last step, is the captcha wait (`model.Captcha`), as for Claude fill.

## The guards (KAN-666)

The generic Filler's clicks are new click paths. It fills under the rehearsal's guard and puts a drive guard
(`submit_guard.DriveGuard`) on the page as its fill starts, so a click that would send is blocked even where the
page dresses a Submit as an option. `tests/test_submit_guard_hostile.py` runs "the generic Filler" (the whole
fill, every question answered, its model the worst one: it picks the first option every time) on every hostile
page. Its page: an option that holds the form's own submit button.

**Tests.** `tests/test_form_tree.py` (no browser, CI): the snapshot parser and how two fields of one label are
asked. `tests/test_generic_filler.py` (Chromium, on a Mac): each kind of control, a box named by its placeholder,
the six saved Lever forms against the engine's own read, the fill of each control and its read-back (on a plain
Worker too), each Handoff, the model's pick on a radio group. `tests/test_student_build.py` (CI): a job system with no Filler gets the
generic Filler, which never submits. `../backend/tests/test_apply_prompts.py`: the kind's schema.
