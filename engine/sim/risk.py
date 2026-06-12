"""RiskManager — ICT 風控規則（倉位計算 + 狀態機）。"""
from __future__ import annotations

from dataclasses import dataclass

from engine.core.types import POINT_VALUE
from engine.sim.orders import Trade


# ─── 設定 ────────────────────────────────────────────────────────────────────

@dataclass
class RiskConfig:
    """風控設定（全部欄位均有預設值）。"""
    risk_per_trade_pct: float = 0.5          # 每筆風險佔權益比例（%）
    account_equity: float = 50_000.0         # 初始帳戶淨值（美元）
    max_trades_per_session: int = 2          # 每節最多交易筆數
    daily_loss_limit_r: float = -2.0         # 單日最大虧損（R，負值）
    halve_after_loss: bool = True            # 虧損後 R% 減半
    halve_after_win_streak: int = 5          # 連勝 N 筆後 R% 減半
    point_value: float = POINT_VALUE


@dataclass
class SessionState:
    """每節交易狀態，由呼叫方管理並傳入 can_trade()。"""
    trades_taken: int = 0
    daily_r_accumulated: float = 0.0   # 本日已累計 R（可正可負）


# ─── RiskManager ─────────────────────────────────────────────────────────────

class RiskManager:
    """ICT 倉位計算與風控狀態機。

    R% 乘數為計算式（非累積式）：multiplier = 0.5^loss_level × streak_factor
    ① 虧損減半：每筆虧損 loss_level +1（已減半再虧繼續減半，Model 1/10 規則），
       恢復條件：current_equity >= equity_after_loss + loss_amount × 0.5，
       達成後 loss_level 歸零（恢復原始 R%）。
    ② 連勝減半：連勝達 halve_after_win_streak 筆後 streak_factor = 0.5，
       任何虧損使連勝歸零、streak_factor 回到 1（此時改由 ① 接手）。
    """

    def __init__(self, config: RiskConfig | None = None) -> None:
        self.cfg = config or RiskConfig()
        self._current_equity: float = self.cfg.account_equity
        self._win_streak: int = 0

        # 虧損減半層級與恢復追蹤
        self._loss_level: int = 0
        self._loss_recovery_target: float = 0.0  # 超過此值即恢復

    # ── 公開介面 ─────────────────────────────────────────────────────────────

    def size_for(self, stop_distance_points: float) -> int:
        """計算合理口數（向下取整，最少 0）。

        risk_usd = equity × (risk_pct / 100) × multiplier
        contracts = floor(risk_usd / (stop_distance_points × point_value))
        """
        if stop_distance_points <= 0:
            return 0
        risk_usd = (
            self._current_equity
            * (self.cfg.risk_per_trade_pct / 100.0)
            * self.risk_multiplier
        )
        risk_per_contract = stop_distance_points * self.cfg.point_value
        if risk_per_contract <= 0:
            return 0
        contracts = int(risk_usd / risk_per_contract)
        return max(0, contracts)

    def can_trade(self, session_state: SessionState) -> bool:
        """是否允許再下一筆單。"""
        if session_state.trades_taken >= self.cfg.max_trades_per_session:
            return False
        if session_state.daily_r_accumulated <= self.cfg.daily_loss_limit_r:
            return False
        return True

    def on_trade_closed(self, trade: Trade) -> None:
        """交易結束後更新淨值、連勝計數、R% 狀態機。"""
        pre_equity = self._current_equity
        self._current_equity += trade.pnl_usd

        if trade.r_multiple > 0:
            # 贏單
            self._win_streak += 1
            self._check_loss_recovery()
        else:
            # 輸單（含 r_multiple == 0 視為不連勝）
            self._win_streak = 0
            if self.cfg.halve_after_loss:
                loss_amount = pre_equity - self._current_equity   # 正值
                # 回補目標：從虧損後淨值往上回補 50% 的虧損金額
                self._loss_recovery_target = self._current_equity + loss_amount * 0.5
                self._loss_level += 1

    # ── 查詢 ─────────────────────────────────────────────────────────────────

    @property
    def current_equity(self) -> float:
        return self._current_equity

    @property
    def risk_multiplier(self) -> float:
        """計算式乘數：0.5^loss_level × (連勝達標 ? 0.5 : 1)。"""
        mult = 0.5 ** self._loss_level
        if self._win_streak >= self.cfg.halve_after_win_streak:
            mult *= 0.5
        return mult

    @property
    def win_streak(self) -> int:
        return self._win_streak

    @property
    def halved_due_to_loss(self) -> bool:
        return self._loss_level > 0

    # ── 內部狀態機 ───────────────────────────────────────────────────────────

    def _check_loss_recovery(self) -> None:
        """淨值回補至目標後，虧損減半層級全數解除（恢復原始 R%）。"""
        if self._loss_level == 0:
            return
        if self._current_equity >= self._loss_recovery_target:
            self._loss_level = 0
