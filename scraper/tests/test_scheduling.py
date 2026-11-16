"""Tests for the shared scheduling pure functions."""

from datetime import timedelta

from workit_scraper.scheduling import (
    FINGERPRINT_FIRST,
    FINGERPRINT_LONGEST,
    QUIET_EVERY,
    REST_AFTER,
    REST_FIRST,
    REST_LONGEST,
    RUN_EVERY,
    fingerprint,
    fingerprint_rest,
    is_quiet_board_due,
    quiet_slot,
    rest_for,
)


class TestFingerprint:
    def test_deterministic(self):
        assert fingerprint(["a", "b"]) == fingerprint(["b", "a"])

    def test_different_sets_differ(self):
        assert fingerprint(["a"]) != fingerprint(["b"])

    def test_eight_hex_chars(self):
        fp = fingerprint(["x", "y", "z"])
        assert len(fp) == 8
        int(fp, 16)  # valid hex


class TestRestFor:
    def test_below_threshold(self):
        for i in range(REST_AFTER):
            assert rest_for(i) is None

    def test_at_threshold(self):
        assert rest_for(REST_AFTER) == REST_FIRST

    def test_doubles(self):
        assert rest_for(REST_AFTER + 1) == REST_FIRST * 2

    def test_capped(self):
        assert rest_for(REST_AFTER + 10) == REST_LONGEST


class TestFingerprintRest:
    def test_zero_unchanged(self):
        assert fingerprint_rest(0) is None

    def test_first_unchanged(self):
        assert fingerprint_rest(1) == FINGERPRINT_FIRST

    def test_doubles(self):
        assert fingerprint_rest(2) == FINGERPRINT_FIRST * 2

    def test_capped(self):
        assert fingerprint_rest(10) == FINGERPRINT_LONGEST


class TestQuietSlot:
    def test_same_period_same_slot(self):
        base = 1_000_000.0
        assert quiet_slot(base) == quiet_slot(base + 1.0)

    def test_different_period_different_slot(self):
        base = 1_000_000.0
        assert quiet_slot(base) != quiet_slot(base + RUN_EVERY.total_seconds())


class TestIsQuietBoardDue:
    def test_never_read(self):
        assert is_quiet_board_due("ats/token", 0, None, 0.0, has_kept=False)

    def test_has_kept(self):
        assert is_quiet_board_due("ats/token", 0, 1.0, 2.0, has_kept=True)

    def test_stale_read(self):
        now = 200_000.0
        old = now - timedelta(days=2).total_seconds()
        assert is_quiet_board_due("ats/token", 0, old, now, has_kept=False)

    def test_slot_mismatch_skipped(self):
        """A quiet board whose CRC32 slot doesn't match is not due."""
        now = 100_000.0
        recent = now - 60.0  # well within QUIET_LONGEST
        slot = quiet_slot(now)
        # Find a key that does NOT match this slot.
        for i in range(100):
            key = f"ats/token-{i}"
            import zlib

            if zlib.crc32(key.encode()) % QUIET_EVERY != slot % QUIET_EVERY:
                assert not is_quiet_board_due(key, slot, recent, now, has_kept=False)
                return
        raise AssertionError("could not find a mismatched key")

    def test_slot_match_due(self):
        """A quiet board whose CRC32 slot matches is due."""
        now = 100_000.0
        recent = now - 60.0
        slot = quiet_slot(now)
        import zlib

        for i in range(100):
            key = f"ats/token-{i}"
            if zlib.crc32(key.encode()) % QUIET_EVERY == slot % QUIET_EVERY:
                assert is_quiet_board_due(key, slot, recent, now, has_kept=False)
                return
        raise AssertionError("could not find a matching key")
