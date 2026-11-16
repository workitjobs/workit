"""The window's tiles for a run's Workers (KAN-858): the frame source for each worker_mode, and stopping the plain
Workers' Chromes once the run ends. A Developer checkout's commands (apply.cli) and WorkIt Auto Apply's window
(apply.app_window) both use them, so they live on the Student path."""

import sys
from collections.abc import Callable

from apply import dashboard


def worker_chrome(workers) -> Callable[[int], int | None]:
    """The PID of the Chrome that has plain Worker k's profile open: its tile films that Chrome only (KAN-717)."""
    from apply.browsers import chrome_pid

    return lambda worker: chrome_pid(workers.profile(worker))


def frames_for(site, tiles: int):
    """The window's frame source for `site`'s Workers (worker_mode): CDP Workers' screencast,
    plain Workers' port (S3), or in `protected` mode whichever Worker k runs now."""
    from apply.plain.site import PlainSite, RoutedSite
    from apply.plain.tile import EitherFrames, PortFrames

    if isinstance(site, PlainSite):
        return PortFrames(tiles, site.workers.bridge.connection, chrome=worker_chrome(site.workers))
    if isinstance(site, RoutedSite):
        return EitherFrames(dashboard.CdpFrames(tiles, site.endpoint),
                            PortFrames(tiles, site.connection, chrome=worker_chrome(site.plain_site.workers)), site.plain)
    return dashboard.CdpFrames(tiles, site.endpoint)


def close_workers(site) -> None:
    """Stop the plain Workers' Chromes the run started (by PID). A CDP Worker's closes with its page."""
    close = getattr(site, "close", None)
    if close:
        try:
            close()
        except Exception as error:
            print(f"Couldn't stop every plain Worker ({type(error).__name__}: {error}).", file=sys.stderr)
