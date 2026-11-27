"""Each OS's own entries (W4, KAN-850): where Chrome, Chrome for Testing and the native host's folder are, how
Chrome starts in the background, and how a Worker comes forward. Each entry is picked by `system` (sys.platform's
"darwin" or "win32", else Linux), so this Mac runs the Windows and Linux entries too, on paths of their own. Running
on Windows and Linux is F4's. Needs no browser: in CI."""

import ast
import contextlib
import json
import os
import plistlib
import signal
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import fake_chrome
import platformdirs
import psutil
import pytest

from apply import (
    awake,
    browsers,
    captcha,
    chrome_finder,
    chrome_host,
    claude_cli,
    dashboard,
    focus,
    home,
    native_host,
    notify,
)
from apply.browsers import WorkerBrowsers
from apply.focus import FocusKeeper, NoKeeper
from apply.plain import channel, extension, launcher, seed_setup, tools, window_capture
from apply.plain.bridge import PortError
from apply.plain.launcher import PlainWorker, PlainWorkers

MAC_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def made(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("")
    return path


def test_chrome_is_looked_for_in_each_oss_own_places(tmp_path):
    assert chrome_finder.places("darwin", home=tmp_path) == [
        MAC_CHROME, tmp_path / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    env = {"PROGRAMFILES": str(tmp_path / "pf"), "PROGRAMFILES(X86)": str(tmp_path / "pf86"),
           "LOCALAPPDATA": str(tmp_path / "local")}
    assert chrome_finder.places("win32", env) == [
        tmp_path / root / "Google/Chrome/Application/chrome.exe" for root in ("pf", "pf86", "local")]
    on_path = {"google-chrome-stable": "/usr/bin/google-chrome-stable"}
    assert chrome_finder.places("linux", which=on_path.get) == [Path("/usr/bin/google-chrome-stable")]


def test_the_finder_takes_the_first_chrome_that_is_there(tmp_path):
    env = {"PROGRAMFILES": str(tmp_path / "pf"), "LOCALAPPDATA": str(tmp_path / "local")}
    assert chrome_finder.find("win32", env) is None
    per_user = made(tmp_path / "local/Google/Chrome/Application/chrome.exe")  # a student with no admin rights
    assert chrome_finder.find("win32", env) == per_user
    machine_wide = made(tmp_path / "pf/Google/Chrome/Application/chrome.exe")
    assert chrome_finder.find("win32", env) == machine_wide

    chrome = made(tmp_path / "bin/google-chrome")
    assert chrome_finder.find("linux", which={"google-chrome": str(chrome)}.get) == chrome
    assert chrome_finder.find("linux", which=lambda name: None) is None


def test_chromes_version_is_read_each_oss_way(tmp_path):
    app = tmp_path / "Google Chrome.app"
    made(app / "Contents/Info.plist").write_bytes(plistlib.dumps({"CFBundleShortVersionString": "142.0.7444.60"}))
    assert chrome_finder.version(app / "Contents/MacOS/Google Chrome", "darwin") == "142.0.7444.60"

    windows = made(tmp_path / "Application/chrome.exe")
    for folder in ("141.0.7390.55", "142.0.7444.60", "SetupMetrics"):
        (windows.parent / folder).mkdir()
    assert chrome_finder.version(windows, "win32") == "142.0.7444.60"  # an update leaves the old one a while

    asked = []

    def run(argv, **_):
        asked.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="Google Chrome 142.0.7444.59 \n")

    assert chrome_finder.version(Path("/usr/bin/google-chrome"), "linux", run=run) == "142.0.7444.59"
    assert asked == [["/usr/bin/google-chrome", "--version"]]

    assert chrome_finder.version(None, "darwin") is None
    assert chrome_finder.version(tmp_path / "none/MacOS/Google Chrome", "darwin") is None
    assert chrome_finder.version(tmp_path / "none/chrome.exe", "win32") is None


def test_a_workers_user_agent_names_its_oss_platform(tmp_path):
    app = tmp_path / "Google Chrome.app"
    made(app / "Contents/Info.plist").write_bytes(plistlib.dumps({"CFBundleShortVersionString": "142.0.7444.60"}))
    mac = chrome_finder.user_agent(app / "Contents/MacOS/Google Chrome", "darwin")
    assert mac == ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/142.0.0.0 Safari/537.36")
    assert "(Windows NT 10.0; Win64; x64)" in chrome_finder.user_agent(tmp_path / "none.exe", "win32")
    linux = chrome_finder.user_agent(tmp_path / "none", "linux")
    assert "(X11; Linux x86_64)" in linux and "Chrome/141.0.0.0" in linux  # no version read: a recent one


@pytest.mark.parametrize("system, binary", [
    ("darwin", "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"),
    ("win32", "chrome-win64/chrome.exe"),
    ("linux", "chrome-linux64/chrome"),
])
def test_chrome_for_testing_is_found_in_each_oss_layout(tmp_path, system, binary):
    for revision in (1248, 1254):
        made(tmp_path / f"chromium-{revision}" / binary)
    made(tmp_path / "chromium_headless_shell-1260" / binary)  # Playwright's headless shell: not Chrome for Testing
    assert chrome_finder.chrome_for_testing(tmp_path, system) == tmp_path / "chromium-1254" / binary
    other = next(s for s in ("darwin", "win32", "linux") if s != system)
    with pytest.raises(FileNotFoundError, match="playwright install chromium"):
        chrome_finder.chrome_for_testing(tmp_path, other)


def test_playwrights_browsers_are_in_its_env_folder_or_the_oss_cache_folder():
    assert chrome_finder.playwright_browsers({"PLAYWRIGHT_BROWSERS_PATH": "/x/browsers"}) == Path("/x/browsers")
    assert chrome_finder.playwright_browsers({}) == platformdirs.user_cache_path() / "ms-playwright"
    if sys.platform == "darwin":
        assert chrome_finder.playwright_browsers({}) == Path.home() / "Library/Caches/ms-playwright"


def test_the_app_folder_is_the_oss_standard_place():
    assert home.APP_FOLDER == platformdirs.user_data_path("WorkIt Auto Apply", appauthor=False, roaming=False)
    if sys.platform == "darwin":
        assert home.APP_FOLDER == Path.home() / "Library/Application Support/WorkIt Auto Apply"


def test_the_native_host_folder_is_each_oss_chromes(tmp_path):
    assert native_host.chrome_hosts("darwin", tmp_path) == \
        tmp_path / "Library/Application Support/Google/Chrome/NativeMessagingHosts"
    assert native_host.chrome_hosts("linux", tmp_path, env={}) == tmp_path / ".config/google-chrome/NativeMessagingHosts"
    assert native_host.chrome_hosts("linux", tmp_path, env={"XDG_CONFIG_HOME": str(tmp_path / "xdg")}) == \
        tmp_path / "xdg/google-chrome/NativeMessagingHosts"
    assert native_host.chrome_hosts("win32", tmp_path) == chrome_host.WINDOWS_FOLDER  # the one the key names


def test_the_accounts_hosts_files_are_where_windows_chrome_looks(tmp_path, monkeypatch):
    """Faults (P5): on Windows no registry key names the accounts host's manifest, so the WorkIt extension's Sign In
    with Your Apply Account finds no host; its .bat doesn't set APPLY_HOME (or reads a % in it as a variable), so the
    host answers from another data folder's Employer accounts; or chrome_host.found, which doctor reads, names
    another manifest than the key does."""
    monkeypatch.setattr(chrome_host, "WINDOWS_FOLDER", tmp_path / "native-hosts")
    home, registry = tmp_path / "ap%1", fake_chrome.FakeRegistry()
    manifest = native_host.install(native_host.chrome_hosts("win32"), r"C:\venv\python.exe", home, "win32", registry)
    assert chrome_host.found(native_host.NAME, tmp_path / "elsewhere", "win32", registry) == manifest
    assert chrome_host.found(native_host.NAME, tmp_path / "elsewhere", "win32", fake_chrome.FakeRegistry()) is None
    wrapper = Path(json.loads(manifest.read_text())["path"])
    assert wrapper == home / "apply-accounts-host.bat"
    bat = (f'@echo off\r\nchcp 65001 >nul\r\nset "APPLY_HOME={tmp_path}{os.sep}ap%%1"\r\n'
           '"C:\\venv\\python.exe" "-m" "apply.native_host" %*\r\n')
    assert wrapper.read_bytes() == bat.encode()


def test_a_workers_host_files_are_where_each_oss_chrome_looks(tmp_path, monkeypatch):
    """Faults (P5): on Windows no registry key names the host's manifest (Chrome there reads no folder); the .bat
    echoes its command or chcp's line into Chrome's pipe, drops Chrome's arguments (%*: the caller's origin), lets
    cmd.exe read a % in a path as a variable, or can't hold a path such as C:\\Users\\Łukasz; the manifest lets
    another extension call the host (on Windows every Chrome of this user's finds it); or off Windows the files
    leave the Worker's profile, or a registry is touched."""
    monkeypatch.setattr(chrome_host, "WINDOWS_FOLDER", tmp_path / "native-hosts")
    command = [r"C:\Program Files\py%1\python.exe", "-I", r"C:\Łukasz\host.py"]
    monkeypatch.setattr(launcher, "host_command", lambda: command)
    workers, registry = PlainWorkers(tmp_path / "profiles", kind="testing"), fake_chrome.FakeRegistry()
    manifest = workers.install_host(1, "win32", registry)
    assert manifest.parent == tmp_path / "native-hosts"
    assert registry.values == {
        ("HKEY_CURRENT_USER", rf"{chrome_host.KEY}\com.workit.apply_worker", ""): (registry.REG_SZ, str(manifest))}
    written = json.loads(manifest.read_text())
    assert written["allowed_origins"] == list(extension.EXTENSION_ORIGINS)
    bat = '@echo off\r\nchcp 65001 >nul\r\n"C:\\Program Files\\py%%1\\python.exe" "-I" "C:\\Łukasz\\host.py" %*\r\n'
    assert Path(written["path"]).read_bytes() == bat.encode()
    off_windows = workers.install_host(1, "darwin", fake_chrome.NoRegistry())
    assert off_windows.parent == workers.profile(1) / "NativeMessagingHosts"


def test_focuskeeper_runs_on_the_mac_only(monkeypatch):
    assert isinstance(focus.keeper("darwin"), FocusKeeper)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("an OS call off the Mac"))
    for system in ("win32", "linux"):
        keeper = focus.keeper(system)
        assert isinstance(keeper, NoKeeper)
        with keeper.launching():
            keeper.watch(4242)
            keeper.watch(4243, seconds=5)
        keeper.forget(4242)
        assert keeper.bring(4242) is False  # its caller brings the Worker through Chrome


