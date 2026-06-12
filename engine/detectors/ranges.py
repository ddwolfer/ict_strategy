"""DealingRange：§7 Premium/Discount 判定與 OTE 區計算。"""
from __future__ import annotations
from dataclasses import dataclass
from engine.core.types import Bar
from engine.core.sessions import trading_date
from datetime import date


@dataclass
class DealingRange:
    """交易範圍，支援 premium/discount 與 OTE 判定。"""
    high: float
    low: float

    @property
    def equilibrium(self) -> float:
        return (self.high + self.low) / 2

    def is_premium(self, price: float) -> bool:
        """價格高於均衡點（範圍上半段）。"""
        return price > self.equilibrium

    def is_discount(self, price: float) -> bool:
        """價格低於均衡點（範圍下半段）。"""
        return price < self.equilibrium

    def ote_zone(self, use_bodies: bool = True) -> tuple[float, float]:
        """OTE 62%–79% retracement 區間，回傳 (ote_low, ote_high)。

        Fibonacci retracement from the high back toward the low:
          - 62% retracement: high - 0.62 * range
          - 79% retracement: high - 0.79 * range
        The lower value is ote_low, higher is ote_high.
        """
        rng = self.high - self.low
        ote_high = self.high - 0.62 * rng  # closer to high
        ote_low = self.high - 0.79 * rng   # deeper retracement
        return (ote_low, ote_high)

    @classmethod
    def from_lookback(
        cls,
        bars: list[Bar],
        lookback_days: int = 20,
        use_bodies: bool = True,
    ) -> "DealingRange":
        """從 lookback_days 個交易日的 bars 計算 DealingRange。

        use_bodies=True (Model 1 default): use open/close bodies instead of wicks.
        """
        if not bars:
            raise ValueError("bars is empty")
        all_days = sorted({trading_date(b.ts_utc) for b in bars})
        if len(all_days) > lookback_days:
            all_days = all_days[-lookback_days:]
        day_set = set(all_days)
        subset = [b for b in bars if trading_date(b.ts_utc) in day_set]
        if use_bodies:
            high = max(max(b.open, b.close) for b in subset)
            low = min(min(b.open, b.close) for b in subset)
        else:
            high = max(b.high for b in subset)
            low = min(b.low for b in subset)
        return cls(high=high, low=low)
