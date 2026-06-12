"""訂單、Bracket、部位、已平倉交易型別。"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


# ─── 列舉常數 ────────────────────────────────────────────────────────────────

Side   = Literal["BUY", "SELL"]
OType  = Literal["LIMIT", "STOP", "MARKET"]
Status = Literal["PENDING", "FILLED", "CANCELLED"]
ExitReason = Literal["STOP", "TARGET", "EOD", "MANUAL"]


# ─── 訂單 ────────────────────────────────────────────────────────────────────

@dataclass
class Order:
    """單筆訂單。"""
    side: Side
    type: OType
    qty: int
    price: float = 0.0          # LIMIT / STOP 用；MARKET 忽略
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: Status = "PENDING"
    created_at: datetime | None = None
    filled_at: datetime | None = None
    fill_price: float = 0.0


# ─── Bracket（OCO 進出場組合）────────────────────────────────────────────────

@dataclass
class Bracket:
    """進場單 + 停損價 + 分批停利目標。

    語意（OCO）：進場成交後掛出停損與停利；停損觸發則取消停利，反之亦然。
    targets: [(price, qty), ...] 由近到遠排列。
    id 為整組 bracket 的識別，進場 Order.id 會沿用此值。
    """
    entry: Order
    stop_price: float
    targets: list[tuple[float, int]]    # [(price, qty), ...]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        # 讓進場單的 id 與 bracket id 一致，便於追蹤
        self.entry.id = self.id


# ─── 部位 ────────────────────────────────────────────────────────────────────

@dataclass
class Position:
    """現有持倉。qty > 0 表示有部位。"""
    side: Side
    qty: int
    avg_entry: float
    stop_price: float
    remaining_targets: list[tuple[float, int]] = field(default_factory=list)
    realized_pnl_pts: float = 0.0
    realized_pnl_usd: float = 0.0
    unrealized_pnl_pts: float = 0.0
    unrealized_pnl_usd: float = 0.0
    bracket_id: str = ""

    def update_unrealized(self, current_price: float, point_value: float) -> None:
        """以當前價格更新未實現損益。"""
        if self.side == "BUY":
            self.unrealized_pnl_pts = (current_price - self.avg_entry) * self.qty
        else:
            self.unrealized_pnl_pts = (self.avg_entry - current_price) * self.qty
        self.unrealized_pnl_usd = self.unrealized_pnl_pts * point_value


# ─── 已平倉交易紀錄 ──────────────────────────────────────────────────────────

@dataclass
class PartialFill:
    """單次分批出場明細。"""
    price: float
    qty: int
    ts: datetime
    reason: ExitReason


@dataclass
class Trade:
    """一筆完整交易（進場 → 全部出場）。"""
    side: Side
    entry_price: float
    entry_time: datetime
    qty: int                        # 原始進場口數
    initial_stop_distance: float    # 進場價 ↔ 初始停損距離（點數，正值）
    exit_fills: list[PartialFill] = field(default_factory=list)

    # 結果（由 close() 填入）
    pnl_pts: float = 0.0
    pnl_usd: float = 0.0
    r_multiple: float = 0.0

    exit_reason: ExitReason = "MANUAL"
    ambiguous: bool = False         # 同根 K 棒停損/停利同時觸及
    bracket_id: str = ""

    def close(self, point_value: float, commission_per_side: float) -> None:
        """根據 exit_fills 計算損益與 R 倍數。"""
        total_qty = sum(f.qty for f in self.exit_fills)
        if total_qty == 0:
            return
        weighted_exit = sum(f.price * f.qty for f in self.exit_fills) / total_qty

        if self.side == "BUY":
            pnl_pts = weighted_exit - self.entry_price
        else:
            pnl_pts = self.entry_price - weighted_exit

        self.pnl_pts = pnl_pts * self.qty
        # 手續費：兩邊各一次（以總口數計）
        commission = commission_per_side * self.qty * 2
        self.pnl_usd = self.pnl_pts * point_value - commission

        if self.initial_stop_distance != 0:
            self.r_multiple = pnl_pts / self.initial_stop_distance
        else:
            self.r_multiple = 0.0