def test_off_the_mac_a_notice_goes_to_the_terminal(monkeypatch, capsys):
    """Fault: a run's notices went to osascript on every OS, so on Windows the first one stopped the run."""
    monkeypatch.setattr(notify.subprocess, "run", lambda *a, **k: pytest.fail("osascript off the Mac"))
    assert isinstance(notify.desktop("darwin"), notify.MacNotifier)
    notify.desktop("win32").notify("Apply", "3 submitted")
    assert capsys.readouterr().err == "Apply: 3 submitted\n"


def test_on_windows_claude_and_its_mcp_server_are_killed_as_a_tree():
    """Fault: Windows has no os.killpg, and start_new_session does nothing there: each stop of claude raised
    AttributeError, and claude and its Playwright MCP server kept running."""
    started = "import subprocess, sys, time; c = subprocess.Popen([sys.executable, '-c', 'import time; " \
              "time.sleep(60)']); print(c.pid, flush=True); time.sleep(60)"
    claude = subprocess.Popen([sys.executable, "-c", started], stdout=subprocess.PIPE, text=True)  # no group of its own
    mcp = psutil.Process(int(claude.stdout.readline()))
    try:
        claude_cli.kill_tree(claude, "win32")
        claude.wait(5)
        mcp.wait(5)  # psutil.TimeoutExpired while it runs
    finally:
        claude.kill()
        with contextlib.suppress(psutil.Error):
            mcp.kill()


