"""Tests for LiquidityPoolTracker."""
from __future__ import annotations
import pytest
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
from engine.core.types import PoolCreated, PoolSwept, Raid, TICK
from engine.detectors.pools import LiquidityPoolTracker

UTC = timezone.utc
ET = ZoneInfo("America/New_York")


def make_bar_utc(ts_utc: datetime, open_=100.0, high=100.0, low=100.0, close=100.0):
    from engine.core.types import Bar
    return Bar(ts_utc=ts_utc, open=open_, high=high, low=low, close=close, volume=0.0)


def rth_bar(dt_et: datetime, **kwargs):
    """Make a bar during RTH hours (09:30–16:00 ET). Pass ET datetime."""
    if dt_et.tzinfo is None:
        dt_et = dt_et.replace(tzinfo=ET)
    ts_utc = dt_et.astimezone(UTC)
    defaults = dict(open_=100.0, high=105.0, low=95.0, close=102.0)
    defaults.update(kwargs)
    return make_bar_utc(ts_utc, **defaults)


class TestSwingPools:
    def test_swing_high_creates_pool(self):
        """A confirmed swing high should create a SWING_HIGH pool."""
        det = LiquidityPoolTracker(n=1)
        # 3-bar fractal: bars with highs [100, 110, 105]
        bars = [
            make_bar_utc(datetime(2026, 5, 14, 14, 30, tzinfo=UTC), high=100.0, low=99.0),
            make_bar_utc(datetime(2026, 5, 14, 14, 31, tzinfo=UTC), high=110.0, low=109.0),
            make_bar_utc(datetime(2026, 5, 14, 14, 32, tzinfo=UTC), high=105.0, low=104.0),
        ]
        events = []
        for bar in bars:
            events.extend(det.on_bar(bar))
        created = [e for e in events if isinstance(e, PoolCreated) and e.kind == "SWING_HIGH"]
        assert len(created) == 1
        assert created[0].level == 110.0
        assert created[0].side == "BUY"

    def test_swing_low_creates_pool(self):
        det = LiquidityPoolTracker(n=1)
        bars = [
            make_bar_utc(datetime(2026, 5, 14, 14, 30, tzinfo=UTC), high=102.0, low=100.0),
            make_bar_utc(datetime(2026, 5, 14, 14, 31, tzinfo=UTC), high=100.0, low=90.0),
            make_bar_utc(datetime(2026, 5, 14, 14, 32, tzinfo=UTC), high=102.0, low=95.0),
        ]
        events = []
        for bar in bars:
            events.extend(det.on_bar(bar))
        created = [e for e in events if isinstance(e, PoolCreated) and e.kind == "SWING_LOW"]
        assert len(created) == 1
        assert created[0].level == 90.0
        assert created[0].side == "SELL"


