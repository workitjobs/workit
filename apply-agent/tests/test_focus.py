"""Apply's Chromes never keep the focus they take on their own: a run starts
while Lisul works in another app, and stays out of his way. The Mac here is
a fake: the front app, his last click, whose window is under the pointer,
his keys and the clock are set by hand."""

from apply.focus import CLICKED, DOCK, FocusKeeper

MAIL, NOTES, WORKER, WINDOW = 100, 101, 200, 300


class FakeMac:
    def __init__(self, front: int):
        self.front, self.clicked, self.now = front, 60.0, 0.0
        self.under: int | None = None  # whose window is under the pointer
        self.key, self.modifier, self.command = 60.0, 60.0, False  # since a key, a modifier; Cmd held
        self.running = {MAIL, NOTES, WORKER, WINDOW}

    def give(self, pid: int) -> bool:
        if pid not in self.running:
            return False
        self.front = pid
        return True

    def keeper(self) -> FocusKeeper:
        return FocusKeeper(front=lambda: self.front, clicked=lambda: self.clicked, give=self.give,
                           now=lambda: self.now, every=None, pointed=lambda: self.under,
                           keys=lambda: (self.key, self.modifier, self.command))


def test_a_workers_chrome_that_comes_forward_on_its_own_goes_back_behind_lisuls_app():
    mac = FakeMac(front=MAIL)
    keeper = mac.keeper()
    keeper.watch(WORKER)

    mac.front = WORKER  # a pop-up, or a new tab, opened with no click of his
    keeper.turn()

    assert mac.front == MAIL


def test_a_chrome_he_clicks_stays_in_front_and_counts_as_his_app():
    mac = FakeMac(front=MAIL)
    keeper = mac.keeper()
    keeper.watch(WORKER)

    mac.now, mac.front, mac.clicked = 5.0, WORKER, CLICKED / 2
    keeper.turn()
    assert mac.front == WORKER

    mac.clicked = 60.0  # moments later the Worker's page opens a pop-up: he is still on it
    keeper.turn()
    assert mac.front == WORKER


def test_the_focus_goes_back_to_the_app_he_switched_to_last():
    mac = FakeMac(front=MAIL)
    keeper = mac.keeper()
    keeper.watch(WORKER)

    mac.front = NOTES  # his own switch, not Apply's
    keeper.turn()
    mac.front = WORKER
    keeper.turn()

    assert mac.front == NOTES


def test_a_chrome_starting_is_sent_back_before_its_pid_is_known():
    mac = FakeMac(front=MAIL)
    keeper = mac.keeper()

    with keeper.launching():
        mac.front = WORKER
        keeper.turn()

    assert mac.front == MAIL


def test_an_app_that_is_not_apply_keeps_the_focus_it_takes():
    mac = FakeMac(front=MAIL)
    keeper = mac.keeper()
    keeper.watch(WORKER)

    mac.front = NOTES  # opened by something else, while no Chrome of Apply's is starting
    keeper.turn()

    assert mac.front == NOTES


def test_a_window_watched_for_a_while_is_left_alone_after():
    mac = FakeMac(front=MAIL)
    keeper = mac.keeper()
    keeper.watch(WINDOW, seconds=10)

    mac.now = 11.0
    mac.front = WINDOW
    keeper.turn()

    assert mac.front == WINDOW


def test_a_forgotten_workers_chrome_is_left_alone():
    mac = FakeMac(front=MAIL)
    keeper = mac.keeper()
    keeper.watch(WORKER)
    keeper.forget(WORKER)

    mac.front = WORKER
    keeper.turn()

    assert mac.front == WORKER


def test_with_his_app_gone_the_chrome_stays_in_front():
    mac = FakeMac(front=MAIL)
    keeper = mac.keeper()
    keeper.watch(WORKER)

    mac.running.discard(MAIL)
    mac.front = WORKER
    keeper.turn()
    keeper.turn()

    assert mac.front == WORKER


