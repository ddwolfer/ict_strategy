"""Tests for session utilities including DST transitions."""
from __future__ import annotations
import pytest
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo
from engine.core.sessions import sessions_at, trading_date, is_in_window, ET, UTC


def utc(ts_str: str) -> datetime:
    """Parse an ISO string with UTC tz."""
    return datetime.fromisoformat(ts_str)


class TestSessionsAt:
    def test_rth_open_in_rth(self):
        # 09:30 ET = 13:30 UTC (EDT, summer)
        ts = utc("2026-05-14T13:30:00+00:00")
        sessions = sessions_at(ts)
        assert "RTH" in sessions

    def test_rth_closed_before_open(self):
        # 08:00 ET = 12:00 UTC (EDT)
        ts = utc("2026-05-14T12:00:00+00:00")
        sessions = sessions_at(ts)
        assert "RTH" not in sessions

    def test_rth_closed_at_16(self):
        # 16:00 ET is NOT in RTH (end is exclusive)
        ts = utc("2026-05-14T20:00:00+00:00")  # 16:00 EDT
        sessions = sessions_at(ts)
        assert "RTH" not in sessions

    def test_ny_am_killzone(self):
        # 07:30 ET
        ts = utc("2026-05-14T11:30:00+00:00")  # 07:30 EDT
        sessions = sessions_at(ts)
        assert "NY_AM_KILLZONE" in sessions

    def test_silver_bullet_am(self):
        # 10:30 ET
        ts = utc("2026-05-14T14:30:00+00:00")  # 10:30 EDT
        sessions = sessions_at(ts)
        assert "SILVER_BULLET_AM" in sessions

    def test_overnight_before_rth(self):
        # 06:00 ET (before 09:30)
        ts = utc("2026-05-14T10:00:00+00:00")  # 06:00 EDT
        sessions = sessions_at(ts)
        assert "OVERNIGHT" in sessions
        assert "RTH" not in sessions

    def test_overnight_after_1800(self):
        # 19:00 ET
        ts = utc("2026-05-14T23:00:00+00:00")  # 19:00 EDT
        sessions = sessions_at(ts)
        assert "OVERNIGHT" in sessions

    def test_rth_open_3h(self):
        # 10:00 ET = 14:00 UTC (EDT)
        ts = utc("2026-05-14T14:00:00+00:00")
        sessions = sessions_at(ts)
        assert "RTH_OPEN_3H" in sessions

    def test_multiple_sessions_overlap(self):
        # 10:00 ET: RTH_OPEN_3H, SILVER_BULLET_AM, RTH overlap
        # NY_AM_KILLZONE ends at 10:00 (exclusive), so it's NOT present at 10:00
        ts = utc("2026-05-14T14:00:00+00:00")  # 10:00 EDT
        sessions = sessions_at(ts)
        assert "RTH" in sessions
        assert "SILVER_BULLET_AM" in sessions
        assert "RTH_OPEN_3H" in sessions
        assert "NY_AM_KILLZONE" not in sessions  # ends at 10:00 exclusive

    def test_ny_am_killzone_before_10(self):
        # 09:59 ET is still in NY_AM_KILLZONE
        ts = utc("2026-05-14T13:59:00+00:00")  # 09:59 EDT
        sessions = sessions_at(ts)
        assert "NY_AM_KILLZONE" in sessions


class TestTradingDate:
    def test_during_rth(self):
        # 2026-05-14 14:30 UTC = 10:30 EDT → trading date is 2026-05-14
        ts = utc("2026-05-14T14:30:00+00:00")
        assert trading_date(ts) == date(2026, 5, 14)

    def test_before_1800_et(self):
        # 17:59 ET → still same day
        ts = utc("2026-05-14T21:59:00+00:00")  # 17:59 EDT
        assert trading_date(ts) == date(2026, 5, 14)

    def test_at_1800_et_belongs_to_next_day(self):
        # 18:00 ET → belongs to NEXT trading day
        ts = utc("2026-05-14T22:00:00+00:00")  # 18:00 EDT
        assert trading_date(ts) == date(2026, 5, 15)

    def test_after_1800_et(self):
        # 20:00 ET → next day
        ts = utc("2026-05-15T00:00:00+00:00")  # 20:00 EDT on 5/14
        assert trading_date(ts) == date(2026, 5, 15)

    def test_early_morning_overnight(self):
        # 02:00 ET next morning still belongs to same trading day
        ts = utc("2026-05-15T06:00:00+00:00")  # 02:00 EDT on 5/15
        assert trading_date(ts) == date(2026, 5, 15)

    def test_dst_spring_forward_2026(self):
        """2026-03-08: spring forward (02:00 → 03:00). ET is UTC-5 before, UTC-4 after."""
        # 14:30 UTC on 2026-03-08 = 10:30 EDT (already switched)
        ts = utc("2026-03-08T14:30:00+00:00")
        assert trading_date(ts) == date(2026, 3, 8)

    def test_dst_fall_back_2026(self):
        """2026-11-01: fall back (02:00 → 01:00). ET is UTC-4 before, UTC-5 after."""
        # 14:30 UTC on 2026-11-01 = 09:30 EST (after fallback)
        ts = utc("2026-11-01T14:30:00+00:00")
        assert trading_date(ts) == date(2026, 11, 1)


class TestSessionsDST:
    """Verify session boundaries hold across DST transitions."""

    def test_spring_forward_rth_boundary(self):
        """On 2026-03-08, RTH opens at 09:30 EDT = 13:30 UTC."""
        ts_open = utc("2026-03-08T13:30:00+00:00")
        ts_before = utc("2026-03-08T13:29:00+00:00")
        assert "RTH" in sessions_at(ts_open)
        assert "RTH" not in sessions_at(ts_before)

    def test_fall_back_rth_boundary(self):
        """On 2026-11-01, RTH opens at 09:30 EST = 14:30 UTC."""
        ts_open = utc("2026-11-01T14:30:00+00:00")
        ts_before = utc("2026-11-01T14:29:00+00:00")
        assert "RTH" in sessions_at(ts_open)
        assert "RTH" not in sessions_at(ts_before)

    def test_spring_forward_trading_date_boundary(self):
        """18:00 ET on spring-forward day = 22:00 UTC (EDT = UTC-4)."""
        ts_boundary = utc("2026-03-08T22:00:00+00:00")  # 18:00 EDT
        ts_before = utc("2026-03-08T21:59:00+00:00")    # 17:59 EDT
        d_before = trading_date(ts_before)
        d_after = trading_date(ts_boundary)
        assert d_after == d_before + __import__("datetime").timedelta(days=1)

    def test_fall_back_trading_date_boundary(self):
        """18:00 ET on fall-back day = 23:00 UTC (EST = UTC-5)."""
        ts_boundary = utc("2026-11-01T23:00:00+00:00")  # 18:00 EST
        ts_before = utc("2026-11-01T22:59:00+00:00")    # 17:59 EST
        d_before = trading_date(ts_before)
        d_after = trading_date(ts_boundary)
        assert d_after == d_before + __import__("datetime").timedelta(days=1)


class TestIsInWindow:
    def test_in_rth(self):
        ts = utc("2026-05-14T15:00:00+00:00")  # 11:00 EDT
        assert is_in_window(ts, "RTH") is True

    def test_not_in_rth(self):
        ts = utc("2026-05-14T10:00:00+00:00")  # 06:00 EDT
        assert is_in_window(ts, "RTH") is False

    def test_overnight_true(self):
        ts = utc("2026-05-14T02:00:00+00:00")  # 22:00 EDT prev day
        assert is_in_window(ts, "OVERNIGHT") is True
