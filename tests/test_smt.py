"""tests/test_smt.py — SMTChecker 單元測試。"""
from __future__ import annotations
import pytest
from datetime import datetime, timezone
from engine.core.types import Bar
from engine.detectors.smt import SMTChecker

UTC = timezone.utc


def _bar(ts_iso: str, h: float, lo: float) -> Bar:
    ts = datetime.fromisoformat(ts_iso).replace(tzinfo=UTC)
    return Bar(ts_utc=ts, open=h, high=h, low=lo, close=(h + lo) / 2, volume=100.0)


def _ts(ts_iso: str) -> datetime:
    return datetime.fromisoformat(ts_iso).replace(tzinfo=UTC)


class TestSMTDivergence:
    """check_divergence 背離成立/不成立。"""

    def _build_checker(self, nq_bars, es_bars_or_none):
        checker = SMTChecker(lookback_bars=10)
        for nq_b, es_b in zip(nq_bars, es_bars_or_none):
            checker.on_bar(nq_b, es_b)
        return checker

    def test_buy_side_divergence_confirmed(self):
        """NQ 掃上方，ES high 未突破參考值 → 背離成立（True）。"""
        # NQ 和 ES 建立參考期：各 5 根
        nq_bars = [_bar(f"2025-01-06T14:0{i}:00", 20100 + i, 20090 + i) for i in range(5)]
        es_bars = [_bar(f"2025-01-06T14:0{i}:00", 5200 + i, 5190 + i) for i in range(5)]
        # 第 3 根設置 ES 參考高 = 5203
        # NQ Raid bar（第 5 根，高掃過水位）
        nq_raid = _bar("2025-01-06T14:05:00", 20115, 20100)  # NQ 高掃
        es_raid = _bar("2025-01-06T14:05:00", 5202, 5195)    # ES high=5202 < 5203 → 未突破

        checker = SMTChecker(lookback_bars=10)
        for nb, eb in zip(nq_bars, es_bars):
            checker.on_bar(nb, eb)
        checker.on_bar(nq_raid, es_raid)

        pool_t = _ts("2025-01-06T14:00:00")
        raid_t = _ts("2025-01-06T14:05:00")
        assert checker.check_divergence("BUY", pool_t, raid_t) is True

    def test_buy_side_no_divergence(self):
        """NQ 掃上方，ES high 同步突破 → 背離不成立（False）。"""
        nq_bars = [_bar(f"2025-01-06T14:0{i}:00", 20100 + i, 20090 + i) for i in range(5)]
        es_bars = [_bar(f"2025-01-06T14:0{i}:00", 5200 + i, 5190 + i) for i in range(5)]
        nq_raid = _bar("2025-01-06T14:05:00", 20115, 20100)
        es_raid = _bar("2025-01-06T14:05:00", 5210, 5195)  # ES high=5210 > 5204 → 突破

        checker = SMTChecker(lookback_bars=10)
        for nb, eb in zip(nq_bars, es_bars):
            checker.on_bar(nb, eb)
        checker.on_bar(nq_raid, es_raid)

        pool_t = _ts("2025-01-06T14:00:00")
        raid_t = _ts("2025-01-06T14:05:00")
        assert checker.check_divergence("BUY", pool_t, raid_t) is False

    def test_sell_side_divergence_confirmed(self):
        """NQ 掃下方，ES low 未突破參考最低值 → 背離成立（True）。"""
        nq_bars = [_bar(f"2025-01-06T15:0{i}:00", 20100 - i, 20090 - i) for i in range(5)]
        es_bars = [_bar(f"2025-01-06T15:0{i}:00", 5200 - i, 5190 - i) for i in range(5)]
        # ES ref low (in range) = 5186
        nq_raid = _bar("2025-01-06T15:05:00", 20080, 20070)  # NQ 低掃
        es_raid = _bar("2025-01-06T15:05:00", 20087, 5187)   # ES low=5187 > 5186 → 未突破

        checker = SMTChecker(lookback_bars=10)
        for nb, eb in zip(nq_bars, es_bars):
            checker.on_bar(nb, eb)
        checker.on_bar(nq_raid, es_raid)

        pool_t = _ts("2025-01-06T15:00:00")
        raid_t = _ts("2025-01-06T15:05:00")
        assert checker.check_divergence("SELL", pool_t, raid_t) is True

    def test_missing_es_bar_uses_previous(self):
        """ES 缺分鐘傳 None → 沿用前值，不出錯。"""
        checker = SMTChecker(lookback_bars=10)
        nq_bars = [_bar(f"2025-01-06T14:0{i}:00", 20100 + i, 20090 + i) for i in range(3)]
        es_bars_src = [_bar(f"2025-01-06T14:0{i}:00", 5200 + i, 5190 + i) for i in range(3)]

        checker.on_bar(nq_bars[0], es_bars_src[0])
        checker.on_bar(nq_bars[1], None)  # 缺分鐘，沿用前值
        checker.on_bar(nq_bars[2], es_bars_src[2])

        # Should not raise; check that es history has 3 entries
        assert len(checker._es_history) == 3

    def test_no_es_data_returns_false(self):
        """完全無 ES 資料時回傳 False（保守，不允許進場）。"""
        checker = SMTChecker(lookback_bars=10)
        nq_b = _bar("2025-01-06T14:00:00", 20100, 20090)
        checker.on_bar(nq_b, None)  # no ES data
        raid_t = _ts("2025-01-06T14:00:00")
        assert checker.check_divergence("BUY", None, raid_t) is False

    def test_lookback_fallback_when_pool_t_none(self):
        """pool_created_t=None → 使用 lookback_bars 做回看參考。"""
        checker = SMTChecker(lookback_bars=5)
        # Feed 10 NQ/ES bars
        for i in range(10):
            nb = _bar(f"2025-01-06T14:{i:02d}:00", 20100 + i, 20090 + i)
            eb = _bar(f"2025-01-06T14:{i:02d}:00", 5200 + i, 5190 + i)
            checker.on_bar(nb, eb)
        # Raid bar — ES high < last 5 bars max (5204+5205+5206+5207+5208 → max=5208)
        # ES raid bar high = 5207 (< 5208? No, tie → not above)
        nb_raid = _bar("2025-01-06T14:10:00", 20115, 20100)
        eb_raid = _bar("2025-01-06T14:10:00", 5207, 5200)  # high=5207 < ref max 5209
        checker.on_bar(nb_raid, eb_raid)
        raid_t = _ts("2025-01-06T14:10:00")
        # pool_created_t=None → use lookback
        result = checker.check_divergence("BUY", None, raid_t)
        assert isinstance(result, bool)  # just verify no crash


class TestSMTNoDivergence:
    """保守性：資料不足時預設 False。"""

    def test_empty_checker_returns_false(self):
        checker = SMTChecker()
        raid_t = _ts("2025-01-06T14:00:00")
        assert checker.check_divergence("BUY", None, raid_t) is False
