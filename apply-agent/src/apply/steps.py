"""Plain code's own presses on a form's steps, and its reads of a dropdown's choices: a step's Next, Back, add
button or listed step, found by its words and pressed through the guards, never a button that sends (KAN-639).

Claude fill (a Developer checkout's) and the generic Filler (apply.generic_fill, the Student build's) share them, so
they live outside apply.claude_fill, which the Student build leaves out (apply.build)."""

import re

from playwright.sync_api import Locator, Page

from apply.account_pages import SENDS
from apply.model import Handoff

# A form in steps: the button that goes on (never one that sends), and how long a step may take to show once it's
# clicked.
NEXT = re.compile(r"\b(next|continue|proceed|review)\b", re.IGNORECASE)
BACK = re.compile(r"\b(back|previous|prev)\b", re.IGNORECASE)
REVIEW_WORDS = "on the form's review page"
STEP_SHOWS_MS = 8_000
ADDS = re.compile(r"^\s*add\b", re.IGNORECASE)  # a section's button that adds an entry ("Add another")


# A dropdown that shows its choices only once opened (Airtable's): its name. Read off each
# element Playwright finds, never by a page script's own list: the two can disagree on which
# are visible (one behind a pop-up, or in a shadow root), and the indexes then point each
# question at its neighbour (Microsoft's country code and residence, live: KAN-646).
COMBOBOX_NAME = """el => {
  const root = el.getRootNode();
  const by = (el.getAttribute('aria-labelledby') || '').split(/\\s+/).filter(Boolean)
    .map(id => ((root.getElementById && root.getElementById(id)) || document.getElementById(id) || {}).innerText || '').join(' ');
  return (el.getAttribute('aria-label') || by || '').trim();
}"""


# The text of the widest part of the page that holds this dropdown and no other: its
# field, with the chips a multi-select shows beside its "+" (Airtable's).
FIELD_TEXT = """el => {
  let text = el.innerText;
  for (let node = el.parentElement, up = 0; node && up < 6; node = node.parentElement, up++) {
    if (node.querySelectorAll('[role=combobox]').length > 1) break;
    text = node.innerText;
  }
  return text;
}"""
OPENS_MS = 1_500  # how long an opened dropdown may take to list its choices
# The form fields a step shows, in a frame, and in each open shadow root in it (SmartRecruiters' spl-input holds its
# input there, live 2026-11-27): a step went on once they change.
FIELDS_SHOWN = """() => {
  const out = [];
  const walk = (root) => {
    for (const el of root.querySelectorAll('*')) {
      if (el.matches('input, select, textarea') && el.type !== 'hidden' && el.checkVisibility && el.checkVisibility())
        out.push(el.name || el.id || el.type);
      if (el.shadowRoot) walk(el.shadowRoot);
    }
  };
  walk(document);
  return out.join('|');
}"""


def press_step(page: Page, guard, name: str, back: bool = False, listed: bool = False, add: bool = False,
               section: str = "") -> None:
    """Plain code's own click on a step's Next (or `back`: its Back; or `listed`: a step in the form's list of
    steps, TAL.net's Progress Tracker; or `add`: the add button of the form's `section`), which goes through the
    guards where it posts natively: a button that sends, a form that has one and the final application URLs stay
    blocked (KAN-639). Waits for the step it leads to; a Handoff says why it didn't."""
    before = _fields_shown(page)
    button = _the_back(page, name) if back else _the_listed(page, name) if listed else _the_add(page, name, section) \
        if add else _the_next(page, name)
    # Plain code's own check: never Claude's word for it. A Back leaves the review page, so only its words count.
    words = _sends_or_reviews(page, button)
    if words and not (back and words == REVIEW_WORDS):
        raise Handoff(f"Claude fill's Next ({name!r}) is {words}, which may send the form. Fill it in yourself.")
    # A frame inside the button (KAN-710): the press lands in it, where no guard may run (a sandboxed one runs no
    # script), and its form could post the application to the top page. Never pressed.
    if guard and not guard.let_account_click(button):
        guard.arm()
        raise Handoff(f"The form's {name!r} holds a frame, where Apply's press could land on another form. "
                      "Press it yourself.")
    try:
        button.click()
        waited = 0
        while _fields_shown(page) == before:
            if waited >= STEP_SHOWS_MS:
                raise Handoff(f"The form's {name!r} didn't go on to its next step: a required answer may be "
                              "missing or wrong on the step it stayed on. Fill it in yourself.")
            page.wait_for_timeout(250)
            waited += 250
    finally:
        if guard:
            guard.arm()  # the account click's flag off again, in the step it led to
            guard.rest()