class TestSweep:
    def test_buy_side_pool_swept_when_high_exceeds(self):
        """BUY-side pool swept when bar.high > pool.level."""
        det = LiquidityPoolTracker(n=1)
        # Create a swing high at 110 via 3 bars
        b0 = make_bar_utc(datetime(2026, 5, 14, 14, 30, tzinfo=UTC), high=100.0, low=99.0)
        b1 = make_bar_utc(datetime(2026, 5, 14, 14, 31, tzinfo=UTC), high=110.0, low=109.0)
        b2 = make_bar_utc(datetime(2026, 5, 14, 14, 32, tzinfo=UTC), high=105.0, low=104.0)
        # Now a bar that sweeps above 110
        b3 = make_bar_utc(datetime(2026, 5, 14, 14, 33, tzinfo=UTC), high=111.0, low=105.0)
        events = []
        for bar in [b0, b1, b2, b3]:
            events.extend(det.on_bar(bar))
        swept = [e for e in events if isinstance(e, PoolSwept) and e.kind == "SWING_HIGH"]
        assert len(swept) == 1
        assert swept[0].level == 110.0

    def test_sell_side_pool_swept_when_low_below(self):
        det = LiquidityPoolTracker(n=1)
        b0 = make_bar_utc(datetime(2026, 5, 14, 14, 30, tzinfo=UTC), high=102.0, low=100.0)
        b1 = make_bar_utc(datetime(2026, 5, 14, 14, 31, tzinfo=UTC), high=100.0, low=90.0)
        b2 = make_bar_utc(datetime(2026, 5, 14, 14, 32, tzinfo=UTC), high=102.0, low=95.0)
        # bar that sweeps below 90
        b3 = make_bar_utc(datetime(2026, 5, 14, 14, 33, tzinfo=UTC), high=92.0, low=88.0)
        events = []
        for bar in [b0, b1, b2, b3]:
            events.extend(det.on_bar(bar))
        swept = [e for e in events if isinstance(e, PoolSwept) and e.kind == "SWING_LOW"]
        assert len(swept) == 1
        assert swept[0].level == 90.0

    def test_pool_not_swept_twice(self):
        """Once swept, pool should not emit PoolSwept again."""
        det = LiquidityPoolTracker(n=1)
        b0 = make_bar_utc(datetime(2026, 5, 14, 14, 30, tzinfo=UTC), high=100.0, low=99.0)
        b1 = make_bar_utc(datetime(2026, 5, 14, 14, 31, tzinfo=UTC), high=110.0, low=109.0)
        b2 = make_bar_utc(datetime(2026, 5, 14, 14, 32, tzinfo=UTC), high=105.0, low=104.0)
        b3 = make_bar_utc(datetime(2026, 5, 14, 14, 33, tzinfo=UTC), high=111.0, low=108.0)
        b4 = make_bar_utc(datetime(2026, 5, 14, 14, 34, tzinfo=UTC), high=112.0, low=109.0)
        events = []
        for bar in [b0, b1, b2, b3, b4]:
            events.extend(det.on_bar(bar))
        swept = [e for e in events if isinstance(e, PoolSwept) and e.kind == "SWING_HIGH"]
        assert len(swept) == 1


