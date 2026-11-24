"""Remove the JavaScript comments from Apply's Python strings, in the app's build only (KAN-833, W8).

    python scripts/strip_js_comments.py <apply package folder> <node>

scripts/build_app.py runs it on its own copy of Apply (build/venv), never on the checkout: the comments stay in
the source for development, and the app ships no sentence that explains how its page code works.

What it removes, inside each Python string literal that holds page code:
- a line that is only a `//` comment, or only a `/* ... */` comment;
- a `//` comment after code, written as this code base writes one: two spaces, then `//`.
A comment that names a license or a copyright stays: a license can require it.

It changes a piece of code only when Node parses it, before and after, the same way: as a script, a function body,
or an expression. A piece Node can't parse alone (CSS, HTML, a string the code fills in with `.format` or joins
to others) stays as it is. An HTML string's <script> blocks are pieces of their own. A comment line inside a
template literal (an odd number of backticks before it) is text, not a comment, and stays.

It never touches the modules in STORE_CODE, whose page code goes into the Worker extension's store copy
(plain/fixed.py, plain/guards.py, plain/extension.py): the extension checks those files by sha256 against Apply's,
and the guards are public in the store copy anyway. build_app.py checks that the store copy's files are the same
after this ran.
"""

import ast
import io
import json
import re
import subprocess
import sys
import tokenize
from pathlib import Path

STORE_CODE = {
    "submit_guard", "natives", "send_click", "upload_origin", "plain/guards",  # the guards and what they take in
    "plain/fixed", "plain/extension",  # fixed.js and injected.js
    # Each module that plain/fixed.functions() takes a page function from.
    "attach", "captcha", "keepalive", "on_page", "page_functions", "regenerate", "stuck", "plain/page", "plain/tools",
}
SCRIPT = re.compile(r"(<script\b[^>]*>)(.*?)(</script>)", re.DOTALL | re.IGNORECASE)
COMMENTS = (
    re.compile(r"^[ \t]*//[^\n]*\n", re.MULTILINE),  # a whole line
    re.compile(r"^[ \t]*/\*(?:(?!\*/).)*\*/[ \t]*\n", re.MULTILINE | re.DOTALL),  # whole lines, one block
    re.compile(r"(?<=[;{}),\]])  +//[^\n]*$", re.MULTILINE),  # after code
)
# A notice a license can require: its word, a copyright, or a license's name ("Apache-2.0", not "license").
KEEP = re.compile(r"licen[cs]e|copyright|\(c\)|©|spdx|apache|\bmit\b|\bbsd\b|\b[al]?gpl|\bmpl\b|\bisc\b",
                  re.IGNORECASE)
# Node, given pieces on stdin, answers how each parses: "script", "body", "expression", or null.
PARSE = r"""
const vm = require('vm');
const pieces = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const tries = [['script', s => s], ['body', s => '(function(){' + s + '\n})'], ['expression', s => '(' + s + '\n)']];
const mode = s => { for (const [name, wrap] of tries) { try { new vm.Script(wrap(s)); return name; } catch (e) {} } return null; };
process.stdout.write(JSON.stringify(pieces.map(mode)));
"""


def stripped(code: str) -> tuple[str, int]:
    """`code` without its comments, and how many it removed."""
    removed = 0
    for pattern in COMMENTS:
        def cut(match: re.Match, code: str = code) -> str:
            nonlocal removed
            if KEEP.search(match.group()) or code.count("`", 0, match.start()) % 2:
                return match.group()
            removed += 1
            return ""

        code = pattern.sub(cut, code)
    return code, removed


def pieces(value: str) -> list[tuple[int, int]]:
    """The spans of `value` that may hold page code: each <script> block's body, or the whole string."""
    if "<script" in value.lower():
        return [match.span(2) for match in SCRIPT.finditer(value)]
    return [(0, len(value))]


def parse_modes(node: str, texts: list[str]) -> list[str | None]:
    done = subprocess.run([node, "-e", PARSE], input=json.dumps(texts), capture_output=True, text=True, check=True)
    return json.loads(done.stdout)


def literals(source: str) -> list[tuple[int, int, str]]:
    """Each plain string literal that may hold a comment: its span in `source` and its value. No f-string, no bytes."""
    starts = [0]
    for line in io.StringIO(source):  # split on "\n" only, as tokenize reads it: splitlines also splits on a form feed
        starts.append(starts[-1] + len(line))
    found = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.STRING:
            continue
        value = ast.literal_eval(token.string)
        if isinstance(value, str) and ("//" in value or "/*" in value):
            found.append((starts[token.start[0] - 1] + token.start[1], starts[token.end[0] - 1] + token.end[1], value))
    return found


def strip_module(path: Path, node: str) -> int:
    """Strip one module in place; returns how many comments it removed."""
    source = path.read_text()
    edits, total = [], 0
    for start, end, value in literals(source):
        spans = pieces(value)
        before = [value[a:b] for a, b in spans]
        after = [stripped(text) for text in before]
        changed = [i for i, (new, removed) in enumerate(after) if removed]
        if not changed:
            continue
        modes = parse_modes(node, [before[i] for i in changed] + [after[i][0] for i in changed])
        keep = {i for i, old, new in zip(changed, modes[:len(changed)], modes[len(changed):]) if old and old == new}
        if not keep:
            continue
        parts, last = [], 0
        for i, (a, b) in enumerate(spans):
            parts += [value[last:a], after[i][0] if i in keep else before[i]]
            last = b
        parts.append(value[last:])
        total += sum(after[i][1] for i in keep)
        edits.append((start, end, repr("".join(parts))))
    for start, end, text in reversed(edits):
        source = source[:start] + text + source[end:]
    if edits:
        path.write_text(source)
    return total


def main(package: Path, node: str) -> None:
    total = sum(strip_module(path, node) for path in sorted(package.rglob("*.py"))
                if path.relative_to(package).with_suffix("").as_posix() not in STORE_CODE)
    print(f"Removed {total} JavaScript comments from the build's copy of Apply.")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2])
