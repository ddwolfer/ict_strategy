"""Tests for MSSDetector."""
from __future__ import annotations
import pytest
from datetime import datetime, timedelta, timezone
from engine.core.types import MSS, TICK
from engine.detectors.mss import MSSDetector

UTC = timezone.utc


def make_bar(i: int, open_: float, close: float, high: float | None = None, low: float | None = None):
    from engine.core.types import Bar
    ts = datetime(2026, 5, 14, 14, 30, tzinfo=UTC) + timedelta(minutes=i)
    if high is None:
        high = max(open_, close) + TICK
    if low is None:
        low = min(open_, close) - TICK
    return Bar(ts_utc=ts, open=open_, high=high, low=low, close=close, volume=0.0)


def make_baseline_bars(n: int, body_size: float = 1.0, start_i: int = 0) -> list:
    bars = []
    for i in range(n):
        bars.append(make_bar(start_i + i, open_=100.0, close=100.0 + body_size))
    return bars


class TestMSSDetector:
    def test_bearish_mss_fires(self):
        """Bearish MSS: displacement BEAR candle whose close < most recent swing low."""
        det = MSSDetector(n=1, window=5, mult=2.0)
        # baseline bars to establish avg_body
        baselines = make_baseline_bars(5, body_size=1.0)
        # swing low at bar 5: [high, LOW, high] pattern
        b5 = make_bar(5, open_=100.5, close=100.5, high=101.0, low=100.0)
        b6 = make_bar(6, open_=99.5, close=99.5, high=100.0, low=90.0)  # swing low candidate at 90.0
        b7 = make_bar(7, open_=100.5, close=100.5, high=101.0, low=99.5)  # confirms swing low
        # Now a bearish displacement that closes below 90.0
        # avg_body from bars 2-6 (window=5) should be around 1.0 → need body >= 2.0
        b8 = make_bar(8, open_=95.0, close=87.0, high=95.5, low=86.5)  # body=8, direction=BEAR, close < 90
        all_events = []
        for bar in baselines + [b5, b6, b7, b8]:
            all_events.extend(det.on_bar(bar))
        mss_events = [e for e in all_events if isinstance(e, MSS)]
        assert len(mss_events) == 1
        assert mss_events[0].direction == "BEAR"
        assert mss_events[0].broken_swing_level == 90.0

    def test_bullish_mss_fires(self):
        """Bullish MSS: displacement BULL candle whose close > most recent swing high."""
        det = MSSDetector(n=1, window=5, mult=2.0)
        baselines = make_baseline_bars(5, body_size=1.0)
        # swing high at bar 6: [low, HIGH, low] pattern
        b5 = make_bar(5, open_=99.5, close=99.5, high=100.0, low=99.0)
        b6 = make_bar(6, open_=109.5, close=109.5, high=110.0, low=109.0)  # swing high candidate
        b7 = make_bar(7, open_=99.5, close=99.5, high=100.0, low=99.0)  # confirms swing high
        # displacement BULL candle that closes above 110.0
        b8 = make_bar(8, open_=105.0, close=113.0, high=113.5, low=104.5)  # body=8
        all_events = []
        for bar in baselines + [b5, b6, b7, b8]:
            all_events.extend(det.on_bar(bar))
        mss_events = [e for e in all_events if isinstance(e, MSS)]
        assert len(mss_events) == 1
        assert mss_events[0].direction == "BULL"
        assert mss_events[0].broken_swing_level == 110.0

    def test_no_mss_without_displacement(self):
        """A bar closing below swing low does NOT fire MSS if it's not a displacement candle.

        We ensure the window is filled with consistent body=2.0 bars so avg_body=2.0.
        A bar with body=1.0 (half of avg) that closes below the swing low should NOT trigger MSS.
        """
        det = MSSDetector(n=1, window=5, mult=2.0)
        # Baseline bars with body=2.0 → avg_body = 2.0; need body >= 4.0 for displacement
        baselines = make_baseline_bars(5, body_size=2.0)
        b5 = make_bar(5, open_=101.0, close=103.0, high=103.5, low=100.5)  # body=2
        b6 = make_bar(6, open_=99.5, close=99.5, high=100.0, low=90.0)    # swing low candidate
        b7 = make_bar(7, open_=101.0, close=103.0, high=103.5, low=100.5)  # confirms swing low
        # Non-displacement bar: body=1.0 (well below 4.0 threshold), close < 90.0
        b8 = make_bar(8, open_=91.0, close=90.0)  # body=1.0, close=90.0 NOT below 90.0 exactly
        # Make close clearly below 90 but body still small
        b8 = make_bar(8, open_=91.0, close=89.5, high=91.5, low=89.0)  # body=1.5 < 4.0
        all_events = []
        for bar in baselines + [b5, b6, b7, b8]:
            all_events.extend(det.on_bar(bar))
        mss_events = [e for e in all_events if isinstance(e, MSS)]
        assert len(mss_events) == 0

    def test_mss_swing_removed_after_fire(self):
        """After a bearish MSS fires on the most recent swing low, it is removed (won't fire again)."""
        det = MSSDetector(n=1, window=5, mult=2.0)
        baselines = make_baseline_bars(5, body_size=1.0)
        b5 = make_bar(5, open_=100.5, close=100.5, high=101.0, low=100.0)
        b6 = make_bar(6, open_=99.5, close=99.5, high=100.0, low=90.0)
        b7 = make_bar(7, open_=100.5, close=100.5, high=101.0, low=99.5)
        b8 = make_bar(8, open_=95.0, close=87.0, high=95.5, low=86.5)  # MSS fires
        b9 = make_bar(9, open_=90.0, close=85.0, high=90.5, low=84.5)  # another displacement — no swing to break
        all_events = []
        for bar in baselines + [b5, b6, b7, b8, b9]:
            all_events.extend(det.on_bar(bar))
        mss_events = [e for e in all_events if isinstance(e, MSS)]
        # Only one MSS should fire (the first)
        bear_mss = [e for e in mss_events if e.direction == "BEAR"]
        # After the first, the swing is consumed; second bar has no swing low to break
        assert len(bear_mss) == 1


