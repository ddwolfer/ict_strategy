"""tests/test_sessions_config.py — §2.4 多時段 config 與 runner 日窗驗證。"""
from __future__ import annotations

from datetime import time

import pytest

from engine.model.config import StrategyConfig, _SESSION_DEFAULTS


# ─── for_session 工廠參數正確性 ───────────────────────────────────────────────

class TestForSession:
    def test_ny_am_defaults(self):
        cfg = StrategyConfig.for_session("NY_AM")
        assert cfg.session == "NY_AM"
        assert cfg.entry_window == ("09:30", "11:00")
        assert cfg.flatten_time == "12:30"
        assert cfg.context_start == "08:00"
        assert cfg.late_window_thu_fri is True

    def test_ny_pm_defaults(self):
        cfg = StrategyConfig.for_session("NY_PM")
        assert cfg.session == "NY_PM"
        assert cfg.entry_window == ("13:30", "15:00")
        assert cfg.flatten_time == "15:55"
        assert cfg.context_start == "08:00"
        assert cfg.late_window_thu_fri is False

    def test_london_defaults(self):
        cfg = StrategyConfig.for_session("LONDON")
        assert cfg.session == "LONDON"
        assert cfg.entry_window == ("02:00", "05:00")
        assert cfg.flatten_time == "05:30"
        assert cfg.context_start == "00:00"
        assert cfg.late_window_thu_fri is False

    def test_override_respected(self):
        """使用者顯式覆蓋應優先於 session 預設。"""
        cfg = StrategyConfig.for_session("NY_PM", flatten_time="16:00")
        assert cfg.flatten_time == "16:00"
        assert cfg.entry_window == ("13:30", "15:00")  # 未覆蓋的仍用預設

    def test_unknown_session_raises(self):
        with pytest.raises(ValueError, match="未知 session"):
            StrategyConfig.for_session("TOKYO")  # type: ignore[arg-type]

    def test_default_config_is_ny_am(self):
        """不帶 session 的 StrategyConfig() 仍是 NY_AM 預設。"""
        cfg = StrategyConfig()
        assert cfg.session == "NY_AM"
        assert cfg.entry_window == ("09:30", "11:00")
        assert cfg.flatten_time == "12:30"
        assert cfg.context_start == "08:00"


# ─── runner 日窗範圍驗證 ──────────────────────────────────────────────────────

from datetime import datetime, timezone, timedelta
from engine.backtest.runner import _bars_for_day_window, _parse_hm
from engine.core.types import Bar


def _make_bar(utc_dt: datetime, price: float = 100.0) -> Bar:
    """建立最簡 Bar fixture。"""
    return Bar(
        ts_utc=utc_dt,
        open=price, high=price, low=price, close=price, volume=0,
    )


def _et_to_utc(y: int, mo: int, d: int, h: int, m: int) -> datetime:
    """ET（UTC-4 夏令）→ UTC，簡化用。"""
    return datetime(y, mo, d, h + 4, m, tzinfo=timezone.utc)


class TestBarsForDayWindow:
    """runner._bars_for_day_window 在不同 session config 下的窗口。"""

    # 用 2026-05-14（週三，夏令 UTC-4）作為基準
    _Y, _MO, _D = 2026, 5, 14

    def _make_day_bars(self):
        """建立 00:00–17:00 ET（整點）的 bars。"""
        bars = []
        for h in range(0, 18):
            bars.append(_make_bar(_et_to_utc(self._Y, self._MO, self._D, h, 0)))
        return bars

    def test_ny_am_window(self):
        """NY_AM：08:00 <= t < 12:30 ET（整點 bars: 08,09,10,11,12 全含）。"""
        cfg = StrategyConfig.for_session("NY_AM")
        bars = self._make_day_bars()
        from datetime import date
        day = date(self._Y, self._MO, self._D)
        result = _bars_for_day_window(bars, day, config=cfg)
        result_hours = [
            (b.ts_utc - timedelta(hours=4)).hour for b in result
        ]
        # 整點：08,09,10,11,12 均 < 12:30，故含 12:00；13:00 排除
        assert result_hours == list(range(8, 13)), f"got {result_hours}"
        assert 13 not in result_hours

    def test_ny_pm_window(self):
        """NY_PM：08:00 <= t < 15:55 ET（context 從 08:00 開始）。"""
        cfg = StrategyConfig.for_session("NY_PM")
        bars = self._make_day_bars()
        from datetime import date
        day = date(self._Y, self._MO, self._D)
        result = _bars_for_day_window(bars, day, config=cfg)
        result_hours = [(b.ts_utc - timedelta(hours=4)).hour for b in result]
        # 整點 bars：08, 09, 10, 11, 12, 13, 14, 15 (15:55 尚未到所以 15:00 整點含)
        assert 8 in result_hours
        assert 15 in result_hours
        assert 16 not in result_hours

    def test_london_window(self):
        """LONDON：00:00 <= t < 05:30 ET（整點 bars: 00..05 全含）。"""
        cfg = StrategyConfig.for_session("LONDON")
        bars = self._make_day_bars()
        from datetime import date
        day = date(self._Y, self._MO, self._D)
        result = _bars_for_day_window(bars, day, config=cfg)
        result_hours = [(b.ts_utc - timedelta(hours=4)).hour for b in result]
        # 整點：00,01,02,03,04,05 均 < 05:30；06:00 排除
        assert result_hours == list(range(0, 6)), f"got {result_hours}"
        assert 6 not in result_hours


# ─── _parse_hm 正確性 ────────────────────────────────────────────────────────

class TestParseHm:
    def test_basic(self):
        assert _parse_hm("09:30") == time(9, 30)
        assert _parse_hm("00:00") == time(0, 0)
        assert _parse_hm("15:55") == time(15, 55)
        assert _parse_hm("05:30") == time(5, 30)