def test_linux_is_not_kept_awake():
    assert awake.command("darwin", 4242) == ["/usr/bin/caffeinate", "-dims", "-w", "4242"]
    assert awake.command("win32") is None and awake.command("linux") is None
    with awake.awake("linux", popen=lambda *a, **k: pytest.fail("an OS call"), state=lambda flags: pytest.fail()):
        pass


def test_windows_is_kept_awake_for_the_block_only():
    """Fault: Windows slept during a run, mid-form (P11): the keep-awake did nothing off the Mac."""
    asked = []
    with pytest.raises(KeyError):  # a run that fails lets Windows sleep again too
        with awake.awake("win32", popen=lambda *a, **k: pytest.fail("Windows needs no process"),
                         state=lambda flags: asked.append(flags) or 1):
            assert asked == [0x80000003]  # ES_CONTINUOUS, ES_SYSTEM_REQUIRED and ES_DISPLAY_REQUIRED
            raise KeyError
    assert asked == [0x80000003, 0x80000000]  # ES_CONTINUOUS alone: sleep as usual


def test_on_the_mac_caffeinate_runs_for_the_block_only():
    started = []

    class Caffeinate:
        def __init__(self, arguments, **kwargs):
            self.arguments, self.stopped = arguments, False
            started.append(self)

        def terminate(self):
            self.stopped = True

        def wait(self, timeout=None):
            return 0

    with awake.awake("darwin", popen=Caffeinate):
        assert started[0].arguments[-1] == str(os.getpid()) and not started[0].stopped
    assert started[0].stopped