class TestStaleSwingPruning:
    """Regression: swings broken slowly (no displacement) must not anchor later MSS."""

    def _mk(self, i, o, h, l, c):
        from datetime import datetime, timedelta, timezone
        from engine.core.types import Bar
        return Bar(
            ts_utc=datetime(2026, 5, 14, 14, 30, tzinfo=timezone.utc) + timedelta(minutes=i),
            open=o, high=h, low=l, close=c, volume=0,
        )

    def test_slow_break_then_displacement_no_mss(self):
        from engine.detectors.mss import MSSDetector
        det = MSSDetector(n=1, window=5)
        bars = [
            self._mk(0, 102, 102.5, 101.8, 102.2),
            self._mk(1, 102.2, 102.6, 100.0, 102.0),  # swing low @100
            self._mk(2, 102.0, 102.4, 101.5, 101.8),  # confirms swing
            self._mk(3, 101.8, 102.0, 101.2, 101.5),
            self._mk(4, 101.5, 101.7, 100.8, 101.0),
            self._mk(5, 101.0, 101.2, 100.2, 100.4),
            self._mk(6, 100.4, 100.6, 99.6, 99.8),    # slow close below 100 (no displacement)
            self._mk(7, 99.8, 100.0, 99.2, 99.4),
            self._mk(8, 99.4, 99.6, 94.0, 94.2),      # displacement far below stale level
        ]
        events = [e for b in bars for e in det.on_bar(b)]
        assert events == [], f"stale swing must not fire MSS, got {events}"

    def test_displacement_through_intact_swing_fires(self):
        from engine.detectors.mss import MSSDetector
        det = MSSDetector(n=1, window=5)
        bars = [
            self._mk(0, 102, 102.5, 101.8, 102.2),
            self._mk(1, 102.2, 102.6, 100.0, 102.0),  # swing low @100
            self._mk(2, 102.0, 102.4, 101.5, 101.8),
            self._mk(3, 101.8, 102.0, 101.2, 101.5),
            self._mk(4, 101.5, 101.7, 100.8, 101.0),
            self._mk(5, 101.0, 101.2, 100.5, 100.7),
            self._mk(6, 100.7, 100.9, 95.0, 95.2),    # displacement through intact 100
        ]
        events = [e for b in bars for e in det.on_bar(b)]
        assert len(events) == 1
        assert events[0].direction == "BEAR"
        assert events[0].broken_swing_level == 100.0
