"""ORBStrategy — Opening Range Breakout 狀態機（1 分 K）。

規則依據：Zarattini & Aziz（2023/2024）NQ 30 分 ORB 期貨版，全客觀。

狀態：IDLE → BUILDING_OR → WAIT_BREAKOUT → IN_POSITION → DONE
進場：09:30–10:00 ET 建立 OR；10:00 後第一根**收盤**突破 → 下一根市價進場。
停損：OR 對側（突破上緣做多 → stop=OR 低；突破下緣做空 → stop=OR 高）。
停利：預設 EOD（15:55 ET 強平）；orb_tp_r=float 時設固定 R 倍數停利。
風控：沿用 RiskManager.size_for，停損距 < 1 點或開不出 1 口 → 當日不交易。
one_shot：預設 True，只取第一次突破方向，後續不二次進場。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Literal

from engine.core.types import Bar, TICK
from engine.core.sessions import _to_et
from engine.model.config import StrategyConfig
from engine.model.bias import DailyBias
from engine.sim.broker import SimBroker
from engine.sim.risk import RiskManager, SessionState
from engine.sim.orders import Bracket, Order, Trade


# ─── ORB 狀態 ────────────────────────────────────────────────────────────────

ORBState = Literal["IDLE", "BUILDING_OR", "WAIT_BREAKOUT", "IN_POSITION", "DONE"]


# ─── 策略事件（與 ICTStrategy 相同介面）──────────────────────────────────────

@dataclass(frozen=True)
class StateChanged:
    confirmed_at: datetime
    prev_state: ORBState
    new_state: ORBState
    waiting_for: str
    detail: dict


# ─── 時間輔助 ─────────────────────────────────────────────────────────────────

def _parse_hm(s: str) -> time:
    h, m = int(s[:2]), int(s[3:])
    return time(h, m)


# ─── ORBStrategy ─────────────────────────────────────────────────────────────

class ORBStrategy:
    """Opening Range Breakout 策略狀態機。

    介面與 ICTStrategy 相同：
    - on_bar(bar) -> list[StateChanged]
    - state_timeline, stop_moves, bracket_targets, closed_trades
    """

    def __init__(
        self,
        config: StrategyConfig,
        bias: DailyBias,
        broker: SimBroker,
        risk_manager: RiskManager,
        es_bars: dict | None = None,  # 相容性，ORB 不用 SMT
    ) -> None:
        self.config = config
        self.bias = bias
        self.broker = broker
        self.risk = risk_manager

        # 狀態機
        self._state: ORBState = "IDLE"
        self._bar_count: int = 0
        self._session_started: bool = False   # 08:00 (context_start) 後
        self._or_building_started: bool = False  # 09:30 後才開始建立 OR

        # OR 建立
        self._or_high: float | None = None
        self._or_low: float | None = None
        self._or_confirmed: bool = False  # 10:00 到才算 OR 建立完成

        # 進場追蹤
        self._breakout_direction: str | None = None  # "LONG" | "SHORT"
        self._shot_used: bool = False  # one_shot 計數
        self._pending_bracket_id: str | None = None
        self._entry_price: float = 0.0
        self._initial_stop_dist: float = 0.0

        # 對外記錄（decision_log 相容）
        self.stop_moves: dict[str, list[dict]] = {}
        self.bracket_targets: dict[str, list[tuple[float, int]]] = {}

        # 每節狀態
        self._session_state = SessionState()

        # 事件
        self._events: list[StateChanged] = []

        # 已完成交易
        self.closed_trades: list[Trade] = []
        self.state_timeline: list[StateChanged] = []

        # 時間解析
        self._or_end_time: time = _parse_hm("10:00")   # OR 建立完成
        # 最晚進場 = entry_window[1]（for_orb 預設 "15:30"，限窗研究可覆蓋）
        self._entry_end_time: time = _parse_hm(config.entry_window[1])
        self._flatten_time_t: time = _parse_hm(config.flatten_time)

    # ── 公開介面 ─────────────────────────────────────────────────────────────

    @property
    def state(self) -> ORBState:
        return self._state

    def on_bar(self, bar: Bar) -> list[StateChanged]:
        """處理一根 1 分 K，推進狀態機。"""
        self._events = []
        self._bar_count += 1

        et = _to_et(bar.ts_utc)
        t = et.time()

        # ── 0. context_start 啟動 + 09:30 觸發 BUILDING_OR ───────────────────
        if not self._session_started:
            ctx_start = _parse_hm(self.config.context_start)
            if t >= ctx_start:
                self._session_started = True

        # OR 建立：09:30 才開始（無論 context_start 設為多早）
        if self._session_started and not self._or_building_started:
            if t >= time(9, 30):
                self._or_building_started = True
                self._transition("BUILDING_OR", bar,
                                 "開始建立 Opening Range（09:30–10:00 ET）", {})

        # ── 1. Broker 事件 ────────────────────────────────────────────────────
        broker_evts = self.broker.on_bar(bar)
        for bev in broker_evts:
            self._handle_broker_event(bev, bar)

        # ── 2. DONE 不再推進 ──────────────────────────────────────────────────
        if self._state == "DONE":
            return self._events

        # ── 3. 強平時間 ──────────────────────────────────────────────────────
        if t >= self._flatten_time_t:
            if self._state == "IN_POSITION":
                self.broker.flatten(bar, reason="EOD")
                self._transition("DONE", bar,
                                 f"EOD 強平（{self.config.flatten_time} ET）", {})
            elif self._state == "WAIT_BREAKOUT" and self._pending_bracket_id:
                self.broker.cancel(self._pending_bracket_id)
                self._pending_bracket_id = None
                self._transition("DONE", bar,
                                 f"強平時間到，撤銷待成交單", {})
            elif self._state not in ("DONE", "IDLE"):
                self._transition("DONE", bar,
                                 f"交易時窗結束（{self.config.flatten_time} ET）", {})
            return self._events

        # ── 4. 狀態機推進 ─────────────────────────────────────────────────────
        if self._state == "BUILDING_OR":
            self._step_building_or(bar, t)

        elif self._state == "WAIT_BREAKOUT":
            self._step_wait_breakout(bar, t)

        elif self._state == "IN_POSITION":
            # ORB 持倉中不做 trailing（EOD 策略）；broker 自動管理停損/停利
            pass

        return self._events

    # ── BUILDING_OR ──────────────────────────────────────────────────────────

    def _step_building_or(self, bar: Bar, t: time) -> None:
        """09:30–10:00 ET：累積 OR 高低點。"""
        # 僅在 09:30 <= t < 10:00 的 bars 建立 OR
        if t >= time(9, 30) and t < self._or_end_time:
            if self._or_high is None or bar.high > self._or_high:
                self._or_high = bar.high
            if self._or_low is None or bar.low < self._or_low:
                self._or_low = bar.low

        # 10:00 ET 到：OR 建立完成
        if t >= self._or_end_time and not self._or_confirmed:
            self._or_confirmed = True

            if self._or_high is None or self._or_low is None:
                self._transition("DONE", bar,
                                 "OR 建立失敗（無 09:30–10:00 K 棒資料）", {})
                return

            or_range = self._or_high - self._or_low
            min_sp = self.config.min_stop_points
            max_sp = self.config.max_stop_points

            if or_range < min_sp:
                self._transition("DONE", bar,
                                 f"OR 過窄（{or_range:.2f} < min_stop_points={min_sp}），當日不交易",
                                 {"or_range": or_range, "or_high": self._or_high, "or_low": self._or_low})
                return

            if or_range > max_sp:
                self._transition("DONE", bar,
                                 f"OR 過寬（{or_range:.2f} > max_stop_points={max_sp}），當日不交易",
                                 {"or_range": or_range, "or_high": self._or_high, "or_low": self._or_low})
                return

            self._transition("WAIT_BREAKOUT", bar,
                             f"OR 確認：高={self._or_high:.2f} 低={self._or_low:.2f} 範圍={or_range:.2f}，等待突破",
                             {"or_high": self._or_high, "or_low": self._or_low, "or_range": or_range})

    # ── WAIT_BREAKOUT ─────────────────────────────────────────────────────────

    def _step_wait_breakout(self, bar: Bar, t: time) -> None:
        """10:00 後等待第一根收盤突破 OR 高/低。"""
        if not self.risk.can_trade(self._session_state):
            self._transition("DONE", bar,
                             "已達每節交易筆數上限或日虧限額，停手", {})
            return

        # one_shot 已用過
        if self.config.orb_one_shot and self._shot_used:
            return

        # 超過最晚進場時間（15:30）
        if t > self._entry_end_time:
            return

        or_high = self._or_high
        or_low = self._or_low
        if or_high is None or or_low is None:
            return

        # 收盤突破確認
        if bar.close > or_high:
            # 向上突破 → LONG
            self._fire_entry(bar, direction="LONG", entry_stop=or_low)
        elif bar.close < or_low:
            # 向下突破 → SHORT
            self._fire_entry(bar, direction="SHORT", entry_stop=or_high)

    def _fire_entry(self, bar: Bar, direction: str, entry_stop: float) -> None:
        """確認突破後，以市價（下一根 open）進場。"""
        or_high = self._or_high
        or_low = self._or_low

        # 停損距離 = 進場棒收盤到 OR 對側
        # （實際成交會是下一根 open，這裡用收盤估算口數；
        #  bracket stop 設 OR 對側，broker 撮合時自動處理）
        approx_entry = bar.close
        stop_px = entry_stop
        stop_dist = abs(approx_entry - stop_px)

        if stop_dist < self.config.min_stop_points:
            return  # 保守：距離不足不進

        qty = int(self.risk.size_for(stop_dist))
        if qty < 1:
            self._transition("DONE", bar,
                             f"放棄突破：停損 {stop_dist:.2f} pt 開不出 1 口",
                             {"stop_dist": stop_dist, "qty": 0})
            return

        # 停利目標（若設 tp_r）
        targets: list[tuple[float, int]] = []
        tp_r = self.config.orb_tp_r
        if tp_r is not None and tp_r > 0.0:
            if direction == "LONG":
                tp_price = approx_entry + stop_dist * tp_r
            else:
                tp_price = approx_entry - stop_dist * tp_r
            targets = [(round(round(tp_price / TICK) * TICK, 10), qty)]

        side: str = "BUY" if direction == "LONG" else "SELL"
        order = Order(side=side, type="MARKET", qty=qty, price=0.0)  # type: ignore[arg-type]
        bracket = Bracket(entry=order, stop_price=stop_px, targets=targets)

        self._pending_bracket_id = self.broker.submit(bracket)
        self.bracket_targets[self._pending_bracket_id] = list(targets)
        self._entry_price = approx_entry
        self._initial_stop_dist = stop_dist
        self._breakout_direction = direction

        if self.config.orb_one_shot:
            self._shot_used = True

        self._transition("IN_POSITION", bar,
                         f"ORB {direction} 突破（收盤={bar.close:.2f}），"
                         f"市價進場，停損={stop_px:.2f}，口數={qty}",
                         {
                             "direction": direction,
                             "close": bar.close,
                             "stop": stop_px,
                             "qty": qty,
                             "or_high": or_high,
                             "or_low": or_low,
                         })

    # ── Broker 事件處理 ───────────────────────────────────────────────────────

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
                # ORB one_shot：平倉後收工
                if self.config.orb_one_shot:
                    self._transition("DONE", bar,
                                     f"交易結束（{trade.exit_reason}，{trade.r_multiple:+.2f}R），ORB one_shot 收工",
                                     {"exit_reason": trade.exit_reason, "r": trade.r_multiple})
                elif self.risk.can_trade(self._session_state):
                    self._transition("WAIT_BREAKOUT", bar,
                                     f"交易結束（{trade.exit_reason}，{trade.r_multiple:+.2f}R），等下一個突破",
                                     {"exit_reason": trade.exit_reason, "r": trade.r_multiple})
                else:
                    self._transition("DONE", bar,
                                     f"交易結束（{trade.exit_reason}），已達每節限制",
                                     {"exit_reason": trade.exit_reason, "r": trade.r_multiple})

    # ── 工具 ─────────────────────────────────────────────────────────────────

    def _transition(self, new_state: ORBState, bar: Bar,
                    waiting_for: str, detail: dict) -> None:
        prev = self._state
        self._state = new_state
        evt = StateChanged(
            confirmed_at=bar.ts_utc,
            prev_state=prev,
            new_state=new_state,
            waiting_for=waiting_for,
            detail=detail,
        )
        self._events.append(evt)
        self.state_timeline.append(evt)
