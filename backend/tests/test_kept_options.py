"""
The filter row's options kept per process (app/queries/jobs/kept_options.py,
KAN-916): made once, served until the job postings' version moves, read at
most once a minute, and never older than an hour.
"""

import asyncio

import pytest

from app.queries.jobs import kept_options

pytestmark = pytest.mark.anyio


@pytest.fixture
def clock(monkeypatch):
    """A clock the test moves, and versions the test sets, with no database."""
    state = {"now": 1000.0, "version": "v1", "reads": 0}

    async def version(db):
        state["reads"] += 1
        return state["version"]

    kept_options.forget()
    monkeypatch.setattr(kept_options.time, "monotonic", lambda: state["now"])
    monkeypatch.setattr(kept_options, "feed_version", version)
    yield state
    kept_options.forget()


def _maker():
    made = []

    async def make(db):
        made.append(1)
        return f"answer {len(made)}"

    return make, made


async def test_an_answer_is_made_once_while_the_postings_stay_the_same(clock):
    make, made = _maker()
    assert await kept_options.kept_options(None, "facets", make) == "answer 1"
    clock["now"] += 30
    assert await kept_options.kept_options(None, "facets", make) == "answer 1"
    clock["now"] += 300
    assert await kept_options.kept_options(None, "facets", make) == "answer 1"
    assert len(made) == 1


async def test_the_version_is_read_at_most_once_a_minute(clock):
    make, _ = _maker()
    for _ in range(5):
        await kept_options.kept_options(None, "facets", make)
        await kept_options.kept_options(None, "locations", make)
        clock["now"] += 5
    # 25 seconds, ten answers, one read of the version for both names.
    assert clock["reads"] == 1
    clock["now"] += 40
    await kept_options.kept_options(None, "facets", make)
    assert clock["reads"] == 2


async def test_an_import_makes_it_again_within_a_minute(clock):
    make, made = _maker()
    await kept_options.kept_options(None, "facets", make)
    clock["version"] = "v2"
    clock["now"] += 30
    # Not checked yet: the kept answer stands.
    assert await kept_options.kept_options(None, "facets", make) == "answer 1"
    clock["now"] += 31
    assert await kept_options.kept_options(None, "facets", make) == "answer 2"
    assert len(made) == 2


async def test_an_answer_is_never_older_than_an_hour(clock):
    make, made = _maker()
    await kept_options.kept_options(None, "facets", make)
    clock["now"] += kept_options.KEEP_SECONDS + 1
    assert await kept_options.kept_options(None, "facets", make) == "answer 2"
    assert len(made) == 2


async def test_each_name_keeps_its_own_answer(clock):
    facets, _ = _maker()

    async def places(db):
        return ["US"]

    assert await kept_options.kept_options(None, "facets", facets) == "answer 1"
    assert await kept_options.kept_options(None, "locations", places) == ["US"]
    assert await kept_options.kept_options(None, "facets", facets) == "answer 1"


async def test_requests_at_once_share_one_making(clock):
    made = []
    started = asyncio.Event()
    release = asyncio.Event()

    async def make(db):
        made.append(1)
        started.set()
        await release.wait()
        return "counted"

    first = asyncio.create_task(kept_options.kept_options(None, "facets", make))
    await started.wait()
    others = [asyncio.create_task(kept_options.kept_options(None, "facets", make)) for _ in range(3)]
    await asyncio.sleep(0)
    release.set()
    assert await asyncio.gather(first, *others) == ["counted"] * 4
    assert len(made) == 1


async def test_a_failed_making_keeps_nothing(clock):
    calls = []

    async def make(db):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("database gone")
        return "counted"

    with pytest.raises(RuntimeError):
        await kept_options.kept_options(None, "facets", make)
    assert await kept_options.kept_options(None, "facets", make) == "counted"
