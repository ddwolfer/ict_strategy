"""LiquidityPoolTracker：§3 流動性池偵測與掃蕩/奇襲事件。"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Literal
from engine.core.types import Bar, PoolCreated, PoolSwept, Raid, SwingConfirmed, TICK
from engine.core.sessions import trading_date, is_in_window
from engine.detectors.swings import SwingDetector


@dataclass
class _Pool:
    kind: str
    side: Literal["BUY", "SELL"]
    level: float
    swept: bool = False
    sweep_bar_idx: int = -1   # global bar index when swept
    raided: bool = False      # raid event already emitted for this pool


class LiquidityPoolTracker:
    """組合 SwingDetector；逐根餵入，輸出 PoolCreated / PoolSwept / Raid。

    Order of operations per bar:
      1. Sweep check against CURRENT pool levels (before any updates)
      2. Raid check for recently-swept pools
      3. Update RTH, overnight, session hi/lo
      4. Emit new pools (PDH/PDL/ONH/ONL/SESSION/SWING/EQUAL)
    """

    def __init__(self, n: int = 1, r: int = 3, eq_tol: int = 2) -> None:
        self.r = r
        self.eq_tol_pts = eq_tol * TICK
        self._swing_det = SwingDetector(n=n)
        self._pools: list[_Pool] = []
        self._bar_count = 0

        # state for PDH/PDL computation
        self._prev_rth_high: float | None = None
        self._prev_rth_low: float | None = None
        self._cur_rth_high: float | None = None
        self._cur_rth_low: float | None = None
        self._cur_rth_day: date | None = None

        # overnight tracking
        self._cur_on_high: float | None = None
        self._cur_on_low: float | None = None
        self._on_trading_day: date | None = None

        # session high/low (rolling from 09:30 ET)
        self._sess_high: float | None = None
        self._sess_low: float | None = None
        self._sess_trading_day: date | None = None

        # swing history for equal highs/lows (keep sorted list of confirmed levels)
        self._swing_high_levels: list[float] = []
        self._swing_low_levels: list[float] = []
        # set of (level_a, level_b) pairs already emitted as EQUAL_HIGHS/LOWS
        self._eq_high_pairs: set[tuple[float, float]] = set()
        self._eq_low_pairs: set[tuple[float, float]] = set()

        # sweep tracker: (pool, sweep_bar_idx) for raid detection
        self._sweep_tracker: list[tuple[_Pool, int]] = []

    # ─── public ──────────────────────────────────────────────────────────

    def on_bar(self, bar: Bar) -> list[PoolCreated | PoolSwept | Raid]:
        idx = self._bar_count
        self._bar_count += 1
        events: list[PoolCreated | PoolSwept | Raid] = []
        td = trading_date(bar.ts_utc)

        # ── STEP 1: Sweep detection (current bar vs existing pool levels) ──
        for pool in self._pools:
            if pool.swept:
                continue
            if pool.side == "BUY" and bar.high > pool.level:
                pool.swept = True
                pool.sweep_bar_idx = idx
                self._sweep_tracker.append((pool, idx))
                events.append(PoolSwept(bar.ts_utc, pool.kind, pool.side, pool.level))
            elif pool.side == "SELL" and bar.low < pool.level:
                pool.swept = True
                pool.sweep_bar_idx = idx
                self._sweep_tracker.append((pool, idx))
                events.append(PoolSwept(bar.ts_utc, pool.kind, pool.side, pool.level))

        # ── STEP 2: Raid detection ────────────────────────────────────
        for pool, sweep_idx in self._sweep_tracker:
            if pool.raided:
                continue
            bars_since = idx - sweep_idx
            if bars_since > self.r:
                continue
            if pool.side == "BUY" and bar.close < pool.level:
                pool.raided = True
                events.append(Raid(bar.ts_utc, pool.kind, pool.side, pool.level))
            elif pool.side == "SELL" and bar.close > pool.level:
                pool.raided = True
                events.append(Raid(bar.ts_utc, pool.kind, pool.side, pool.level))
        # clean up entries older than r bars
        self._sweep_tracker = [
            (p, si) for p, si in self._sweep_tracker if idx - si <= self.r
        ]

        # ── STEP 3 & 4: Update reference levels and emit new pools ───

        # PDH / PDL (RTH 09:30–16:00 ET hi/lo of previous day)
        if is_in_window(bar.ts_utc, "RTH"):
            if td != self._cur_rth_day:
                # New trading day started — roll over previous RTH range
                if self._cur_rth_day is not None:
                    self._prev_rth_high = self._cur_rth_high
                    self._prev_rth_low = self._cur_rth_low
                    if self._prev_rth_high is not None:
                        p = _Pool("PDH", "BUY", self._prev_rth_high)
                        self._pools.append(p)
                        events.append(PoolCreated(bar.ts_utc, "PDH", "BUY", self._prev_rth_high))
                    if self._prev_rth_low is not None:
                        p = _Pool("PDL", "SELL", self._prev_rth_low)
                        self._pools.append(p)
                        events.append(PoolCreated(bar.ts_utc, "PDL", "SELL", self._prev_rth_low))
                self._cur_rth_day = td
                self._cur_rth_high = bar.high
                self._cur_rth_low = bar.low
            else:
                if self._cur_rth_high is None or bar.high > self._cur_rth_high:
                    self._cur_rth_high = bar.high
                if self._cur_rth_low is None or bar.low < self._cur_rth_low:
                    self._cur_rth_low = bar.low

        # ONH / ONL (OVERNIGHT bars of the current trading day)
        if is_in_window(bar.ts_utc, "OVERNIGHT"):
            if td != self._on_trading_day:
                # New overnight session — emit previous overnight range as pools
                if self._on_trading_day is not None:
                    if self._cur_on_high is not None:
                        p = _Pool("ONH", "BUY", self._cur_on_high)
                        self._pools.append(p)
                        events.append(PoolCreated(bar.ts_utc, "ONH", "BUY", self._cur_on_high))
                    if self._cur_on_low is not None:
                        p = _Pool("ONL", "SELL", self._cur_on_low)
                        self._pools.append(p)
                        events.append(PoolCreated(bar.ts_utc, "ONL", "SELL", self._cur_on_low))
                self._on_trading_day = td
                self._cur_on_high = bar.high
                self._cur_on_low = bar.low
            else:
                if bar.high > self._cur_on_high:
                    self._cur_on_high = bar.high
                if bar.low < self._cur_on_low:
                    self._cur_on_low = bar.low

        # SESSION_HIGH / SESSION_LOW (rolling since 09:30 ET)
        if is_in_window(bar.ts_utc, "RTH"):
            if td != self._sess_trading_day:
                # First RTH bar of a new day — emit initial SESSION pools
                self._sess_trading_day = td
                self._sess_high = bar.high
                self._sess_low = bar.low
                p_hi = _Pool("SESSION_HIGH", "BUY", bar.high)
                p_lo = _Pool("SESSION_LOW", "SELL", bar.low)
                self._pools.append(p_hi)
                self._pools.append(p_lo)
                events.append(PoolCreated(bar.ts_utc, "SESSION_HIGH", "BUY", bar.high))
                events.append(PoolCreated(bar.ts_utc, "SESSION_LOW", "SELL", bar.low))
            else:
                # Rolling update — mutate the pool level in-place
                if bar.high > self._sess_high:
                    old_level = self._sess_high
                    self._sess_high = bar.high
                    for p in self._pools:
                        if p.kind == "SESSION_HIGH" and p.level == old_level and not p.swept:
                            p.level = bar.high
                if bar.low < self._sess_low:
                    old_level = self._sess_low
                    self._sess_low = bar.low
                    for p in self._pools:
                        if p.kind == "SESSION_LOW" and p.level == old_level and not p.swept:
                            p.level = bar.low

        # SWING_HIGH / SWING_LOW → also check EQUAL_HIGHS / EQUAL_LOWS
        swing_events = self._swing_det.on_bar(bar)
        for ev in swing_events:
            if ev.side == "HIGH":
                # Check equal highs BEFORE appending (compare against existing levels)
                eq_events = self._check_equal_highs(bar, ev.level)
                events.extend(eq_events)
                self._swing_high_levels.append(ev.level)
                p = _Pool("SWING_HIGH", "BUY", ev.level)
                self._pools.append(p)
                events.append(PoolCreated(bar.ts_utc, "SWING_HIGH", "BUY", ev.level))
            else:
                eq_events = self._check_equal_lows(bar, ev.level)
                events.extend(eq_events)
                self._swing_low_levels.append(ev.level)
                p = _Pool("SWING_LOW", "SELL", ev.level)
                self._pools.append(p)
                events.append(PoolCreated(bar.ts_utc, "SWING_LOW", "SELL", ev.level))

        return events

    # ─── helpers ─────────────────────────────────────────────────────────

    def _check_equal_highs(self, bar: Bar, new_level: float) -> list[PoolCreated]:
        """Emit EQUAL_HIGHS pool if new_level matches any existing swing high within tolerance.
        Use the more extreme (higher) value as the pool level. Avoid duplicate pairs.
        """
        events: list[PoolCreated] = []
        for prev in self._swing_high_levels:
            if abs(prev - new_level) <= self.eq_tol_pts:
                level = max(prev, new_level)
                pair = (min(prev, new_level), max(prev, new_level))
                if pair not in self._eq_high_pairs:
                    self._eq_high_pairs.add(pair)
                    p = _Pool("EQUAL_HIGHS", "BUY", level)
                    self._pools.append(p)
                    events.append(PoolCreated(bar.ts_utc, "EQUAL_HIGHS", "BUY", level))
        return events

    def _check_equal_lows(self, bar: Bar, new_level: float) -> list[PoolCreated]:
        """Emit EQUAL_LOWS pool if new_level matches any existing swing low within tolerance.
        Use the more extreme (lower) value as the pool level. Avoid duplicate pairs.
        """
        events: list[PoolCreated] = []
        for prev in self._swing_low_levels:
            if abs(prev - new_level) <= self.eq_tol_pts:
                level = min(prev, new_level)
                pair = (min(prev, new_level), max(prev, new_level))
                if pair not in self._eq_low_pairs:
                    self._eq_low_pairs.add(pair)
                    p = _Pool("EQUAL_LOWS", "SELL", level)
                    self._pools.append(p)
                    events.append(PoolCreated(bar.ts_utc, "EQUAL_LOWS", "SELL", level))
        return events
