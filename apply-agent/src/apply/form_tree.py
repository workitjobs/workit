"""The fields of an open form, read with no model (KAN-861, W2 step 2): the generic Filler's reader.

The page's accessibility tree gives each control its role and its name, as Playwright's ARIA snapshot reads it
(`locator.aria_snapshot()`), on a CDP Worker and on a plain Worker alike (apply.plain.page runs Playwright's own
injected script). A text box is a text question, a combobox or a radio group a select with its options, a set of
checkboxes a multi-select, and a lone checkbox a Yes or No. The tree has no required mark, no text area, no file
input and no `<select>`'s placeholder, so the reader asks each control's own element for those few facts (DOM).

Each Field keeps how to find its element again: its role, its name and its place among the controls of that role
and name (`nth`), which `get_by_role(role, name=..., exact=True).nth(nth)` finds. A nameless control is found by
its place among every control of its role. A dropdown that lists its choices only once opened is opened, read and
closed (apply.steps._options_of), as Claude fill read one.

The reader reads only the top frame. A form in another frame is the embedded form's (apply.embedded opens it in its
own page first), and a form whose fields are all in a frame is a Handoff: the generic Filler can't place them.
"""

import json
import re
from dataclasses import dataclass, field, replace

from playwright.sync_api import Locator, Page

from apply.model import Question
from apply.steps import _options_of

# A control the tree names, and the roles that hold a control's options.
CONTROLS = frozenset({"textbox", "searchbox", "spinbutton", "combobox", "listbox", "radio", "checkbox", "switch"})
GROUPS = frozenset({"group", "radiogroup"})
# A snapshot line: "- role "name" [attr] [attr=v]: value", indented two spaces a level.
LINE = re.compile(r'^(?P<indent>\s*)- (?P<role>[a-z]+)(?: (?P<name>"(?:[^"\\]|\\.)*"))?(?P<attrs>(?: \[[^\]]*\])*)'
                  r"(?::(?: (?P<value>.*))?)?$")
ATTR = re.compile(r"\[([a-z]+)(?:=([^\]]*))?\]")
# A select's first option that only asks for a pick ("Select...", "-- Choose one --", "Please select"): no answer.
PLACEHOLDER = re.compile(r"^\W*(select|choose|pick|please (select|choose)|none selected|--+)\b.*$|^\W*$", re.IGNORECASE)
# A label's required mark, which the tree keeps in its name ("First Name *").
STAR = re.compile(r"\s*[*✱]\s*$")
# A control's own name that only asks for input ("Type your response", "Select...", Lever's): the words just before it
# on the page are its question.
GENERIC = re.compile(r"^\W*(type (your|a|an) (response|answer)|enter (your |an? )?(answer|response|text)|start typing\b.*|"
                     r"(please )?(select|choose|pick|search)\b.*|other|none)\W*$", re.IGNORECASE)
AGREES = 3  # the most words of a lone box's name that is an option of the question before it ("I Understand")
TEXT_TYPES = frozenset({"", "text", "email", "tel", "url", "search", "number", "date", "month"})

# What the reader asks a control's element: the facts the tree leaves out. Never a property the page could have
# replaced alone: each read is a plain attribute or a built-in property of the element's own kind.
FACTS = r"""el => {
  const attr = (n) => el.getAttribute(n);
  const tag = el.tagName;
  const options = tag === 'SELECT' ? [...el.options].map((o) => [o.text.trim(), o.value, o.disabled]) : [];
  return {
    tag, type: (attr('type') || '').toLowerCase(), group: attr('name') || '', placeholder: attr('placeholder') || '',
    required: !!el.required || attr('aria-required') === 'true',
    multiple: !!el.multiple, readonly: !!el.readOnly || attr('aria-readonly') === 'true',
    disabled: !!el.disabled || attr('aria-disabled') === 'true',
    popup: (attr('aria-haspopup') || '').toLowerCase(), autocomplete: (attr('aria-autocomplete') || '').toLowerCase(),
    // A list a combobox opens (its aria-controls or aria-owns): that combobox's, never a question of its own.
    owned: !!el.id && [...document.querySelectorAll('[aria-controls], [aria-owns]')].some((other) => other !== el &&
      `${other.getAttribute('aria-controls') || ''} ${other.getAttribute('aria-owns') || ''}`.split(/\s+/).includes(el.id)),
    options,
  };
}"""