@pytest.mark.parametrize("system, detached", [
    ("linux", {"start_new_session": True}),
    ("win32", {"creationflags": launcher.CREATE_NEW_PROCESS_GROUP}),
])
def test_off_the_mac_chrome_starts_as_a_plain_background_process(tmp_path, system, detached):
    started = []

    def popen(argv, **kwargs):
        started.append((argv, kwargs))
        return SimpleNamespace(pid=4242)

    arguments = ["/opt/google/chrome/chrome", f"--user-data-dir={tmp_path}", "--no-startup-window"]
    process = launcher.start_in_background(arguments, tmp_path, tmp_path / "plain-1.log", system, popen)

    [(argv, kwargs)] = started
    assert process.pid == 4242 and argv == arguments  # the binary itself, never `open`
    assert kwargs["stdin"] == subprocess.DEVNULL and kwargs["stdout"] is kwargs["stderr"]
    assert {key: kwargs[key] for key in detached} == detached
    assert (tmp_path / "plain-1.log").exists()


def test_on_the_mac_chrome_starts_through_open_g(tmp_path, monkeypatch):
    ran = []
    monkeypatch.setattr(launcher.subprocess, "run", lambda argv, **kwargs: ran.append(argv))
    monkeypatch.setattr(launcher, "chrome_pid", lambda profile: 4242)
    arguments = [str(MAC_CHROME), f"--user-data-dir={tmp_path}"]

    process = launcher.start_in_background(arguments, tmp_path, tmp_path / "plain-1.log", "darwin",
                                           popen=lambda *a, **k: pytest.fail("the binary itself, on the Mac"))

    assert isinstance(process, launcher.Chrome) and process.pid == 4242
    assert ran[0][:5] == ["/usr/bin/open", "-g", "-n", "-a", "/Applications/Google Chrome.app"]
    assert ran[0][-2:] == ["--args", f"--user-data-dir={tmp_path}"]


def test_on_the_mac_the_seeds_chrome_starts_through_open_in_front_never_as_this_apps_child(tmp_path, monkeypatch):
    """Fault: the seed's Chrome started from its binary is the app's child, so macOS blamed WorkIt Auto Apply when
    Chrome's updater changed Google Chrome.app ("prevented from modifying apps"); or started with -g, so the window
    the user works in stays behind."""
    from apply.plain import seed_setup

    ran = []
    monkeypatch.setattr(launcher.subprocess, "run", lambda argv, **kwargs: ran.append(argv))
    monkeypatch.setattr(launcher, "chrome_pid", lambda profile: 4242)
    seed_setup.Desk(tmp_path / "plain-seed", MAC_CHROME).open_chrome(seed_setup.EXTENSIONS_PAGE, "darwin")
    assert ran[0][:4] == ["/usr/bin/open", "-n", "-a", "/Applications/Google Chrome.app"]


class Port:
    """A plain Worker's port: the ops it was called with, and what `windows.focus` does."""

    def __init__(self, error: Exception | None = None):
        self.calls, self.error = [], error

    def call(self, op, **params):
        self.calls.append(op)
        if self.error:
            raise self.error


def plain(tmp_path, port):
    workers = PlainWorkers(tmp_path / "profiles", kind="testing")
    workers.running[0] = PlainWorker(0, tmp_path / "plain-1", SimpleNamespace(pid=4242), port)
    return workers


