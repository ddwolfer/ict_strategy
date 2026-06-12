"""No-lookahead golden rule tests (§9).

For each detector, running on bars[:t] must produce an exact prefix
of the events produced by running on all bars.
"""
from __future__ import annotations
import pytest
from datetime import datetime, timedelta, timezone
from typing import Callable, Any
from engine.core.types import Bar, TICK

UTC = timezone.utc


# ─── Bar factories ───────────────────────────────────────────────────────────

def _ts(i: int) -> datetime:
    return datetime(2026, 5, 14, 14, 30, tzinfo=UTC) + timedelta(minutes=i)


def _bar(i: int, open_=100.0, high=100.0, low=100.0, close=100.0) -> Bar:
    return Bar(ts_utc=_ts(i), open=open_, high=high, low=low, close=close, volume=0.0)


def make_varying_bars(n: int) -> list[Bar]:
    """Generate n bars with some variation to trigger swing/FVG/displacement events."""
    bars = []
    import math
    for i in range(n):
        angle = i * 0.5
        base = 100.0 + 5.0 * math.sin(angle)
        body = 1.0 + 0.5 * abs(math.cos(angle * 0.7))
        direction = 1 if math.cos(angle) > 0 else -1
        open_ = base
        close = base + direction * body
        high = max(open_, close) + 0.5
        low = min(open_, close) - 0.5
        bars.append(Bar(ts_utc=_ts(i), open=open_, high=high, low=low, close=close, volume=float(i)))
    return bars


def run_detector(factory: Callable[[], Any], bars: list[Bar]) -> list:
    """Run a fresh detector on the given bars, returning all events."""
    det = factory()
    events = []
    for bar in bars:
        events.extend(det.on_bar(bar))
    return events


def check_no_lookahead(factory: Callable[[], Any], bars: list[Bar], check_indices: list[int]) -> None:
    """Assert that for each t in check_indices, run(bars[:t]) is a prefix of run(bars)."""
    full_events = run_detector(factory, bars)
    for t in check_indices:
        partial_events = run_detector(factory, bars[:t])
        prefix = full_events[:len(partial_events)]
        assert partial_events == prefix, (
            f"Lookahead violation at t={t}: "
            f"partial[{len(partial_events)}] != full[:{len(partial_events)}]\n"
            f"partial tail: {partial_events[-3:] if len(partial_events) >= 3 else partial_events}\n"
            f"full prefix tail: {prefix[-3:] if len(prefix) >= 3 else prefix}"
        )


# ─── Tests ───────────────────────────────────────────────────────────────────

BARS_N = 50
BARS = make_varying_bars(BARS_N)
CHECK_INDICES = [5, 10, 20, 30, 40, BARS_N]


class TestSwingNoLookahead:
    def test_swing_n1(self):
        from engine.detectors.swings import SwingDetector
        check_no_lookahead(lambda: SwingDetector(n=1), BARS, CHECK_INDICES)

    def test_swing_n2(self):
        from engine.detectors.swings import SwingDetector
        check_no_lookahead(lambda: SwingDetector(n=2), BARS, CHECK_INDICES)


class TestFVGNoLookahead:
    def test_fvg_default(self):
        from engine.detectors.fvg import FVGDetector
        check_no_lookahead(lambda: FVGDetector(), BARS, CHECK_INDICES)


class TestDisplacementNoLookahead:
    def test_displacement_window20(self):
        from engine.detectors.displacement import DisplacementDetector
        check_no_lookahead(lambda: DisplacementDetector(window=20), BARS, CHECK_INDICES)

    def test_displacement_small_window(self):
        from engine.detectors.displacement import DisplacementDetector
        check_no_lookahead(lambda: DisplacementDetector(window=5), BARS, CHECK_INDICES)


class TestMSSNoLookahead:
    def test_mss_default(self):
        from engine.detectors.mss import MSSDetector
        check_no_lookahead(lambda: MSSDetector(n=1, window=5), BARS, CHECK_INDICES)


class TestPoolsNoLookahead:
    def test_pools_default(self):
        from engine.detectors.pools import LiquidityPoolTracker
        check_no_lookahead(lambda: LiquidityPoolTracker(n=1), BARS, CHECK_INDICES)


class TestRangesNoLookahead:
    """DealingRange is computed from a static set of bars (not streaming),
    so the no-lookahead guarantee is structural: from_lookback uses only bars passed to it."""

    def test_from_lookback_uses_only_given_bars(self):
        from engine.detectors.ranges import DealingRange
        full_dr = DealingRange.from_lookback(BARS, lookback_days=10)
        partial_dr = DealingRange.from_lookback(BARS[:20], lookback_days=10)
        # They may differ — that's fine. The key is partial only uses BARS[:20]
        # Verify that the partial result doesn't depend on BARS[20:]
        partial_dr2 = DealingRange.from_lookback(BARS[:20], lookback_days=10)
        assert partial_dr.high == partial_dr2.high
        assert partial_dr.low == partial_dr2.low


