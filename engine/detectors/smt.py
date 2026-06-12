"""SMTChecker — ES/NQ 背離過濾器（§2.5 SMT divergence）。"""
from __future__ import annotations
from collections import deque
from datetime import datetime
from engine.core.types import Bar


class SMTChecker:
    """逐分鐘餵入 NQ/ES bar，提供 check_divergence 查詢。

    SMT (Smart Money Technique) divergence:
    - BUY raid (NQ 掃上方水位): ES 在參考期間的最高 high 為基準；
      若 ES 在 raid_t 當根（含前 1 根容差）的 high 未突破該基準 → 背離成立（True）
    - SELL raid 對稱（low）
    無前視：只用 <= raid_t 的資料。
    """

    def __init__(self, lookback_bars: int = 30) -> None:
        self._lookback = lookback_bars
        # 滾動歷史：(ts, high, low) deque（固定長度防記憶體爆炸）
        self._nq_history: deque[tuple[datetime, float, float]] = deque(maxlen=500)
        self._es_history: deque[tuple[datetime, float, float]] = deque(maxlen=500)
        self._last_es: tuple[datetime, float, float] | None = None  # 缺分鐘沿用

    def on_bar(self, nq_bar: Bar, es_bar: Bar | None) -> None:
        """每根 1 分 K 呼叫一次。es_bar=None 時沿用前值。"""
        self._nq_history.append((nq_bar.ts_utc, nq_bar.high, nq_bar.low))
        if es_bar is not None:
            self._last_es = (es_bar.ts_utc, es_bar.high, es_bar.low)
        # 補齊 ES（缺分鐘沿用前值，ts 對齊 nq 當根）
        if self._last_es is not None:
            self._es_history.append((nq_bar.ts_utc, self._last_es[1], self._last_es[2]))

    def check_divergence(
        self,
        side: str,           # "BUY" | "SELL"
        pool_created_t: datetime | None,
        raid_t: datetime,
    ) -> bool:
        """
        Returns True if SMT divergence is confirmed (ES did NOT confirm NQ's raid).

        side="BUY" (NQ raided buy-side / sweep above):
          ES reference high = max high in [pool_created_t, raid_t) window
          ES at raid_t (or raid_t-1 tolerance): high does NOT exceed reference → divergence
        side="SELL" symmetric.
        """
        # Collect ES bars <= raid_t
        es_bars = [(ts, h, lo) for ts, h, lo in self._es_history if ts <= raid_t]
        if not es_bars:
            return False  # no ES data → can't confirm divergence, be conservative

        # Determine reference window start
        if pool_created_t is not None:
            window_start = pool_created_t
        else:
            # Use last smt_lookback_bars bars before raid_t as reference window
            bars_before = [(ts, h, lo) for ts, h, lo in es_bars if ts < raid_t]
            if len(bars_before) > self._lookback:
                window_start = bars_before[-self._lookback][0]
            elif bars_before:
                window_start = bars_before[0][0]
            else:
                return False

        # Reference extremes in [window_start, raid_t) — excluding raid bar itself
        reference_bars = [(ts, h, lo) for ts, h, lo in es_bars
                          if window_start <= ts < raid_t]
        if not reference_bars:
            return False

        # ES at raid_t with ±1 bar tolerance
        sorted_es = sorted(es_bars, key=lambda x: x[0])
        raid_idx = next((i for i, (ts, _, _) in enumerate(sorted_es) if ts == raid_t), None)
        if raid_idx is None:
            # no ES bar at raid_t — use last available
            tolerance_bars = sorted_es[-1:]
        else:
            start_idx = max(0, raid_idx - 1)
            tolerance_bars = sorted_es[start_idx: raid_idx + 1]

        if side == "BUY":
            ref_high = max(h for _, h, _ in reference_bars)
            raid_high = max(h for _, h, _ in tolerance_bars) if tolerance_bars else 0.0
            # divergence: ES did NOT break reference high
            return raid_high <= ref_high
        else:  # SELL
            ref_low = min(lo for _, _, lo in reference_bars)
            raid_low = min(lo for _, _, lo in tolerance_bars) if tolerance_bars else float("inf")
            # divergence: ES did NOT break reference low
            return raid_low >= ref_low