def test_off_the_mac_a_plain_worker_comes_forward_through_its_extension(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "KEEPER", NoKeeper())
    port = Port()
    assert plain(tmp_path, port).show(0) and port.calls == ["windows.focus"]
    assert not plain(tmp_path, port).show(1)  # no Worker 2 runs
    old = Port(PortError("UnknownOp", "windows.focus: no such op"))  # an extension from before windows.focus
    assert not plain(tmp_path, old).show(0)


def test_on_the_mac_focuskeeper_brings_a_plain_worker_and_its_extension_only_if_that_fails(tmp_path, monkeypatch):
    brought, port = [], Port()
    monkeypatch.setattr(launcher.KEEPER, "bring", lambda pid: brought.append(pid) or True)
    assert plain(tmp_path, port).show(0) and brought == [4242] and port.calls == []
    monkeypatch.setattr(launcher.KEEPER, "bring", lambda pid: False)  # System Events refused, say
    assert plain(tmp_path, port).show(0) and port.calls == ["windows.focus"]


@pytest.fixture
def devtools():
    """A Chrome's DevTools HTTP server, faked: `/json/list` lists `targets`, most recently used first, and
    `/json/activate/<id>` notes the page it brought forward."""
    activated, targets = [], [{"id": "SW", "type": "service_worker"}, {"id": "FORM", "type": "page"},
                              {"id": "OLD", "type": "page"}]

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/json/list":
                body = json.dumps(targets).encode()
            elif self.path.startswith("/json/activate/"):
                activated.append(self.path.rsplit("/", 1)[1])
                body = b"Target activated"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield SimpleNamespace(port=server.server_address[1], activated=activated)
    server.shutdown()
    server.server_close()


def test_off_the_mac_a_cdp_worker_comes_forward_through_chrome(tmp_path, monkeypatch, devtools):
    monkeypatch.setattr(browsers, "KEEPER", NoKeeper())
    monkeypatch.setattr(browsers, "chrome_pid", lambda profile: 4242 if profile.name == "worker-2" else None)
    for worker in ("worker-1", "worker-2"):  # worker-1's Chrome quit: Chrome leaves the file, and the port is another's now
        made(tmp_path / worker / "DevToolsActivePort").write_text(f"{devtools.port}\n/devtools/browser/x\n")

    assert WorkerBrowsers(tmp_path, headless=False).show(1)
    assert devtools.activated == ["FORM"]  # the page used last: the Worker's form
    assert not WorkerBrowsers(tmp_path, headless=False).show(0)  # not open: the Chrome on its old port is left alone
    assert not WorkerBrowsers(tmp_path, headless=True).show(1)  # no window to show
    assert devtools.activated == ["FORM"]


def test_activate_is_false_when_no_chrome_answers():
    assert not browsers.activate(None)
    server = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    gone = server.server_address[1]
    server.server_close()
    assert not browsers.activate(f"http://127.0.0.1:{gone}")


@pytest.mark.parametrize("system", ["win32", "linux"])
def test_off_the_mac_the_everyday_chrome_gets_the_link_and_no_profile_flag(monkeypatch, system):
    started, url = [], "https://asml.wd3.myworkdayjobs.com/en-US/ASMLExternal/job/X_R1"
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("`open` off the Mac"))
    captcha.to_everyday_chrome(url, Path("/opt/google/chrome/google-chrome"), system,
                               popen=lambda argv, **kwargs: started.append((argv, kwargs["start_new_session"])))
    assert started == [(["/opt/google/chrome/google-chrome", url], True)]  # a running Chrome takes it in its own profile


def test_on_the_mac_the_everyday_chrome_opens_the_link_as_its_own_app(monkeypatch):
    ran, url = [], "https://asml.wd3.myworkdayjobs.com/en-US/ASMLExternal/job/X_R1"
    monkeypatch.setattr(subprocess, "run", lambda argv, **kwargs: ran.append(argv))
    captcha.to_everyday_chrome(url, MAC_CHROME, "darwin",
                               popen=lambda *a, **k: pytest.fail("its binary would make it Apply's child process"))
    assert ran == [["open", "-a", "/Applications/Google Chrome.app", url]]  # Launch Services starts it: no Apply's permissions


def test_with_no_chrome_the_everyday_chrome_says_how_to_get_it(monkeypatch):
    monkeypatch.setattr(chrome_finder, "find", lambda *a, **k: None)
    with pytest.raises(FileNotFoundError, match="google.com/chrome"):
        captcha.to_everyday_chrome("https://x.example/", popen=lambda argv, **kwargs: pytest.fail("no Chrome to start"))


