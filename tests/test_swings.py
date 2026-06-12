"""Tests for SwingDetector."""
from __future__ import annotations
import pytest
from datetime import datetime, timedelta, timezone
from engine.core.types import SwingConfirmed, TICK
from engine.detectors.swings import SwingDetector

UTC = timezone.utc


def make_bar(i: int, open_=100.0, high=100.0, low=100.0, close=100.0, volume=0.0):
    from engine.core.types import Bar
    ts = datetime(2026, 5, 14, 14, 30, tzinfo=UTC) + timedelta(minutes=i)
    return Bar(ts_utc=ts, open=open_, high=high, low=low, close=close, volume=volume)


def make_bars_with_high(highs: list[float]) -> list:
    """Make bars with the given high values (and matching lows one tick below)."""
    return [make_bar(i, high=h, low=h - TICK, open_=h - TICK / 2, close=h - TICK / 2)
            for i, h in enumerate(highs)]


def make_bars_with_low(lows: list[float]) -> list:
    """Make bars with the given low values (and matching highs one tick above)."""
    return [make_bar(i, low=l, high=l + TICK, open_=l + TICK / 2, close=l + TICK / 2)
            for i, l in enumerate(lows)]


class TestSwingDetector:
    def test_no_events_before_enough_bars(self):
        det = SwingDetector(n=1)
        bar = make_bar(0, high=100.0, low=99.75)
        assert det.on_bar(bar) == []
        bar2 = make_bar(1, high=101.0, low=100.75)
        assert det.on_bar(bar2) == []

    def test_swing_high_detected_n1(self):
        """3-bar fractal: [low, high, low] → swing high at bar 1."""
        det = SwingDetector(n=1)
        bars = make_bars_with_high([100.0, 105.0, 102.0])
        all_events = []
        for bar in bars:
            all_events.extend(det.on_bar(bar))
        highs = [e for e in all_events if isinstance(e, SwingConfirmed) and e.side == "HIGH"]
        assert len(highs) == 1
        assert highs[0].level == 105.0
        assert highs[0].anchor == bars[1].ts_utc
        assert highs[0].confirmed_at == bars[2].ts_utc

    def test_swing_low_detected_n1(self):
        """3-bar fractal: [high, low, high] → swing low at bar 1."""
        det = SwingDetector(n=1)
        bars = make_bars_with_low([100.0, 95.0, 98.0])
        all_events = []
        for bar in bars:
            all_events.extend(det.on_bar(bar))
        lows = [e for e in all_events if isinstance(e, SwingConfirmed) and e.side == "LOW"]
        assert len(lows) == 1
        assert lows[0].level == 95.0
        assert lows[0].anchor == bars[1].ts_utc

    def test_no_swing_if_equal_high(self):
        """Strict greater-than: equal high should NOT qualify."""
        det = SwingDetector(n=1)
        bars = make_bars_with_high([100.0, 100.0, 100.0])
        all_events = []
        for bar in bars:
            all_events.extend(det.on_bar(bar))
        highs = [e for e in all_events if isinstance(e, SwingConfirmed) and e.side == "HIGH"]
        assert len(highs) == 0

    def test_no_swing_if_equal_low(self):
        det = SwingDetector(n=1)
        bars = make_bars_with_low([95.0, 95.0, 95.0])
        all_events = []
        for bar in bars:
            all_events.extend(det.on_bar(bar))
        lows = [e for e in all_events if isinstance(e, SwingConfirmed) and e.side == "LOW"]
        assert len(lows) == 0

    def test_swing_high_n2(self):
        """n=2: 5-bar fractal, confirmed at bar i+2."""
        det = SwingDetector(n=2)
        highs_values = [100.0, 102.0, 108.0, 104.0, 101.0]
        bars = make_bars_with_high(highs_values)
        all_events = []
        for bar in bars:
            all_events.extend(det.on_bar(bar))
        highs = [e for e in all_events if isinstance(e, SwingConfirmed) and e.side == "HIGH"]
        assert len(highs) == 1
        assert highs[0].level == 108.0
        assert highs[0].anchor == bars[2].ts_utc
        assert highs[0].confirmed_at == bars[4].ts_utc

    def test_multiple_swings(self):
        """Multiple swings in a longer sequence."""
        det = SwingDetector(n=1)
        # high, low, high, low pattern
        highs_values = [100, 105, 102, 108, 104]
        bars = make_bars_with_high(highs_values)
        all_events = []
        for bar in bars:
            all_events.extend(det.on_bar(bar))
        highs = [e for e in all_events if isinstance(e, SwingConfirmed) and e.side == "HIGH"]
        # bar 1 (105) and bar 3 (108) should both be swing highs
        assert len(highs) == 2
        levels = {e.level for e in highs}
        assert 105.0 in levels
        assert 108.0 in levels

    def test_confirmed_at_is_bar_i_plus_n(self):
        """confirmed_at must be bar i+n's ts_utc."""
        det = SwingDetector(n=1)
        bars = make_bars_with_high([100.0, 110.0, 105.0])
        all_events = []
        for bar in bars:
            all_events.extend(det.on_bar(bar))
        highs = [e for e in all_events if isinstance(e, SwingConfirmed) and e.side == "HIGH"]
        assert highs[0].confirmed_at == bars[2].ts_utc
        assert highs[0].anchor == bars[1].ts_utc
