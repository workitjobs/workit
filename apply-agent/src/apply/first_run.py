"""WorkIt Auto Apply's first run (KAN-858, W5 step 3; section 3.1 of docs/desktop_application_auto_apply.md): what
the window checks after sign-in and before the Apply window, one step at a time, in this order.

1. Google Chrome (D21): the Chrome finder's. Missing, the window links its download and looks again.
2. The disclosure (D8, W10): what leaves the computer, and the app's license. Accepted once for each DISCLOSURE.
3. Screen Recording, on a Mac only: asked once. Without it, a form's live view in the window (Fix here) is about two
   frames a second (W2), so the student may skip it.
4. The seed: `apply plain seed`'s guided setup (apply.plain.seed_setup.Wizard), its words in the window, until a
   real Worker says hello. It stays the way in until a Chrome Web Store copy can be used (W6).

Chrome and the seed are looked at again at each launch; the disclosure and the Screen Recording ask are kept as done
in the data folder (STATE).
"""

import json
import sys
import threading
from collections.abc import Callable
from pathlib import Path

from apply import chrome_finder
from apply.home import CODE, HOME

STATE = HOME / "app.json"
# The disclosure's version: a new text is shown again to everyone who accepted an older one.
DISCLOSURE = 1
EULA = CODE / "legal" / "EULA.txt"
CHROME_DOWNLOAD = "https://www.google.com/chrome/"
CHROME, SHOWN, SCREEN, SEED, READY = "chrome", "disclosure", "screen", "seed", "ready"


def screen_allowed() -> bool | None:
    """Whether macOS lets this app record the screen, only looking; None off a Mac, where nothing asks."""
    if sys.platform != "darwin":
        return None
    import Quartz  # pyobjc, which pywebview brings on a Mac

    return bool(Quartz.CGPreflightScreenCaptureAccess())


def ask_screen() -> None:
    """macOS's own Screen Recording question, once; after that, System Settings holds the switch."""
    import Quartz

    Quartz.CGRequestScreenCaptureAccess()


def seed_problem() -> object | None:
    """The seed's first step that isn't saved yet (seed_setup.Problem), or None when it is set up."""
    from apply.plain import seed_setup
    from apply.plain.launcher import PlainWorkers

    workers = PlainWorkers(kind="chrome")
    return seed_setup.first_problem(seed_setup.read_state(workers.seed), workers.copy)


def seed(out: Callable[[str], None], ask_again: Callable[[], bool]) -> bool:
    """`apply plain seed`'s wizard, saying each line through `out`. True once a real Worker said hello."""
    from apply.plain import seed_setup
    from apply.plain.launcher import PlainWorkers

    return seed_setup.Wizard(PlainWorkers(kind="chrome"), out=out, ask_again=ask_again).run()


class FirstRun:
    """The first run's steps and what the window's buttons do to them. Each check is a callable, so tests give
    fakes: `chrome` finds Chrome, `screen` and `ask_screen` look at and ask for Screen Recording, `problem` is the
    seed's first unsaved step, and `seeding(out, ask_again)` runs the seed's wizard."""

    def __init__(self, state: Path = STATE, chrome: Callable[[], Path | None] = chrome_finder.find,
                 screen: Callable[[], bool | None] = screen_allowed, ask: Callable[[], None] = ask_screen,
                 problem: Callable[[], object | None] = seed_problem,
                 seeding: Callable[[Callable[[str], None], Callable[[], bool]], bool] = seed):
        self._state, self._chrome, self._screen, self._ask = state, chrome, screen, ask
        self._problem, self._seeding = problem, seeding
        self._said: list[str] = []  # the seed's wizard's lines, for the window
        self._thread: threading.Thread | None = None
        self._again = threading.Event()  # the window's Try Again, for the wizard's ask_again
        self._waiting = False  # the wizard waits on Try Again
        self._failed = ""  # why the last seed setup stopped

    def step(self) -> str:
        """The first step not done: CHROME, SHOWN, SCREEN, SEED, or READY."""
        if self._chrome() is None:
            return CHROME
        kept = self._kept()
        if kept.get("disclosure") != DISCLOSURE:
            return SHOWN
        if self._screen() is False and not kept.get("screen_asked"):
            return SCREEN
        if self.seeding() or self._problem() is not None:
            return SEED
        return READY

    def state(self) -> dict:
        """The step, and the seed's setup as the window shows it."""
        return {"step": self.step(), "lines": list(self._said), "running": self.seeding(),
                "waiting": self._waiting, "failed": self._failed}

    def accept(self) -> None:
        self._keep(disclosure=DISCLOSURE)

    def allow_screen(self) -> None:
        self._ask()
        self._keep(screen_asked=True)

    def skip_screen(self) -> None:
        self._keep(screen_asked=True)

    def seeding(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start_seed(self) -> None:
        """Run the seed's wizard in its own thread, once at a time."""
        if self.seeding():
            return
        self._said.clear()
        self._failed = ""
        self._thread = threading.Thread(target=self._seed, daemon=True)
        self._thread.start()

    def seed_again(self) -> None:
        """The window's Try Again, after the wizard said what to check."""
        self._again.set()

    def _seed(self) -> None:
        try:
            if not self._seeding(self._said.append, self._ask_again):
                self._failed = "The setup stopped before a Worker said hello. Press Set Up to start again."
        except Exception as error:  # a Chrome that wouldn't start, a profile in use: say it, and let the student retry
            self._failed = f"The setup stopped: {error}"

    def _ask_again(self) -> bool:
        self._waiting = True
        self._again.wait()
        self._again.clear()
        self._waiting = False
        return True

    def _kept(self) -> dict:
        try:
            kept = json.loads(self._state.read_text())
        except (OSError, ValueError):
            return {}
        return kept if isinstance(kept, dict) else {}

    def _keep(self, **values: object) -> None:
        self._state.parent.mkdir(parents=True, exist_ok=True)
        self._state.write_text(json.dumps(self._kept() | values, indent=1) + "\n")