@pytest.mark.parametrize("system, command", [
    ("darwin", ["open", "-R", "/a/worker-extension"]),
    ("win32", 'explorer /select,"/a/worker-extension"'),  # one string: a path with a space stays one
    ("linux", ["xdg-open", "/a"]),
])
def test_the_seed_guide_shows_the_folder_each_oss_way(monkeypatch, system, command):
    ran = []
    monkeypatch.setattr(subprocess, "run", lambda argv, **kwargs: ran.append(argv))
    seed_setup.Desk(Path("/seed")).reveal(Path("/a/worker-extension"), system)
    assert ran == [command]


def test_on_windows_a_folder_with_a_space_in_its_path_is_shown_whole(monkeypatch):
    ran = []
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: ran.append(command))
    seed_setup.Desk(Path("/seed")).reveal(Path("/Users/Jane Doe/profiles/worker-extension"), "win32")
    # Python would quote the whole "/select,<path>" argument, and Explorer would open its default folder.
    assert ran == ['explorer /select,"/Users/Jane Doe/profiles/worker-extension"']


def test_a_stale_lock_whose_pid_another_user_took_leaves_the_profile_free(tmp_path, monkeypatch):
    """Fault: chrome_pid counts a live PID whose arguments Apply may not read as the profile's Chrome. A Chrome that
    crashed left its lock, the OS gave its PID to another user's process (root's, on a Mac: AccessDenied), and the
    Worker stayed in use for good: reclaim can't read that process either (found in review, 2026-11-21)."""
    (tmp_path / "SingletonLock").symlink_to(f"this-mac-{os.getpid()}")  # a live PID, played as another user's

    def denied():
        raise psutil.AccessDenied(os.getpid())

    monkeypatch.setattr(browsers.psutil, "Process", lambda pid: SimpleNamespace(cmdline=denied))
    assert not browsers.in_use(tmp_path)


def test_on_windows_the_profiles_chrome_is_found_by_its_arguments(tmp_path, monkeypatch):
    """Windows' Chrome makes no SingletonLock, so chrome_pid read nothing there and every profile looked free: a second
    run could open a profile a Worker had open (P3). Faults: no Windows entry; a helper (`--type=`), another
    profile's browser, or a process whose arguments Apply may not read taken for the profile's Chrome."""
    profile = tmp_path / "plain-1"
    profile.mkdir()
    chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    processes = [
        (11, [chrome, "--type=renderer", f"--user-data-dir={profile}"]),  # a helper of the profile's Chrome
        (12, [chrome, f"--user-data-dir={tmp_path / 'plain-2'}"]),  # another profile's browser
        (13, None),  # a process Apply may not read: psutil gives it no arguments
        (14, [chrome, f"--user-data-dir={profile}", "--no-first-run"]),  # the profile's own browser
    ]
    monkeypatch.setattr(browsers.psutil, "process_iter", lambda attrs=None, ad_value=None: [
        SimpleNamespace(pid=pid, info={"cmdline": arguments}) for pid, arguments in processes])

    assert browsers.chrome_pid(profile, "win32") == 14
    processes.pop()  # its Chrome quits
    assert browsers.chrome_pid(profile, "win32") is None


@pytest.mark.parametrize("system", ["win32", "linux"])
def test_off_the_mac_a_tile_takes_the_extensions_frames(monkeypatch, system):
    """Fault: native capture off the Mac. Its helper is ScreenCaptureKit's, and its permission note named the app
    through `ps`, which Windows lacks: every plain Worker's tile failed on each watch turn and stayed blank, and each
    turn added its handlers again (found in review, 2026-11-24)."""
    monkeypatch.delenv("APPLY_TILE_CAPTURE", raising=False)
    assert window_capture.mode(system) == "extension"
    assert window_capture.mode("darwin") == "native"


