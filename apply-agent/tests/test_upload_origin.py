"""A file goes only to the form's own site (KAN-795): hostile pages that try to get the applicant's file into a frame
of another site, on a CDP Worker and on a plain Worker, and a legitimate embedded form that still takes it.

The hostile pages: a cross-origin frame with a file input; a frame that navigates to another origin between the
choice and the set; and a script that swaps in a new input after the chooser opened. Every fake is on loopback:
127.0.0.1 is the form's site, and localhost, another origin, is the other site. Greenhouse's embed is served by a
Playwright route under its real https host, so no request leaves the Mac.
- no browser (CI's fast list): the rule, and the extension's copies of it;
- CDP: Playwright's Chromium, skipped where it isn't installed;
- plain: a plain Worker on Chrome for Testing, skipped where there is none.
"""

import http.server
import re
import sys
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from apply import upload_origin
from apply.upload_origin import Elsewhere, may_upload

APPLY = Path(__file__).parents[1]
GREENHOUSE_EMBED = "https://job-boards.greenhouse.io/embed/job_app?for=acme&token=5442881008"

# The other site's frame: a file input labelled for the résumé, and an upload button whose script clicks it.
EVIL = """<!doctype html><title>Widget</title><label>Resume <input type=file id=f></label>
<button type=button id=up onclick="document.getElementById('f').click()">Upload resume</button>
<script>
const f = document.getElementById('f');
const token = new URLSearchParams(location.search).get('token');
if (token) f.setAttribute('data-apply-mcp-chooser', token);  // the old document's mark, written again
f.addEventListener('change', () => { window.got = f.files.length; });
</script>"""
# The form's own frame (an iCIMS-style frame of the same site), or an embedded job system's form.
OWN = """<!doctype html><title>Form</title><label>Resume <input type=file id=f></label>
<button type=button id=up onclick="document.getElementById('f').click()">Upload resume</button>
<script>document.getElementById('f').addEventListener('change', (e) => { window.got = e.target.files[0].name; });</script>"""
PAGES = {
    "/cross": '<!doctype html><title>Apply</title><h1>Apply to Acme</h1><label>Name <input id=name></label>'
              '<iframe id=w src="http://localhost:{port}/evil" width=400 height=200></iframe>',
    "/same": '<!doctype html><title>Apply</title><h1>Apply to Acme</h1><iframe id=w src="/own" width=400 height=200></iframe>',
    "/company": f'<!doctype html><title>Careers at Acme</title><h1>Software Intern</h1>'
                f'<iframe id=w src="{GREENHOUSE_EMBED}" width=400 height=200></iframe>',
    # A localhost frame, a job system's in the test that names localhost one.
    "/embedded": '<!doctype html><title>Careers at Acme</title><h1>Software Intern</h1>'
                 '<iframe id=w src="http://localhost:{port}/own" width=400 height=200></iframe>',
    # The top frame's own input; swap() puts a new one, which posts its file elsewhere, in its place.
    "/swap": """<!doctype html><title>Apply</title><h1>Apply to Acme</h1>
        <button type=button id=up onclick="document.getElementById('f').click()">Upload resume</button>
        <input type=file id=f hidden>
        <script>window.swap = () => {
          const old = document.getElementById('f'), b = document.createElement('input');
          b.type = 'file'; b.id = 'b';
          for (const a of old.attributes) if (a.name.startsWith('data-')) b.setAttribute(a.name, a.value);
          b.addEventListener('change', () => { window.got = b.files.length; });
          old.replaceWith(b);
        };</script>""",
    "/evil": EVIL,
    "/own": OWN,
}


def _resume(folder: Path) -> Path:
    path = folder / "Test_Person_Resume.pdf"
    path.write_bytes(b"%PDF-1.4 test")
    return path