# Every file input in the top frame, shown or hidden (a custom uploader hides its own), with the words that name it:
# its label, its aria-label, else the first short line of the nearest part of the page around it, or just before
# that part, that is no upload button's own word (Greenhouse's "Attach", "Dropbox", "Enter manually" sit under
# "Resume/CV").
FILES = r"""() => [...document.querySelectorAll('input[type=file]')].map((el) => {
  const verb = /^(attach|upload|browse|choose( a)? file|drop( files?)?( here)?|dropbox|google drive|enter manually|or|\(optional\)|no files? (chosen|selected))\b/i;
  const lines = (s) => String(s || '').split('\n').map((l) => l.trim()).filter((l) => l && !verb.test(l));
  const clean = (s) => lines(s)[0] || '';
  const code = /^[a-z0-9]+([-_][a-z0-9]+)+$/i;  // a name for the page's code ("file-input", BambooHR's), not a person
  const own = (s) => { const said = clean(s); return code.test(said) ? '' : said; };
  let name = own(el.labels && el.labels[0] && el.labels[0].innerText) || own(el.getAttribute('aria-label'));
  for (let node = el.parentElement, up = 0; !name && node && up < 6; node = node.parentElement, up++) {
    for (const part of [node, node.previousElementSibling]) {
      const text = part ? clean(part.innerText) : '';
      if (!name && text && text.length <= 120) name = text;
    }
  }
  return {name, required: !!el.required, multiple: !!el.multiple, disabled: !!el.disabled};
})"""


# Whether a click on the element would submit a form: it is, sits in or holds a form's submit button (a <button> of
# no type or type=submit, an <input type=submit|image>), or a label for one (a click on a label clicks its control).
# A dropdown or option made of one submits its form as it opens or is picked, and a GET form's own submit handler can
# post the application past the guards (the review of KAN-861). Plain code never clicks one: its field is the
# student's.
SUBMITS = r"""el => {
  const submits = (b) => !!b && !!b.form && (b.tagName === 'BUTTON'
    ? (b.getAttribute('type') || 'submit').toLowerCase() === 'submit' : /^(submit|image)$/i.test(b.type || ''));
  const labelled = (l) => !!l && submits(l.control);
  return submits(el.closest('button, input')) || labelled(el.closest('label'))
    || [...el.querySelectorAll('button, input')].some(submits) || [...el.querySelectorAll('label')].some(labelled);
}"""


def submits(element: Locator) -> bool:
    """Whether a click on `element` would submit a form (SUBMITS). An element Apply can't read counts as one."""
    try:
        return element.evaluate(SUBMITS, timeout=3_000) is not False
    except Exception:
        return True


@dataclass
class Node:
    """One line of the ARIA snapshot and the lines under it."""

    role: str
    name: str = ""
    attrs: dict[str, str] = field(default_factory=dict)
    value: str = ""
    children: list["Node"] = field(default_factory=list)


def parse(snapshot: str) -> list[Node]:
    """The ARIA snapshot's tree, as nodes. A line it can't read (a link's /url) is left out with what is under it."""
    root = Node("root")
    stack: list[tuple[int, Node]] = [(-1, root)]
    for line in snapshot.splitlines():
        found = LINE.match(line)
        if not found:
            continue
        depth = len(found["indent"])
        while stack[-1][0] >= depth:
            stack.pop()
        name = json.loads(found["name"]) if found["name"] else ""
        attrs = {a[1]: a[2] if a[2] is not None else "true" for a in ATTR.finditer(found["attrs"] or "")}
        node = Node(found["role"], name, attrs, _scalar(found["value"] or ""))
        stack[-1][1].children.append(node)
        stack.append((depth, node))
    return root.children


def _scalar(value: str) -> str:
    """A snapshot value as text: a YAML scalar the snapshot quoted is read as JSON's."""
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        try:
            return str(json.loads(value))
        except ValueError:
            return value[1:-1]
    return value