def test_a_workers_chrome_lisul_asks_for_comes_forward_and_stays():
    mac = FakeMac(front=WINDOW)
    keeper = mac.keeper()
    keeper.watch(WORKER)

    assert keeper.bring(WORKER)
    mac.clicked = 60.0  # long after his click on Open in Chrome
    keeper.turn()

    assert mac.front == WORKER


def test_a_click_in_the_apply_window_just_before_a_chrome_comes_forward_keeps_the_window_in_front():
    """Seen live: a click in Lisul's own app, then a Worker's Chrome coming
    forward under a second later, was taken for a click on the Chrome, which
    kept the focus; each Worker after it then handed the focus to the last."""
    mac = FakeMac(front=WINDOW)
    keeper = mac.keeper()
    keeper.watch(WORKER)

    mac.now, mac.clicked = 5.0, 0.1  # he clicks in the Apply window
    keeper.turn()  # and it is still in front

    mac.now, mac.front, mac.clicked = 5.4, WORKER, 0.5
    keeper.turn()

    assert mac.front == WINDOW


def test_a_click_on_a_workers_window_that_lands_before_the_last_look_keeps_it_in_front():
    """KAN-752, seen live: macOS makes a clicked app the front app a moment
    after the mouse-down, so a look still saw his app in front after his click
    on the Worker's window, and the Worker went straight back behind it."""
    mac = FakeMac(front=MAIL)
    keeper = mac.keeper()
    keeper.watch(WORKER)

    mac.now, mac.clicked, mac.under = 5.0, 0.05, WORKER  # he clicks the Worker's window; Mail is still in front
    keeper.turn()

    mac.now, mac.front, mac.clicked = 5.2, WORKER, 0.25  # and the Worker comes forward
    keeper.turn()
    assert mac.front == WORKER

    mac.clicked = 60.0  # it is his app now: it stays in front as he fills the form
    keeper.turn()
    assert mac.front == WORKER


def test_a_click_in_his_app_before_the_last_look_still_sends_a_chrome_back():
    mac = FakeMac(front=MAIL)
    keeper = mac.keeper()
    keeper.watch(WORKER)

    mac.now, mac.clicked, mac.under = 5.0, 0.05, MAIL  # he clicks in Mail
    keeper.turn()

    mac.now, mac.front, mac.clicked = 5.3, WORKER, 0.35  # and a Worker's new tab brings Chrome forward
    mac.under = WORKER  # its window, raised, under the pointer now
    keeper.turn()

    assert mac.front == MAIL


def test_a_worker_he_picks_in_the_dock_or_mission_control_stays_in_front():
    mac = FakeMac(front=MAIL)
    keeper = mac.keeper()
    keeper.watch(WORKER)

    mac.now, mac.clicked, mac.under = 5.0, 0.1, DOCK
    keeper.turn()
    mac.now, mac.front, mac.clicked = 5.3, WORKER, 0.4
    keeper.turn()

    assert mac.front == WORKER


def test_a_worker_he_cmd_tabs_to_stays_in_front():
    mac = FakeMac(front=MAIL)
    keeper = mac.keeper()
    keeper.watch(WORKER)

    mac.now, mac.key, mac.modifier, mac.command = 5.0, 0.1, 0.3, True  # Cmd held, Tab pressed
    keeper.turn()
    mac.now, mac.front, mac.key, mac.modifier, mac.command = 5.2, WORKER, 0.3, 0.05, False  # Cmd let go
    keeper.turn()

    assert mac.front == WORKER


def test_a_chrome_that_comes_forward_as_he_types_goes_back():
    mac = FakeMac(front=MAIL)
    keeper = mac.keeper()
    keeper.watch(WORKER)

    mac.now = 5.0
    keeper.turn()
    mac.now, mac.front, mac.key, mac.modifier = 5.2, WORKER, 0.3, 0.1  # Shift let go after a capital: no Cmd
    keeper.turn()

    assert mac.front == MAIL
