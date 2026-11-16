"""The generic Filler's reader of the ARIA snapshot (KAN-861), with no browser: CI's fast list. The reader on real
pages, and on the Fill engine's saved forms, is in test_generic_filler.py (Chromium, on a Mac)."""

from apply import form_tree
from apply.form_tree import Field, parse

SNAPSHOT = '''- heading "About you" [level=2]
- list:
  - listitem:
    - text: City ✱
    - textbox "Type your response"
- combobox "State":
  - option "Select..." [selected]
  - option "New York"
- group "Are you authorized?":
  - radio "Yes" [checked]
  - text: "Yes"
- textbox "Name \\"quoted\\"": "a: b"
- link "Privacy":
  - /url: https://example.com
- button "Next"'''


def test_a_snapshot_reads_as_its_tree():
    # Fault: a nested line read at the wrong depth, a quoted name or value read with its quotes, or an attribute lost.
    nodes = parse(SNAPSHOT)
    assert [n.role for n in nodes] == ["heading", "list", "combobox", "group", "textbox", "link", "button"]
    city = nodes[1].children[0].children
    assert [(n.role, n.name, n.value) for n in city] == [("text", "", "City ✱"), ("textbox", "Type your response", "")]
    assert [(o.name, o.attrs) for o in nodes[2].children] == [("Select...", {"selected": "true"}), ("New York", {})]
    assert nodes[3].children[0].attrs == {"checked": "true"} and nodes[3].children[1].value == "Yes"
    assert (nodes[4].name, nodes[4].value) == ('Name "quoted"', "a: b")
    assert nodes[5].children == []  # a link's /url is no node
    assert nodes[0].attrs == {"level": "2"}


def test_two_fields_of_one_label_are_asked_apart_and_keep_their_own_key():
    # Fault: two "Phone" questions the planner can't tell apart, or a renamed label that no longer finds its field
    # when the step is read again.
    one = Field("text", "Phone", "text", False, role="textbox", name="Phone", nth=0)
    two = Field("text", "Phone", "text", False, role="textbox", name="Phone", nth=1)
    asked, by_name = form_tree.questions([one, two], first=3)
    assert [(q.name, q.label) for q in asked] == [("g3", "Phone"), ("g4", "Phone (2)")]
    assert by_name["g4"].key == two.key == ("textbox", "phone", 1)
