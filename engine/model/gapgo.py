"""GapGoStrategy — 順缺口日內策略狀態機（1 分 K）。

規則依據：docs/strategy/ny-window-research-spec.md §4 F3（預登記，零自由參數）。

  觸發：|今日 09:30 開盤 − 昨日 RTH 收盤| ≥ gap_atr_min × 昨日日線 ATR(14)
  確認：09:30–09:34 首根 5 分 K 收盤順缺口方向（gap up 且 m5_close > open_930）
  進場：確認棒（09:34 棒）收盤後市價 → 次棒（09:35）open 成交
  停損：5 分 K 對側（多 = m5_low、空 = m5_high），無移動
  停利：無；flatten_time 強平（win_eod=15:55 / win_flat=11:30）
  每日最多 1 筆。

無前視保證：gap 與 ATR 只用 history_bars（嚴格昨日以前的完整時段資料）
與今日 09:30 後已收盤的 K 棒。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Literal

from engine.core.types import Bar
from engine.core.sessions import _to_et, trading_date
from engine.model.config import StrategyConfig
from engine.model.bias import DailyBias
from engine.sim.broker import SimBroker
from engine.sim.risk import RiskManager, SessionState
from engine.sim.orders import Bracket, Order, Trade


GapGoState = Literal["IDLE", "CHECK_GAP", "BUILD_M5", "IN_POSITION", "DONE"]


@dataclass(frozen=True)
class StateChanged:
    confirmed_at: datetime
    prev_state: GapGoState
    new_state: GapGoState
    waiting_for: str
    detail: dict


def _parse_hm(s: str) -> time:
    h, m = int(s[:2]), int(s[3:])
    return time(h, m)


def _daily_context(history_bars: list[Bar]) -> tuple[float | None, float | None]:
    """從嚴格過去的 bars 算（昨日 RTH 收盤, 昨日為止 ATR(14)）。

    ATR 用完整時段日線高低收（與 runner 的 ATR 閘門、daily_features 一致）。
    資料不足（< 15 個歷史交易日）回傳 (None, None) → 當日不交易。
    """
    if not history_bars:
        return None, None

    days: dict = {}
    for b in history_bars:
        days.setdefault(trading_date(b.ts_utc), []).append(b)
    ordered = sorted(days.keys())
    if len(ordered) < 15:
        return None, None

    # 昨日 RTH 收盤：往回找最近一個有 RTH（09:30–15:59 ET）K 棒的日子
    prev_rth_close: float | None = None
    for d in reversed(ordered):
        rth = [b for b in days[d]
               if time(9, 30) <= _to_et(b.ts_utc).time() < time(16, 0)]
        if rth:
            prev_rth_close = max(rth, key=lambda b: b.ts_utc).close
            break
    if prev_rth_close is None:
        return None, None

    # ATR(14)：TR 需要前日收盤，從第 2 個歷史日開始
    daily = [(d,
              max(b.high for b in days[d]),
              min(b.low for b in days[d]),
              max(days[d], key=lambda b: b.ts_utc).close) for d in ordered]
    trs: list[float] = []
    for k in range(1, len(daily)):
        _d, h, l, _c = daily[k]
        c_prev = daily[k - 1][3]
        trs.append(max(h - l, abs(h - c_prev), abs(l - c_prev)))
    if len(trs) < 14:
        return None, None
    atr14 = sum(trs[-14:]) / 14.0
    return prev_rth_close, atr14


class GapGoStrategy:
    """Gap-Go 順缺口狀態機（介面與 ORBStrategy 相同）。"""

    def __init__(
        self,
        config: StrategyConfig,
        bias: DailyBias,
        broker: SimBroker,
        risk_manager: RiskManager,
        history_bars: list[Bar] | None = None,
        es_bars: dict | None = None,   # 介面相容，不使用
    ) -> None:
        self.config = config
        self.bias = bias
        self.broker = broker
        self.risk = risk_manager

        self._state: GapGoState = "IDLE"
        self._prev_rth_close, self._atr14 = _daily_context(history_bars or [])

        self._open_930: float | None = None
        self._direction: str | None = None      # "LONG" | "SHORT"
        self._m5_high: float | None = None
        self._m5_low: float | None = None
        self._m5_close: float | None = None
        self._m5_last_hm: int = -1

        self._pending_bracket_id: str | None = None
        self._flatten_time_t: time = _parse_hm(config.flatten_time)

        # decision_log 相容
        self.stop_moves: dict[str, list[dict]] = {}
        self.bracket_targets: dict[str, list[tuple[float, int]]] = {}
        self.closed_trades: list[Trade] = []
        self.state_timeline: list[StateChanged] = []

        self._session_state = SessionState()
        self._events: list[StateChanged] = []

    @property
    def state(self) -> GapGoState:
        return self._state

    # ── 主循環 ───────────────────────────────────────────────────────────────

    def on_bar(self, bar: Bar) -> list[StateChanged]:
        self._events = []
        et = _to_et(bar.ts_utc)
        t = et.time()
        hm = t.hour * 60 + t.minute

        # broker 事件（停損成交等）
        for bev in self.broker.on_bar(bar):
            self._handle_broker_event(bev, bar)

        if self._state == "DONE":
            return self._events

        # 強平時間
        if t >= self._flatten_time_t:
            if self._state == "IN_POSITION":
                self.broker.flatten(bar, reason="EOD")
                self._transition("DONE", bar,
                                 f"強平（{self.config.flatten_time} ET）", {})
            elif self._state != "IDLE":
                self._transition("DONE", bar, "交易時窗結束", {})
            return self._events

        # 09:30 首棒：評估缺口觸發
        if self._state == "IDLE" and hm >= 570:
            self._open_930 = bar.open
            self._eval_gap(bar)
            # 觸發成立時，這根棒（09:30）同時是 5 分 K 的第一根
            if self._state == "BUILD_M5":
                self._accumulate_m5(bar, hm)
            return self._events

        if self._state == "BUILD_M5":
            if hm <= 574:
                self._accumulate_m5(bar, hm)
                if hm == 574:                    # 09:34 棒收盤 = 5 分 K 完成
                    self._decide_entry(bar)
            else:                                 # 資料缺棒：用已累積的決策
                self._decide_entry(bar)
            return self._events

        return self._events

    # ── 缺口評估 ─────────────────────────────────────────────────────────────

    def _eval_gap(self, bar: Bar) -> None:
        if self._prev_rth_close is None or self._atr14 is None or self._atr14 <= 0:
            self._transition("DONE", bar, "歷史資料不足（需 15 個交易日算 ATR）", {})
            return
        gap = self._open_930 - self._prev_rth_close
        thr = self.config.gap_atr_min * self._atr14
        if abs(gap) < thr:
            self._transition("DONE", bar,
                             f"非缺口日（|gap|={abs(gap):.1f} < {thr:.1f} pt）",
                             {"gap": gap, "atr14": self._atr14})
            return
        self._direction = "LONG" if gap > 0 else "SHORT"
        self._transition("BUILD_M5", bar,
                         f"缺口觸發 {self._direction}（gap={gap:+.1f} pt，"
                         f"ATR14={self._atr14:.1f}），等 5 分 K 確認",
                         {"gap": gap, "atr14": self._atr14})

    def _accumulate_m5(self, bar: Bar, hm: int) -> None:
        if self._m5_high is None or bar.high > self._m5_high:
            self._m5_high = bar.high
        if self._m5_low is None or bar.low < self._m5_low:
            self._m5_low = bar.low
        if hm > self._m5_last_hm:
            self._m5_close = bar.close
            self._m5_last_hm = hm

    # ── 進場決策（09:34 棒收盤）───────────────────────────────────────────────

    def _decide_entry(self, bar: Bar) -> None:
        if self._m5_close is None or self._open_930 is None:
            self._transition("DONE", bar, "5 分 K 資料不足", {})
            return

        long_ok = self._direction == "LONG" and self._m5_close > self._open_930
        short_ok = self._direction == "SHORT" and self._m5_close < self._open_930
        if not (long_ok or short_ok):
            self._transition("DONE", bar,
                             f"5 分 K 未順向確認（close={self._m5_close:.2f} vs "
                             f"open={self._open_930:.2f}），當日放棄", {})
            return

        if not self.risk.can_trade(self._session_state):
            self._transition("DONE", bar, "風控限制，停手", {})
            return

        stop_px = self._m5_low if long_ok else self._m5_high
        approx_entry = self._m5_close
        stop_dist = abs(approx_entry - stop_px)

        if stop_dist < self.config.min_stop_points:
            self._transition("DONE", bar,
                             f"停損距 {stop_dist:.2f} pt < 下限，放棄", {})
            return
        if stop_dist > self.config.max_stop_points:
            self._transition("DONE", bar,
                             f"停損距 {stop_dist:.2f} pt > 上限，放棄", {})
            return

        qty = int(self.risk.size_for(stop_dist))
        if qty < 1:
            self._transition("DONE", bar,
                             f"放棄：停損 {stop_dist:.2f} pt 開不出 1 口",
                             {"stop_dist": stop_dist, "qty": 0})
            return

        side = "BUY" if long_ok else "SELL"
        order = Order(side=side, type="MARKET", qty=qty, price=0.0)  # type: ignore[arg-type]
        bracket = Bracket(entry=order, stop_price=stop_px, targets=[])
        self._pending_bracket_id = self.broker.submit(bracket)
        self.bracket_targets[self._pending_bracket_id] = []

        self._transition("IN_POSITION", bar,
                         f"Gap-Go {self._direction} 確認（m5_close={self._m5_close:.2f}），"
                         f"市價進場，停損={stop_px:.2f}，口數={qty}",
                         {"direction": self._direction, "stop": stop_px, "qty": qty,
                          "gap_open": self._open_930})

    # ── Broker 事件 ──────────────────────────────────────────────────────────

    def _handle_broker_event(self, bev, bar: Bar) -> None:
        from engine.sim.broker import TradeOpened, TradeClosed

        if isinstance(bev, TradeOpened):
            self._session_state.trades_taken += 1
        elif isinstance(bev, TradeClosed):
            trade = bev.trade
            self._session_state.daily_r_accumulated += trade.r_multiple
            self.risk.on_trade_closed(trade)
            self.closed_trades.append(trade)
            if self._state == "IN_POSITION":
                self._transition("DONE", bar,
                                 f"交易結束（{trade.exit_reason}，"
                                 f"{trade.r_multiple:+.2f}R），Gap-Go 每日一筆收工",
                                 {"exit_reason": trade.exit_reason, "r": trade.r_multiple})

    def _transition(self, new_state: GapGoState, bar: Bar,
                    waiting_for: str, detail: dict) -> None:
        prev = self._state
        self._state = new_state
        evt = StateChanged(confirmed_at=bar.ts_utc, prev_state=prev,
                           new_state=new_state, waiting_for=waiting_for, detail=detail)
        self._events.append(evt)
        self.state_timeline.append(evt)
