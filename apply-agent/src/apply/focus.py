"""Keeps Apply's own Chromes from taking Lisul's focus.

On macOS a Chrome makes itself the front app as it starts and whenever it
opens a tab or pop-up (seen live: Playwright's new page, window.open, a link
with target=_blank). A run starts a Chrome per Worker, and the Apply window,
while Lisul works in another app, so each one pulled him away from it.

The FocusKeeper hands the focus back to the app he was in whenever one of
Apply's Chromes comes to the front with no switch of his just before it. A
Chrome he switched to is his, and it stays in front. A switch of his is one of:

- a click since his app was last seen in front;
- a click before that, which landed on that Chrome's own window or on the
  Dock (which also draws Mission Control and the Cmd-Tab switcher). macOS
  makes a clicked app the front app a moment after the mouse-down, so a look
  often still sees his app in front after the click (KAN-752: a Worker he
  clicked went straight back behind it). Each such look notes whose window
  is under the pointer, the window the click landed on;
- Cmd-Tab: a key press, then a modifier key let go as the last key event,
  with Cmd seen held at a look just before. A Cmd-Tab too quick for any look
  to see Cmd held is handed back: hold Cmd a moment longer, or click.

A click in his app itself (the Apply window's tiles, say) is no switch to the
Chrome that comes forward a moment after: that Chrome goes back behind.
"""

import ctypes
import subprocess
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager

CLICKED = 1.0  # s: an app that came forward this soon after a click or Cmd-Tab came forward by it
HELD = 3.0  # s: the longest Cmd is held down for one Cmd-Tab
EVERY = 0.2  # s between looks at the front app
# CoreGraphics' event source state of the hardware, and its event types.
HID_STATE = 1
MOUSE_DOWNS = (1, 3, 25)  # left, right, other
KEY_DOWN, FLAGS_CHANGED = 10, 12  # a key pressed; a modifier key pressed or let go
COMMAND = 1 << 20  # kCGEventFlagMaskCommand
DOCK = -1  # stands for a window of the Dock's: the Dock, Mission Control and the Cmd-Tab switcher
ON_SCREEN = 1 | 16  # kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements
CF_INT, CF_DOUBLE, UTF8 = 9, 6, 0x08000100


def front_pid() -> int | None:
    """The pid of the front app."""
    asn = subprocess.run(["lsappinfo", "front"], capture_output=True, text=True, check=False).stdout.strip()
    found = subprocess.run(["lsappinfo", "info", "-only", "pid", asn], capture_output=True, text=True,
                           check=False).stdout.strip()
    try:
        return int(found.rsplit("=", 1)[1])
    except (IndexError, ValueError):
        return None


def since_click() -> float:
    """Seconds since Lisul last pressed a mouse button, anywhere."""
    try:
        graphics = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
    except OSError:
        return float("inf")
    since = graphics.CGEventSourceSecondsSinceLastEventType
    since.restype, since.argtypes = ctypes.c_double, [ctypes.c_int, ctypes.c_uint32]
    return min(since(HID_STATE, kind) for kind in MOUSE_DOWNS)


def since_keys() -> tuple[float, float, bool]:
    """Seconds since Lisul last pressed a key, and since he last pressed or let go
    of a modifier key; and whether he holds Cmd down now."""
    try:
        graphics = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
    except OSError:
        return float("inf"), float("inf"), False
    since = graphics.CGEventSourceSecondsSinceLastEventType
    since.restype, since.argtypes = ctypes.c_double, [ctypes.c_int, ctypes.c_uint32]
    flags = graphics.CGEventSourceFlagsState
    flags.restype, flags.argtypes = ctypes.c_uint64, [ctypes.c_int]
    return since(HID_STATE, KEY_DOWN), since(HID_STATE, FLAGS_CHANGED), bool(flags(HID_STATE) & COMMAND)


class _Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


class _Rect(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double), ("width", ctypes.c_double),
                ("height", ctypes.c_double)]