@pytest.fixture(scope="module")
def site():
    posted = []

    class Pages(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = PAGES.get(urlsplit(self.path).path, "<p>no").replace("{port}", str(self.server.server_address[1]))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode())

        def do_POST(self):  # never taken: recorded, and refused
            posted.append(self.path)
            self.send_response(403)
            self.end_headers()

        def log_message(self, *_):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Pages)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    server.url = f"http://127.0.0.1:{server.server_address[1]}"
    server.other = f"http://localhost:{server.server_address[1]}"
    yield server
    server.shutdown()
    assert not posted, "a fake form was sent"


# --- no browser


@pytest.mark.parametrize("own, ancestors, may", [
    ("https://acme.com/apply", [], True),  # the top frame
    ("https://acme.com/frame", ["https://acme.com/careers"], True),  # a frame of the top frame's own origin
    ("about:srcdoc", ["https://acme.com/careers"], True),  # takes its parent's origin
    ("about:blank", ["https://evil.example/x", "https://acme.com/careers"], False),
    ("https://evil.example/upload", ["https://acme.com/careers"], False),
    ("https://cdn.acme.com/frame", ["https://acme.com/careers"], False),  # another origin of the same site
    ("http://acme.com/frame", ["https://acme.com/careers"], False),  # another scheme
    (GREENHOUSE_EMBED, ["https://acme.com/careers"], True),
    ("https://careers-acme.icims.com/jobs/1/job?in_iframe=1", ["https://acme.com/careers"], True),
    ("https://jobs.ashbyhq.com/acme/embed", ["https://acme.com/careers"], True),
    ("https://greenhouse.io.evil.example/embed", ["https://acme.com/careers"], False),
    ("https://evilgreenhouse.io/embed", ["https://acme.com/careers"], False),
    ("data:text/html,<input type=file>", ["https://acme.com/careers"], False),
    ("https://acme.com/careers", ["null"], False),
])
def test_a_file_goes_only_to_the_top_frame_its_own_origin_or_a_job_systems_embedded_form(own, ancestors, may):
    assert may_upload(own, ancestors) is may


def _same(js: str) -> str:
    return re.sub(r"\s+", " ", js).strip()


@pytest.mark.parametrize("path", ["worker-extension/page/dom.js", "worker-extension/ops/tile.js"])
def test_the_worker_extensions_copies_of_the_rule_are_the_rules_own_words(path):
    assert _same(upload_origin.RULE_JS) in _same((APPLY / path).read_text())


def test_the_guard_script_carries_the_rule_and_the_job_systems_hosts():
    from apply import submit_guard

    for script in (submit_guard.SCRIPT, submit_guard.drive_script()):
        assert upload_origin.RULE_JS in script and '"greenhouse.io"' in script and upload_origin.BLOCKED in script


# --- CDP: Playwright's Chromium


def _chromium() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            p.chromium.launch().close()
        return True
    except Exception:
        return False


needs_chromium = pytest.mark.skipif(not _chromium(), reason="needs Playwright's Chromium (uv run playwright install chromium)")


@contextmanager
def cdp_page(guarded: bool = False):
    from playwright.sync_api import sync_playwright

    from apply import submit_guard
    from apply.submit_guard import DriveGuard

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.route(re.compile(r"^https://job-boards\.greenhouse\.io/"),
                   lambda route: route.fulfill(status=200, content_type="text/html", body=OWN))
        if guarded:
            submit_guard.on_open(page)  # the drive guard from before each document's own code, as a live run's page

        def armed():
            drive = DriveGuard(page)
            drive.arm()
            return drive
        try:
            yield page, armed
        finally:
            browser.close()


def _frame(page, part: str):
    page.wait_for_load_state("load")
    return next(f for f in page.frames if part in f.url)