# The heading of the part of the page an add button holds alone: the widest one around it with no other button of
# its name (its section, fieldset or group), named by the aria-labels on the way up to it and its first heading before
# the button. The way up crosses shadow roots, and so does the look for another button: SmartRecruiters' "Add" is an
# spl-button's own button, the host named "Add experience entry" (live 2026-11-27). Run on each button by itself: a
# plain Worker passes no element handles to a page script.
ADD_SECTION = """(el, name) => {
  const key = words => (words || '').replace(/\\s+/g, ' ').trim().toLowerCase();
  const BUTTONS = 'button, [role=button], input[type=button], input[type=submit]';
  const host = node => { const root = node.getRootNode(); return root instanceof ShadowRoot ? root.host : null; };
  // A shadow root's button is named by its slotted words, which its own innerText may not show: its host's too.
  const same = b => b !== el && [b.getAttribute('aria-label'), b.innerText, b.value, host(b) && host(b).innerText]
    .some(w => key(w) === key(name));
  const buttons = root => {
    const found = [...root.querySelectorAll(BUTTONS)];
    for (const node of [root, ...root.querySelectorAll('*')]) if (node.shadowRoot) found.push(...buttons(node.shadowRoot));
    return found;
  };
  const labels = [];
  let region = el;
  for (let node = el.parentElement || host(el); node; node = node.parentElement || host(node)) {
    if (buttons(node).some(same)) break;
    region = node;
    if (node.getAttribute('aria-label')) labels.push(node.getAttribute('aria-label'));
  }
  // Placed in the region's own tree by its host there: an order across shadow roots means nothing.
  let at = el;
  while (at.getRootNode() !== region.getRootNode() && host(at)) at = host(at);
  const head = [...region.querySelectorAll('h1, h2, h3, h4, h5, h6, legend, [role=heading]')]
    .find(h => h.compareDocumentPosition(at) & Node.DOCUMENT_POSITION_FOLLOWING);
  return [...labels, head ? head.innerText : ''].join(' | ');
}"""


def _add_section(button, name: str) -> str:
    """The heading of the part of the page that holds this add button alone (ADD_SECTION); "" where Apply can't read it."""
    try:
        return str(button.evaluate(ADD_SECTION, name))
    except Exception:
        return ""


def _the_add(page: Page, name: str, section: str = ""):
    """The one button of exactly the name Claude gave a section's add button ("Add another"), whose words add an entry
    and say nothing that sends. Where several share the name (SmartRecruiters' "Add" in Experience and in Education),
    the one whose part of the page is headed by a word of `section` ("Work Experience"). None, or two, is a Handoff."""
    if SENDS.search(name) or not ADDS.match(name):
        raise Handoff(f"Claude named {name!r} as a section's add button, which may send the form. Fill it in yourself.")
    shown = [b for b in page.get_by_role("button", name=name, exact=True).all() if b.is_visible()]
    found = shown
    if len(shown) > 1 and (words := re.findall(r"\w+", section)):
        heads = re.compile(rf"\b({'|'.join(map(re.escape, words))})\b", re.IGNORECASE)
        found = [b for b in shown if heads.search(_add_section(b, name))]
    if len(found) != 1:
        raise Handoff(f"The form shows {len(shown)} buttons named {name!r}, so Apply didn't add an entry. Add it yourself.")
    return found[0]


def _the_back(page: Page, name: str):
    """The one button of exactly the name Claude gave a step's Back, which says nothing that sends. None, or two, is a Handoff."""
    if SENDS.search(name) or not BACK.search(name):
        raise Handoff(f"Claude named {name!r} as the form's Back, which may send it. Fill it in yourself.")
    found = [b for b in page.get_by_role("button", name=name, exact=True).all() if b.is_visible()]
    if len(found) != 1:
        raise Handoff(f"The form shows {len(found)} buttons named {name!r}, so Apply didn't press one. Do it yourself.")
    return found[0]
