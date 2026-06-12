"""Tests for core types and constants."""
from __future__ import annotations
import pytest
from datetime import datetime, timezone
from engine.core.types import (
    Bar, SwingConfirmed, PoolCreated, PoolSwept, Raid,
    FVGCreated, FVGTouched, FVGFilled, Displacement, MSS,
    SessionBoundary, TICK, POINT_VALUE,
)


def make_bar(ts_str: str = "2026-05-14T14:30:00+00:00", **kwargs) -> Bar:
    ts = datetime.fromisoformat(ts_str)
    defaults = dict(open=100.0, high=105.0, low=95.0, close=102.0, volume=100.0)
    defaults.update(kwargs)
    return Bar(ts_utc=ts, **defaults)


class TestConstants:
    def test_tick(self):
        assert TICK == 0.25

    def test_point_value(self):
        assert POINT_VALUE == 20.0


class TestBar:
    def test_bar_fields(self):
        bar = make_bar()
        assert bar.open == 100.0
        assert bar.high == 105.0
        assert bar.low == 95.0
        assert bar.close == 102.0
        assert bar.volume == 100.0

    def test_bar_frozen(self):
        bar = make_bar()
        with pytest.raises((AttributeError, TypeError)):
            bar.open = 999.0  # type: ignore

    def test_bar_tz_aware(self):
        bar = make_bar()
        assert bar.ts_utc.tzinfo is not None


class TestSwingConfirmed:
    def test_fields(self):
        ts = datetime.fromisoformat("2026-05-14T14:30:00+00:00")
        ev = SwingConfirmed(confirmed_at=ts, anchor=ts, side="HIGH", level=105.0)
        assert ev.side == "HIGH"
        assert ev.level == 105.0

    def test_frozen(self):
        ts = datetime.fromisoformat("2026-05-14T14:30:00+00:00")
        ev = SwingConfirmed(confirmed_at=ts, anchor=ts, side="LOW", level=95.0)
        with pytest.raises((AttributeError, TypeError)):
            ev.level = 0.0  # type: ignore


class TestFVGCreated:
    def test_ce_calculation(self):
        ts = datetime.fromisoformat("2026-05-14T14:30:00+00:00")
        ev = FVGCreated(
            confirmed_at=ts, anchor=ts,
            direction="BULL", top=110.0, bottom=100.0, ce=105.0,
        )
        assert ev.ce == (ev.top + ev.bottom) / 2


class TestPoolCreated:
    def test_kinds(self):
        ts = datetime.fromisoformat("2026-05-14T14:30:00+00:00")
        for kind in ["PDH", "PDL", "ONH", "ONL", "SESSION_HIGH", "SESSION_LOW",
                     "SWING_HIGH", "SWING_LOW", "EQUAL_HIGHS", "EQUAL_LOWS"]:
            ev = PoolCreated(confirmed_at=ts, kind=kind, side="BUY", level=100.0)
            assert ev.kind == kind


class TestMSS:
    def test_fields(self):
        ts = datetime.fromisoformat("2026-05-14T14:30:00+00:00")
        ev = MSS(
            confirmed_at=ts,
            direction="BEAR",
            broken_swing_level=95.0,
            broken_swing_anchor=ts,
            displacement_anchor=ts,
            left_fvg=True,
        )
        assert ev.direction == "BEAR"
        assert ev.left_fvg is True