def pointed() -> int | None:
    """The pid of the app whose window is under the pointer, the topmost one that
    is not see-through (DOCK for the Dock's), or None. It needs no permission:
    a window's owner, bounds and alpha are readable by any app."""
    try:
        graphics = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        core = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    except OSError:
        return None
    ref = ctypes.c_void_p
    graphics.CGEventCreate.restype, graphics.CGEventCreate.argtypes = ref, [ref]
    graphics.CGEventGetLocation.restype, graphics.CGEventGetLocation.argtypes = _Point, [ref]
    graphics.CGWindowListCopyWindowInfo.restype = ref
    graphics.CGWindowListCopyWindowInfo.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
    graphics.CGRectMakeWithDictionaryRepresentation.restype = ctypes.c_bool
    graphics.CGRectMakeWithDictionaryRepresentation.argtypes = [ref, ctypes.POINTER(_Rect)]
    core.CFArrayGetCount.restype, core.CFArrayGetCount.argtypes = ctypes.c_long, [ref]
    core.CFArrayGetValueAtIndex.restype, core.CFArrayGetValueAtIndex.argtypes = ref, [ref, ctypes.c_long]
    core.CFDictionaryGetValue.restype, core.CFDictionaryGetValue.argtypes = ref, [ref, ref]
    core.CFNumberGetValue.restype, core.CFNumberGetValue.argtypes = ctypes.c_bool, [ref, ctypes.c_int, ref]
    core.CFStringGetCString.restype = ctypes.c_bool
    core.CFStringGetCString.argtypes = [ref, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
    core.CFRelease.restype, core.CFRelease.argtypes = None, [ref]

    def key(name: str):
        return ref.in_dll(graphics, name).value

    def number(window, name: str, kind: int, out):
        found = core.CFDictionaryGetValue(window, key(name))
        return bool(found) and core.CFNumberGetValue(found, kind, ctypes.byref(out))

    event = graphics.CGEventCreate(None)
    if not event:
        return None
    at = graphics.CGEventGetLocation(event)
    core.CFRelease(event)
    windows = graphics.CGWindowListCopyWindowInfo(ON_SCREEN, 0)
    if not windows:
        return None
    try:
        for index in range(core.CFArrayGetCount(windows)):  # front to back
            window, box, alpha, pid = core.CFArrayGetValueAtIndex(windows, index), _Rect(), ctypes.c_double(1), \
                ctypes.c_int()
            bounds = core.CFDictionaryGetValue(window, key("kCGWindowBounds"))
            if not bounds or not graphics.CGRectMakeWithDictionaryRepresentation(bounds, ctypes.byref(box)):
                continue
            if not (box.x <= at.x < box.x + box.width and box.y <= at.y < box.y + box.height):
                continue
            number(window, "kCGWindowAlpha", CF_DOUBLE, alpha)
            if alpha.value <= 0 or not number(window, "kCGWindowOwnerPID", CF_INT, pid):
                continue  # an overlay that shows nothing, and takes no click
            name, owner = ctypes.create_string_buffer(256), core.CFDictionaryGetValue(window, key("kCGWindowOwnerName"))
            if owner and core.CFStringGetCString(owner, name, len(name), UTF8) and name.value == b"Dock":
                return DOCK
            return pid.value
        return None
    finally:
        core.CFRelease(windows)


def bring_forward(pid: int) -> bool:
    """Make the app with `pid` the front app again."""
    script = f'tell application "System Events" to set frontmost of (first process whose unix id is {pid}) to true'
    return subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False).returncode == 0


class FocusKeeper:
    def __init__(self, front: Callable[[], int | None] = front_pid, clicked: Callable[[], float] = since_click,
                 give: Callable[[int], bool] = bring_forward, now: Callable[[], float] = time.monotonic,
                 every: float | None = EVERY, pointed: Callable[[], int | None] = pointed,
                 keys: Callable[[], tuple[float, float, bool]] = since_keys):
        """Looks at the front app every `every` seconds once it has something
        to watch; with None, only when `turn` is called."""
        self._front, self._clicked, self._give, self._now, self._every = front, clicked, give, now, every
        self._pointed, self._keys = pointed, keys
        self._lock = threading.Lock()
        self._watched: dict[int, float] = {}  # pid -> when to stop watching it (inf: till forgotten)
        self._launching = 0
        self._yours: int | None = None
        self._seen = float("-inf")  # when his app was last seen in front
        self._under: int | None = None  # whose window was under the pointer then, after a click
        self._command = float("-inf")  # when a look last saw Cmd held down
        self._thread: threading.Thread | None = None

    @contextmanager
    def launching(self):
        """While one of Apply's Chromes starts and its pid is not yet known, any
        app that comes forward with no click is taken to be it."""
        self._start()
        with self._lock:
            self._launching += 1
        try:
            yield
        finally:
            with self._lock:
                self._launching -= 1

    def watch(self, pid: int, seconds: float | None = None) -> None:
        """Hand the focus back whenever `pid` takes it unclicked: till `forget`,
        or for `seconds` only."""
        self._start()
        with self._lock:
            self._watched[pid] = float("inf") if seconds is None else self._now() + seconds

    def forget(self, pid: int) -> None:
        with self._lock:
            self._watched.pop(pid, None)

    def bring(self, pid: int) -> bool:
        """Bring `pid` to the front for Lisul, who asked for it (Open in Chrome
        in the Apply window): it is his app now, however long it takes to come."""
        with self._lock:
            self._yours = pid
        return self._give(pid)

    def turn(self) -> None:
        """One look at the front app."""
        front, now = self._front(), self._now()
        key, modifier, command = self._keys()
        if command:
            self._command = now
        if front is not None and front == self._yours:
            self._seen = now
            self._under = self._pointed() if self._clicked() < CLICKED else None  # where a click landed
        if front is None or front == self._yours:
            return
        with self._lock:
            self._watched = {pid: until for pid, until in self._watched.items() if until > now}
            ours = front in self._watched or self._launching > 0
        if ours and self._yours is not None and not self._switched(front, now, key, modifier) \
                and self._give(self._yours):
            return
        self._yours, self._seen, self._under = front, now, None  # Lisul's own choice, or an app gone: his

    def _switched(self, front: int, now: float, key: float, modifier: float) -> bool:
        """Whether Lisul brought `front` forward himself, just now."""
        clicked = self._clicked()
        if clicked < min(CLICKED, now - self._seen):  # since his app was last seen in front
            return True
        if clicked < CLICKED and self._under in (front, DOCK):  # before, on this app's window or the Dock
            return True
        # Cmd-Tab: Cmd, held a moment ago, let go after Tab, with no key since.
        return modifier < CLICKED and modifier <= key < HELD and now - self._command < HELD

    def _start(self) -> None:
        with self._lock:
            if self._thread is not None:
                return
            self._yours, self._seen = self._front(), self._now()
            self._thread = threading.Thread(target=self._run, daemon=True, name="focus-keeper")
            if self._every is not None:
                self._thread.start()

    def _run(self) -> None:
        while True:
            try:
                self.turn()
            except Exception:
                pass  # a look that failed: the next one tries again
            time.sleep(self._every)


KEEPER = FocusKeeper()
