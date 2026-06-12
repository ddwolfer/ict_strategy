"""Tests for DisplacementDetector."""
from __future__ import annotations
import pytest
from datetime import datetime, timedelta, timezone
from engine.core.types import Displacement, FVGCreated, TICK
from engine.detectors.displacement import DisplacementDetector

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
    """Create n bars with consistent body size for baseline average."""
    bars = []
    for i in range(n):
        bars.append(make_bar(start_i + i, open_=100.0, close=100.0 + body_size))
    return bars


class TestDisplacementDetector:
    def test_no_event_before_window_bars(self):
        """No displacement before window+1 bars have been seen."""
        det = DisplacementDetector(window=20, mult=2.0)
        bars = make_baseline_bars(20)
        all_events = []
        for bar in bars:
            all_events.extend(det.on_bar(bar))
        disps = [e for e in all_events if isinstance(e, Displacement)]
        assert len(disps) == 0

    def test_displacement_fires_when_body_large_enough(self):
        """A bar with body >= 2 * avg_body fires Displacement."""
        det = DisplacementDetector(window=20, mult=2.0)
        # 20 baseline bars with body=1.0 → avg_body = 1.0
        bars = make_baseline_bars(20)
        # displacement bar: body = 2.0 (exactly 2x)
        disp_bar = make_bar(20, open_=100.0, close=102.0)
        all_events = []
        for bar in bars + [disp_bar]:
            all_events.extend(det.on_bar(bar))
        disps = [e for e in all_events if isinstance(e, Displacement)]
        assert len(disps) == 1
        assert disps[0].direction == "BULL"
        assert disps[0].body_size == pytest.approx(2.0)
        assert disps[0].avg_body == pytest.approx(1.0)

    def test_no_displacement_below_threshold(self):
        """A bar with body < 2 * avg_body does NOT fire."""
        det = DisplacementDetector(window=20, mult=2.0)
        bars = make_baseline_bars(20)
        # body = 1.9 (just below 2x)
        near_bar = make_bar(20, open_=100.0, close=101.9)
        all_events = []
        for bar in bars + [near_bar]:
            all_events.extend(det.on_bar(bar))
        disps = [e for e in all_events if isinstance(e, Displacement)]
        assert len(disps) == 0

    def test_bearish_displacement(self):
        det = DisplacementDetector(window=20, mult=2.0)
        bars = make_baseline_bars(20)
        disp_bar = make_bar(20, open_=102.0, close=100.0)  # bearish body = 2.0
        all_events = []
        for bar in bars + [disp_bar]:
            all_events.extend(det.on_bar(bar))
        disps = [e for e in all_events if isinstance(e, Displacement)]
        assert len(disps) == 1
        assert disps[0].direction == "BEAR"

    def test_left_fvg_true_when_fvg_created(self):
        """left_fvg=True when displacement bar is bar i+2 in a FVG pattern."""
        det = DisplacementDetector(window=20, mult=2.0)
        # 18 baseline bars
        bars = make_baseline_bars(18)
        # bar 18: high=100.0, low=99.0 (this will be b0 of FVG)
        b_fvg0 = make_bar(18, open_=99.5, close=99.5, high=100.0, low=99.0)
        # bar 19: middle bar (b1)
        b_fvg1 = make_bar(19, open_=100.5, close=100.5, high=101.0, low=100.0)
        # bar 20: displacement AND FVG b2 — low > b0.high creates bull FVG
        # body = 103.0 - 100.5 = 2.5 (but avg_body from prev 20 bars = ~1.0 → displacement)
        # b2.low = 100.5 > b0.high = 100.0 → bull FVG
        b_disp = make_bar(20, open_=100.5, close=103.0, high=103.5, low=100.5)
        all_events = []
        for bar in bars + [b_fvg0, b_fvg1, b_disp]:
            all_events.extend(det.on_bar(bar))
        disps = [e for e in all_events if isinstance(e, Displacement)]
        assert len(disps) == 1
        assert disps[0].left_fvg is True

    def test_left_fvg_false_when_no_fvg(self):
        """left_fvg=False when the displacement candle does not create an FVG."""
        det = DisplacementDetector(window=20, mult=2.0)
        bars = make_baseline_bars(20)
        # displacement bar that does NOT create FVG (overlapping with prev bars)
        disp_bar = make_bar(20, open_=100.0, close=102.0, high=102.5, low=99.5)
        all_events = []
        for bar in bars + [disp_bar]:
            all_events.extend(det.on_bar(bar))
        disps = [e for e in all_events if isinstance(e, Displacement)]
        assert len(disps) == 1
        assert disps[0].left_fvg is False

    def test_displacement_anchor_is_bar_ts(self):
        det = DisplacementDetector(window=20, mult=2.0)
        bars = make_baseline_bars(20)
        disp_bar = make_bar(20, open_=100.0, close=102.0)
        all_events = []
        for bar in bars + [disp_bar]:
            all_events.extend(det.on_bar(bar))
        disps = [e for e in all_events if isinstance(e, Displacement)]
        assert disps[0].anchor == disp_bar.ts_utc
        assert disps[0].confirmed_at == disp_bar.ts_utc
