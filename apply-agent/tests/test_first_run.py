"""WorkIt Auto Apply's first run (KAN-858, W5 step 3): Chrome, the disclosure and license, Screen Recording, then
the seed, one step at a time, with fakes for each check. No window and no browser: in CI."""

import threading
from pathlib import Path

from apply.first_run import CHROME, READY, SCREEN, SEED, SHOWN, FirstRun

CHROME_BINARY = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


class Mac:
    """What first run looks at: Chrome, Screen Recording, the seed. Each can be changed as the student acts."""

    def __init__(self):
        self.chrome, self.screen, self.asked, self.problem = None, False, 0, "Developer mode"

    def first_run(self, state: Path, seeding=None) -> FirstRun:
        return FirstRun(state, chrome=lambda: self.chrome, screen=lambda: self.screen, ask=self._ask,
                        problem=lambda: self.problem, seeding=seeding or (lambda out, again: True))

    def _ask(self):
        self.asked += 1


def test_each_step_comes_in_order_and_what_is_done_stays_done(tmp_path):
    """Fault: a step skipped, or the disclosure or the Screen Recording ask shown again at every launch."""
    mac, state = Mac(), tmp_path / "app.json"
    run = mac.first_run(state)
    assert run.step() == CHROME
    mac.chrome = CHROME_BINARY
    assert run.step() == SHOWN
    run.accept()
    assert run.step() == SCREEN
    run.skip_screen()
    assert run.step() == SEED and mac.asked == 0
    mac.problem = None
    assert run.step() == READY
    # The next launch: Chrome and the seed are looked at again; the disclosure and the ask are kept.
    assert mac.first_run(state).step() == READY
    mac.chrome = None
    assert mac.first_run(state).step() == CHROME


def test_allow_asks_macos_once_and_a_granted_or_other_os_skips_the_step(tmp_path):
    """Fault: macOS asked again and again, or a student who already granted it (or isn't on a Mac) asked."""
    mac = Mac()
    run = mac.first_run(tmp_path / "app.json")
    mac.chrome = CHROME_BINARY
    run.accept()
    run.allow_screen()
    assert mac.asked == 1 and run.step() == SEED
    for screen in (True, None):  # granted already, or not a Mac: nothing to ask
        mac.screen = screen
        other = mac.first_run(tmp_path / f"{screen}.json")
        other.accept()
        assert other.step() == SEED


def test_the_seed_runs_in_its_own_thread_and_try_again_answers_it(tmp_path):
    """Fault: the wizard's lines lost, its ask_again never answered (the setup hangs), or a stop said nothing."""
    mac, asked, answered = Mac(), threading.Event(), threading.Event()
    mac.chrome, mac.screen = CHROME_BINARY, True

    def seeding(out, again):
        out("Now: Turn on Developer mode.")
        asked.set()
        assert again() is True
        answered.set()
        return False  # stopped before a Worker said hello

    run = mac.first_run(tmp_path / "app.json", seeding)
    run.accept()
    run.start_seed()
    assert asked.wait(5)
    for _ in range(50):
        if run.state()["waiting"]:
            break
        threading.Event().wait(0.02)
    state = run.state()
    assert state["step"] == SEED and state["running"] and state["waiting"]
    assert state["lines"] == ["Now: Turn on Developer mode."]
    run.seed_again()
    assert answered.wait(5)
    run._thread.join(5)
    assert not run.seeding() and "stopped" in run.state()["failed"]
