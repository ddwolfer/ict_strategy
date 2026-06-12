"""Tests for FVGDetector lifecycle."""
from __future__ import annotations
import pytest
from datetime import datetime, timedelta, timezone
from engine.core.types import FVGCreated, FVGTouched, FVGFilled, TICK
from engine.detectors.fvg import FVGDetector

UTC = timezone.utc


def make_bar(i: int, open_=100.0, high=100.0, low=100.0, close=100.0, volume=0.0):
    from engine.core.types import Bar
    ts = datetime(2026, 5, 14, 14, 30, tzinfo=UTC) + timedelta(minutes=i)
    return Bar(ts_utc=ts, open=open_, high=high, low=low, close=close, volume=volume)


class TestFVGDetector:
    def test_bullish_fvg_created(self):
        """b0.high=100, b2.low=102 → bull FVG [100, 102]."""
        det = FVGDetector()
        b0 = make_bar(0, high=100.0, low=99.0)
        b1 = make_bar(1, high=101.0, low=100.0)  # middle bar
        b2 = make_bar(2, high=105.0, low=102.0)  # gap: b2.low > b0.high
        events = []
        for bar in [b0, b1, b2]:
            events.extend(det.on_bar(bar))
        created = [e for e in events if isinstance(e, FVGCreated)]
        assert len(created) == 1
        assert created[0].direction == "BULL"
        assert created[0].bottom == 100.0
        assert created[0].top == 102.0
        assert created[0].ce == 101.0
        assert created[0].anchor == b1.ts_utc
        assert created[0].confirmed_at == b2.ts_utc

    def test_bearish_fvg_created(self):
        """b0.low=100, b2.high=98 → bear FVG [98, 100]."""
        det = FVGDetector()
        b0 = make_bar(0, high=101.0, low=100.0)
        b1 = make_bar(1, high=100.0, low=99.0)  # middle bar
        b2 = make_bar(2, high=98.0, low=95.0)   # gap: b2.high < b0.low
        events = []
        for bar in [b0, b1, b2]:
            events.extend(det.on_bar(bar))
        created = [e for e in events if isinstance(e, FVGCreated)]
        assert len(created) == 1
        assert created[0].direction == "BEAR"
        assert created[0].top == 100.0
        assert created[0].bottom == 98.0
        assert created[0].ce == 99.0

    def test_no_fvg_if_gap_too_small(self):
        """Gap < 1 tick should not create FVG."""
        det = FVGDetector(min_gap_ticks=1)
        # gap = 0.1 < TICK (0.25)
        b0 = make_bar(0, high=100.0, low=99.0)
        b1 = make_bar(1, high=100.05, low=99.95)
        b2 = make_bar(2, high=105.0, low=100.1)  # gap = 0.1
        events = []
        for bar in [b0, b1, b2]:
            events.extend(det.on_bar(bar))
        created = [e for e in events if isinstance(e, FVGCreated)]
        assert len(created) == 0

    def test_bullish_fvg_touched(self):
        """After bull FVG created, a bar with low <= top → FVGTouched."""
        det = FVGDetector()
        b0 = make_bar(0, high=100.0, low=99.0)
        b1 = make_bar(1, high=101.0, low=100.0)
        b2 = make_bar(2, high=105.0, low=102.0)  # creates FVG top=102, bot=100
        b3 = make_bar(3, high=104.0, low=101.5)  # low=101.5 <= top=102 → touched
        events = []
        for bar in [b0, b1, b2, b3]:
            events.extend(det.on_bar(bar))
        touched = [e for e in events if isinstance(e, FVGTouched)]
        assert len(touched) == 1
        assert touched[0].direction == "BULL"
        assert touched[0].confirmed_at == b3.ts_utc

    def test_bullish_fvg_filled(self):
        """Bar with low <= bottom → FVGFilled."""
        det = FVGDetector()
        b0 = make_bar(0, high=100.0, low=99.0)
        b1 = make_bar(1, high=101.0, low=100.0)
        b2 = make_bar(2, high=105.0, low=102.0)  # FVG top=102, bot=100
        b3 = make_bar(3, high=104.0, low=99.5)   # low=99.5 <= bot=100 → filled
        events = []
        for bar in [b0, b1, b2, b3]:
            events.extend(det.on_bar(bar))
        filled = [e for e in events if isinstance(e, FVGFilled)]
        assert len(filled) == 1
        assert filled[0].direction == "BULL"

    def test_bearish_fvg_touched(self):
        """Bear FVG touched when bar.high >= bottom."""
        det = FVGDetector()
        b0 = make_bar(0, high=101.0, low=100.0)
        b1 = make_bar(1, high=100.0, low=99.0)
        b2 = make_bar(2, high=98.0, low=95.0)   # FVG top=100, bot=98
        b3 = make_bar(3, high=98.5, low=96.0)   # high=98.5 >= bot=98 → touched
        events = []
        for bar in [b0, b1, b2, b3]:
            events.extend(det.on_bar(bar))
        touched = [e for e in events if isinstance(e, FVGTouched)]
        assert len(touched) == 1
        assert touched[0].direction == "BEAR"

    def test_bearish_fvg_filled(self):
        """Bear FVG filled when bar.high >= top."""
        det = FVGDetector()
        b0 = make_bar(0, high=101.0, low=100.0)
        b1 = make_bar(1, high=100.0, low=99.0)
        b2 = make_bar(2, high=98.0, low=95.0)   # FVG top=100, bot=98
        b3 = make_bar(3, high=100.5, low=97.0)  # high=100.5 >= top=100 → filled
        events = []
        for bar in [b0, b1, b2, b3]:
            events.extend(det.on_bar(bar))
        filled = [e for e in events if isinstance(e, FVGFilled)]
        assert len(filled) == 1
        assert filled[0].direction == "BEAR"

    def test_touched_then_filled_sequence(self):
        """Touched event fires before filled event on different bars."""
        det = FVGDetector()
        b0 = make_bar(0, high=100.0, low=99.0)
        b1 = make_bar(1, high=101.0, low=100.0)
        b2 = make_bar(2, high=105.0, low=102.0)  # FVG top=102, bot=100
        b3 = make_bar(3, high=104.0, low=101.0)  # touched (101 <= 102)
        b4 = make_bar(4, high=103.0, low=99.5)   # filled (99.5 <= 100)
        all_events = []
        for bar in [b0, b1, b2, b3, b4]:
            all_events.extend(det.on_bar(bar))
        touched = [e for e in all_events if isinstance(e, FVGTouched)]
        filled = [e for e in all_events if isinstance(e, FVGFilled)]
        assert len(touched) == 1
        assert len(filled) == 1
        # touched must come before filled
        assert touched[0].confirmed_at < filled[0].confirmed_at

    def test_touched_only_fires_once(self):
        """Touched event only fires once per FVG (not on every bar in the gap).
        Note: b1, b2, b3 may form a *second* FVG; we verify the original FVG only touches once.
        """
        det = FVGDetector()
        b0 = make_bar(0, high=100.0, low=99.0)
        b1 = make_bar(1, high=101.0, low=100.0)
        b2 = make_bar(2, high=105.0, low=102.0)  # creates FVG: anchor=b1.ts
        b3 = make_bar(3, high=104.0, low=101.5)  # touches first FVG
        b4 = make_bar(4, high=103.0, low=101.0)  # still in gap of first FVG
        all_events = []
        for bar in [b0, b1, b2, b3, b4]:
            all_events.extend(det.on_bar(bar))
        # Filter touched events for the ORIGINAL FVG (anchor = b1.ts_utc)
        orig_fvg_anchor = b1.ts_utc
        touched_orig = [
            e for e in all_events
            if isinstance(e, FVGTouched) and e.fvg_anchor == orig_fvg_anchor
        ]
        assert len(touched_orig) == 1

    def test_filled_fvg_not_in_active(self):
        """After filled, FVG should no longer produce events."""
        det = FVGDetector()
        b0 = make_bar(0, high=100.0, low=99.0)
        b1 = make_bar(1, high=101.0, low=100.0)
        b2 = make_bar(2, high=105.0, low=102.0)  # FVG
        b3 = make_bar(3, high=104.0, low=99.5)   # filled
        b4 = make_bar(4, high=103.0, low=99.0)   # nothing more
        all_events = []
        for bar in [b0, b1, b2, b3, b4]:
            all_events.extend(det.on_bar(bar))
        filled = [e for e in all_events if isinstance(e, FVGFilled)]
        assert len(filled) == 1  # only one fill event

    def test_no_fvg_when_no_gap(self):
        """Bars with overlapping ranges should produce no FVG."""
        det = FVGDetector()
        b0 = make_bar(0, high=100.0, low=98.0)
        b1 = make_bar(1, high=101.0, low=99.0)
        b2 = make_bar(2, high=102.0, low=99.5)  # b2.low=99.5 < b0.high=100 → no gap
        events = []
        for bar in [b0, b1, b2]:
            events.extend(det.on_bar(bar))
        created = [e for e in events if isinstance(e, FVGCreated)]
        assert len(created) == 0