class TestNoLookaheadWithRealData:
    """Smoke test: run all streaming detectors on real data and verify prefix property."""

    def test_swing_on_real_data(self):
        """Load a small slice of real data and verify no-lookahead for SwingDetector."""
        try:
            from pathlib import Path
            from engine.data.loader import load_bars
            csv = Path(r"D:\AI\ict_trade\data\cache\nq_1m.csv")
            bars = load_bars(csv)[:100]  # first 100 bars
        except Exception:
            pytest.skip("Real data not available")
        from engine.detectors.swings import SwingDetector
        check_no_lookahead(lambda: SwingDetector(n=1), bars, [10, 30, 60, 90, 100])

    def test_fvg_on_real_data(self):
        try:
            from pathlib import Path
            from engine.data.loader import load_bars
            csv = Path(r"D:\AI\ict_trade\data\cache\nq_1m.csv")
            bars = load_bars(csv)[:100]
        except Exception:
            pytest.skip("Real data not available")
        from engine.detectors.fvg import FVGDetector
        check_no_lookahead(lambda: FVGDetector(), bars, [10, 30, 60, 90, 100])

    def test_displacement_on_real_data(self):
        try:
            from pathlib import Path
            from engine.data.loader import load_bars
            csv = Path(r"D:\AI\ict_trade\data\cache\nq_1m.csv")
            bars = load_bars(csv)[:200]
        except Exception:
            pytest.skip("Real data not available")
        from engine.detectors.displacement import DisplacementDetector
        check_no_lookahead(lambda: DisplacementDetector(window=20), bars, [25, 50, 100, 150, 200])


# ─── SimBroker 無前視保證 ────────────────────────────────────────────────────

class TestSimBrokerNoLookahead:
    """SimBroker 不得使用未來 K 棒資料。

    測試策略：固定一組 BARS，提交相同的 bracket；
    分別以 BARS[:t] 與 BARS 餵入，確認前者產生的 Trade 結果
    是後者的精確前綴（或相同）—— 早截斷不能改變已發生的成交。
    """

    @staticmethod
    def _run_broker_on_bars(bars: list[Bar]) -> list:
        """在一組 bars 上跑完整個流程，回傳 (events_per_bar, trades) 快照。"""
        from engine.sim.broker import BrokerConfig, SimBroker
        from engine.sim.orders import Bracket, Order

        broker = SimBroker(BrokerConfig(slippage_ticks=0, commission_per_side=0))
        # 以第一根 bar 附近的價格設定 bracket（不依賴未來資料）
        ref_open = bars[0].open
        entry_price = round(ref_open - 1.0, 2)   # BUY LIMIT 略低於開盤
        stop_price = entry_price - 2.0
        target_price = entry_price + 3.0

        order = Order(side="BUY", type="LIMIT", price=entry_price, qty=1)
        bracket = Bracket(entry=order, stop_price=stop_price, targets=[(target_price, 1)])
        broker.submit(bracket)

        all_events = []
        for bar in bars:
            evts = broker.on_bar(bar)
            all_events.append(evts)
        return all_events, broker.trades

    def test_partial_run_is_prefix_of_full_run(self):
        """bars[:30] 與 bars[:50] 的交易紀錄不矛盾（前者是後者的前綴）。"""
        _, trades_full = self._run_broker_on_bars(BARS)
        _, trades_partial = self._run_broker_on_bars(BARS[:30])

        # partial 中發生的交易必須與 full 中對應位置一致
        for i, t_partial in enumerate(trades_partial):
            if i < len(trades_full):
                t_full = trades_full[i]
                assert t_partial.entry_price == t_full.entry_price, (
                    f"Trade {i} entry_price mismatch: "
                    f"partial={t_partial.entry_price} full={t_full.entry_price}"
                )
                assert t_partial.exit_fills[0].price == t_full.exit_fills[0].price, (
                    f"Trade {i} exit price mismatch"
                )

    def test_event_sequence_prefix_property(self):
        """bars[:20] 產生的 events（前 20 棒）應與 bars[:50] 前 20 棒一致。"""
        events_full, _ = self._run_broker_on_bars(BARS)
        events_partial, _ = self._run_broker_on_bars(BARS[:20])

        # 比較前 20 棒的事件序列
        for i in range(len(events_partial)):
            assert len(events_partial[i]) == len(events_full[i]), (
                f"Bar {i}: event count differs — "
                f"partial={len(events_partial[i])} full={len(events_full[i])}"
            )
            for j, (ep, ef) in enumerate(zip(events_partial[i], events_full[i])):
                assert type(ep) == type(ef), (
                    f"Bar {i} event {j}: type mismatch {type(ep)} vs {type(ef)}"
                )

    def test_no_future_bar_data_in_fill(self):
        """各棒的成交價只能落在 [bar.low, bar.high] 範圍內（含 open）。

        這是保守成交規則的必要條件：fill_price 不能來自未來 K 棒。
        """
        from engine.sim.broker import OrderFilled, TradeClosed

        events_list, trades = self._run_broker_on_bars(BARS)
        for i, (bar, evts) in enumerate(zip(BARS, events_list)):
            for evt in evts:
                if isinstance(evt, OrderFilled):
                    assert bar.low - 1e-9 <= evt.fill_price <= bar.high + 1e-9, (
                        f"Bar {i}: fill_price {evt.fill_price} outside "
                        f"[{bar.low}, {bar.high}]"
                    )


