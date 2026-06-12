"""ICTStrategy — §3 盤中狀態機（1 分 K）v2。

v2 變更：
- WAIT_SWEEP：bias=BOTH 時雙向監測掃蕩，掃上方 → 鎖 SHORT；掃下方 → 鎖 LONG
- 新倉時間窗：entry_window（09:30–11:00 ET），late_window_thu_fri=True 時週四五到 11:30
- 進場：stop_mode="fvg_candle" → 停損 = FVG 三根第一棒極值，無 buffer
- fvg_filter="leg_equilibrium"：bearish FVG proximal 須 >= 位移段 equilibrium
- targets_mode="m13_liquidity"：T1=內部流動性, T2=ONH/ONL, T3=PDH/PDL + 順延/fallback
- trailing：trail_half_at/trail_be_at 相對 T1 距離
- min/max_stop_points：超出範圍放棄 setup
- 每筆記錄進場子窗（9:30-10/10-10:30/10:30-11/late）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
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
from engine.detectors.smt import SMTChecker


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
    """WAIT_RETRACE 時使用的 FVG 快照。

    v2 新增：
    - candle_stop_level：FVG 形成三根 K 棒第一根的極值（空單 = b0.high，多單 = b0.low）
    - leg_high/leg_low：位移段高低（用於 leg_equilibrium 過濾）
    """
    direction: str
    top: float
    bottom: float
    ce: float
    confirmed_at: datetime
    candle_stop_level: float = 0.0   # fvg_candle 停損精確值（第一棒極值）
    leg_high: float = 0.0            # 位移段 high
    leg_low: float = 0.0             # 位移段 low

    @property
    def proximal(self) -> float:
        """BEAR FVG：proximal = bottom（近端回踩位）。BULL FVG：proximal = top。"""
        return self.bottom if self.direction == "BEAR" else self.top

    @property
    def distal(self) -> float:
        return self.top if self.direction == "BEAR" else self.bottom

    @property
    def leg_equilibrium(self) -> float:
        """位移段中點（equilibrium）。"""
        return (self.leg_high + self.leg_low) / 2.0


def _entry_window_time(config: StrategyConfig, et: datetime) -> bool:
    """判斷是否在新倉時間窗內。

    週四五且 late_window_thu_fri=True → 延至 11:30；否則到 11:00。
    """
    t = et.time()
    start_str, end_str = config.entry_window  # e.g. "09:30", "11:00"
    sh, sm = int(start_str[:2]), int(start_str[3:])
    eh, em = int(end_str[:2]), int(end_str[3:])
    start_t = time(sh, sm)
    end_t = time(eh, em)

    # late window
    day_name = et.strftime("%a")
    if config.late_window_thu_fri and day_name in ("Thu", "Fri"):
        end_t = time(11, 30)

    return start_t <= t < end_t


def _flatten_time(config: StrategyConfig, et: datetime) -> bool:
    """是否已到強平時間。"""
    ft_str = config.flatten_time  # e.g. "12:30"
    fh, fm = int(ft_str[:2]), int(ft_str[3:])
    return et.time() >= time(fh, fm)


def _entry_subwindow(et: datetime) -> str:
    """記錄進場落在哪個子窗。"""
    t = et.time()
    if t < time(10, 0):
        return "09:30-10:00"
    elif t < time(10, 30):
        return "10:00-10:30"
    elif t < time(11, 0):
        return "10:30-11:00"
    else:
        return "late"


# ─── ICTStrategy ─────────────────────────────────────────────────────────────

class ICTStrategy:
    """ICT NQ 1 分 K 策略狀態機 v2。"""

    def __init__(
        self,
        config: StrategyConfig,
        bias: DailyBias,
        broker: SimBroker,
        risk_manager: RiskManager,
        es_bars: dict | None = None,   # ts_utc → Bar (ES 1m bars for SMT)
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
        # fvg_evidence 模式：實體門檻歸零（任何收破 swing 都先當候選），
        # 位移證據改由「位移段留下 FVG」承擔（_find_mss_fvg 的 raid 後新鮮度檢查）
        self._mss_det = MSSDetector(
            n=config.swing_n,
            window=config.displacement_window,
            mult=0.0 if config.mss_confirm == "fvg_evidence" else config.displacement_mult,
        )
        self._fvg_det = FVGDetector()

        # 狀態機
        self._state: State = "IDLE"
        self._bar_count: int = 0
        self._session_started: bool = False

        # v2：當 bias=BOTH 時，掃蕩後鎖定的方向（None=仍雙向）
        self._locked_direction: str | None = None   # "LONG" | "SHORT"

        # WAIT_SWEEP 計時
        self._last_raid: Raid | None = None

        # WAIT_MSS 計時
        self._mss_start_bar: int = 0
        self._raid_level: float = 0.0
        self._raid_extreme: float = 0.0   # 掃蕩極值（用於 leg_equilibrium 計算）

        # WAIT_RETRACE
        self._entry_fvg: _EntryFVG | None = None
        self._entry_bar: int = 0
        self._pending_bracket_id: str | None = None
        self._entry_price: float = 0.0
        self._mss_broken_level: float = 0.0  # MSS 破的 swing level（位移段起點之一）

        # IN_POSITION
        self._trade_open_bar: int = 0
        self._initial_stop_dist: float = 0.0
        self._t1_dist: float = 0.0        # T1 距離（trailing 基準）
        self._trailing_milestone: int = 0  # 0=未觸發, 1=半距, 2=BE

        # 對外記錄（決策日誌用）：bracket_id → 停損移動 / 停利目標
        self.stop_moves: dict[str, list[dict]] = {}
        self.bracket_targets: dict[str, list[tuple[float, int]]] = {}

        # 每節交易記錄
        self._session_state = SessionState()

        # 事件收集
        self._events: list[StateChanged] = []

        # SMT
        self._smt = SMTChecker(lookback_bars=config.smt_lookback_bars)
        self._es_bars = es_bars or {}

        # first_setup_only: set to True once first MSS chain has started
        self._first_setup_used: bool = False

        # 前時段/前日極值（m13_liquidity 停利素材）
        self._pdh = bias.prev_day_high
        self._pdl = bias.prev_day_low
        self._onh = bias.overnight_high
        self._onl = bias.overnight_low

        # DOL（m1_program 模式；m13 模式動態決定）
        self._dol_level = bias.dol_level

        # 日常偏向方向
        self._direction_bias = bias.direction  # "LONG"|"SHORT"|"NO_TRADE"|"BOTH"

        # 輔助：追蹤 session 內已掃蕩的水位方向（m13_raid 雙向去重）
        self._raided_sides: set[str] = set()  # "BUY" | "SELL"

        # 已完成交易記錄
        self.closed_trades: list[Trade] = []
        self.state_timeline: list[StateChanged] = []

        # 追蹤在 WAIT_MSS 階段進場的 displacement 最高/最低點（用於 leg_equilibrium）
        self._disp_high: float = 0.0
        self._disp_low: float = 999999.0

    # ── 公開介面 ─────────────────────────────────────────────────────────────

    @property
    def state(self) -> State:
        return self._state

    def _effective_direction(self) -> str:
        """當前有效方向（BOTH 時看 _locked_direction）。"""
        if self._direction_bias != "BOTH":
            return self._direction_bias
        return self._locked_direction or "BOTH"

    def on_bar(self, bar: Bar) -> list[StateChanged]:
        """處理一根 1 分 K，推進狀態機，回傳本棒產生的策略事件。"""
        self._events = []
        self._bar_count += 1

        et = _to_et(bar.ts_utc)

        # ── 0. 09:30 啟動 ───────────────────────────────────────────────────
        if not self._session_started:
            # 是否進入 entry_window 開始時間
            entry_start_str = self.config.entry_window[0]
            eh, em = int(entry_start_str[:2]), int(entry_start_str[3:])
            if et.time() >= time(eh, em):
                self._session_started = True
                d = self._direction_bias
                if d == "NO_TRADE":
                    self._transition("DONE", bar, f"偏向 NO_TRADE（{self.bias.reason}），今日不進場", {})
                else:
                    self._transition(
                        "WAIT_SWEEP", bar,
                        f"等待掃蕩（bias={d}）",
                        {"bias": d},
                    )

        # ── 1. 永遠餵偵測器 ──────────────────────────────────────────────────
        pool_evts = self._pool_tracker.on_bar(bar)
        mss_evts = self._mss_det.on_bar(bar)
        fvg_evts = self._fvg_det.on_bar(bar)

        # Feed SMT checker
        es_bar = self._es_bars.get(bar.ts_utc)
        self._smt.on_bar(bar, es_bar)

        broker_evts = self.broker.on_bar(bar)
        for bev in broker_evts:
            self._handle_broker_event(bev, bar)

        # ── 2. 若 DONE，不進一步推進 ─────────────────────────────────────────
        if self._state == "DONE":
            return self._events

        # ── 3. 強平時間檢查（flatten_time = 12:30 預設）─────────────────────
        if self._session_started and _flatten_time(self.config, et):
            if self._state == "IN_POSITION":
                flatten_evts = self.broker.flatten(bar, reason="EOD")
                for bev in flatten_evts:
                    self._handle_broker_event(bev, bar)
                self._transition("DONE", bar, f"強平（{self.config.flatten_time} ET）", {})
            elif self._state == "WAIT_RETRACE" and self._pending_bracket_id:
                self.broker.cancel(self._pending_bracket_id)
                self._pending_bracket_id = None
                self._transition("DONE", bar, "強平時間到，撤銷待成交限價單", {})
            elif self._state not in ("DONE", "IDLE"):
                self._transition("DONE", bar, f"交易窗結束（{self.config.flatten_time} ET）", {})
            return self._events

        # ── 4. 兼容舊版 EOD 邏輯（window="RTH_OPEN_3H" 超出）───────────────
        if not is_in_window(bar.ts_utc, self.config.window):
            if self._session_started:
                if self._state == "IN_POSITION":
                    flatten_evts = self.broker.flatten(bar, reason="EOD")
                    for bev in flatten_evts:
                        self._handle_broker_event(bev, bar)
                    self._transition("DONE", bar, "EOD 強制平倉（RTH_OPEN_3H 窗結束）", {})
                elif self._state == "WAIT_RETRACE" and self._pending_bracket_id:
                    self.broker.cancel(self._pending_bracket_id)
                    self._pending_bracket_id = None
                    self._transition("DONE", bar, "EOD 進場窗結束，撤銷待成交限價單", {})
                elif self._state not in ("DONE",):
                    self._transition("DONE", bar, "交易窗結束（RTH_OPEN_3H）", {})
            return self._events

        # ── 5. 每日過濾（星期過濾）───────────────────────────────────────────
        if self.config.use_day_filter and self.config.day_filter is not None:
            day_name = et.strftime("%a")
            if day_name not in self.config.day_filter:
                if self._state == "WAIT_SWEEP":
                    self._transition("DONE", bar, f"今日 {day_name} 不在交易日過濾名單，不進場", {})
                return self._events

        # ── 6. 新倉時間窗過濾 ─────────────────────────────────────────────
        # 窗外不開新倉，但繼續管理持倉
        in_entry_window = _entry_window_time(self.config, et)

        # ── 7. 狀態機推進 ─────────────────────────────────────────────────────
        if self._state == "WAIT_SWEEP":
            if in_entry_window:
                self._step_wait_sweep(bar, pool_evts)
            else:
                # 超出新倉窗，等待強平
                pass

        elif self._state == "WAIT_MSS":
            self._step_wait_mss(bar, mss_evts)

        elif self._state == "WAIT_RETRACE":
            self._step_wait_retrace(bar, fvg_evts)

        elif self._state == "IN_POSITION":
            self._step_in_position(bar)

        return self._events

    # ── WAIT_SWEEP ─────────────────────────────────────────────────────────

    def _step_wait_sweep(self, bar: Bar, pool_evts: list) -> None:
        """等待反向流動性掃蕩（Raid 事件）。

        v2 BOTH 模式：上方被 Raid → 鎖 SHORT；下方被 Raid → 鎖 LONG。
        """
        if not self.risk.can_trade(self._session_state):
            self._transition("DONE", bar, "已達每節交易筆數上限或日虧限額，停手", {})
            return

        direction = self._effective_direction()

        for evt in pool_evts:
            if not isinstance(evt, Raid):
                continue

            # 方向過濾
            if direction == "BOTH":
                # 兩個方向都可，但避免重複掃同方向
                if evt.side in self._raided_sides:
                    continue
            elif direction == "SHORT" and evt.side != "BUY":
                continue
            elif direction == "LONG" and evt.side != "SELL":
                continue
            elif direction not in ("BOTH", "SHORT", "LONG"):
                continue

            # Determine locked direction
            if direction == "BOTH":
                locked = "SHORT" if evt.side == "BUY" else "LONG"
            else:
                locked = direction

            # SMT filter — check BEFORE committing state
            if self.config.smt_filter == "require":
                diverged = self._smt.check_divergence(
                    side=evt.side,
                    pool_created_t=None,
                    raid_t=bar.ts_utc,
                )
                if not diverged:
                    self._transition(
                        "WAIT_SWEEP", bar,
                        f"SMT 未背離，忽略掃蕩（{evt.kind} {evt.level:.2f}）",
                        {"raid_kind": evt.kind, "raid_level": evt.level, "smt": "no_divergence"},
                    )
                    continue  # try next pool event

            # Commit state
            if direction == "BOTH":
                self._locked_direction = locked
                self._raided_sides.add(evt.side)

            self._last_raid = evt
            self._raid_level = evt.level
            self._raid_extreme = evt.level
            self._mss_start_bar = self._bar_count
            # 重置位移段追蹤
            self._disp_high = bar.high
            self._disp_low = bar.low

            # 注意：first_setup_only 的名額在「MSS 確認」時才消耗——
            # 掃蕩後 MSS 沒出現不算一個 setup（朋友規則：第一個 MSS）
            self._transition(
                "WAIT_MSS", bar,
                f"掃蕩確認（{evt.kind} {evt.level:.2f}），鎖定方向={locked}，等 MSS（最多 {self.config.mss_timeout_bars} 根）",
                {"raid_kind": evt.kind, "raid_level": evt.level, "locked_direction": locked},
            )
            return  # 一次只處理一個 Raid

    # ── WAIT_MSS ───────────────────────────────────────────────────────────

    def _step_wait_mss(self, bar: Bar, mss_evts: list) -> None:
        """等位移+MSS；超時 → 回 WAIT_SWEEP。"""
        # 追蹤位移段極值
        if bar.high > self._disp_high:
            self._disp_high = bar.high
        if bar.low < self._disp_low:
            self._disp_low = bar.low

        bars_since = self._bar_count - self._mss_start_bar
        if bars_since > self.config.mss_timeout_bars:
            # 鎖定方向重置（bias=BOTH 時讓下一次掃蕩重新決定）
            if self._direction_bias == "BOTH":
                self._locked_direction = None
                self._raided_sides.clear()  # 允許再次掃蕩任何方向
            dest = "DONE" if (self.config.first_setup_only and self._first_setup_used) else "WAIT_SWEEP"
            self._transition(
                dest, bar,
                f"MSS 等待超時（{self.config.mss_timeout_bars} 根），{'收工（first_setup_only）' if dest == 'DONE' else '重回等待掃蕩'}",
                {"timeout_bars": bars_since},
            )
            return

        direction = self._effective_direction()
        if direction == "BOTH":
            return  # 尚未鎖定，不應到這裡

        for evt in mss_evts:
            if not isinstance(evt, MSS):
                continue
            # 方向過濾
            if direction == "SHORT" and evt.direction != "BEAR":
                continue
            if direction == "LONG" and evt.direction != "BULL":
                continue
            # 找最近的對應方向 FVG（加入 candle_stop_level 和 leg 資訊）
            # left_fvg=True 優先，但只要有 active FVG 即可（displacement 棒緊接其後也算）
            fvg = self._find_mss_fvg(evt.direction)
            if fvg is None:
                continue

            # FVG 過濾
            if not self._fvg_passes_filter(fvg, direction):
                continue

            self._entry_fvg = fvg
            self._mss_broken_level = evt.broken_swing_level
            self._entry_bar = self._bar_count
            entry_px = self._entry_price_for(fvg)

            # first_setup_only：MSS 正式確認，消耗當日唯一名額
            if self.config.first_setup_only:
                self._first_setup_used = True

            self._transition(
                "WAIT_RETRACE", bar,
                f"MSS 確認（{evt.direction}，破 {evt.broken_swing_level:.2f}），"
                f"掛 {'Sell' if direction == 'SHORT' else 'Buy'} Limit @ {entry_px:.2f}",
                {
                    "mss_broken_level": evt.broken_swing_level,
                    "fvg_top": fvg.top,
                    "fvg_bottom": fvg.bottom,
                    "fvg_ce": fvg.ce,
                    "candle_stop": fvg.candle_stop_level,
                },
            )
            self._submit_entry_order(bar, fvg)
            return

    def _find_mss_fvg(self, direction: str) -> "_EntryFVG | None":
        """從 FVGDetector 的 active list 找最近的對應方向 FVG。

        v2：同時從 FVGDetector._buf 取得第一棒的極值作為 candle_stop_level。
        """
        raid_t = self._last_raid.confirmed_at if self._last_raid else None
        matching = [
            fvg for fvg in self._fvg_det._active
            if fvg.direction == direction and not fvg.filled
            # 進場 FVG 必須來自掃蕩後的位移段，不能撿掃蕩前的舊缺口
            and (raid_t is None or fvg.anchor >= raid_t)
        ]
        if not matching:
            return None
        latest = max(matching, key=lambda f: f.anchor)

        # candle_stop_level：第一棒極值
        # FVG 由 b0, b1, b2 形成；b1 is anchor。在 _buf 中找 b0。
        candle_stop = latest.top if direction == "BEAR" else latest.bottom
        buf = self._fvg_det._buf
        if len(buf) >= 3:
            # b2 = latest bar that completed FVG；b0 = 2 bars before b2
            # 找 anchor（b1）在 buf 中的位置
            for i, b in enumerate(buf):
                if b.ts_utc == latest.anchor and i > 0:
                    b0 = buf[i - 1]
                    if direction == "BEAR":
                        candle_stop = b0.high  # 空單停損 = FVG 第一根 high
                    else:
                        candle_stop = b0.low   # 多單停損 = FVG 第一根 low
                    break

        return _EntryFVG(
            direction=latest.direction,
            top=latest.top,
            bottom=latest.bottom,
            ce=latest.ce,
            confirmed_at=latest.anchor,
            candle_stop_level=candle_stop,
            leg_high=self._disp_high,
            leg_low=self._disp_low,
        )

    def _fvg_passes_filter(self, fvg: "_EntryFVG", direction: str) -> bool:
        """fvg_filter 判斷（leg_equilibrium / prev_day_half / none）。"""
        mode = self.config.fvg_filter

        if mode == "none":
            return True

        if mode == "leg_equilibrium":
            # bearish FVG：proximal >= 位移段 equilibrium（proximal 在 premium 區）
            # bullish FVG：proximal <= 位移段 equilibrium（proximal 在 discount 區）
            eq = fvg.leg_equilibrium
            if eq == 0.0:
                return True  # 無法計算，放行
            if direction == "SHORT":
                return fvg.proximal >= eq
            else:
                return fvg.proximal <= eq

        elif mode == "prev_day_half":
            # 等同 v1 fvg_half_filter：FVG 須在前日 range 正確半段
            dr = self.bias.dealing_range
            if dr is None:
                return True
            if direction == "SHORT":
                return not dr.is_discount(fvg.proximal)
            else:
                return not dr.is_premium(fvg.proximal)

        # 兼容 v1 fvg_half_filter bool
        if self.config.fvg_half_filter and self.bias.dealing_range is not None:
            dr = self.bias.dealing_range
            if direction == "SHORT":
                if dr.is_discount(fvg.proximal):
                    return False
            else:
                if dr.is_premium(fvg.proximal):
                    return False

        return True

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
                direction = self._effective_direction()
                if direction == "SHORT":
                    return ote_high
                else:
                    return ote_low
            return fvg.proximal

    def _submit_entry_order(self, bar: Bar, fvg: "_EntryFVG") -> None:
        """計算停損口數並提交 Bracket。"""
        direction = self._effective_direction()
        entry_px = self._entry_price_for(fvg)

        # ── 停損計算 ─────────────────────────────────────────────────────────
        if self.config.stop_mode == "fvg_candle":
            # M13 精確：空單停損 = FVG 第一根 high；多單 = 第一根 low
            stop_px = fvg.candle_stop_level
            if stop_px == 0.0:
                # fallback：用 distal + 1 tick
                if direction == "SHORT":
                    stop_px = fvg.top + TICK
                else:
                    stop_px = fvg.bottom - TICK
        else:  # sweep_extreme
            buf = self.config.stop_buffer_ticks * TICK
            if direction == "SHORT":
                stop_px = self._raid_level + buf
            else:
                stop_px = self._raid_level - buf

        stop_dist = abs(entry_px - stop_px)

        # ── min/max_stop_points 過濾 ──────────────────────────────────────────
        min_sp = self.config.min_stop_points
        max_sp = self.config.max_stop_points
        if stop_dist < min_sp:
            dest = "DONE" if (self.config.first_setup_only and self._first_setup_used) else "WAIT_SWEEP"
            self._transition(
                dest, bar,
                f"停損距離 {stop_dist:.2f} pt < min_stop_points({min_sp})，放棄此 setup",
                {"stop_dist": stop_dist, "min_stop": min_sp},
            )
            if self._direction_bias == "BOTH":
                self._locked_direction = None
                self._raided_sides.clear()
            return
        if stop_dist > max_sp:
            dest = "DONE" if (self.config.first_setup_only and self._first_setup_used) else "WAIT_SWEEP"
            self._transition(
                dest, bar,
                f"停損距離 {stop_dist:.2f} pt > max_stop_points({max_sp})，放棄此 setup",
                {"stop_dist": stop_dist, "max_stop": max_sp},
            )
            if self._direction_bias == "BOTH":
                self._locked_direction = None
                self._raided_sides.clear()
            return

        # ── min_rr 過濾 ─────────────────────────────────────────────────────────
        if self.config.min_rr > 0.0:
            # 計算 T1 距離（預覽，不分配口數）
            targets_preview, t1_dist_preview = self._build_targets_v2(
                entry_px, stop_dist, 1, direction
            )
            if t1_dist_preview < self.config.min_rr * stop_dist:
                reason = (
                    f"T1 距離 {t1_dist_preview:.2f} pt < min_rr({self.config.min_rr})×"
                    f"stop({stop_dist:.2f})={self.config.min_rr * stop_dist:.2f}，放棄 setup"
                )
                if self.config.first_setup_only and self._first_setup_used:
                    self._transition("DONE", bar, reason, {"t1_dist": t1_dist_preview, "min_rr": self.config.min_rr})
                else:
                    self._transition("WAIT_SWEEP", bar, reason, {"t1_dist": t1_dist_preview, "min_rr": self.config.min_rr})
                if self._direction_bias == "BOTH":
                    self._locked_direction = None
                    self._raided_sides.clear()
                return

        # ── 口數 ─────────────────────────────────────────────────────────────
        et = _to_et(bar.ts_utc)
        size_factor = 1.0
        if self.config.thursday_size_factor != 1.0 and et.strftime("%a") == "Thu":
            size_factor = self.config.thursday_size_factor

        qty = int(self.risk.size_for(stop_dist) * size_factor)
        if qty < 1:
            # 風險預算開不出 1 口 → 誠實放棄，不可偷偷加大風險
            dest = "DONE" if (self.config.first_setup_only and self._first_setup_used) else "WAIT_SWEEP"
            self._transition(
                dest, bar,
                f"放棄 setup：停損 {stop_dist:.2f} pt 在 "
                f"{self.config.risk_per_trade_pct}% 風險下開不出 1 口"
                f"（每口風險 ${stop_dist * self.risk.cfg.point_value:.0f}）",
                {"stop_dist": stop_dist, "qty": 0},
            )
            if self._direction_bias == "BOTH":
                self._locked_direction = None
                self._raided_sides.clear()
            return

        # ── 停利目標 ─────────────────────────────────────────────────────────
        targets, t1_dist = self._build_targets_v2(entry_px, stop_dist, qty, direction)

        side: str = "SELL" if direction == "SHORT" else "BUY"
        order = Order(side=side, type="LIMIT", qty=qty, price=entry_px)  # type: ignore[arg-type]
        bracket = Bracket(entry=order, stop_price=stop_px, targets=targets)

        self._pending_bracket_id = self.broker.submit(bracket)
        self.bracket_targets[self._pending_bracket_id] = list(targets)
        self._entry_price = entry_px
        self._initial_stop_dist = stop_dist
        self._t1_dist = t1_dist
        self._trailing_milestone = 0

    def _build_targets_v2(
        self, entry_px: float, stop_dist: float, total_qty: int, direction: str
    ) -> tuple[list[tuple[float, int]], float]:
        """v2 停利目標，回傳 (targets, t1_dist)。"""
        mode = self.config.targets_mode

        if mode == "m13_liquidity":
            return self._build_m13_liquidity_targets(entry_px, stop_dist, total_qty, direction)
        elif mode == "fixed_points":
            return self._build_fixed_targets(entry_px, stop_dist, total_qty, direction), stop_dist * 1.0
        else:  # r_multiple
            return self._build_r_multiple_targets(entry_px, stop_dist, total_qty, direction), stop_dist * 1.0

    def _build_m13_liquidity_targets(
        self, entry_px: float, stop_dist: float, total_qty: int, direction: str
    ) -> tuple[list[tuple[float, int]], float]:
        """m13_liquidity 停利階梯。

        T1 = 位移方向上最近的對側內部流動性水位（未掃 swing 或未回補 FVG 的 CE），
             取距離進場最近且 >1R 者；若無則 1R
        T2 = 前一時段極值（AM 空單→ONL，多單→ONH），平 25%
        T3 = 前日極值（PDL/PDH），平剩餘
        每層前 dol_early_exit_ticks 提前掛單。
        某層缺失或比上層近 → 順延；全缺 → r_multiple fallback（1R/2R/3R）。
        """
        early = self.config.dol_early_exit_ticks * TICK
        fracs = self.config.tp_fractions   # (0.5, 0.25, 1.0)
        one_r = stop_dist
        max_target_dist = self.config.max_target_r * one_r

        def _adjusted(raw_price: float) -> float:
            """加入提前出場偏移，並對齊 tick。"""
            p = raw_price + early if direction == "SHORT" else raw_price - early
            return round(round(p / TICK) * TICK, 10)

        def _cap(p: float | None) -> float | None:
            """流動性目標超過 max_target_r → 視為缺層（改用 R 倍數 fallback）。

            極端日（如大跌隔天）的隔夜/前日極值可能在 10R 以外，
            掛在那裡等於尾倉永不出場，最後被移動停損收走。
            """
            if p is not None and abs(p - entry_px) > max_target_dist:
                return None
            return p

        # ── T1：最近的對側內部流動性，>1R 且 <=max_target_r，取最近者 ────────
        t1_raw: float | None = None
        internal_liq = self._get_internal_liquidity(entry_px, direction)
        for lvl in internal_liq:
            dist = abs(lvl - entry_px)
            if one_r < dist <= max_target_dist:
                t1_raw = lvl
                break  # 已從最近到最遠排序
        if t1_raw is None:
            # fallback 1R
            t1_raw = entry_px - one_r if direction == "SHORT" else entry_px + one_r

        t1_dist = abs(t1_raw - entry_px)
        t1_price = _adjusted(t1_raw)

        # ── T2：前時段極值（超過 R 上限視為缺層）──────────────────────────────
        t2_raw: float | None = None
        if direction == "SHORT":
            t2_raw = _cap(self._onl)   # 空單→隔夜低
        else:
            t2_raw = _cap(self._onh)   # 多單→隔夜高

        # ── T3：前日極值（超過 R 上限視為缺層）────────────────────────────────
        t3_raw: float | None = None
        if direction == "SHORT":
            t3_raw = _cap(self._pdl)
        else:
            t3_raw = _cap(self._pdh)

        # ── 有效性驗證 + 順延 ─────────────────────────────────────────────────
        # 空單：目標需 < entry_px；多單：目標需 > entry_px
        def _valid(p: float | None, prev_p: float | None) -> bool:
            if p is None:
                return False
            if direction == "SHORT" and p >= entry_px:
                return False
            if direction == "LONG" and p <= entry_px:
                return False
            if prev_p is not None:
                # 此層不能比上一層更遠（空單：此層 >= 上一層表示比上層靠近進場，不行）
                # 空單目標越小越遠，T2 要比 T1 更小
                if direction == "SHORT" and p >= prev_p:
                    return False  # T2 需比 T1 更低
                if direction == "LONG" and p <= prev_p:
                    return False  # T2 需比 T1 更高
            return True

        layers_raw: list[float | None] = [t1_raw, t2_raw, t3_raw]
        validated: list[float] = []
        last_valid: float | None = None
        for raw in layers_raw:
            if _valid(raw, last_valid):
                validated.append(raw)
                last_valid = raw
            # 否則跳過（順延）

        # 全缺 → r_multiple fallback
        if not validated:
            targets, _ = self._build_r_multiple_targets(entry_px, stop_dist, total_qty, direction)
            return targets, one_r

        # 若不足 3 層，補 r_multiple 填充（1R/2R/3R 依序）
        r_fallbacks = [
            (entry_px - stop_dist * m) if direction == "SHORT" else (entry_px + stop_dist * m)
            for m in (1.0, 2.0, 3.0)
        ]
        while len(validated) < 3:
            candidate = r_fallbacks[len(validated)]
            if _valid(candidate, validated[-1] if validated else None):
                validated.append(candidate)
            else:
                validated.append(validated[-1])   # 重複最後一層（全平）

        # ── 分配口數 ─────────────────────────────────────────────────────────
        remaining = total_qty
        targets: list[tuple[float, int]] = []

        qty1 = max(1, int(total_qty * fracs[0]))
        qty1 = min(qty1, remaining)
        targets.append((_adjusted(validated[0]), qty1))
        remaining -= qty1

        if remaining > 0:
            qty2 = max(1, int(total_qty * fracs[1]))
            qty2 = min(qty2, remaining)
            targets.append((_adjusted(validated[1]), qty2))
            remaining -= qty2

        if remaining > 0:
            targets.append((_adjusted(validated[2]), remaining))

        return targets, t1_dist

    def _get_internal_liquidity(self, entry_px: float, direction: str) -> list[float]:
        """取位移方向上，對側內部流動性水位列表（由近至遠，已確認且未掃）。

        使用 pool_tracker 的 swing 水位（SWING_LOW/HIGH），過濾方向後排序。
        """
        pools = self._pool_tracker._pools
        candidates: list[float] = []
        for p in pools:
            if p.swept or p.raided:
                continue
            if direction == "SHORT":
                # 空單目標在下方：取 SELL 側水位（SWING_LOW / EQUAL_LOWS / PDL / ONL）
                if p.side == "SELL" and p.level < entry_px:
                    candidates.append(p.level)
            else:
                # 多單目標在上方：取 BUY 側水位
                if p.side == "BUY" and p.level > entry_px:
                    candidates.append(p.level)

        if direction == "SHORT":
            # 從最近（最高）到最遠（最低）
            candidates.sort(reverse=True)
        else:
            candidates.sort()
        return candidates

    def _build_fixed_targets(
        self, entry_px: float, stop_dist: float, total_qty: int, direction: str
    ) -> list[tuple[float, int]]:
        """fixed_points 模式停利目標。"""
        fracs = self.config.tp_fractions
        tp_pts = self.config.tp_points
        targets: list[tuple[float, int]] = []
        remaining = total_qty

        for i, (pts, frac) in enumerate(zip(tp_pts, fracs)):
            if remaining <= 0:
                break
            if i < len(tp_pts) - 1:
                qty = max(1, int(total_qty * frac))
                qty = min(qty, remaining)
            else:
                qty = remaining
            if direction == "SHORT":
                price = entry_px - pts
            else:
                price = entry_px + pts
            targets.append((price, qty))
            remaining -= qty

        if remaining > 0 and targets:
            last_price, last_qty = targets[-1]
            targets[-1] = (last_price, last_qty + remaining)

        return targets

    def _build_r_multiple_targets(
        self, entry_px: float, stop_dist: float, total_qty: int, direction: str
    ) -> tuple[list[tuple[float, int]], float]:
        """r_multiple 模式停利目標（1R/2R/3R）。"""
        fracs = self.config.tp_fractions
        targets: list[tuple[float, int]] = []
        remaining = total_qty
        multiples = (1.0, 2.0, 3.0)

        for i, (mult, frac) in enumerate(zip(multiples, fracs)):
            if remaining <= 0:
                break
            if i < len(multiples) - 1:
                qty = max(1, int(total_qty * frac))
                qty = min(qty, remaining)
            else:
                qty = remaining
            if direction == "SHORT":
                price = entry_px - stop_dist * mult
            else:
                price = entry_px + stop_dist * mult
            targets.append((price, qty))
            remaining -= qty

        if remaining > 0 and targets:
            last_price, last_qty = targets[-1]
            targets[-1] = (last_price, last_qty + remaining)

        return targets, stop_dist * 1.0

    # ── WAIT_RETRACE ──────────────────────────────────────────────────────

    def _step_wait_retrace(self, bar: Bar, fvg_evts: list) -> None:
        """等限價單成交；超時或 FVG 填滿 → 撤單回 WAIT_SWEEP。"""
        bars_since = self._bar_count - self._entry_bar
        if bars_since > self.config.entry_timeout_bars:
            if self._pending_bracket_id:
                self.broker.cancel(self._pending_bracket_id)
                self._pending_bracket_id = None
            if self._direction_bias == "BOTH":
                self._locked_direction = None
                self._raided_sides.clear()
            dest = "DONE" if (self.config.first_setup_only and self._first_setup_used) else "WAIT_SWEEP"
            self._transition(
                dest, bar,
                f"進場超時（{self.config.entry_timeout_bars} 根），撤銷限價單，{'收工（first_setup_only）' if dest == 'DONE' else '重回等待掃蕩'}",
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
                if self._direction_bias == "BOTH":
                    self._locked_direction = None
                    self._raided_sides.clear()
                dest = "DONE" if (self.config.first_setup_only and self._first_setup_used) else "WAIT_SWEEP"
                self._transition(
                    dest, bar,
                    f"FVG 被收盤穿越失效，撤銷限價單，{'收工（first_setup_only）' if dest == 'DONE' else '重回等待掃蕩'}",
                    {"fvg_top": fvg.top, "fvg_bottom": fvg.bottom},
                )
                return

    # ── IN_POSITION ────────────────────────────────────────────────────────

    def _step_in_position(self, bar: Bar) -> None:
        """管理浮盈停損收緊（v2：基於 T1 距離 trail_half_at/trail_be_at）。"""
        if self.broker.position is None:
            return

        pos = self.broker.position
        entry_px = pos.avg_entry
        current_price = bar.close
        direction = self._effective_direction()

        if direction == "SHORT":
            float_profit_pts = entry_px - current_price
        else:
            float_profit_pts = current_price - entry_px

        t1 = self._t1_dist
        if t1 <= 0:
            t1 = self._initial_stop_dist  # fallback

        progress = float_profit_pts / t1  # 0% → 100% = T1 距離

        # trail_be_at（預設 75%）→ BE
        if self._trailing_milestone < 2 and progress >= self.config.trail_be_at:
            new_stop = entry_px
            self._update_stop(pos, new_stop, bar, f"浮盈達 T1×{self.config.trail_be_at:.0%}，停損移至 BE")
            self._trailing_milestone = 2

        # trail_half_at（預設 50%）→ 停損收至初始距離一半
        elif self._trailing_milestone < 1 and progress >= self.config.trail_half_at:
            if direction == "SHORT":
                new_stop = entry_px - self._initial_stop_dist * 0.5
            else:
                new_stop = entry_px + self._initial_stop_dist * 0.5
            self._update_stop(pos, new_stop, bar, f"浮盈達 T1×{self.config.trail_half_at:.0%}，停損收至 50% 距離")
            self._trailing_milestone = 1

    def _update_stop(self, pos, new_stop: float, bar: Bar, msg: str) -> None:
        """更新 position 停損價（只允許往有利方向移動），並記錄移動時點。"""
        direction = self._effective_direction()
        new_stop = round(round(new_stop / TICK) * TICK, 10)  # 對齊 tick
        moved = False
        if direction == "SHORT":
            if new_stop < pos.stop_price:
                pos.stop_price = new_stop
                moved = True
        else:
            if new_stop > pos.stop_price:
                pos.stop_price = new_stop
                moved = True
        if moved:
            self.stop_moves.setdefault(pos.bracket_id, []).append(
                {"t_utc": bar.ts_utc, "price": new_stop, "reason": msg}
            )
            self._transition("IN_POSITION", bar, msg, {"new_stop": new_stop})

    # ── Broker 事件處理 ───────────────────────────────────────────────────

    def _handle_broker_event(self, bev, bar: Bar) -> None:
        """處理 SimBroker 回調事件，推進策略狀態機。"""
        from engine.sim.broker import TradeOpened, TradeClosed

        if isinstance(bev, TradeOpened):
            if self._state == "WAIT_RETRACE":
                self._trade_open_bar = self._bar_count
                self._session_state.trades_taken += 1
                et = _to_et(bar.ts_utc)
                subwindow = _entry_subwindow(et)
                self._transition(
                    "IN_POSITION", bar,
                    f"限價單成交 @ {bev.entry_price:.2f}，持倉 {bev.qty} 口，"
                    f"停損 {self.broker.position.stop_price if self.broker.position else 'N/A'}，"
                    f"子窗={subwindow}",
                    {
                        "entry_price": bev.entry_price,
                        "qty": bev.qty,
                        "entry_subwindow": subwindow,
                    },
                )

        elif isinstance(bev, TradeClosed):
            trade = bev.trade
            self._session_state.daily_r_accumulated += trade.r_multiple
            self.risk.on_trade_closed(trade)
            self.closed_trades.append(trade)

            if self._state == "IN_POSITION":
                # BOTH 模式：平倉後重置鎖定，回 WAIT_SWEEP 雙向等待
                if self._direction_bias == "BOTH":
                    self._locked_direction = None
                    self._raided_sides.clear()  # 允許再次掃蕩任何方向
                force_done = self.config.first_setup_only and self._first_setup_used
                if not force_done and self.risk.can_trade(self._session_state):
                    self._transition(
                        "WAIT_SWEEP", bar,
                        f"交易結束（{trade.exit_reason}，{trade.r_multiple:+.2f}R），可再進場，等下一個掃蕩",
                        {"exit_reason": trade.exit_reason, "r": trade.r_multiple},
                    )
                else:
                    reason = "first_setup_only 收工" if force_done else "已達每節限制，收工"
                    self._transition(
                        "DONE", bar,
                        f"交易結束（{trade.exit_reason}，{trade.r_multiple:+.2f}R），{reason}",
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