class TestRaid:
    def test_raid_on_buy_side(self):
        """BUY-side raid: sweep above, then close returns below level within r bars."""
        det = LiquidityPoolTracker(n=1, r=3)
        b0 = make_bar_utc(datetime(2026, 5, 14, 14, 30, tzinfo=UTC), high=100.0, low=99.0)
        b1 = make_bar_utc(datetime(2026, 5, 14, 14, 31, tzinfo=UTC), high=110.0, low=109.0)
        b2 = make_bar_utc(datetime(2026, 5, 14, 14, 32, tzinfo=UTC), high=105.0, low=104.0)
        # sweep bar: high > 110
        b3 = make_bar_utc(datetime(2026, 5, 14, 14, 33, tzinfo=UTC), high=111.0, low=108.0, close=108.0)
        # raid bar: close < 110
        b4 = make_bar_utc(datetime(2026, 5, 14, 14, 34, tzinfo=UTC), high=110.5, low=107.0, close=108.0)
        events = []
        for bar in [b0, b1, b2, b3, b4]:
            events.extend(det.on_bar(bar))
        raids = [e for e in events if isinstance(e, Raid)]
        assert len(raids) >= 1
        assert raids[0].side == "BUY"
        assert raids[0].level == 110.0

    def test_raid_not_fired_after_r_bars(self):
        """Raid should NOT fire if close-below happens after r bars."""
        det = LiquidityPoolTracker(n=1, r=2)
        b0 = make_bar_utc(datetime(2026, 5, 14, 14, 30, tzinfo=UTC), high=100.0, low=99.0)
        b1 = make_bar_utc(datetime(2026, 5, 14, 14, 31, tzinfo=UTC), high=110.0, low=109.0)
        b2 = make_bar_utc(datetime(2026, 5, 14, 14, 32, tzinfo=UTC), high=105.0, low=104.0)
        b3 = make_bar_utc(datetime(2026, 5, 14, 14, 33, tzinfo=UTC), high=111.0, low=110.5, close=110.5)
        # bars 4, 5 pass without closing below
        b4 = make_bar_utc(datetime(2026, 5, 14, 14, 34, tzinfo=UTC), high=112.0, low=110.5, close=111.0)
        b5 = make_bar_utc(datetime(2026, 5, 14, 14, 35, tzinfo=UTC), high=111.5, low=110.5, close=111.0)
        # bar 6: close below — but r=2, so 3 bars after sweep → too late
        b6 = make_bar_utc(datetime(2026, 5, 14, 14, 36, tzinfo=UTC), high=110.5, low=107.0, close=108.0)
        events = []
        for bar in [b0, b1, b2, b3, b4, b5, b6]:
            events.extend(det.on_bar(bar))
        raids = [e for e in events if isinstance(e, Raid)]
        assert len(raids) == 0

    def test_raid_fires_only_once(self):
        """Raid should only fire once per pool-sweep (raided flag)."""
        det = LiquidityPoolTracker(n=1, r=3)
        b0 = make_bar_utc(datetime(2026, 5, 14, 14, 30, tzinfo=UTC), high=100.0, low=99.0)
        b1 = make_bar_utc(datetime(2026, 5, 14, 14, 31, tzinfo=UTC), high=110.0, low=109.0)
        b2 = make_bar_utc(datetime(2026, 5, 14, 14, 32, tzinfo=UTC), high=105.0, low=104.0)
        b3 = make_bar_utc(datetime(2026, 5, 14, 14, 33, tzinfo=UTC), high=111.0, low=108.0, close=108.0)
        # Two bars closing below 110 within r bars
        b4 = make_bar_utc(datetime(2026, 5, 14, 14, 34, tzinfo=UTC), high=110.0, low=107.0, close=108.0)
        b5 = make_bar_utc(datetime(2026, 5, 14, 14, 35, tzinfo=UTC), high=109.5, low=107.0, close=108.0)
        events = []
        for bar in [b0, b1, b2, b3, b4, b5]:
            events.extend(det.on_bar(bar))
        raids = [e for e in events if isinstance(e, Raid) and e.kind == "SWING_HIGH"]
        assert len(raids) == 1


