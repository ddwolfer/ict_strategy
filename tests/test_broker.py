"""SimBroker 精確撮合規則測試。"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

from engine.core.types import Bar, TICK, POINT_VALUE
from engine.sim.orders import Bracket, Order
from engine.sim.broker import (
    BrokerConfig,
    OrderFilled,
    SimBroker,
    TradeClosed,
    TradeOpened,
)

UTC = timezone.utc


# ─── 工具函式 ────────────────────────────────────────────────────────────────

def _ts(i: int = 0) -> datetime:
    return datetime(2026, 5, 14, 14, 30, tzinfo=UTC) + timedelta(minutes=i)


def _bar(
    open_: float,
    high: float,
    low: float,
    close: float,
    i: int = 0,
) -> Bar:
    return Bar(ts_utc=_ts(i), open=open_, high=high, low=low, close=close, volume=0.0)


def _broker(slippage: int = 1, commission: float = 2.25) -> SimBroker:
    return SimBroker(BrokerConfig(slippage_ticks=slippage, commission_per_side=commission))


def _buy_bracket(
    entry_type: str,
    entry_price: float,
    stop: float,
    targets: list[tuple[float, int]],
    qty: int = 1,
) -> Bracket:
    order = Order(side="BUY", type=entry_type, price=entry_price, qty=qty)  # type: ignore[arg-type]
    return Bracket(entry=order, stop_price=stop, targets=targets)


def _sell_bracket(
    entry_type: str,
    entry_price: float,
    stop: float,
    targets: list[tuple[float, int]],
    qty: int = 1,
) -> Bracket:
    order = Order(side="SELL", type=entry_type, price=entry_price, qty=qty)  # type: ignore[arg-type]
    return Bracket(entry=order, stop_price=stop, targets=targets)


# ─── Buy LIMIT 成交規則 ──────────────────────────────────────────────────────

class TestBuyLimit:
    def test_gap_through_fills_at_open(self):
        """bar.open < limit → 以 open 成交（穿價）。"""
        broker = _broker()
        b = _buy_bracket("LIMIT", entry_price=100.0, stop=99.0, targets=[(101.0, 1)])
        broker.submit(b)
        events = broker.on_bar(_bar(open_=99.5, high=101.0, low=99.0, close=100.5, i=0))
        fills = [e for e in events if isinstance(e, OrderFilled)]
        assert len(fills) == 1
        assert fills[0].fill_price == 99.5   # open，不是 100.0

    def test_limit_touched_fills_at_price(self):
        """bar.open > limit & bar.low <= limit → 以 limit 價成交。"""
        broker = _broker()
        b = _buy_bracket("LIMIT", entry_price=100.0, stop=99.0, targets=[(101.0, 1)])
        broker.submit(b)
        events = broker.on_bar(_bar(open_=100.5, high=101.0, low=99.75, close=100.25, i=0))
        fills = [e for e in events if isinstance(e, OrderFilled)]
        assert len(fills) == 1
        assert fills[0].fill_price == 100.0

    def test_limit_not_reached(self):
        """low > limit → 不成交。"""
        broker = _broker()
        b = _buy_bracket("LIMIT", entry_price=100.0, stop=99.0, targets=[(101.0, 1)])
        broker.submit(b)
        events = broker.on_bar(_bar(open_=101.0, high=102.0, low=100.25, close=101.0, i=0))
        fills = [e for e in events if isinstance(e, OrderFilled)]
        assert fills == []

    def test_gap_through_exact_tick(self):
        """open 等於 limit → 以 open 成交。"""
        broker = _broker()
        b = _buy_bracket("LIMIT", entry_price=100.0, stop=99.0, targets=[(101.0, 1)])
        broker.submit(b)
        events = broker.on_bar(_bar(open_=100.0, high=101.0, low=99.5, close=100.5, i=0))
        fills = [e for e in events if isinstance(e, OrderFilled)]
        assert fills[0].fill_price == 100.0


# ─── Sell LIMIT 成交規則 ─────────────────────────────────────────────────────

class TestSellLimit:
    def test_gap_through_fills_at_open(self):
        """bar.open > limit → 以 open 成交（gap 穿價）。"""
        broker = _broker()
        b = _sell_bracket("LIMIT", entry_price=100.0, stop=101.0, targets=[(99.0, 1)])
        broker.submit(b)
        events = broker.on_bar(_bar(open_=100.5, high=101.0, low=99.5, close=100.0, i=0))
        fills = [e for e in events if isinstance(e, OrderFilled)]
        assert fills[0].fill_price == 100.5

    def test_limit_touched_fills_at_price(self):
        """open < limit & high >= limit → 以 limit 成交。"""
        broker = _broker()
        b = _sell_bracket("LIMIT", entry_price=100.0, stop=101.0, targets=[(99.0, 1)])
        broker.submit(b)
        events = broker.on_bar(_bar(open_=99.5, high=100.25, low=99.0, close=99.75, i=0))
        fills = [e for e in events if isinstance(e, OrderFilled)]
        assert fills[0].fill_price == 100.0


# ─── Buy STOP 成交規則 ───────────────────────────────────────────────────────

class TestBuyStop:
    def test_gap_through_fills_at_open_plus_slip(self):
        """bar.open >= stop → 以 open + slippage 成交。"""
        broker = _broker(slippage=1)   # 1 tick = 0.25
        b = _buy_bracket("STOP", entry_price=100.0, stop=99.0, targets=[(101.0, 1)])
        broker.submit(b)
        events = broker.on_bar(_bar(open_=100.5, high=101.0, low=99.5, close=100.5, i=0))
        fills = [e for e in events if isinstance(e, OrderFilled)]
        assert fills[0].fill_price == 100.5 + TICK    # 100.75

    def test_stop_triggered_fills_at_stop_plus_slip(self):
        """open < stop & high >= stop → 以 stop + slippage。"""
        broker = _broker(slippage=1)
        b = _buy_bracket("STOP", entry_price=100.0, stop=99.0, targets=[(101.0, 1)])
        broker.submit(b)
        events = broker.on_bar(_bar(open_=99.5, high=100.25, low=99.25, close=100.0, i=0))
        fills = [e for e in events if isinstance(e, OrderFilled)]
        assert fills[0].fill_price == 100.0 + TICK    # 100.25

    def test_stop_not_triggered(self):
        """high < stop → 不成交。"""
        broker = _broker()
        b = _buy_bracket("STOP", entry_price=100.0, stop=99.0, targets=[(101.0, 1)])
        broker.submit(b)
        events = broker.on_bar(_bar(open_=98.0, high=99.75, low=97.5, close=98.5, i=0))
        fills = [e for e in events if isinstance(e, OrderFilled)]
        assert fills == []


# ─── Sell STOP 成交規則 ──────────────────────────────────────────────────────

class TestSellStop:
    def test_gap_through_fills_at_open_minus_slip(self):
        """bar.open <= stop → 以 open - slippage 成交。"""
        broker = _broker(slippage=1)
        b = _sell_bracket("STOP", entry_price=100.0, stop=101.0, targets=[(99.0, 1)])
        broker.submit(b)
        events = broker.on_bar(_bar(open_=99.5, high=100.0, low=99.0, close=99.5, i=0))
        fills = [e for e in events if isinstance(e, OrderFilled)]
        assert fills[0].fill_price == 99.5 - TICK     # 99.25

    def test_stop_triggered_fills_at_stop_minus_slip(self):
        """open > stop & low <= stop → 以 stop - slippage。"""
        broker = _broker(slippage=1)
        b = _sell_bracket("STOP", entry_price=100.0, stop=101.0, targets=[(99.0, 1)])
        broker.submit(b)
        events = broker.on_bar(_bar(open_=100.5, high=101.0, low=99.75, close=100.0, i=0))
        fills = [e for e in events if isinstance(e, OrderFilled)]
        assert fills[0].fill_price == 100.0 - TICK    # 99.75


# ─── MARKET 單 ───────────────────────────────────────────────────────────────

class TestMarket:
    def test_market_buy_fills_at_open_plus_slip(self):
        """MARKET BUY：本棒（即提交後第一根）open + slippage。"""
        broker = _broker(slippage=1)
        b = _buy_bracket("MARKET", entry_price=0.0, stop=99.0, targets=[(101.0, 1)])
        broker.submit(b)
        events = broker.on_bar(_bar(open_=100.0, high=101.0, low=99.5, close=100.5, i=0))
        fills = [e for e in events if isinstance(e, OrderFilled)]
        assert fills[0].fill_price == 100.0 + TICK   # 100.25

    def test_market_sell_fills_at_open_minus_slip(self):
        """MARKET SELL：本棒 open - slippage。"""
        broker = _broker(slippage=1)
        b = _sell_bracket("MARKET", entry_price=0.0, stop=101.0, targets=[(99.0, 1)])
        broker.submit(b)
        events = broker.on_bar(_bar(open_=100.0, high=100.5, low=99.0, close=99.5, i=0))
        fills = [e for e in events if isinstance(e, OrderFilled)]
        assert fills[0].fill_price == 100.0 - TICK   # 99.75


# ─── 停損優先規則（規則 4）───────────────────────────────────────────────────

class TestStopBeforeTarget:
    def test_same_bar_stop_and_target_stop_wins(self):
        """同一根 K 棒同時觸及停損與停利 → 停損優先，ambiguous=True。

        設計：
          進場棒（bar 0）：open=100.5, high=100.75, low=99.75 → LIMIT @100 成交，
            同棒 high=100.75 < 101(target)、low=99.75 > 99(stop) → 不觸發
          停損+停利棒（bar 1）：low=98.5 <= 99(stop) & high=101.5 >= 101(target)
        """
        broker = _broker(slippage=0)
        b = _buy_bracket("LIMIT", entry_price=100.0, stop=99.0, targets=[(101.0, 1)])
        broker.submit(b)
        # bar 0：進場，high/low 均不觸及停損或停利
        broker.on_bar(_bar(open_=100.5, high=100.75, low=99.75, close=100.25, i=0))
        assert broker.position is not None, "should have position after entry"
        # bar 1：同時觸及停損(low=98.5<99)與停利(high=101.5>101)
        events = broker.on_bar(_bar(open_=100.0, high=101.5, low=98.5, close=100.0, i=1))
        closed = [e for e in events if isinstance(e, TradeClosed)]
        assert len(closed) == 1
        trade = closed[0].trade
        assert trade.exit_reason == "STOP"
        assert trade.ambiguous is True
        assert trade.pnl_pts < 0   # 停損 → 虧損

    def test_ambiguous_flag_present_in_trade(self):
        """ambiguous trade 標記進入 broker.trades。"""
        broker = _broker(slippage=0)
        b = _buy_bracket("LIMIT", entry_price=100.0, stop=99.0, targets=[(101.0, 1)])
        broker.submit(b)
        broker.on_bar(_bar(open_=100.5, high=100.75, low=99.75, close=100.25, i=0))
        broker.on_bar(_bar(open_=100.0, high=101.5, low=98.5, close=100.0, i=1))
        assert broker.trades[-1].ambiguous is True


# ─── 進場當根掃到停損（規則 5）──────────────────────────────────────────────

class TestEntryBarStopSweep:
    def test_entry_bar_sweeps_stop_immediately(self):
        """進場當根 low 觸及停損 → 同棒止損，ambiguous=True。"""
        broker = _broker(slippage=0)
        # 進場 BUY LIMIT @100，停損 @99，停利 @101
        # 進場棒：open=100.5, low=98.5 → 穿價進場(open=100.5<100? No, 100.5>100)
        # → limit: low=98.5 <= 100 → 以 100 進場；同棒 low=98.5 <= 99(stop) → 停損
        b = _buy_bracket("LIMIT", entry_price=100.0, stop=99.0, targets=[(101.0, 1)])
        broker.submit(b)
        events = broker.on_bar(_bar(open_=100.5, high=101.0, low=98.5, close=99.5, i=0))
        closed = [e for e in events if isinstance(e, TradeClosed)]
        assert len(closed) == 1
        assert closed[0].trade.exit_reason == "STOP"
        assert closed[0].trade.ambiguous is True

    def test_entry_bar_no_stop_sweep(self):
        """進場當根 low 未觸及停損、high 未觸及停利 → 部位保留。"""
        broker = _broker(slippage=0)
        b = _buy_bracket("LIMIT", entry_price=100.0, stop=99.0, targets=[(101.0, 1)])
        broker.submit(b)
        # high=100.75 < 101(target), low=99.25 > 99(stop) → 不觸發任何出場
        events = broker.on_bar(_bar(open_=100.5, high=100.75, low=99.25, close=100.25, i=0))
        closed = [e for e in events if isinstance(e, TradeClosed)]
        assert closed == []
        assert broker.position is not None


# ─── Flatten（EOD）───────────────────────────────────────────────────────────

class TestFlatten:
    def test_flatten_closes_at_close(self):
        """flatten 以 bar.close 平倉，reason=EOD。"""
        broker = _broker(slippage=0, commission=0)
        b = _buy_bracket("LIMIT", entry_price=100.0, stop=99.0, targets=[(102.0, 1)])
        broker.submit(b)
        # 進場
        broker.on_bar(_bar(open_=100.5, high=101.0, low=99.75, close=100.25, i=0))
        assert broker.position is not None
        # EOD flatten
        eod_bar = _bar(open_=100.25, high=100.5, low=100.0, close=100.75, i=1)
        events = broker.flatten(eod_bar, reason="EOD")
        closed = [e for e in events if isinstance(e, TradeClosed)]
        assert len(closed) == 1
        assert closed[0].trade.exit_reason == "EOD"
        assert closed[0].trade.exit_fills[-1].price == 100.75
        assert broker.position is None

    def test_flatten_no_position_returns_empty(self):
        broker = _broker()
        events = broker.flatten(_bar(100.0, 101.0, 99.0, 100.0), reason="EOD")
        assert events == []


# ─── 停利分批出場 ────────────────────────────────────────────────────────────

class TestPartialTargets:
    def test_first_target_reduces_qty(self):
        """第一個停利成交後部位剩餘，第二個停利成交後全倉出場。"""
        broker = _broker(slippage=0, commission=0)
        # 2 口，分批：101 出 1 口，102 出 1 口
        b = _buy_bracket("LIMIT", entry_price=100.0, stop=99.0,
                         targets=[(101.0, 1), (102.0, 1)], qty=2)
        broker.submit(b)
        # 進場棒
        broker.on_bar(_bar(open_=100.5, high=100.75, low=99.75, close=100.25, i=0))
        assert broker.position is not None
        assert broker.position.qty == 2
        # 第一個停利觸及
        events = broker.on_bar(_bar(open_=100.5, high=101.25, low=100.25, close=101.0, i=1))
        closed = [e for e in events if isinstance(e, TradeClosed)]
        assert closed == []
        assert broker.position is not None
        assert broker.position.qty == 1
        # 第二個停利觸及
        events = broker.on_bar(_bar(open_=101.0, high=102.25, low=100.75, close=102.0, i=2))
        closed = [e for e in events if isinstance(e, TradeClosed)]
        assert len(closed) == 1
        assert closed[0].trade.exit_reason == "TARGET"
        assert broker.position is None

    def test_r_multiple_partial_targets(self):
        """分批出場的 R 倍數以加權平均出場價計算。

        進場 100，停損 99（1R = 1 點），兩目標 101 / 103 各 1 口。
        加權出場 = (101+103)/2 = 102 → pnl_pts = 2×2 = 4，R = 2.0
        """
        broker = _broker(slippage=0, commission=0)
        b = _buy_bracket("LIMIT", entry_price=100.0, stop=99.0,
                         targets=[(101.0, 1), (103.0, 1)], qty=2)
        broker.submit(b)
        broker.on_bar(_bar(open_=100.5, high=100.75, low=99.75, close=100.25, i=0))
        broker.on_bar(_bar(open_=100.5, high=101.25, low=100.25, close=101.0, i=1))
        broker.on_bar(_bar(open_=101.0, high=103.25, low=100.75, close=103.0, i=2))
        trade = broker.trades[-1]
        # 加權出場 = 102, pnl_pts = (102 - 100) * 2 = 4
        assert trade.pnl_pts == pytest.approx(4.0)
        assert trade.r_multiple == pytest.approx(2.0)


# ─── Equity Curve ────────────────────────────────────────────────────────────

class TestEquityCurve:
    def test_equity_curve_accumulates_with_commission(self):
        """equity_curve 正確累計已實現損益（含手續費）。"""
        commission = 2.25
        broker = _broker(slippage=0, commission=commission)

        # 交易 1：買 100，停利 101，1 口 → pnl = 1×20 - 2×2.25 = 20 - 4.5 = 15.5
        b1 = _buy_bracket("LIMIT", entry_price=100.0, stop=99.0, targets=[(101.0, 1)])
        broker.submit(b1)
        broker.on_bar(_bar(open_=100.5, high=100.75, low=99.75, close=100.25, i=0))
        broker.on_bar(_bar(open_=100.5, high=101.25, low=100.25, close=101.0, i=1))
        assert len(broker.equity_curve) == 1
        assert broker.equity_curve[0] == pytest.approx(15.5)

        # 交易 2：買 102，停損 101（虧 1 點）→ pnl = -1×20 - 4.5 = -24.5
        # bar 2：進場棒，low=101.75 <= 102 → fills@102；high=102.5 < 103(target)，low=101.75 > 101(stop) → 不出場
        # bar 3：low=100.75 <= 101(stop) → 停損@101，pnl = (101-102)×20 - 4.5 = -20 - 4.5 = -24.5
        b2 = _buy_bracket("LIMIT", entry_price=102.0, stop=101.0, targets=[(103.0, 1)])
        broker.submit(b2)
        broker.on_bar(_bar(open_=102.5, high=102.5, low=101.75, close=102.25, i=2))
        broker.on_bar(_bar(open_=102.0, high=102.5, low=100.75, close=101.5, i=3))
        assert len(broker.equity_curve) == 2
        assert broker.equity_curve[1] == pytest.approx(15.5 - 24.5)

    def test_equity_curve_empty_before_any_trade(self):
        broker = _broker()
        assert broker.equity_curve == []


# ─── 取消訂單 ────────────────────────────────────────────────────────────────

class TestCancel:
    def test_cancel_prevents_fill(self):
        broker = _broker()
        b = _buy_bracket("LIMIT", entry_price=100.0, stop=99.0, targets=[(101.0, 1)])
        broker.submit(b)
        broker.cancel(b.id)
        events = broker.on_bar(_bar(open_=100.5, high=101.0, low=99.5, close=100.25, i=0))
        fills = [e for e in events if isinstance(e, OrderFilled)]
        assert fills == []


# ─── 多棒連續流程 ────────────────────────────────────────────────────────────

class TestMultiBarFlow:
    def test_full_win_cycle(self):
        """完整流程：提交 → 進場 → 停利 → 結算。"""
        broker = _broker(slippage=0, commission=0)
        b = _buy_bracket("LIMIT", entry_price=100.0, stop=99.0, targets=[(101.0, 1)])
        broker.submit(b)

        # 棒 0：不觸及
        events0 = broker.on_bar(_bar(open_=100.5, high=100.75, low=100.25, close=100.5, i=0))
        assert all(not isinstance(e, OrderFilled) for e in events0)

        # 棒 1：進場（low=99.75 <= 100 → fills@100；high=100.75 < 101，low=99.75 > 99 → 不出場）
        events1 = broker.on_bar(_bar(open_=100.75, high=100.75, low=99.75, close=100.25, i=1))
        assert any(isinstance(e, TradeOpened) for e in events1)

        # 棒 2：停利
        events2 = broker.on_bar(_bar(open_=100.5, high=101.25, low=100.0, close=101.0, i=2))
        closed = [e for e in events2 if isinstance(e, TradeClosed)]
        assert len(closed) == 1
        assert closed[0].trade.r_multiple == pytest.approx(1.0)

    def test_full_loss_cycle(self):
        """完整流程：提交 → 進場 → 停損 → 結算。"""
        broker = _broker(slippage=0, commission=0)
        b = _buy_bracket("LIMIT", entry_price=100.0, stop=99.0, targets=[(102.0, 1)])
        broker.submit(b)
        broker.on_bar(_bar(open_=100.5, high=101.0, low=99.75, close=100.25, i=0))
        events = broker.on_bar(_bar(open_=100.0, high=100.5, low=98.5, close=99.0, i=1))
        closed = [e for e in events if isinstance(e, TradeClosed)]
        assert len(closed) == 1
        assert closed[0].trade.exit_reason == "STOP"
        assert closed[0].trade.r_multiple == pytest.approx(-1.0)

    def test_position_is_none_after_close(self):
        broker = _broker(slippage=0, commission=0)
        b = _buy_bracket("LIMIT", entry_price=100.0, stop=99.0, targets=[(101.0, 1)])
        broker.submit(b)
        broker.on_bar(_bar(open_=100.5, high=101.0, low=99.75, close=100.25, i=0))
        broker.on_bar(_bar(open_=100.5, high=101.25, low=100.0, close=101.0, i=1))
        assert broker.position is None


class TestMultiTargetSameBar:
    """一根 K 棒掃過多個停利目標時必須全部成交。"""

    def test_one_bar_sweeps_tp1_and_tp2(self):
        broker = _broker(slippage=0, commission=0.0)
        b = _buy_bracket("LIMIT", entry_price=100.0, stop=95.0,
                         targets=[(105.0, 1), (110.0, 1)], qty=2)
        broker.submit(b)
        # 進場棒
        broker.on_bar(_bar(open_=101.0, high=101.5, low=100.0, close=101.0, i=0))
        assert broker.position is not None
        # 一根大陽棒同時掃過 TP1 與 TP2
        broker.on_bar(_bar(open_=102.0, high=112.0, low=101.5, close=111.0, i=1))
        assert broker.position is None, "兩個目標都該成交並平倉"
        trade = broker.trades[-1]
        assert trade.exit_reason == "TARGET"
        prices = [pf.price for pf in trade.exit_fills]
        assert prices == [105.0, 110.0]