@dataclass(frozen=True)
class Field:
    """One question of the form, as the reader found it. `how` says how the generic Filler fills it:
    "text" (a text box or text area), "native select" (a `<select>`), "radios", "checkbox" (one, as Yes or No),
    "checkboxes", "dropdown" (a combobox that lists its choices once opened), "search" (a box that lists its
    choices only as one types), "two-level" (a dropdown whose choices open more choices) or "file".
    `role`, `name` and `nth` find its element again (`locate`): for a radio group or a set of checkboxes, its
    first control's; `controls` are its options' (role, name, nth), in order. A file input has no role: `nth` is its
    place among the frame's file inputs."""

    how: str
    label: str
    kind: str
    required: bool
    options: tuple[str, ...] = ()
    role: str = ""
    name: str = ""
    nth: int = 0
    controls: tuple[tuple[str, str, int], ...] = ()
    shows: str | tuple[str, ...] = ""
    section: str = ""

    @property
    def key(self) -> tuple[str, str, int]:
        """What tells this field from the others on a step, read after read: its role (a file input: "file"), its
        label and its place. Never its `how`: a read that opens no dropdown can't tell a two-level list or a search
        box from a dropdown."""
        return (self.role or self.how, " ".join(self.label.lower().split()), self.nth)

    def question(self, name: str) -> Question:
        return Question(name, self.label, self.kind, self.required, self.options, section=self.section)


def locate(page: Page, role: str, name: str, nth: int) -> Locator:
    """The element of `role` named `name` (exactly), the `nth` of those; a nameless one by its place among every
    element of its role."""
    if name:
        return page.get_by_role(role, name=name, exact=True).nth(nth)
    return page.get_by_role(role).nth(nth)


def read(page: Page, open_dropdowns: bool = True) -> list[Field]:
    """Every field the top frame of `page` shows, in the page's order: each control the tree names, grouped into
    questions, then each file input. `open_dropdowns`: open each dropdown with no options in the tree to read its
    choices (one click each, then Escape)."""
    nodes = parse(page.locator("body").aria_snapshot())
    fields = _Reader(page, open_dropdowns).fields(nodes)
    return fields + _files(page)