class TestEqualHighsLows:
    def test_equal_highs_created(self):
        """Two swing highs within eq_tol should create EQUAL_HIGHS pool."""
        det = LiquidityPoolTracker(n=1, eq_tol=2)  # tol = 0.5 pts
        base = datetime(2026, 5, 14, 14, 30, tzinfo=UTC)
        # First swing high at 110.0
        bars1 = [
            make_bar_utc(base, high=100.0, low=99.0),
            make_bar_utc(base + timedelta(minutes=1), high=110.0, low=109.0),
            make_bar_utc(base + timedelta(minutes=2), high=105.0, low=104.0),
        ]
        # Second swing high at 110.25 (within 0.5 pts of 110.0)
        bars2 = [
            make_bar_utc(base + timedelta(minutes=3), high=106.0, low=105.0),
            make_bar_utc(base + timedelta(minutes=4), high=110.25, low=109.5),
            make_bar_utc(base + timedelta(minutes=5), high=107.0, low=106.0),
        ]
        events = []
        for bar in bars1 + bars2:
            events.extend(det.on_bar(bar))
        eq_highs = [e for e in events if isinstance(e, PoolCreated) and e.kind == "EQUAL_HIGHS"]
        assert len(eq_highs) >= 1
        assert eq_highs[0].level == 110.25  # max of (110.0, 110.25)

    def test_equal_highs_no_duplicate_pair(self):
        """Same pair should only produce one EQUAL_HIGHS event."""
        det = LiquidityPoolTracker(n=1, eq_tol=2)
        base = datetime(2026, 5, 14, 14, 30, tzinfo=UTC)
        # Swing high 1 at 110.0, swing high 2 at 110.25
        bars1 = [
            make_bar_utc(base, high=100.0, low=99.0),
            make_bar_utc(base + timedelta(minutes=1), high=110.0, low=109.0),
            make_bar_utc(base + timedelta(minutes=2), high=105.0, low=104.0),
        ]
        bars2 = [
            make_bar_utc(base + timedelta(minutes=3), high=106.0, low=105.0),
            make_bar_utc(base + timedelta(minutes=4), high=110.25, low=109.5),
            make_bar_utc(base + timedelta(minutes=5), high=107.0, low=106.0),
        ]
        events = []
        for bar in bars1 + bars2:
            events.extend(det.on_bar(bar))
        eq_highs = [e for e in events if isinstance(e, PoolCreated) and e.kind == "EQUAL_HIGHS"]
        # Should only be 1 even if we process more bars
        assert len(eq_highs) == 1

    def test_equal_lows_created(self):
        """Two swing lows within eq_tol → EQUAL_LOWS pool at more extreme (lower) value."""
        det = LiquidityPoolTracker(n=1, eq_tol=2)
        base = datetime(2026, 5, 14, 14, 30, tzinfo=UTC)
        bars1 = [
            make_bar_utc(base, high=102.0, low=100.0),
            make_bar_utc(base + timedelta(minutes=1), high=100.0, low=90.0),
            make_bar_utc(base + timedelta(minutes=2), high=102.0, low=95.0),
        ]
        bars2 = [
            make_bar_utc(base + timedelta(minutes=3), high=98.0, low=96.0),
            make_bar_utc(base + timedelta(minutes=4), high=96.0, low=89.75),  # within 0.5 of 90.0
            make_bar_utc(base + timedelta(minutes=5), high=98.0, low=95.0),
        ]
        events = []
        for bar in bars1 + bars2:
            events.extend(det.on_bar(bar))
        eq_lows = [e for e in events if isinstance(e, PoolCreated) and e.kind == "EQUAL_LOWS"]
        assert len(eq_lows) >= 1
        assert eq_lows[0].level == 89.75  # min of (90.0, 89.75)

    def test_no_equal_highs_if_too_far_apart(self):
        """Swing highs more than eq_tol apart should not create EQUAL_HIGHS."""
        det = LiquidityPoolTracker(n=1, eq_tol=2)  # tol = 0.5 pts
        base = datetime(2026, 5, 14, 14, 30, tzinfo=UTC)
        bars1 = [
            make_bar_utc(base, high=100.0, low=99.0),
            make_bar_utc(base + timedelta(minutes=1), high=110.0, low=109.0),
            make_bar_utc(base + timedelta(minutes=2), high=105.0, low=104.0),
        ]
        bars2 = [
            make_bar_utc(base + timedelta(minutes=3), high=106.0, low=105.0),
            make_bar_utc(base + timedelta(minutes=4), high=111.0, low=109.5),  # 1.0 pts away
            make_bar_utc(base + timedelta(minutes=5), high=107.0, low=106.0),
        ]
        events = []
        for bar in bars1 + bars2:
            events.extend(det.on_bar(bar))
        eq_highs = [e for e in events if isinstance(e, PoolCreated) and e.kind == "EQUAL_HIGHS"]
        assert len(eq_highs) == 0


class TestSessionHighLow:
    def test_session_high_emitted_at_rth_start(self):
        """SESSION_HIGH and SESSION_LOW pools emitted when RTH starts."""
        det = LiquidityPoolTracker()
        # 09:30 ET on 2026-05-14 = 13:30 UTC (EDT)
        ts = datetime(2026, 5, 14, 13, 30, tzinfo=UTC)
        bar = make_bar_utc(ts, high=105.0, low=95.0)
        events = det.on_bar(bar)
        sh = [e for e in events if isinstance(e, PoolCreated) and e.kind == "SESSION_HIGH"]
        sl = [e for e in events if isinstance(e, PoolCreated) and e.kind == "SESSION_LOW"]
        assert len(sh) == 1
        assert len(sl) == 1
        assert sh[0].level == 105.0
        assert sl[0].level == 95.0