@needs_chromium
def test_cdp_plain_code_gives_no_file_to_an_input_in_another_sites_frame(site, tmp_path):
    from apply.attach import attach_resume

    with cdp_page() as (page, _):
        page.goto(f"{site.url}/cross")
        evil = _frame(page, "/evil")
        with pytest.raises(Elsewhere, match="localhost"):
            attach_resume(page, _resume(tmp_path))
        with pytest.raises(Elsewhere):  # the input itself, named outright
            upload_origin.give(evil.locator("#f"), _resume(tmp_path))
        assert evil.evaluate("() => document.getElementById('f').files.length") == 0


@needs_chromium
def test_cdp_the_guard_opens_no_picker_in_another_sites_frame_so_claude_has_no_chooser(site):
    """Playwright MCP's upload sets the files of the chooser a click opened: under the guard, a click in the other
    site's frame, on its input or on a button whose script clicks it, opens none."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeout

    with cdp_page(guarded=True) as (page, armed):
        page.goto(f"{site.url}/cross")
        guard = armed()
        evil = _frame(page, "/evil")
        for target in ("#f", "#up"):
            with pytest.raises(PlaywrightTimeout):
                with page.expect_file_chooser(timeout=1_500):
                    evil.locator(target).click(force=True)
        assert any(b.startswith(upload_origin.BLOCKED) and "localhost" in b for b in guard.blocked())
        # A detached input's click() and a showPicker() are refused too.
        assert evil.evaluate("""() => { const i = document.createElement('input'); i.type = 'file'; i.click();
          try { document.getElementById('f').showPicker(); return 'opened'; } catch (e) { return e.name; } }""") == "NotAllowedError"


@needs_chromium
def test_cdp_a_frame_that_navigates_to_another_site_between_choose_and_set_gets_nothing(site, tmp_path):
    from playwright.sync_api import Error

    with cdp_page() as (page, _):
        page.goto(f"{site.url}/same")
        own = _frame(page, "/own")
        with page.expect_file_chooser() as chosen:
            own.locator("#up").click()
        own.evaluate(f"() => {{ location.href = '{site.other}/evil'; }}")
        page.wait_for_function("() => true")
        evil = None
        for _ in range(40):
            evil = next((f for f in page.frames if f.url.startswith(site.other)), None)
            if evil:
                break
            page.wait_for_timeout(100)
        evil.wait_for_load_state("load")
        with pytest.raises((Error, Elsewhere)):
            upload_origin.give(chosen.value, _resume(tmp_path))
        with pytest.raises(Error):  # Playwright MCP's own set, on the chooser it holds
            chosen.value.set_files(_resume(tmp_path))
        assert evil.evaluate("() => document.getElementById('f').files.length") == 0


@needs_chromium
def test_cdp_a_script_swapped_input_gets_no_file(site, tmp_path):
    with cdp_page() as (page, _):
        page.goto(f"{site.url}/swap")
        with page.expect_file_chooser() as chosen:
            page.locator("#up").click()
        page.evaluate("() => window.swap()")
        try:
            upload_origin.give(chosen.value, _resume(tmp_path))  # the old input only, now out of the page
        except Exception:
            pass
        assert page.evaluate("() => document.getElementById('b').files.length") == 0
        assert page.evaluate("() => window.got") is None


@needs_chromium
def test_cdp_an_embedded_greenhouse_form_still_takes_the_resume_and_opens_its_picker(site, tmp_path):
    from apply.attach import attach_resume

    with cdp_page(guarded=True) as (page, armed):
        page.goto(f"{site.url}/company")
        guard = armed()
        form = _frame(page, "greenhouse.io")
        assert attach_resume(page, _resume(tmp_path)) is True
        assert form.evaluate("() => window.got") == "Test_Person_Resume.pdf"
        with page.expect_file_chooser(timeout=3_000) as chosen:  # Claude's upload: the picker opens there
            form.locator("#up").click()
        upload_origin.give(chosen.value, _resume(tmp_path))
        assert not any(b.startswith(upload_origin.BLOCKED) for b in guard.blocked())


@needs_chromium
def test_cdp_a_same_origin_frame_still_takes_the_resume(site, tmp_path):
    from apply.attach import attach_resume

    with cdp_page(guarded=True) as (page, armed):
        page.goto(f"{site.url}/same")
        armed()
        assert attach_resume(page, _resume(tmp_path)) is True
        assert _frame(page, "/own").evaluate("() => window.got") == "Test_Person_Resume.pdf"


# --- plain Worker: Chrome for Testing


def _have_chrome() -> bool:
    try:
        from apply.plain.launcher import chrome_for_testing

        chrome_for_testing()
        return True
    except FileNotFoundError:
        return False


needs_chrome = pytest.mark.skipif(not _have_chrome(), reason="needs Chrome for Testing (uv run playwright install chromium)")


@pytest.fixture(scope="module")
def worker():
    from apply.plain.bridge import Bridge
    from apply.plain.launcher import PlainWorkers

    folder = Path(tempfile.mkdtemp(prefix="apw-upload-", dir="/tmp"))
    workers = PlainWorkers(folder, kind="testing", bridge=Bridge(folder / "w.sock"))  # its own socket
    yield workers.launch(0)
    workers.stop_all()


@pytest.fixture
def plain(worker, site):
    from apply.plain.page import PortPage

    return PortPage.first(worker.connection)


def _port_frame(page, part: str):
    import time

    for _ in range(50):
        if found := next((f for f in page.frames if part in f.url), None):
            return found
        time.sleep(0.1)
    raise AssertionError(f"no frame at {part}")


@contextmanager
def tools_on(page, folder: Path):
    from test_plain_claude import Client

    from apply.plain.tools import ToolServer

    with ToolServer(page, folder, sys.executable) as server:
        client = Client(server.mcp_server())
        try:
            yield client
        finally:
            client.close()


def _ref(snapshot: str, line_has: str, after: str = "") -> str:
    lines = snapshot.splitlines()
    start = next(i for i, line in enumerate(lines) if after in line) if after else 0
    line = next(line for line in lines[start:] if line_has in line)
    return line.split("[ref=")[1].split("]")[0]


@needs_chrome
def test_plain_claudes_upload_gives_no_file_to_another_sites_frame(plain, site, tmp_path):
    plain.goto(f"{site.url}/cross")
    evil = _port_frame(plain, "/evil")
    resume = _resume(tmp_path)
    with tools_on(plain, tmp_path) as tools:
        snapshot = tools.tool("browser_snapshot")[0]
        said, _ = tools.tool("browser_click", target=_ref(snapshot, 'button "Upload resume"', "/evil"), element="Upload resume")
        said, error = tools.tool("browser_file_upload", paths=[str(resume)])
        assert error and "not on the form's own site" in said and "localhost" in said
    assert evil.evaluate("() => document.getElementById('f').files.length") == 0
    with pytest.raises(Elsewhere):  # the frame's own check, with no word from Apply's first
        evil.locator("#f").set_input_files(resume)
    assert evil.evaluate("() => document.getElementById('f').files.length") == 0


@needs_chrome
def test_plain_code_gives_no_file_to_another_sites_frame(plain, site, tmp_path):
    from apply.attach import attach_resume

    plain.goto(f"{site.url}/cross")
    evil = _port_frame(plain, "/evil")
    with pytest.raises(Elsewhere):
        attach_resume(plain, _resume(tmp_path))
    assert evil.evaluate("() => document.getElementById('f').files.length") == 0


@needs_chrome
def test_plain_a_frame_that_navigates_to_another_site_between_choose_and_set_gets_nothing(plain, site, tmp_path):
    plain.goto(f"{site.url}/same")
    own = _port_frame(plain, "/own")
    resume = _resume(tmp_path)
    with tools_on(plain, tmp_path) as tools:
        snapshot = tools.tool("browser_snapshot")[0]
        said, _ = tools.tool("browser_click", target=_ref(snapshot, 'button "Upload resume"', "/own"), element="Upload resume")
        assert "[File chooser]" in said
        chooser = next(f["chooser"] for f in plain.worker.call("mcp.modal", tab=plain.tab, clear=[]) if f.get("chooser"))
        # The frame goes to the other site, whose input carries the old document's mark.
        own.evaluate(f"() => {{ location.href = '{site.other}/evil?token={chooser['token']}'; }}")
        evil = _port_frame(plain, site.other)
        evil.wait_for_function("() => document.readyState === 'complete'")
        with pytest.raises(Elsewhere):  # the set itself, in the frame as it is now
            evil.locator(f'[data-apply-mcp-chooser="{chooser["token"]}"]').set_input_files(resume)
        said, error = tools.tool("browser_file_upload", paths=[str(resume)])
        assert error
    assert evil.evaluate("() => document.getElementById('f').files.length") == 0


@needs_chrome
def test_plain_a_script_swapped_input_gets_no_file(plain, site, tmp_path):
    plain.goto(f"{site.url}/swap")
    with tools_on(plain, tmp_path) as tools:
        snapshot = tools.tool("browser_snapshot")[0]
        said, _ = tools.tool("browser_click", target=_ref(snapshot, 'button "Upload resume"'), element="Upload resume")
        assert "[File chooser]" in said
        plain.evaluate("() => window.swap()")  # later, the page's script: a new input, with the old one's mark
        said, error = tools.tool("browser_file_upload", paths=[str(_resume(tmp_path))])
        assert error and "put another file input" in said
    assert plain.evaluate("() => document.getElementById('b').files.length") == 0


@needs_chrome
def test_plain_a_same_origin_frame_and_a_job_systems_frame_still_take_the_file(plain, site, tmp_path, monkeypatch):
    resume = _resume(tmp_path)
    plain.goto(f"{site.url}/same")
    with tools_on(plain, tmp_path) as tools:
        snapshot = tools.tool("browser_snapshot")[0]
        tools.tool("browser_click", target=_ref(snapshot, 'button "Upload resume"', "/own"), element="Upload resume")
        said, error = tools.tool("browser_file_upload", paths=[str(resume)])
        assert not error, said
    assert _port_frame(plain, "/own").evaluate("() => window.got") == "Test_Person_Resume.pdf"
    # A job system's embedded form: localhost stands in for job-boards.greenhouse.io, which a plain Worker can't serve.
    monkeypatch.setattr(upload_origin, "JOB_SYSTEM_HOSTS", ("localhost",))
    plain.goto(f"{site.url}/embedded")
    with tools_on(plain, tmp_path) as tools:
        snapshot = tools.tool("browser_snapshot")[0]
        tools.tool("browser_click", target=_ref(snapshot, 'button "Upload resume"', "/own"), element="Upload resume")
        said, error = tools.tool("browser_file_upload", paths=[str(resume)])
        assert not error, said
    assert _port_frame(plain, site.other).evaluate("() => window.got") == "Test_Person_Resume.pdf"


@needs_chrome
def test_plain_the_guard_opens_no_picker_in_another_sites_frame(plain, site, tmp_path):
    from apply import submit_guard
    from apply.submit_guard import DriveGuard

    plain.goto("about:blank")
    submit_guard.on_open(plain)
    plain.goto(f"{site.url}/cross")
    guard = DriveGuard(plain)
    guard.arm()
    evil = _port_frame(plain, "/evil")
    with tools_on(plain, tmp_path) as tools:
        snapshot = tools.tool("browser_snapshot")[0]
        tools.tool("browser_click", target=_ref(snapshot, 'button "Upload resume"', "/evil"), element="Upload resume")
        _, error = tools.tool("browser_file_upload", paths=[str(_resume(tmp_path))])
        assert error
    assert any(b.startswith(upload_origin.BLOCKED) and "localhost" in b for b in guard.blocked())
    assert evil.evaluate("() => document.getElementById('f').files.length") == 0
    guard.lift()