class _Reader:
    def __init__(self, page: Page, open_dropdowns: bool):
        self._page = page
        self._open = open_dropdowns
        self._seen: dict[tuple[str, str], int] = {}  # (role, name): how many came so far, for each one's nth
        self._all: dict[str, int] = {}  # role: how many came so far, for a nameless one's nth
        self._before = ""  # the words just before this control, in the same part of the page
        self._fields: list[Field] = []
        self._text = ""  # the last words the page showed before a control: a nameless control's label
        self._section = ""  # the last heading
        self._loose: list[tuple[str, str, int, dict, str]] = []  # radios or checkboxes outside any group, in a row

    def fields(self, nodes: list[Node]) -> list[Field]:
        self._walk(nodes)
        self._flush()
        return self._fields

    def _nth(self, role: str, name: str) -> int:
        """The place of this control among those of its role and name; a nameless one's, among every one of its role
        (what `locate` finds it by). Every control counts, read or not."""
        key = (role, name)
        nth, every = self._seen.get(key, 0), self._all.get(role, 0)
        self._seen[key], self._all[role] = nth + 1, every + 1
        return nth if name else every

    def _facts(self, role: str, name: str, nth: int) -> dict:
        try:
            return locate(self._page, role, name, nth).evaluate(FACTS, timeout=3_000)
        except Exception:
            return {}

    def _walk(self, nodes: list[Node]) -> None:
        self._before = ""
        for node in nodes:
            if node.role == "heading":
                self._flush()
                self._section = self._text = node.name or node.value
                self._before = ""
            elif node.role in ("text", "paragraph", "strong", "emphasis", "label", "legend") and not node.children:
                said = (node.value or node.name).strip()
                if said and not any(said == name for _, name, _, _, _ in self._loose):
                    self._flush()
                    self._text = self._before = said
            elif node.role in GROUPS and _holds(node, {"radio", "checkbox", "switch"}):
                self._flush()
                self._group(node)
                self._before = ""
            elif node.role in CONTROLS:
                self._control(node)
                self._before = ""
            else:
                self._walk(node.children)
                self._before = ""
                if node.name and node.role not in ("link", "button", "img", "list", "listitem", "main", "form"):
                    self._text = self._text or node.name

    def _control(self, node: Node) -> None:
        role, name = node.role, node.name
        nth = self._nth(role, name)
        if role in ("radio", "checkbox", "switch"):
            facts = self._facts(role, name, nth)
            if self._loose and (self._loose[-1][0] != role or self._loose[-1][3].get("group", "") != facts.get("group", "")
                                or not facts.get("group")):
                self._flush()
            self._loose.append((role, name, nth, facts, node.attrs.get("checked", "")))
            if not facts.get("group"):
                self._flush()
            return
        self._flush()
        facts = self._facts(role, name, nth)
        if facts.get("disabled") or (facts.get("readonly") and role != "combobox"):
            return
        label, required = _label(self._named(name, facts), facts)
        if not label:
            return
        common = {"label": label, "required": required, "role": role, "name": name, "nth": nth, "section": self._section}
        if role in ("textbox", "searchbox", "spinbutton"):
            if facts.get("tag") == "INPUT" and facts.get("type") not in TEXT_TYPES:
                return
            kind = "textarea" if facts.get("tag") == "TEXTAREA" else "text"
            self._fields.append(Field("text", kind=kind, shows=node.value, **common))
        elif facts.get("tag") == "SELECT":
            options = tuple(dict.fromkeys(text for text, value, off in facts.get("options") or []
                                          if text and not off and not (value == "" and PLACEHOLDER.match(text))))
            options = tuple(o for i, o in enumerate(options) if i or not PLACEHOLDER.match(o))
            shown = [o.name for o in node.children if o.role == "option" and o.attrs.get("selected")]
            multiple = bool(facts.get("multiple"))
            self._fields.append(Field("native select", kind="multi_select" if multiple else "select", options=options,
                                      shows=tuple(shown) if multiple else (shown[0] if shown and shown[0] in options else ""),
                                      **common))
        elif role == "listbox":  # a list of options always open (aria): picked by clicking an option
            options = tuple(o.name for o in node.children if o.role == "option" and o.name)
            if options and not facts.get("owned"):
                self._fields.append(Field("dropdown", kind="select", options=options, shows=node.value, **common))
        else:  # a combobox of the page's own making
            self._fields.append(self._dropdown(node, facts, common))

    def _named(self, name: str, facts: dict) -> str:
        """A control's question: its own name, unless it has none or only asks for input (its placeholder, "Select...",
        Lever's "Type your response"); then the words just before it, else the last words the page showed. Words
        just before it that end in a required mark name it too when its own name doesn't hold them (Lever's
        "Name of School ✱" over a box named by its choice)."""
        before = " ".join(self._before.split())
        generic = not name or name == facts.get("placeholder") or GENERIC.match(name)
        if generic:
            return before or self._text
        if before and STAR.search(before) and STAR.sub("", before).lower() not in name.lower():
            return before
        return name

    def _dropdown(self, node: Node, facts: dict, common: dict) -> Field:
        """A combobox the page made: its options as the tree lists them, else as it lists them once opened; with
        none, a search box (it lists choices only as one types) or a dropdown whose choices the fill reads."""
        listed = tuple(o.name for o in node.children if o.role == "option" and o.name)
        typed = facts.get("tag") == "INPUT" and not facts.get("readonly")
        options = listed
        two_level = False
        if not options and self._open:
            options, two_level = _opened(self._page, locate(self._page, common["role"], common["name"], common["nth"]))
        shows = node.value
        if two_level:
            return Field("two-level", kind="text", shows=shows, **common)
        if options:
            return Field("dropdown", kind="select", options=options, shows=shows, **common)
        return Field("search" if typed else "dropdown", kind="text", shows=shows, **common)

    def _group(self, node: Node) -> None:
        """A group of radios or checkboxes: one question named by the group, else by its first words."""
        said = node.name or next((c.value or c.name for c in node.children if c.role in ("text", "paragraph", "legend")
                                  and (c.value or c.name)), "") or self._text
        members: list[tuple[str, str, int, dict, str]] = []

        def collect(nodes: list[Node]) -> None:
            for child in nodes:
                if child.role in ("radio", "checkbox", "switch"):
                    nth = self._nth(child.role, child.name)
                    members.append((child.role, child.name, nth, self._facts(child.role, child.name, nth),
                                    child.attrs.get("checked", "")))
                elif child.role in CONTROLS:
                    self._nth(child.role, child.name)
                else:
                    collect(child.children)
        collect(node.children)
        self._choices(members, said)

    def _flush(self) -> None:
        if self._loose:
            loose, self._loose = self._loose, []
            self._choices(loose, self._text)
            self._before = ""

    def _choices(self, members: list[tuple[str, str, int, dict, str]], said: str) -> None:
        members = [m for m in members if not m[3].get("disabled")]
        if not members:
            return
        role, name, nth, facts, checked = members[0]
        required = any(m[3].get("required") for m in members)
        controls = tuple((r, n, i) for r, n, i, _, _ in members)
        if role == "radio":
            label, starred = _label(said, {})
            if label:
                self._fields.append(Field("radios", label, "select", required or starred, tuple(m[1] for m in members),
                                          role, name, nth, controls, next((m[1] for m in members if m[4] == "true"), ""),
                                          self._section))
        elif len(members) == 1 and len(name.split()) <= AGREES and said and said != name:
            # One box of a few words under its question ("I Understand", Lever's): that one option, ticked or not.
            label, starred = _label(said, facts)
            if label:
                self._fields.append(Field("checkboxes", label, "multi_select", required or starred, (name,), role, name, nth,
                                          controls, (name,) if checked == "true" else (), self._section))
        elif len(members) == 1:  # one checkbox: Yes or No, named by its own words
            label, starred = _label(name or said, facts)
            if label:
                self._fields.append(Field("checkbox", label, "select", required or starred, ("Yes", "No"), role, name, nth,
                                          controls, "Yes" if checked == "true" else "", self._section))
        else:
            label, starred = _label(said, {})
            if label:
                self._fields.append(Field("checkboxes", label, "multi_select", required or starred,
                                          tuple(m[1] for m in members), role, name, nth, controls,
                                          tuple(m[1] for m in members if m[4] == "true"), self._section))


