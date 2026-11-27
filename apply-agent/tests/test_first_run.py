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


def test_workers_on_chrome_for_testing_skip_the_seed_step(tmp_path, monkeypatch):
    """Fault: the seed demanded whatever the Workers' Chrome, so with plain_chrome: testing (whose Workers load the
    worker extension with --load-extension) the window stayed on Set Up the Worker Extension and no link ever ran."""
    from apply.first_run import seed_problem

    monkeypatch.setenv("APPLY_PROFILES", str(tmp_path / "profiles"))  # a fresh folder: no seed in it
    assert seed_problem(kind="chrome") is not None
    monkeypatch.setenv("APPLY_PLAIN_CHROME", "testing")
    assert seed_problem() is None
    run = FirstRun(tmp_path / "app.json", chrome=lambda: CHROME_BINARY, screen=lambda: True)
    run.accept()
    assert run.step() == READY


def test_the_worker_count_stays_within_one_to_three_and_is_kept(tmp_path, monkeypatch):
    """Fault: a count past D24's one to three reaching the run, or Settings' choice lost at the next launch."""
    from apply import first_run
    from apply.first_run import MOST_WORKERS, chosen_workers, set_workers, workers

    monkeypatch.setattr(first_run, "memory", lambda: 32 * first_run.GB)
    state = tmp_path / "app.json"
    assert chosen_workers(state) is None and workers(state) == 3  # Automatic until the student picks a count
    assert set_workers(9, state) == MOST_WORKERS and set_workers(0, state) == 1
    assert workers(state) == 1 and chosen_workers(state) == 1  # the student's choice wins over 32 GB's three
    assert set_workers(None, state) == 3 and chosen_workers(state) is None  # back to Automatic


def test_the_automatic_worker_count_follows_the_memory():
    """Fault: a Mac with little memory given more Chromes than it can hold (D24), or a boundary on the wrong side."""
    from apply.first_run import GB, WORKERS, automatic_workers

    assert [automatic_workers(size * GB) for size in (4, 7, 8, 12, 16, 17, 32)] == [1, 1, 2, 2, 2, 3, 3]
    assert automatic_workers(int(7.8 * GB)) == 2  # an 8 GB laptop that reports a little less
    assert automatic_workers(0) == WORKERS == 2  # memory reported as nothing


def test_the_automatic_worker_count_is_two_when_the_memory_cannot_be_read(monkeypatch):
    """Fault: a computer whose memory can't be read failing the run instead of taking the default."""
    from apply import first_run

    def broken():
        raise OSError("no memory figure")

    monkeypatch.setattr(first_run.psutil, "virtual_memory", broken)
    assert first_run.memory() is None and first_run.automatic_workers() == first_run.WORKERS == 2


def test_remove_all_my_data_forgets_each_job_site_password_and_names_any_it_could_not(tmp_path, monkeypatch):
    """Fault: Apply's job-site passwords left in the keychain once the list of their accounts went with the folder,
    or a password the keychain kept left unsaid."""
    from datetime import date

    from apply import build
    from apply.first_run import remove_all_data
    from apply.keychain import InMemoryKeychain
    from apply.tracker import EmployerAccount, FileTracker

    monkeypatch.setattr(build, "STUDENT", True)
    home = tmp_path / "WorkIt Auto Apply"
    sites = ["acme.wd1.myworkdayjobs.com", "beta.wd5.myworkdayjobs.com"]

    def made_accounts():
        tracker = FileTracker(home / "tracker.json")
        for site in sites:
            tracker.add_employer_account(EmployerAccount("Acme", site, "test.person@example.com", date(2026, 11, 15)))

    made_accounts()
    keychain = InMemoryKeychain({sites[0]: "one", sites[1]: "two", "made-by-hand.example.com": "kept"})
    said = remove_all_data(lambda: None, home, keychain)
    assert said.startswith("Removed.") and "Keychain" not in said and not home.exists()
    assert [keychain.password(site) for site in sites] == [None, None]
    assert keychain.password("made-by-hand.example.com") == "kept"

    class Locked(InMemoryKeychain):
        def forget(self, site):
            raise RuntimeError("the keychain is locked")

    made_accounts()
    said = remove_all_data(lambda: None, home, Locked())
    assert said.startswith("Removed.") and all(site in said for site in sites) and not home.exists()