def test_a_hosts_chrome_is_the_browser_above_it_read_with_no_ps(monkeypatch, tmp_path):
    """Faults: chrome_of reads the host's parent with `ps`, which Windows lacks (found in review, 2026-11-24), or
    takes the host's parent for its Chrome: on Windows that is cmd.exe, which starts the host's .bat (P5). Either way
    the tile's check that a connection is its Worker's own fails on every Worker there."""
    def no_ps(*args, **kwargs):
        raise FileNotFoundError("ps")  # as on Windows

    monkeypatch.setattr(window_capture.subprocess, "run", no_ps)
    host = "import os, sys; print(os.getpid(), flush=True); sys.stdin.read()"  # it ends as its stdin closes
    chrome = subprocess.Popen(fake_chrome.command(tmp_path / "plain-1", sys.executable, "-c", host),
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        assert window_capture.chrome_of(int(chrome.stdout.readline())) == chrome.pid
    finally:
        chrome.stdin.close()
        chrome.wait(5)
    assert window_capture.chrome_of(None) is None


def taskkill(record: Path) -> tuple[str, ...]:
    """A stand-in for Windows' taskkill (launcher.TASKKILL) that writes what it was asked into `record`."""
    return sys.executable, "-c", f"import sys; open({str(record)!r}, 'w').write(' '.join(sys.argv[1:]))"


def test_on_windows_a_worker_is_asked_to_close_and_killed_only_after_the_wait(tmp_path, monkeypatch):
    """Fault: on Windows a signal, Popen.terminate and psutil's terminate all kill at once, with no save (P7): a
    Worker stopped so loses its job sites' sign-ins, the session cookies that --restore-last-session keeps."""
    monkeypatch.setattr(launcher, "TASKKILL", taskkill(tmp_path / "asked"))
    monkeypatch.setattr(launcher, "STOP_WAIT", 0.5)
    chrome = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        launcher._stop(chrome, "win32")  # this stand-in never closes: it has no window
        assert (tmp_path / "asked").read_text() == f"/PID {chrome.pid}"  # asked while it ran, and no /F
        assert chrome.returncode == -signal.SIGKILL  # killed only once it didn't quit in time
    finally:
        chrome.kill()
        chrome.wait()


def test_off_the_mac_the_apply_window_is_chrome_itself_found_by_its_profile(tmp_path, monkeypatch):
    """Fault: every rehearsal and run opened its Apply window with `open -na` and the Dock app, and found it with
    pgrep, none of which Windows has: `apply rehearse` stopped at its start there, and each window's close too."""
    real_run = subprocess.run

    def run(arguments, **kwargs):
        if arguments[0] in ("open", "pgrep", "osascript"):
            pytest.fail(f"a Mac command off the Mac: {arguments}")
        return real_run(arguments, **kwargs)

    started, chromes = [], []

    def start(arguments, profile, log, system, front=False):  # a stand-in Chrome, as launcher's Windows start
        started.append((arguments, front))
        chromes.append(subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", *arguments[1:]]))
        return chromes[-1]

    monkeypatch.setattr(dashboard.subprocess, "run", run)
    monkeypatch.setattr(launcher, "start_in_background", start)
    monkeypatch.setattr(chrome_finder, "find", lambda system=None: Path("C:/Chrome/chrome.exe"))
    # Windows' taskkill as a Chrome takes it: its window closes, and so it quits.
    asked = tmp_path / "asked"
    monkeypatch.setattr(launcher, "TASKKILL", (sys.executable, "-c", f"import os, sys; open({str(asked)!r}, 'w')"
                                               ".write(' '.join(sys.argv[1:])); os.kill(int(sys.argv[2]), 15)"))
    profile = tmp_path / "dashboard"
    try:
        dashboard.open_window("http://127.0.0.1:5001", profile, front=False, system="win32")
        (arguments, front), = started
        assert arguments[0] == "C:/Chrome/chrome.exe" and not front
        assert {"--app=http://127.0.0.1:5001", f"--user-data-dir={profile}"} <= set(arguments)
        assert dashboard.window_open(profile, "win32")  # found by its profile
        dashboard.open_window("http://127.0.0.1:5001", profile, system="win32")  # this server's window: not again
        assert len(started) == 1
        dashboard.open_window("http://127.0.0.1:6002", profile, system="win32")  # an older run's: it quits first
        assert asked.read_text() == f"/PID {chromes[0].pid}"  # asked to close: a signal would kill it at once
        assert len(started) == 2 and dashboard._window_chromes(profile, "win32")[0][1] == "http://127.0.0.1:6002"
    finally:
        for process in chromes:
            process.kill()
            process.wait()
        dashboard._STARTED.clear()


def test_a_chrome_whose_pid_went_to_another_program_is_never_signalled(tmp_path, monkeypatch):
    """Fault: launcher.Chrome polls and signals a bare PID. Its Chrome had ended, the OS gave the PID to another
    program (played by this test's own process), and _stop sent that program SIGTERM, then SIGKILL (found in review,
    2026-11-24). psutil refuses a reused PID: is_running() is False, and each signal raises NoSuchProcess."""
    sent = []
    monkeypatch.setattr(launcher.os, "kill", lambda pid, number: sent.append((pid, number)))

    class Reused:  # the Chrome's psutil.Process, after its PID went to another program
        def is_running(self):
            return False

        def send_signal(self, number):
            raise psutil.NoSuchProcess(os.getpid())

        def kill(self):
            raise psutil.NoSuchProcess(os.getpid())

    monkeypatch.setattr(launcher.psutil, "Process", lambda pid: Reused())
    chrome = launcher.Chrome(os.getpid())

    assert chrome.poll() == 0
    chrome.send_signal(signal.SIGTERM)
    chrome.kill()
    launcher._stop(chrome)
    assert sent == []
    monkeypatch.setattr(launcher, "TASKKILL", taskkill(tmp_path / "asked"))
    launcher.ask_to_quit(chrome, "win32")  # taskkill would close that other program's windows
    assert not (tmp_path / "asked").exists()


def test_on_windows_the_channel_is_a_named_pipe_one_for_each_folder(tmp_path, monkeypatch):
    """Faults: the Windows channel is a Unix socket (Python on Windows has none: no plain Worker reaches Apply), two
    profiles folders share one pipe (a second Apply would take the first one's Workers' channel), or a Windows path
    reaches os.getuid, which Windows lacks (P4)."""
    monkeypatch.delattr(os, "getuid")
    long = tmp_path / ("x" * 120)
    path = channel.socket_path(long, "win32")
    assert path == long / "workers.sock"  # no /tmp fallback: on Windows the path only names the pipe
    assert channel.pipe_name(path).startswith("\\\\.\\pipe\\workit-apply-")
    assert channel.pipe_name(path) == channel.pipe_name(long / "workers.sock")
    assert channel.pipe_name(path) != channel.pipe_name(channel.socket_path(tmp_path / "two", "win32"))
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))  # Windows' temp folder, played here
    assert tools.socket_folder("win32") == tmp_path / "apply"
    made = []
    monkeypatch.setattr(channel, "ConnectionListener", lambda address, family, at: made.append((address, family)))
    channel.listen(path, "win32")
    assert made == [(channel.pipe_name(path), "AF_PIPE")]


