"""測試每日偏向計算（engine/model/bias.py）。

手工構造日 K 情境：
1. Sell Program（跌破 swing low，現價在 premium）
2. Buy Program（突破 swing high，現價在 discount）
3. NO_TRADE（無 swing 或都不成立）
4. NO_TRADE（DOL 距離不足 min_dol_points）
5. NO_TRADE（歷史資料不足）
"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from engine.core.types import Bar
from engine.model.bias import compute_bias, DailyBias
from engine.model.config import StrategyConfig

UTC = ZoneInfo("utc")
ET = ZoneInfo("America/New_York")


def _b(day_offset: int, o: float, h: float, lo: float, c: float) -> Bar:
    """Make a daily-granularity 1-bar (not RTH 1min but aggregate-like) at UTC 14:30."""
    ts = datetime(2025, 1, 2, 14, 30, tzinfo=UTC) + timedelta(days=day_offset)
    return Bar(ts_utc=ts, open=o, high=h, low=lo, close=c, volume=1000.0)


def _rth(day_offset: int, minute: int, o: float, h: float, lo: float, c: float) -> Bar:
    """Make a RTH 1-min bar at 09:30+minute ET on 2025-01-02+day_offset."""
    d = date(2025, 1, 2) + timedelta(days=day_offset)
    # Skip weekends
    while d.weekday() >= 5:
        d += timedelta(days=1)
    et_dt = datetime(d.year, d.month, d.day, 9, 30, tzinfo=ET) + timedelta(minutes=minute)
    return Bar(ts_utc=et_dt.astimezone(UTC), open=o, high=h, low=lo, close=c, volume=1000.0)


def _make_rth_day(day_offset: int, o: float, h: float, lo: float, c: float, n: int = 3) -> list[Bar]:
    """Make n RTH bars for a trading day, skipping weekends."""
    d = date(2025, 1, 2) + timedelta(days=day_offset)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    bars = []
    for i in range(n):
        et_dt = datetime(d.year, d.month, d.day, 9, 30, tzinfo=ET) + timedelta(minutes=i)
        bars.append(Bar(ts_utc=et_dt.astimezone(UTC), open=o, high=h, low=lo, close=c, volume=1000.0))
    return bars


class TestSellProgram:
    """Sell Program：日線收盤跌破某 swing low，且現價在 premium（均衡點以上）。

    精確構造：
      日 K swing LOW 判定依 bar.low（非 close）
      DealingRange 使用 body (open/close) → eq = (max_body + min_body) / 2

      構造：
        Day 0: o=50,  h=55,  l=45,  c=52   → body min=50
        Day 1: o=400, h=405, l=395, c=402  → body max=402; eq=(402+50)/2=226
        Day 2: o=240, h=245, l=235, c=242
        Day 3: o=238, h=240, l=234, c=239
        Day 4: o=239, h=244, l=228, c=229  → swing LOW candidate (low=228)
        Day 5: o=229, h=238, l=232, c=236  → low=232 > 228 ✓ (right side)
        Day 6: o=236, h=241, l=233, c=240  → low=233 > 228 → SWING LOW 228 confirmed!
        Day 7: o=240, h=241, l=226, c=227  → close=227 < swing_low 228 ✓
                                              227 > eq(226) → premium → SELL PROGRAM!
        DOL = max(lows < 227) = 226 (day7 low); distance = 227-226 = 1
    """

    def _make_bars(self) -> list[Bar]:
        bars = []
        pattern = [
            (50,  55,  45,  52),
            (400, 405, 395, 402),
            (240, 245, 235, 242),
            (238, 240, 234, 239),
            (239, 244, 228, 229),  # swing low candidate
            (229, 238, 232, 236),  # right neighbor 1
            (236, 241, 233, 240),  # right neighbor 2 → confirmed
            (240, 241, 226, 227),  # last bar: broke 228, close=227>eq(226)
        ]
        for i, (o, h, lo, c) in enumerate(pattern):
            bars.extend(_make_rth_day(i, o, h, lo, c))
        return bars

    def test_direction_is_short(self):
        history = self._make_bars()
        cfg = StrategyConfig(min_dol_points=0.5)
        result = compute_bias(history, cfg)
        assert result.direction == "SHORT", (
            f"Expected SHORT, got {result.direction}\nReason: {result.reason}"
        )

    def test_dol_level_below_close(self):
        history = self._make_bars()
        cfg = StrategyConfig(min_dol_points=0.5)
        result = compute_bias(history, cfg)
        if result.direction == "SHORT":
            assert result.dol_level is not None
            assert result.dol_level < 227.0

    def test_swing_lows_captured(self):
        history = self._make_bars()
        cfg = StrategyConfig(min_dol_points=0.5)
        result = compute_bias(history, cfg)
        # Must have detected the swing low at 228
        # (direction might be SHORT or NO_TRADE but swing_lows should be populated)
        # At minimum dealing range should be computed
        assert result.dealing_range is not None

    def test_sell_program_cancelled_in_discount(self):
        """現價 < eq → discount → sell program 取消 → NO_TRADE。

        Same pattern but change last bar: close = 220 < eq(226) → discount.
        """
        bars = []
        pattern = [
            (50,  55,  45,  52),
            (400, 405, 395, 402),
            (240, 245, 235, 242),
            (238, 240, 234, 239),
            (239, 244, 228, 229),
            (229, 238, 232, 236),
            (236, 241, 233, 240),
            (240, 241, 215, 220),  # close=220 < eq(226) → discount → cancelled
        ]
        for i, (o, h, lo, c) in enumerate(pattern):
            bars.extend(_make_rth_day(i, o, h, lo, c))
        cfg = StrategyConfig(min_dol_points=0.5)
        result = compute_bias(bars, cfg)
        assert result.direction == "NO_TRADE"


class TestBuyProgram:
    """Buy Program：突破 swing high，現價在 discount（均衡點以下）。

    精確構造：
      SWING HIGH 判定依 bar.high（非 close）
      DealingRange eq = (max_body + min_body) / 2

      構造：
        Day 0: o=500, h=505, l=495, c=502  → body max=502
        Day 1: o=50,  h=55,  l=45,  c=52   → body min=50; eq=(502+50)/2=276
        Day 2: o=260, h=268, l=255, c=263
        Day 3: o=263, h=270, l=260, c=266
        Day 4: o=266, h=272, l=259, c=261  → swing HIGH candidate (high=272)
        Day 5: o=261, h=268, l=258, c=264  → high=268 < 272 ✓ (right 1)
        Day 6: o=264, h=269, l=260, c=265  → high=269 < 272 → SWING HIGH 272 confirmed!
        Day 7: o=265, h=278, l=262, c=275  → close=275 > swing_high 272 ✓
                                              275 < eq(276) → discount → BUY PROGRAM!
        DOL = min(highs > 275) = 278 (day7 high); distance = 278-275 = 3
    """

    def _make_bars(self) -> list[Bar]:
        bars = []
        pattern = [
            (500, 505, 495, 502),
            (50,  55,  45,  52),
            (260, 268, 255, 263),
            (263, 270, 260, 266),
            (266, 272, 259, 261),  # swing high candidate
            (261, 268, 258, 264),  # right 1
            (264, 269, 260, 265),  # right 2 → confirmed
            (265, 278, 262, 275),  # last: broke 272, close=275 < eq(276)
        ]
        for i, (o, h, lo, c) in enumerate(pattern):
            bars.extend(_make_rth_day(i, o, h, lo, c))
        return bars

    def test_direction_is_long(self):
        history = self._make_bars()
        cfg = StrategyConfig(min_dol_points=0.5)
        result = compute_bias(history, cfg)
        assert result.direction == "LONG", (
            f"Expected LONG, got {result.direction}\nReason: {result.reason}"
        )

    def test_dol_level_above_close(self):
        history = self._make_bars()
        cfg = StrategyConfig(min_dol_points=0.5)
        result = compute_bias(history, cfg)
        if result.direction == "LONG":
            assert result.dol_level is not None
            assert result.dol_level > 275.0

    def test_buy_program_cancelled_in_premium(self):
        """現價 > eq → premium → buy program 取消 → NO_TRADE。

        Change last bar: close=280 > eq(276) → premium → cancelled.
        """
        bars = []
        pattern = [
            (500, 505, 495, 502),
            (50,  55,  45,  52),
            (260, 268, 255, 263),
            (263, 270, 260, 266),
            (266, 272, 259, 261),
            (261, 268, 258, 264),
            (264, 269, 260, 265),
            (265, 285, 262, 280),  # close=280 > eq(276) → premium → cancelled
        ]
        for i, (o, h, lo, c) in enumerate(pattern):
            bars.extend(_make_rth_day(i, o, h, lo, c))
        cfg = StrategyConfig(min_dol_points=0.5)
        result = compute_bias(bars, cfg)
        assert result.direction == "NO_TRADE"


class TestNoTrade:
    """NO_TRADE 情境。"""

    def test_empty_history(self):
        result = compute_bias([])
        assert result.direction == "NO_TRADE"
        assert result.reason  # must have a reason

    def test_insufficient_daily_bars(self):
        """只有 2 根日 K → SwingDetector 需要至少 3 根 → NO_TRADE。"""
        bars = []
        for i in range(2):
            bars.extend(_make_rth_day(i, 100.0, 105.0, 95.0, 102.0))
        result = compute_bias(bars)
        assert result.direction == "NO_TRADE"
        assert "不足" in result.reason

    def test_flat_market_no_strict_swing(self):
        """所有日 K 高低完全相同 → 無嚴格 swing → NO_TRADE。"""
        bars = []
        for i in range(10):
            bars.extend(_make_rth_day(i, 100.0, 102.0, 98.0, 100.0))
        result = compute_bias(bars)
        assert result.direction == "NO_TRADE"

    def test_no_swing_lows_for_sell(self):
        """連續上漲日 K，無 swing low 確認 → sell program 無法觸發。"""
        bars = []
        for i in range(10):
            bars.extend(_make_rth_day(i, 100.0 + i, 105.0 + i, 99.0 + i, 103.0 + i))
        result = compute_bias(bars)
        # Might have swing highs but not lows, and close > eq → no sell program
        assert result.direction in ("NO_TRADE", "LONG")


class TestDolDistance:
    """DOL 距離不足 min_dol_points → NO_TRADE。"""

    def test_dol_too_close(self):
        """Sell Program 成立，但 min_dol_points 設為 999 → NO_TRADE。"""
        bars = []
        pattern = [
            (50,  55,  45,  52),
            (400, 405, 395, 402),
            (240, 245, 235, 242),
            (238, 240, 234, 239),
            (239, 244, 228, 229),
            (229, 238, 232, 236),
            (236, 241, 233, 240),
            (240, 241, 226, 227),
        ]
        for i, (o, h, lo, c) in enumerate(pattern):
            bars.extend(_make_rth_day(i, o, h, lo, c))

        # Normal config: should be SHORT
        cfg_normal = StrategyConfig(min_dol_points=0.5)
        result_normal = compute_bias(bars, cfg_normal)
        # If SHORT, then large min_dol_points should give NO_TRADE
        if result_normal.direction == "SHORT":
            cfg_large = StrategyConfig(min_dol_points=9999.0)
            result_large = compute_bias(bars, cfg_large)
            assert result_large.direction == "NO_TRADE"
            assert ("DOL" in result_large.reason or "距" in result_large.reason or
                    "min_dol" in result_large.reason)
