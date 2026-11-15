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

**Tests.** `tests/test_form_tree.py` (no browser, CI): the snapshot parser and how two fields of one label are
asked. `tests/test_generic_filler.py` (Chromium, on a Mac): each kind of control, a box named by its placeholder,
and the six saved Lever forms against the engine's own read.