def _holds(node: Node, roles: set[str]) -> bool:
    return any(child.role in roles or _holds(child, roles) for child in node.children)


def _label(said: str, facts: dict) -> tuple[str, bool]:
    """A label as the form shows it, without its required mark, and whether it is required (the element says so, or
    the label ends in a star)."""
    said = " ".join(str(said).split())
    starred = bool(STAR.search(said))
    return STAR.sub("", said), starred or bool(facts.get("required"))


def _opened(page: Page, box: Locator) -> tuple[tuple[str, ...], bool]:
    """The choices a dropdown lists once opened (apply.steps._options_of: its own listbox's, else the ones that showed
    as it opened), and whether they open more choices of their own (a two-level list: an option that says it has a
    pop-up or that it expands)."""
    if submits(box):  # opening it would submit its form: never clicked, and its field is the student's
        return (), False
    try:
        options = _options_of(page, box)
    except Exception:
        return (), False
    if not options:
        return (), False
    try:
        box.click(timeout=3_000)
        nested = page.locator("[role=option][aria-haspopup]:visible, [role=option][aria-expanded]:visible").count() > 0
        page.keyboard.press("Escape")
    except Exception:
        nested = False
    return tuple(options), nested


def _files(page: Page) -> list[Field]:
    try:
        found = page.evaluate(FILES)
    except Exception:
        return []
    fields = []
    for at, one in enumerate(found):  # its place among the frame's file inputs: `input[type=file]` >> nth
        if one.get("disabled"):
            continue
        label, starred = _label(one.get("name") or "File", one)
        fields.append(Field("file", label, "file", starred or bool(one.get("required")), nth=at))
    return fields


def questions(fields: list[Field], first: int = 1, prefix: str = "g") -> tuple[list[Question], dict[str, Field]]:
    """The fields as Questions named g1, g2, ... from `first`, and each Field by its Question's name. Two fields of
    one label get the place they show in after it ("Phone (2)"), so the planner tells them apart."""
    counts: dict[str, int] = {}
    for f in fields:
        counts[f.label] = counts.get(f.label, 0) + 1
    seen: dict[str, int] = {}
    out, by_name = [], {}
    for i, f in enumerate(fields, first):
        name, asked = f"{prefix}{i}", f
        if counts[f.label] > 1:
            seen[f.label] = seen.get(f.label, 0) + 1
            if seen[f.label] > 1:
                asked = replace(f, label=f"{f.label} ({seen[f.label]})")
        out.append(asked.question(name))
        by_name[name] = f
    return out, by_name