# An entry in a list of a form's steps (TAL.net's Progress Tracker: each step's link posts the page to save_page,
# then opens that step, KAN-692): in a nav or a list of more than one entry, and never a form's own button (a
# submit, or any button of a form), nor one holding or held by a control or label, which would post that
# form with no check of its other buttons. A link can post only by script (form.submit(), requestSubmit()),
# where the guard still blocks a form with a button that sends.
STEP_ENTRY = """el => {
  if ((el.tagName === 'BUTTON' || el.tagName === 'INPUT') && (el.type !== 'button' || el.form)) return false;
  // A click on it must land on it alone: never a control, a label (one that clicks a submit) or a frame inside it, nor a control or label around it.
  if (el.querySelector('button, input, select, textarea, label, iframe, frame, object, embed') || el.parentElement?.closest('button, label')) return false;
  const list = el.closest('nav, [role=navigation], ol, ul, [role=list], [role=tablist]');
  return !!list && list.querySelectorAll('a[href], [role=link], [role=tab], button[type=button]').length > 1;
}"""


def _step_entry(el) -> bool:
    """Whether `el` is an entry of the form's list of steps (STEP_ENTRY); an element Apply can't read there (a plain
    Worker's in a shadow root) is none, so it is never pressed."""
    try:
        return el.evaluate(STEP_ENTRY) is True
    except Exception:
        return False


def _the_listed(page: Page, name: str):
    """The one entry in the form's list of steps that Claude named: of exactly that name, else the one whose name
    starts with it (a tracker's "Declaration Item not completed"), else the one that has it just after a heading's
    colon ("Section Header: Declaration"). A name that sends (Claude's, or the entry's own as the page names it),
    none, or two that differ is a Handoff: no click."""
    if not name.strip() or SENDS.search(name):
        raise Handoff(f"Claude named {name!r} as a step of the form, which may send it. Fill it in yourself.")
    starts = re.compile(rf"^\s*{re.escape(name.strip())}(?!\w)", re.IGNORECASE)
    # TAL.net's live links are named by an aria-label with a heading first: "Section Header: Additional Information
    # Item incomplete" (KAN-729). The step's name right after that heading's colon counts as its start.
    headed = re.compile(rf"^[^:]{{0,40}}:\s*{re.escape(name.strip())}(?!\w)", re.IGNORECASE)
    for match in ({"name": name, "exact": True}, {"name": starts}, {"name": headed}):
        found = [el for role in ("link", "button", "tab") for el in page.get_by_role(role, **match).all()
                 if el.is_visible() and _step_entry(el)]
        if found:
            break
    if not found:
        raise Handoff(f"Claude fill found no step named {name!r} in the form's list of steps. Fill it in yourself.")
    if len({el.aria_snapshot() for el in found}) > 1:
        raise Handoff(f"The form's list of steps shows more than one {name!r}, so Apply didn't press one. Do it yourself.")
    if SENDS.search(found[0].aria_snapshot()):
        raise Handoff(f"The form's step {name!r} is named as one that sends, so Apply didn't press it. Do it yourself.")
    return found[0]


def _the_next(page: Page, name: str):
    """The one button that is the step's Next Claude named: the button of
    exactly that name, else the one whose whole name is a Next's ("Continue"
    for Claude's "Continue →") and has no word that sends ("Continue &
    Submit" never is). None, or two that differ, is a Handoff: no click."""
    if SENDS.search(name) or not NEXT.search(name):
        raise Handoff(f"Claude fill named {name!r} as the form's Next, which may send it. Fill it in yourself.")
    exact = [b for b in page.get_by_role("button", name=name, exact=True).all() if b.is_visible()]
    if exact:
        return exact[0]
    word = NEXT.search(name)[0]
    # Matched against each button's whole accessible name: has the word, and nowhere a sending one.
    goes_on = re.compile(rf"^(?!.*{SENDS.pattern}).*\b{word}\b", re.IGNORECASE)
    found = [b for b in page.get_by_role("button", name=goes_on).all() if b.is_visible()]
    if not found:
        raise Handoff(f"Claude fill found no {name!r} button to go on to the form's next step. Fill it in yourself.")
    if len({b.aria_snapshot() for b in found}) > 1:
        raise Handoff(f"Claude fill found more than one button that could be the form's {name!r}. Fill it in yourself.")
    return found[0]