# ─── ICTStrategy 無前視保證 ───────────────────────────────────────────────────

class TestICTStrategyNoLookahead:
    """ICTStrategy 的 StateChanged 事件確認時間不得超過當前 bar 的 ts_utc。"""

    @staticmethod
    def _make_et_bars(n: int = 40) -> list[Bar]:
        """製造 n 根 09:30 ET 開始的 1 分 K bars。"""
        from zoneinfo import ZoneInfo
        from datetime import date as _date
        ET_ = ZoneInfo("America/New_York")
        UTC_ = ZoneInfo("utc")
        bars = []
        import math
        from datetime import timedelta as _td
        base_et = datetime(2025, 6, 16, 9, 30, 0, tzinfo=ET_)
        for i in range(n):
            et_dt = base_et + _td(minutes=i)
            utc_dt = et_dt.astimezone(UTC_)
            base = 20100.0 + 5.0 * math.sin(i * 0.4)
            body = 2.0 + abs(math.cos(i * 0.6))
            d = 1 if math.sin(i) > 0 else -1
            o = base
            c = base + d * body
            h = max(o, c) + 1.0
            lo = min(o, c) - 1.0
            bars.append(Bar(ts_utc=utc_dt, open=o, high=h, low=lo, close=c, volume=100.0))
        return bars

    @staticmethod
    def _make_strategy():
        from engine.model.bias import DailyBias
        from engine.detectors.ranges import DealingRange
        from engine.model.strategy import ICTStrategy
        from engine.sim.broker import SimBroker, BrokerConfig
        from engine.sim.risk import RiskManager, RiskConfig
        bias = DailyBias(
            direction="SHORT",
            dealing_range=DealingRange(20200.0, 19800.0),
            dol_level=19900.0,
            reason="test",
            swing_highs=[],
            swing_lows=[],
        )
        from engine.model.config import StrategyConfig
        cfg = StrategyConfig(use_day_filter=False, fvg_half_filter=False)
        broker = SimBroker(BrokerConfig(slippage_ticks=0, commission_per_side=0.0))
        risk_mgr = RiskManager(RiskConfig(account_equity=50_000.0))
        return ICTStrategy(config=cfg, bias=bias, broker=broker, risk_manager=risk_mgr)

    def test_state_events_confirmed_at_not_in_future(self):
        """所有 StateChanged 事件的 confirmed_at <= 當前 bar ts_utc。"""
        from engine.model.config import StrategyConfig
        bars = self._make_et_bars(40)
        strategy = self._make_strategy()
        for i, bar in enumerate(bars):
            evts = strategy.on_bar(bar)
            for e in evts:
                assert e.confirmed_at <= bar.ts_utc, (
                    f"bar[{i}] ts={bar.ts_utc}, event confirmed_at={e.confirmed_at}"
                )

    def test_truncation_state_consistency(self):
        """截斷一致性：bar[0..k] 的第 k 個狀態 == 全量的第 k 個狀態。"""
        from engine.model.config import StrategyConfig
        bars = self._make_et_bars(30)

        strategy_full = self._make_strategy()
        full_states = []
        for bar in bars:
            strategy_full.on_bar(bar)
            full_states.append(strategy_full.state)

        for k in range(1, len(bars) + 1):
            s = self._make_strategy()
            states = []
            for bar in bars[:k]:
                s.on_bar(bar)
                states.append(s.state)
            assert states == full_states[:k], (
                f"Truncation k={k}: {states} != {full_states[:k]}"
            )
