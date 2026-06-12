"""SimBroker — 逐根 K 棒保守撮合引擎。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Union

from engine.core.types import Bar, TICK, POINT_VALUE
from engine.sim.orders import (
    Bracket, ExitReason, Order, PartialFill, Position, Side, Trade,
)


# ─── 設定 ────────────────────────────────────────────────────────────────────

@dataclass
class BrokerConfig:
    slippage_ticks: int = 1                  # STOP / MARKET 滑價（tick 數）
    commission_per_side: float = 2.25        # 每口每邊美元
    point_value: float = POINT_VALUE
    tick_size: float = TICK


# ─── 事件 ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class OrderFilled:
    order_id: str
    fill_price: float
    qty: int
    ts: datetime

@dataclass(frozen=True)
class TradeOpened:
    bracket_id: str
    entry_price: float
    qty: int
    ts: datetime

@dataclass(frozen=True)
class TradeClosed:
    bracket_id: str
    trade: Trade
    ts: datetime

@dataclass(frozen=True)
class OrderCancelled:
    order_id: str
    ts: datetime

BrokerEvent = Union[OrderFilled, TradeOpened, TradeClosed, OrderCancelled]


# ─── 輔助函式 ────────────────────────────────────────────────────────────────

def _round_tick(price: float, tick: float) -> float:
    """將價格 round 至最近 tick。"""
    return round(round(price / tick) * tick, 10)


def _slippage_amount(side: Side, ticks: int, tick: float) -> float:
    """Buy STOP/MARKET 滑價為正（成交更差）；Sell 為負。"""
    return ticks * tick * (1 if side == "BUY" else -1)


# ─── 內部 bracket 狀態 ───────────────────────────────────────────────────────

@dataclass
class _BracketState:
    bracket: Bracket
    entry_filled: bool = False
    cancelled: bool = False


# ─── SimBroker ───────────────────────────────────────────────────────────────

class SimBroker:
    """逐根 K 棒保守撮合引擎。

    保守成交規則（回測誠實性核心）：
    1. Buy LIMIT @P：open <= P → open 成交；否則 low <= P → P 成交。
       Sell LIMIT @P：open >= P → open；否則 high >= P → P。
    2. Buy STOP @P：open >= P → open + slip；否則 high >= P → P + slip。
       Sell STOP @P：open <= P → open - slip；否則 low <= P → P - slip。
    3. MARKET：本棒 open ± slippage（已是「下一根」語意，由呼叫方保證）。
    4. 同一根同時觸及停損與停利 → 停損優先，標記 ambiguous=True。
    5. 進場成交當根若掃到停損 → 視為當根止損，標記 ambiguous=True。
    6. 手續費：每邊固定美元（BrokerConfig.commission_per_side）。
    7. 所有成交價 round 到 tick。
    """

    def __init__(self, config: BrokerConfig | None = None) -> None:
        self.cfg = config or BrokerConfig()
        # bracket_id -> _BracketState（尚未進場的 bracket）
        self._pending_brackets: dict[str, _BracketState] = {}
        # 待下一根 open 撮合的 MARKET 進場單（bracket_id -> Bracket）
        self._market_queue: list[tuple[str, Bracket]] = []

        self.position: Position | None = None
        self._current_trade: Trade | None = None
        self.trades: list[Trade] = []
        self.equity_curve: list[float] = []
        self._equity: float = 0.0   # 累計已實現損益（含手續費扣除）

    # ── 公開介面 ─────────────────────────────────────────────────────────────

    def submit(self, order_or_bracket: Order | Bracket) -> str:
        """提交訂單或 bracket，回傳 id。

        注意：SimBroker 目前僅支援 Bracket 模式（進場 + 停損 + 停利）。
        裸 Order（無 bracket）不提供退出管理，建議使用 Bracket。
        """
        if isinstance(order_or_bracket, Bracket):
            b = order_or_bracket
            if b.entry.type == "MARKET":
                self._market_queue.append((b.id, b))
            else:
                self._pending_brackets[b.id] = _BracketState(bracket=b)
            return b.id
        else:
            # 裸單：暫不實作，若真的需要可擴充
            raise NotImplementedError("裸 Order 尚未支援，請使用 Bracket 封裝")

    def cancel(self, bracket_id: str) -> None:
        """取消尚未進場的 bracket（已進場者忽略）。"""
        state = self._pending_brackets.get(bracket_id)
        if state and not state.entry_filled:
            state.cancelled = True
            state.bracket.entry.status = "CANCELLED"

    def on_bar(self, bar: Bar) -> list[BrokerEvent]:
        """處理一根 K 棒，回傳本棒觸發的事件列表。

        執行順序：
        a) 先以本棒 open 撮合上一根排隊的 MARKET 單。
        b) 若已有持倉，檢查停損 / 停利（保守規則）。
        c) 若無持倉，掃描 pending brackets 嘗試進場；
           進場成功後立刻在同一棒範圍檢查停損（規則 5）。
        """
        events: list[BrokerEvent] = []

        # (a) MARKET 進場單（以本棒 open）
        events.extend(self._fill_market_queue(bar))

        # (b) 已持倉時：停損 / 停利
        if self.position is not None:
            events.extend(self._check_exit(bar, same_bar_as_entry=False))

        # (c) 無持倉時：掃描 pending brackets
        if self.position is None:
            events.extend(self._try_fill_brackets(bar))

        # 更新 unrealized PnL（不產生事件）
        if self.position is not None:
            self.position.update_unrealized(bar.close, self.cfg.point_value)

        return events

    def flatten(self, bar: Bar, reason: ExitReason = "EOD") -> list[BrokerEvent]:
        """以該根收盤價強制平倉。"""
        if self.position is None:
            return []
        fill_price = _round_tick(bar.close, self.cfg.tick_size)
        return self._close_remaining(fill_price, bar.ts_utc, reason, ambiguous=False)

    # ── 內部：MARKET 撮合 ────────────────────────────────────────────────────

    def _fill_market_queue(self, bar: Bar) -> list[BrokerEvent]:
        events: list[BrokerEvent] = []
        queue = self._market_queue[:]
        self._market_queue.clear()
        for bid, bracket in queue:
            entry = bracket.entry
            slip = _slippage_amount(entry.side, self.cfg.slippage_ticks, self.cfg.tick_size)
            fill = _round_tick(bar.open + slip, self.cfg.tick_size)
            events.extend(self._open_position(bracket, fill, bar.ts_utc))
            # 進場當根立刻檢查停損（規則 5）
            if self.position is not None:
                events.extend(self._check_exit(bar, same_bar_as_entry=True))
        return events

    # ── 內部：LIMIT / STOP 進場撮合 ─────────────────────────────────────────

    def _try_fill_brackets(self, bar: Bar) -> list[BrokerEvent]:
        events: list[BrokerEvent] = []
        for state in list(self._pending_brackets.values()):
            if state.cancelled or state.entry_filled:
                continue
            # 已有持倉時不再嘗試進場（單部位模式）
            if self.position is not None:
                break
            fill = self._entry_fill_price(state.bracket.entry, bar)
            if fill is None:
                continue
            state.entry_filled = True
            entry = state.bracket.entry
            entry.status = "FILLED"
            entry.fill_price = fill
            entry.filled_at = bar.ts_utc
            events.extend(self._open_position(state.bracket, fill, bar.ts_utc))
            # 規則 5：進場當根立刻檢查停損
            if self.position is not None:
                events.extend(self._check_exit(bar, same_bar_as_entry=True))
        return events

    def _entry_fill_price(self, order: Order, bar: Bar) -> float | None:
        """判斷進場單在本棒是否成交，回傳成交價（round tick）或 None。"""
        p = order.price
        tick = self.cfg.tick_size
        slip = _slippage_amount(order.side, self.cfg.slippage_ticks, tick)

        if order.type == "LIMIT":
            if order.side == "BUY":
                if bar.open <= p:
                    return _round_tick(bar.open, tick)
                if bar.low <= p:
                    return _round_tick(p, tick)
            else:  # SELL LIMIT
                if bar.open >= p:
                    return _round_tick(bar.open, tick)
                if bar.high >= p:
                    return _round_tick(p, tick)

        elif order.type == "STOP":
            if order.side == "BUY":
                if bar.open >= p:
                    return _round_tick(bar.open + slip, tick)
                if bar.high >= p:
                    return _round_tick(p + slip, tick)
            else:  # SELL STOP
                if bar.open <= p:
                    return _round_tick(bar.open + slip, tick)
                if bar.low <= p:
                    return _round_tick(p + slip, tick)

        return None

    # ── 內部：開部位 ──────────────────────────────────────────────────────────

    def _open_position(
        self,
        bracket: Bracket,
        fill: float,
        ts: datetime,
    ) -> list[BrokerEvent]:
        entry = bracket.entry
        stop_dist = abs(fill - bracket.stop_price)
        self.position = Position(
            side=entry.side,
            qty=entry.qty,
            avg_entry=fill,
            stop_price=bracket.stop_price,
            remaining_targets=list(bracket.targets),
            bracket_id=bracket.id,
        )
        self._current_trade = Trade(
            side=entry.side,
            entry_price=fill,
            entry_time=ts,
            qty=entry.qty,
            initial_stop_distance=stop_dist,
            bracket_id=bracket.id,
        )
        return [
            OrderFilled(order_id=entry.id, fill_price=fill, qty=entry.qty, ts=ts),
            TradeOpened(bracket_id=bracket.id, entry_price=fill, qty=entry.qty, ts=ts),
        ]

    # ── 內部：停損 / 停利判斷 ────────────────────────────────────────────────

    def _check_exit(self, bar: Bar, same_bar_as_entry: bool) -> list[BrokerEvent]:
        """判斷停損/停利，回傳本棒產生的平倉事件。"""
        if self.position is None or self._current_trade is None:
            return []

        pos = self.position
        tick = self.cfg.tick_size

        stop_hit = (
            bar.low <= pos.stop_price if pos.side == "BUY"
            else bar.high >= pos.stop_price
        )

        def _first_target_hit() -> bool:
            if not pos.remaining_targets:
                return False
            price, _ = pos.remaining_targets[0]
            return bar.high >= price if pos.side == "BUY" else bar.low <= price

        # 規則 4 & 5：同根觸及 or 進場當根停損 → ambiguous
        ambiguous = (stop_hit and _first_target_hit()) or (same_bar_as_entry and stop_hit)

        if stop_hit:
            fill = _round_tick(pos.stop_price, tick)
            self._current_trade.ambiguous = ambiguous
            return self._close_remaining(fill, bar.ts_utc, "STOP", ambiguous=ambiguous)

        # 同一根可連續成交多個停利目標（1 分 K 位移棒常一根掃過 TP1+TP2）
        while _first_target_hit():
            target_price, target_qty = pos.remaining_targets[0]
            fill = _round_tick(target_price, tick)
            pf = PartialFill(price=fill, qty=target_qty, ts=bar.ts_utc, reason="TARGET")
            self._current_trade.exit_fills.append(pf)
            pos.qty -= target_qty
            pos.remaining_targets = pos.remaining_targets[1:]

            # 分批已實現損益
            if pos.side == "BUY":
                pts = (fill - pos.avg_entry) * target_qty
            else:
                pts = (pos.avg_entry - fill) * target_qty
            commission = self.cfg.commission_per_side * target_qty * 2
            pos.realized_pnl_pts += pts
            pos.realized_pnl_usd += pts * self.cfg.point_value - commission

            if pos.qty <= 0:
                self._current_trade.exit_reason = "TARGET"
                return self._finalize_current_trade(bar.ts_utc)

        return []

    # ── 內部：關閉剩餘部位 ───────────────────────────────────────────────────

    def _close_remaining(
        self,
        fill_price: float,
        ts: datetime,
        reason: ExitReason,
        ambiguous: bool,
    ) -> list[BrokerEvent]:
        """以 fill_price 平掉 position 剩餘 qty，完成 Trade。"""
        if self.position is None or self._current_trade is None:
            return []
        pos = self.position
        trade = self._current_trade

        pf = PartialFill(price=fill_price, qty=pos.qty, ts=ts, reason=reason)
        trade.exit_fills.append(pf)
        trade.exit_reason = reason
        trade.ambiguous = ambiguous
        pos.qty = 0
        return self._finalize_current_trade(ts)

    def _finalize_current_trade(self, ts: datetime) -> list[BrokerEvent]:
        """計算損益、推入 trades、更新 equity curve，清除持倉。"""
        if self._current_trade is None:
            return []
        trade = self._current_trade
        trade.close(self.cfg.point_value, self.cfg.commission_per_side)
        self.trades.append(trade)
        self._equity += trade.pnl_usd
        self.equity_curve.append(self._equity)
        bid = trade.bracket_id
        event = TradeClosed(bracket_id=bid, trade=trade, ts=ts)
        self.position = None
        self._current_trade = None
        return [event]