REVIEW_PAGE = re.compile(r"\b(review (your|and submit|the) application|application (summary|review)|summary of your "
                         r"application|review (&|and) submit)\b", re.IGNORECASE)


BUTTON_WORDS = "b => [b.innerText, b.value, b.getAttribute('aria-label'), b.getAttribute('title')].filter(Boolean).join(' | ')"
HEADINGS = "() => [document.title, ...[...document.querySelectorAll('h1, h2, h3, legend')].map(h => h.innerText)].join(' | ')"


def _sends_or_reviews(page: Page, button) -> str:
    """Why the button plain code would click as a Next may send the form ("" when it can't): its own text,
    value, aria-label or title has a word that sends, or the page is the form's review or summary."""
    try:
        words = str(button.evaluate(BUTTON_WORDS))
    except Exception:
        return "a button Apply can't read"
    if SENDS.search(words):
        return f"a button that says {words.strip()[:60]!r}"
    try:
        headings = str(page.evaluate(HEADINGS))
    except Exception:
        headings = ""
    if REVIEW_PAGE.search(headings):
        return REVIEW_WORDS
    return ""


def _options_of(page: Page, combobox) -> tuple[str, ...]:
    """The choices the dropdown lists once opened: those of the listbox it names (aria-controls,
    aria-owns), else the options that showed when it opened and weren't showing before. Never every
    option on the page: Microsoft's form kept another list's options there, and each dropdown read
    them as its own, so a Yes/No question offered only "United States, California, Aliso Viejo" and
    its answer fit none (live, 2026-11-06)."""
    try:
        before = set(_visible_options(page))
        combobox.click(timeout=3_000)
        options = _owned_options(page, combobox) or _new_options(page, before)
    except Exception:
        options = ()
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    return options


def _visible_options(page: Page) -> list[str]:
    return [o.strip() for o in page.get_by_role("option").filter(visible=True).all_inner_texts() if o.strip()]


def _owned_listbox(page: Page, combobox) -> Locator | None:
    """The listbox an opened dropdown names as its own (aria-controls, aria-owns) once it lists options, else None."""
    ids = combobox.evaluate("el => ((el.getAttribute('aria-controls') || '') + ' ' + (el.getAttribute('aria-owns') || '')).split(/\\s+/).filter(Boolean)")
    for listbox in ids:
        owned = page.locator(f'[id="{listbox}"]').first
        try:
            owned.get_by_role("option").first.wait_for(state="attached", timeout=OPENS_MS)
        except Exception:
            continue
        return owned
    return None


def _owned_options(page: Page, combobox) -> tuple[str, ...]:
    """The options of the listbox an opened dropdown names as its own, or () when it names none that lists any."""
    owned = _owned_listbox(page, combobox)
    if owned is None:
        return ()
    return tuple(dict.fromkeys(o.strip() for o in owned.get_by_role("option").all_inner_texts() if o.strip()))


def _new_options(page: Page, before: set[str]) -> tuple[str, ...]:
    """The options showing once a dropdown opened that weren't showing before it did, as soon as any show."""
    for _ in range(max(1, OPENS_MS // 100)):
        found = tuple(dict.fromkeys(o for o in _visible_options(page) if o not in before))
        if found:
            return found
        page.wait_for_timeout(100)
    return ()


def _fields_shown(page: Page) -> str:
    shown = [page.url.removesuffix("#")]  # a step link's href="#" whose post the guard blocked: still the same step
    for frame in page.frames:
        try:
            shown.append(frame.evaluate(FIELDS_SHOWN))
        except Exception:
            continue  # a frame that went away, or one that refuses scripts
    return "\n".join(shown)