def _stops_windows(node: ast.AST, module: Path) -> str | None:
    """Why `node`, in `module`, is a call that works on macOS and Linux but stops Apply on Windows
    (docs/windows_desktop.md), or None."""
    if isinstance(node, ast.Import) and any(alias.name.split(".")[0] == "fcntl" for alias in node.names):
        return "imports fcntl (P1: lock through apply.locks)"
    if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "fcntl":
        return "imports fcntl (P1: lock through apply.locks)"
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "kill"
            and isinstance(node.func.value, ast.Name) and node.func.value.id == "os" and len(node.args) == 2
            and isinstance(node.args[1], ast.Constant) and node.args[1].value == 0):
        return "checks a process with os.kill(pid, 0) (P2: psutil.pid_exists)"
    if isinstance(node, ast.Attribute) and node.attr == "AF_UNIX" and module.name != "channel.py":
        return "makes a Unix socket of its own (P4: open the channel through apply.plain.channel)"
    return None


def test_no_module_of_apply_makes_a_call_that_stops_windows():
    """Faults: a module imports `fcntl` again (P1: on Windows no command, window or seed setup then starts),
    checks a process with `os.kill(pid, 0)` (P2: on Windows signal 0 is CTRL_C_EVENT, and any other number ends the
    process), or makes a Unix socket outside the channel (P4: Python on Windows has no AF_UNIX). It reads the
    source: on this computer each call works, and portalocker itself imports `fcntl` on macOS and Linux, so only
    Windows would show the fault."""
    source = Path(home.__file__).parent
    found = [f"{path.relative_to(source)}:{node.lineno}: {why}"
             for path in sorted(source.rglob("*.py"))
             for node in ast.walk(ast.parse(path.read_text()))
             if (why := _stops_windows(node, path))]
    assert found == []
