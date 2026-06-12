"""Tests for data loader."""
from __future__ import annotations
import pytest
from pathlib import Path
from datetime import timezone
from engine.data.loader import load_bars, list_trading_days, load_session_bars

CSV_PATH = Path(r"D:\AI\ict_trade\data\cache\nq_1m.csv")


@pytest.fixture(scope="module")
def bars():
    return load_bars(CSV_PATH)


@pytest.fixture(scope="module")
def trading_days():
    return list_trading_days(CSV_PATH)


class TestLoadBars:
    def test_returns_list(self, bars):
        assert isinstance(bars, list)
        assert len(bars) > 0

    def test_bars_sorted_by_time(self, bars):
        for i in range(1, len(bars)):
            assert bars[i].ts_utc >= bars[i - 1].ts_utc

    def test_bars_tz_aware_utc(self, bars):
        for bar in bars[:10]:
            assert bar.ts_utc.tzinfo is not None
            assert bar.ts_utc.utcoffset().total_seconds() == 0

    def test_bar_fields_float(self, bars):
        for bar in bars[:10]:
            assert isinstance(bar.open, float)
            assert isinstance(bar.high, float)
            assert isinstance(bar.low, float)
            assert isinstance(bar.close, float)
            assert isinstance(bar.volume, float)

    def test_high_gte_low(self, bars):
        for bar in bars:
            assert bar.high >= bar.low, f"Bar {bar.ts_utc}: high {bar.high} < low {bar.low}"

    def test_count_reasonable(self, bars):
        # ~27000 rows mentioned in spec
        assert len(bars) > 1000


class TestListTradingDays:
    def test_returns_sorted(self, trading_days):
        assert trading_days == sorted(trading_days)

    def test_returns_dates(self, trading_days):
        from datetime import date
        for d in trading_days:
            assert isinstance(d, date)

    def test_at_least_one_day(self, trading_days):
        assert len(trading_days) >= 1


class TestLoadSessionBars:
    def test_rth_bars_in_rth(self, trading_days):
        from engine.core.sessions import is_in_window
        if not trading_days:
            pytest.skip("No trading days found")
        day = trading_days[5] if len(trading_days) > 5 else trading_days[0]
        session_bars = load_session_bars(day, "RTH", CSV_PATH)
        for bar in session_bars:
            assert is_in_window(bar.ts_utc, "RTH"), f"{bar.ts_utc} not in RTH"

    def test_empty_for_nonexistent_day(self):
        from datetime import date
        result = load_session_bars(date(1990, 1, 1), "RTH", CSV_PATH)
        assert result == []
