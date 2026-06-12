"""Tests for DealingRange."""
from __future__ import annotations
import pytest
from datetime import datetime, timedelta, timezone
from engine.core.types import Bar, TICK
from engine.detectors.ranges import DealingRange

UTC = timezone.utc


def make_bar(i: int, open_: float, close: float, high: float | None = None, low: float | None = None):
    ts = datetime(2026, 5, 14, 14, 30, tzinfo=UTC) + timedelta(minutes=i)
    if high is None:
        high = max(open_, close)
    if low is None:
        low = min(open_, close)
    return Bar(ts_utc=ts, open=open_, high=high, low=low, close=close, volume=0.0)


class TestDealingRange:
    def test_equilibrium(self):
        dr = DealingRange(high=200.0, low=100.0)
        assert dr.equilibrium == pytest.approx(150.0)

    def test_is_premium(self):
        dr = DealingRange(high=200.0, low=100.0)
        assert dr.is_premium(160.0) is True
        assert dr.is_premium(140.0) is False
        assert dr.is_premium(150.0) is False  # exactly equilibrium

    def test_is_discount(self):
        dr = DealingRange(high=200.0, low=100.0)
        assert dr.is_discount(140.0) is True
        assert dr.is_discount(160.0) is False
        assert dr.is_discount(150.0) is False

    def test_ote_zone_range(self):
        """OTE zone for range 100–200: 62–79% retracement from high."""
        dr = DealingRange(high=200.0, low=100.0)
        ote_low, ote_high = dr.ote_zone()
        # 62% retracement from 200 = 200 - 0.62*100 = 138
        # 79% retracement from 200 = 200 - 0.79*100 = 121
        assert ote_high == pytest.approx(138.0)
        assert ote_low == pytest.approx(121.0)
        assert ote_low < ote_high

    def test_from_lookback_use_bodies(self):
        """use_bodies=True uses max(open, close) for high, min(open, close) for low."""
        bars = [
            make_bar(i, open_=100.0, close=110.0, high=115.0, low=95.0)
            for i in range(5)
        ]
        dr = DealingRange.from_lookback(bars, lookback_days=20, use_bodies=True)
        assert dr.high == 110.0  # max body top
        assert dr.low == 100.0   # min body bottom

    def test_from_lookback_use_wicks(self):
        """use_bodies=False uses high/low wicks."""
        bars = [
            make_bar(i, open_=100.0, close=110.0, high=115.0, low=95.0)
            for i in range(5)
        ]
        dr = DealingRange.from_lookback(bars, lookback_days=20, use_bodies=False)
        assert dr.high == 115.0
        assert dr.low == 95.0

    def test_from_lookback_respects_lookback_days(self):
        """Only the most recent lookback_days trading days should be used."""
        # Create bars spanning multiple days
        bars = []
        base = datetime(2026, 5, 1, 14, 30, tzinfo=UTC)
        for day in range(25):  # 25 days
            ts = base + timedelta(days=day)
            # Day 0-4: open=200, close=220 (older)
            # Day 20-24: open=100, close=110 (recent)
            if day < 5:
                bars.append(Bar(ts_utc=ts, open=200.0, high=225.0, low=195.0, close=220.0, volume=0.0))
            else:
                bars.append(Bar(ts_utc=ts, open=100.0, high=115.0, low=95.0, close=110.0, volume=0.0))
        dr = DealingRange.from_lookback(bars, lookback_days=20, use_bodies=True)
        # Recent 20 days are days 5-24, all with body [100, 110]
        assert dr.high == 110.0
        assert dr.low == 100.0

    def test_from_lookback_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            DealingRange.from_lookback([])

    def test_from_lookback_single_bar(self):
        bar = make_bar(0, open_=100.0, close=105.0, high=107.0, low=99.0)
        dr = DealingRange.from_lookback([bar], use_bodies=True)
        assert dr.high == 105.0
        assert dr.low == 100.0
