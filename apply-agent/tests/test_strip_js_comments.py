"""The app build's JavaScript comment stripper (scripts/strip_js_comments.py, KAN-833): it removes comments from the
build's copy of Apply only where nothing else can change. No browser: in CI. Node is Playwright's own."""

import ast
import importlib.util
from pathlib import Path

import playwright

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "strip_js_comments.py"
spec = importlib.util.spec_from_file_location("strip_js_comments", SCRIPT)
strip = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strip)
NODE = str(Path(playwright.__file__).parent / "driver" / "node")

PAGE = '''const a = 1;  // why a is one
// a line of its own
/* a block
   of its own */
function f() { return a; }
'''


def module(folder: Path, name: str, value: str) -> Path:
    path = folder / f"{name}.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"PAGE = {value!r}\n")
    return path


def page_of(path: Path) -> str:
    return ast.literal_eval(ast.parse(path.read_text()).body[0].value)


def test_page_code_loses_its_comments_and_keeps_its_code(tmp_path):
    """Fault: a comment left in the app's page code, or code cut with it."""
    path = module(tmp_path, "dashboard_page", PAGE)
    assert strip.strip_module(path, NODE) == 3
    assert page_of(path) == "const a = 1;\nfunction f() { return a; }\n"


def test_a_block_comment_beside_code_keeps_the_code_between():
    """Fault: a block comment pattern that runs on to a later `*/` and takes the code in between with it. Node
    parses what is left, so only this catches it."""
    code = "/* a */ foo();\nbar(); /* b */\n"
    assert strip.stripped(code) == (code, 0)


def test_a_license_comment_and_a_template_literals_lines_stay():
    """Fault: a license notice removed (Playwright's injected script is Apache-2.0), or the text of a template
    literal changed because a line of it starts with //."""
    code = "// Playwright's injected script (Apache-2.0)\nconst t = `\n// text, not a comment\n`;\n"
    assert strip.stripped(code) == (code, 0)


def test_a_piece_node_cant_parse_stays_as_it_is(tmp_path):
    """Fault: comments cut from a string no parse can check (a template the code fills in), which could cut code."""
    template = "const a = {{}};  // filled in by .format\n{body}\n"
    path = module(tmp_path, "dashboard_page", template)
    assert strip.strip_module(path, NODE) == 0
    assert page_of(path) == template


def test_the_worker_extensions_page_code_is_never_touched(tmp_path):
    """Fault: a guard's or a fixed function's text changed in the app, so its sha256 no longer matches the store
    copy's and a plain Worker refuses it."""
    path = module(tmp_path / "plain", "guards", PAGE)
    strip.main(tmp_path, NODE)
    assert page_of(path) == PAGE
