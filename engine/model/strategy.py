"""ICTStrategy — §3 盤中狀態機（1 分 K）。

狀態：IDLE → WAIT_SWEEP → WAIT_MSS → WAIT_RETRACE → IN_POSITION → DONE

每次狀態轉換發 StateChanged 事件；所有決策都在 on_bar(bar) 中完成，
嚴格無前視（只用當前棒收盤後已知資訊）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from engine.core.types import Bar, Raid, MSS, FVGCreated, FVGFilled, TICK
from engine.core.sessions import is_in_window, trading_date, _to_et
from engine.detectors.pools import LiquidityPoolTracker
from engine.detectors.mss import MSSDetector
from engine.detectors.fvg import FVGDetector
from engine.detectors.ranges import DealingRange
from engine.model.config import StrategyConfig
from engine.model.bias import DailyBias
from engine.sim.broker import SimBroker, BrokerConfig
from engine.sim.risk import RiskManager, RiskConfig, SessionState
from engine.sim.orders import Bracket, Order, Trade


# ─── 狀態機狀態 ──────────────────────────────────────────────────────────────

State = Literal["IDLE", "WAIT_SWEEP", "WAIT_MSS", "WAIT_RETRACE", "IN_POSITION", "DONE"]


# ─── 策略事件 ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StateChanged:
    """狀態轉換事件（前端側欄顯示）。"""
    confirmed_at: datetime
    prev_state: State
    new_state: State
    waiting_for: str          # 人話描述（繁中），告知前端「現在等什麼」
    detail: dict              # 任意補充欄位


StrategyEvent = StateChanged


# ─── 進場 FVG 快照 ────────────────────────────────────────────────────────────

@dataclass
class _EntryFVG:
    """WAIT_RETRACE 時使用的 FVG 快照。"""
    direction: str
    top: float
    bottom: float
    ce: float
    confirmed_at: datetime

    @property
    def proximal(self) -> float:
        """BEAR FVG：proximal = bottom（頂端是遠端，底端是近端回踩位）。"""
        return self.bottom if self.direction == "BEAR" else self.top

    @property
    def distal(self) -> float:
        return self.top if self.direction == "BEAR" else self.bottom


# ─── ICTStrategy ─────────────────────────────────────────────────────────────

class ICTStrategy:
    """ICT NQ 1 分 K 策略狀態機。

    使用方式：
        strategy = ICTStrategy(config, bias, broker, risk_manager)
        for bar in bars:
            events = strategy.on_bar(bar)
    """

    def __init__(
        self,
        config: StrategyConfig,
        bias: DailyBias,
        broker: SimBroker,
        risk_manager: RiskManager,
    ) -> None:
        self.config = config
        self.bias = bias
        self.broker = broker
        self.risk = risk_manager

        # 偵測器
        self._pool_tracker = LiquidityPoolTracker(
            n=config.swing_n,
            r=config.raid_recover_bars,
        )
        self._mss_det = MSSDetector(n=config.swing_n)
        self._fvg_det = FVGDetector()   # 獨立 FVG 偵測（追蹤 WAIT_RETRACE 中的 FVG 狀態）

        # 狀態機
        self._state: State = "IDLE"
        self._bar_count: int = 0          # 本日 bars 計數
        self._session_started: bool = False

        # WAIT_SWEEP 計時
        self._last_raid: Raid | None = None

        # WAIT_MSS 計時
        self._mss_start_bar: int = 0
        self._raid_level: float = 0.0     # 掃蕩極值（停損基準）

        # WAIT_RETRACE
        self._entry_fvg: _EntryFVG | None = None
        self._entry_bar: int = 0          # 進場掛單的 bar index
        self._pending_bracket_id: str | None = None
        self._entry_price: float = 0.0    # 掛單價格

        # IN_POSITION
        self._trade_open_bar: int = 0
        self._initial_stop_dist: float = 0.0
        self._tp2_dist: float = 0.0       # 階梯收停損基準距離
        self._trailing_milestone: int = 0  # 已達 25/50/75 哪個階段

        # 每節交易記錄
        self._session_state = SessionState()

        # 事件收集
        self._events: list[StateChanged] = []

        # DOL 提前出場追蹤
        self._dol_level = bias.dol_level

        # 日常偏向方向
        self._direction = bias.direction  # "LONG" | "SHORT" | "NO_TRADE"

        # 已完成交易記錄（供 runner 使用）
        self.closed_trades: list[Trade] = []

        # 各棒 state timeline（包含所有狀態事件）
        self.state_timeline: list[StateChanged] = []

    # ── 公開介面 ─────────────────────────────────────────────────────────────

    @property
    def state(self) -> State:
        return self._state

    def on_bar(self, bar: Bar) -> list[StateChanged]:
        """處理一根 1 分 K，推進狀態機，回傳本棒產生的策略事件。"""
        self._events = []
        self._bar_count += 1

        et = _to_et(bar.ts_utc)

        # ── 0. 09:30 啟動 ───────────────────────────────────────────────────
        if not self._session_started:
            if is_in_window(bar.ts_utc, self.config.window):
                self._session_started = True
                if self._direction == "NO_TRADE":
                    self._transition("DONE", bar, f"偏向 NO_TRADE（{self.bias.reason}），今日不進場", {})
                else:
                    self._transition("WAIT_SWEEP", bar, "等待掃蕩反向流動性水位（ONH/PDH/SESSION_HIGH...）", {})

        # ── 1. 永遠餵偵測器（包含 08:00–09:29 的 context-building 階段）──────
        pool_evts = self._pool_tracker.on_bar(bar)
        mss_evts = self._mss_det.on_bar(bar)
        fvg_evts = self._fvg_det.on_bar(bar)

        broker_evts = self.broker.on_bar(bar)
        # 處理 broker 事件（停利/停損/成交）
        for bev in broker_evts:
            self._handle_broker_event(bev, bar)

        # ── 2. 若 DONE，不進一步推進 ─────────────────────────────────────────
        if self._state == "DONE":
            return self._events

        # ── 3. EOD 強平（12:30 ET）───────────────────────────────────────────
        if is_in_window(bar.ts_utc, self.config.window):
            pass  # 正常交易窗
        else:
            # 已出窗
            if self._session_started:
                if self._state == "IN_POSITION":
                    flatten_evts = self.broker.flatten(bar, reason="EOD")
                    for bev in flatten_evts:
                        self._handle_broker_event(bev, bar)
                    self._transition("DONE", bar, "EOD 強制平倉（12:30 ET）", {})
                elif self._state in ("WAIT_RETRACE",) and self._pending_bracket_id:
                    self.broker.cancel(self._pending_bracket_id)
                    self._pending_bracket_id = None
                    self._transition("DONE", bar, "EOD 進場窗結束，撤銷待成交限價單", {})
                elif self._state != "DONE":
                    self._transition("DONE", bar, "交易窗結束（12:30 ET）", {})
            return self._events

        # ── 4. 每日過濾（星期過濾）───────────────────────────────────────────
        if self.config.use_day_filter:
            day_name = et.strftime("%a")  # "Mon", "Tue", ...
            if day_name not in self.config.day_filter:
                if self._state == "WAIT_SWEEP":
                    self._transition("DONE", bar, f"今日 {day_name} 不在交易日過濾名單，不進場", {})
                return self._events

        # ── 5. 狀態機推進 ─────────────────────────────────────────────────────
        if self._state == "WAIT_SWEEP":
            self._step_wait_sweep(bar, pool_evts)

        elif self._state == "WAIT_MSS":
            self._step_wait_mss(bar, mss_evts)

        elif self._state == "WAIT_RETRACE":
            self._step_wait_retrace(bar, fvg_evts)

        elif self._state == "IN_POSITION":
            self._step_in_position(bar)

        return self._events

    # ── WAIT_SWEEP ─────────────────────────────────────────────────────────

    def _step_wait_sweep(self, bar: Bar, pool_evts: list) -> None:
        """等待反向流動性掃蕩（Raid 事件），方向依偏向過濾。"""
        if not self.risk.can_trade(self._session_state):
            self._transition("DONE", bar, "已達每節交易筆數上限或日虧限額，停手", {})
            return

        for evt in pool_evts:
            if not isinstance(evt, Raid):
                continue
            # 方向過濾
            # SHORT bias → 等 BUY side Raid（掃過上方流動性，即掃高位買單）
            # LONG  bias → 等 SELL side Raid（掃過下方流動性，即掃低位賣單）
            if self._direction == "SHORT" and evt.side != "BUY":
                continue
            if self._direction == "LONG" and evt.side != "SELL":
                continue

            self._last_raid = evt
            self._raid_level = evt.level
            self._mss_start_bar = self._bar_count
            self._transition(
                "WAIT_MSS", bar,
                f"掃蕩確認（{evt.kind} {evt.level:.2f}），等位移+MSS（最多 {self.config.mss_timeout_bars} 根）",
                {"raid_kind": evt.kind, "raid_level": evt.level},
            )
            return  # 一次只處理一個 Raid

    # ── WAIT_MSS ───────────────────────────────────────────────────────────

    def _step_wait_mss(self, bar: Bar, mss_evts: list) -> None:
        """等位移+MSS；超時 → 回 WAIT_SWEEP。"""
        bars_since = self._bar_count - self._mss_start_bar
        if bars_since > self.config.mss_timeout_bars:
            self._transition(
                "WAIT_SWEEP", bar,
                f"MSS 等待超時（{self.config.mss_timeout_bars} 根），重回等待掃蕩",
                {"timeout_bars": bars_since},
            )
            return

        for evt in mss_evts:
            if not isinstance(evt, MSS):
                continue
            # 方向過濾
            if self._direction == "SHORT" and evt.direction != "BEAR":
                continue
            if self._direction == "LONG" and evt.direction != "BULL":
                continue
            # MSS 必須有 FVG
            if not evt.left_fvg:
                continue

            # 找最近的 FVG（從獨立 FVG 偵測器中取最近一個對應方向的）
            fvg = self._find_mss_fvg(evt.direction)
            if fvg is None:
                continue

            # FVG half filter（fvg_half_filter：FVG 須位於前日 range 的正確半段）
            if self.config.fvg_half_filter and self.bias.dealing_range is not None:
                dr = self.bias.dealing_range
                if self._direction == "SHORT":
                    # FVG 須在 premium 或 equilibrium（上半）
                    if dr.is_discount(fvg.proximal):
                        continue
                else:
                    # FVG 須在 discount 或 equilibrium（下半）
                    if dr.is_premium(fvg.proximal):
                        continue

            self._entry_fvg = fvg
            self._entry_bar = self._bar_count
            self._transition(
                "WAIT_RETRACE", bar,
                f"MSS 確認（{evt.direction}，破 {evt.broken_swing_level:.2f}），"
                f"掛 {'Sell' if self._direction == 'SHORT' else 'Buy'} Limit "
                f"@ FVG {self._entry_price_for(fvg):.2f}",
                {
                    "mss_broken_level": evt.broken_swing_level,
                    "fvg_top": fvg.top,
                    "fvg_bottom": fvg.bottom,
                },
            )
            self._submit_entry_order(bar, fvg)
            return

    def _find_mss_fvg(self, direction: str) -> "_EntryFVG | None":
        """從 FVGDetector 的 active list 找最近的對應方向 FVG。"""
        matching = [
            fvg for fvg in self._fvg_det._active
            if fvg.direction == direction and not fvg.filled
        ]
        if not matching:
            return None
        # 取最新（anchor 最晚）的
        latest = max(matching, key=lambda f: f.anchor)
        return _EntryFVG(
            direction=latest.direction,
            top=latest.top,
            bottom=latest.bottom,
            ce=latest.ce,
            confirmed_at=latest.anchor,
        )

    def _entry_price_for(self, fvg: "_EntryFVG") -> float:
        """根據 entry_level config 計算進場價。"""
        mode = self.config.entry_level
        if mode == "proximal":
            return fvg.proximal
        elif mode == "ce":
            return fvg.ce
        else:  # ote62
            if self.bias.dealing_range:
                ote_low, ote_high = self.bias.dealing_range.ote_zone()
                if self._direction == "SHORT":
                    return ote_high  # 62% retracement = 較高價位賣
                else:
                    return ote_low
            return fvg.proximal

    def _submit_entry_order(self, bar: Bar, fvg: "_EntryFVG") -> None:
        """計算口數並提交 Bracket。"""
        entry_px = self._entry_price_for(fvg)

        # 停損 = 掃蕩極值 ± stop_buffer
        buf = self.config.stop_buffer_ticks * TICK
        if self._direction == "SHORT":
            stop_px = self._raid_level + buf      # 賣空，停損在掃蕩高點上方
        else:
            stop_px = self._raid_level - buf      # 買多，停損在掃蕩低點下方

        stop_dist = abs(entry_px - stop_px)
        if stop_dist <= 0:
            return

        # 週四減半
        import datetime as _dt
        et = _to_et(bar.ts_utc)
        size_factor = 1.0
        if self.config.use_day_filter and et.strftime("%a") == "Thu":
            size_factor = self.config.thursday_size_factor

        qty = self.risk.size_for(stop_dist)
        qty = max(1, int(qty * size_factor))   # 最少 1 口（0 口由 can_trade 過濾）

        # 分批停利目標
        targets = self._build_targets(entry_px, stop_dist, qty)

        side: str = "SELL" if self._direction == "SHORT" else "BUY"
        order = Order(side=side, type="LIMIT", qty=qty, price=entry_px)  # type: ignore[arg-type]
        bracket = Bracket(entry=order, stop_price=stop_px, targets=targets)

        self._pending_bracket_id = self.broker.submit(bracket)
        self._entry_price = entry_px
        self._initial_stop_dist = stop_dist

        # TP2 距離（階梯收停損基準）
        tp2_dist = self._tp2_distance(stop_dist)
        self._tp2_dist = tp2_dist
        self._trailing_milestone = 0

    def _build_targets(
        self, entry_px: float, stop_dist: float, total_qty: int
    ) -> list[tuple[float, int]]:
        """計算分批停利目標列表。"""
        targets: list[tuple[float, int]] = []
        remaining = total_qty

        if self.config.targets_mode == "fixed_points":
            tp_pts = self.config.tp_points
            fracs = self.config.tp_fractions
        else:  # r_multiple
            tp_pts = (stop_dist * 1.0, stop_dist * 2.0, stop_dist * 3.0)
            fracs = self.config.tp_fractions

        # TP1
        qty1 = max(1, int(total_qty * fracs[0]))
        qty1 = min(qty1, remaining)
        if self._direction == "SHORT":
            tp1_price = entry_px - tp_pts[0]
        else:
            tp1_price = entry_px + tp_pts[0]
        targets.append((tp1_price, qty1))
        remaining -= qty1

        if remaining <= 0:
            return targets

        # TP2
        qty2 = max(1, int(total_qty * fracs[1]))
        qty2 = min(qty2, remaining)
        if self._direction == "SHORT":
            tp2_price = entry_px - tp_pts[1]
        else:
            tp2_price = entry_px + tp_pts[1]
        targets.append((tp2_price, qty2))
        remaining -= qty2

        if remaining <= 0:
            return targets

        # TP3 / DOL 目標
        # TP3：剩餘的 fracs[2]（預設 80%）
        qty3 = max(1, int(remaining * fracs[2]))
        qty3 = min(qty3, remaining)
        if self._direction == "SHORT":
            tp3_price = entry_px - tp_pts[2]
        else:
            tp3_price = entry_px + tp_pts[2]
        targets.append((tp3_price, qty3))
        remaining -= qty3

        # 尾單 → DOL target
        if remaining > 0 and self._dol_level is not None:
            dol_buf = self.config.dol_early_exit_ticks * TICK
            if self._direction == "SHORT":
                dol_exit = self._dol_level + dol_buf
            else:
                dol_exit = self._dol_level - dol_buf
            targets.append((dol_exit, remaining))

        elif remaining > 0:
            # 沒有 DOL，就在 TP3 一起出
            targets[-1] = (targets[-1][0], targets[-1][1] + remaining)

        return targets

    def _tp2_distance(self, stop_dist: float) -> float:
        """TP2 的距離（用於階梯收停損計算）。"""
        if self.config.targets_mode == "fixed_points":
            return self.config.tp_points[1]
        else:
            return stop_dist * 2.0

    # ── WAIT_RETRACE ──────────────────────────────────────────────────────

    def _step_wait_retrace(self, bar: Bar, fvg_evts: list) -> None:
        """等限價單成交；超時或 FVG 填滿 → 撤單回 WAIT_SWEEP。"""
        bars_since = self._bar_count - self._entry_bar
        if bars_since > self.config.entry_timeout_bars:
            if self._pending_bracket_id:
                self.broker.cancel(self._pending_bracket_id)
                self._pending_bracket_id = None
            self._transition(
                "WAIT_SWEEP", bar,
                f"進場超時（{self.config.entry_timeout_bars} 根），撤銷限價單，重回等待掃蕩",
                {"timeout_bars": bars_since},
            )
            return

        # FVG 被填滿（收盤穿越 FVG）→ 限價單失效
        if self._entry_fvg:
            fvg = self._entry_fvg
            fvg_invalidated = False
            if fvg.direction == "BEAR" and bar.close > fvg.top:
                fvg_invalidated = True
            elif fvg.direction == "BULL" and bar.close < fvg.bottom:
                fvg_invalidated = True
            if fvg_invalidated:
                if self._pending_bracket_id:
                    self.broker.cancel(self._pending_bracket_id)
                    self._pending_bracket_id = None
                self._transition(
                    "WAIT_SWEEP", bar,
                    "FVG 被收盤穿越失效，撤銷限價單，重回等待掃蕩",
                    {"fvg_top": fvg.top, "fvg_bottom": fvg.bottom},
                )
                return

        # 成交後 broker 會在 on_bar 中 emit TradeOpened；
        # _handle_broker_event 負責轉換到 IN_POSITION

    # ── IN_POSITION ────────────────────────────────────────────────────────

    def _step_in_position(self, bar: Bar) -> None:
        """管理浮盈停損收緊與 DOL 提前出場。"""
        if self.broker.position is None:
            return

        pos = self.broker.position
        entry_px = pos.avg_entry
        current_price = bar.close

        if self._direction == "SHORT":
            float_profit_pts = entry_px - current_price
        else:
            float_profit_pts = current_price - entry_px

        obj = self._tp2_dist
        if obj <= 0:
            return

        # 階梯收停損（對 broker.position.stop_price 直接修改）
        progress = float_profit_pts / obj  # 0% → 100% = TP2

        if self._trailing_milestone < 3 and progress >= 0.75:
            # 移 BE
            new_stop = entry_px
            self._update_stop(pos, new_stop, bar, "浮盈達 75%（TP2 基準），停損移至 BE")
            self._trailing_milestone = 3

        elif self._trailing_milestone < 2 and progress >= 0.50:
            # 收 50%
            if self._direction == "SHORT":
                new_stop = entry_px - self._initial_stop_dist * 0.5
            else:
                new_stop = entry_px + self._initial_stop_dist * 0.5
            # 對 SHORT：停損要往下移（對持倉更有利）
            if self._direction == "SHORT":
                new_stop = entry_px - self._initial_stop_dist * 0.5
            else:
                new_stop = entry_px + self._initial_stop_dist * 0.5
            self._update_stop(pos, new_stop, bar, "浮盈達 50%（TP2 基準），停損收緊至 50%")
            self._trailing_milestone = 2

        elif self._trailing_milestone < 1 and progress >= 0.25:
            # 收 25%
            if self._direction == "SHORT":
                new_stop = entry_px - self._initial_stop_dist * 0.75
            else:
                new_stop = entry_px + self._initial_stop_dist * 0.75
            self._update_stop(pos, new_stop, bar, "浮盈達 25%（TP2 基準），停損收緊至 75% 距離")
            self._trailing_milestone = 1

        # DOL 提前出場
        if self._dol_level is not None:
            dol_buf = self.config.dol_early_exit_ticks * TICK
            if self._direction == "SHORT":
                # 若 bar.low 碰到 DOL + buffer
                if bar.low <= self._dol_level + dol_buf:
                    flatten_evts = self.broker.flatten(bar, reason="EOD")  # reason EOD 借用
                    for bev in flatten_evts:
                        self._handle_broker_event(bev, bar)
                    self._transition("DONE", bar, f"DOL 提前出場（{self._dol_level:.2f} ± {dol_buf:.2f}）", {})
            else:
                if bar.high >= self._dol_level - dol_buf:
                    flatten_evts = self.broker.flatten(bar, reason="EOD")
                    for bev in flatten_evts:
                        self._handle_broker_event(bev, bar)
                    self._transition("DONE", bar, f"DOL 提前出場（{self._dol_level:.2f} ± {dol_buf:.2f}）", {})

    def _update_stop(self, pos, new_stop: float, bar: Bar, msg: str) -> None:
        """更新 position 停損價（直接修改 broker.position.stop_price）。"""
        if self._direction == "SHORT":
            # Short：新停損只允許往下移（對持倉更有利）
            if new_stop < pos.stop_price:
                pos.stop_price = new_stop
        else:
            # Long：新停損只允許往上移
            if new_stop > pos.stop_price:
                pos.stop_price = new_stop

    # ── Broker 事件處理 ───────────────────────────────────────────────────

    def _handle_broker_event(self, bev, bar: Bar) -> None:
        """處理 SimBroker 回調事件，推進策略狀態機。"""
        from engine.sim.broker import TradeOpened, TradeClosed

        if isinstance(bev, TradeOpened):
            if self._state == "WAIT_RETRACE":
                self._trade_open_bar = self._bar_count
                self._session_state.trades_taken += 1
                self._transition(
                    "IN_POSITION", bar,
                    f"限價單成交 @ {bev.entry_price:.2f}，持倉 {bev.qty} 口，"
                    f"停損 {self.broker.position.stop_price if self.broker.position else 'N/A'}",
                    {"entry_price": bev.entry_price, "qty": bev.qty},
                )

        elif isinstance(bev, TradeClosed):
            trade = bev.trade
            # 更新 R 累積
            self._session_state.daily_r_accumulated += trade.r_multiple
            self.risk.on_trade_closed(trade)
            self.closed_trades.append(trade)

            if self._state == "IN_POSITION":
                # 決定次狀態：還可再進場則回 WAIT_SWEEP，否則 DONE
                if self.risk.can_trade(self._session_state):
                    self._transition(
                        "WAIT_SWEEP", bar,
                        f"交易結束（{trade.exit_reason}，{trade.r_multiple:+.2f}R），可再進場，等下一個掃蕩",
                        {"exit_reason": trade.exit_reason, "r": trade.r_multiple},
                    )
                else:
                    self._transition(
                        "DONE", bar,
                        f"交易結束（{trade.exit_reason}，{trade.r_multiple:+.2f}R），已達每節限制，收工",
                        {"exit_reason": trade.exit_reason, "r": trade.r_multiple},
                    )

    # ── 工具 ─────────────────────────────────────────────────────────────────

    def _transition(self, new_state: State, bar: Bar, waiting_for: str, detail: dict) -> None:
        """記錄狀態轉換，發出 StateChanged 事件。"""
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
