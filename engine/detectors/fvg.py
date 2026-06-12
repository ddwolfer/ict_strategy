"""FVGDetector：§4 三根 K 棒 Fair Value Gap，含生命週期事件。"""
from __future__ import annotations
from dataclasses import dataclass
from engine.core.types import Bar, FVGCreated, FVGTouched, FVGFilled, TICK


@dataclass
class _FVGState:
    anchor: object  # datetime of bar i+1
    direction: str  # "BULL" or "BEAR"
    top: float
    bottom: float
    ce: float
    touched: bool = False
    filled: bool = False


class FVGDetector:
    """偵測 FVG 並維護生命週期（fresh → touched → filled）。

    Bullish FVG (b0, b1, b2):
      - Created when b2.low > b0.high  (gap size >= min_gap)
      - range = [b0.high (bottom), b2.low (top)]
      - Touched: bar.low <= top (price enters gap from above)
      - Filled: bar.low <= bottom (price reaches far edge)

    Bearish FVG:
      - Created when b2.high < b0.low
      - range = [b2.high (bottom), b0.low (top)]
      - Touched: bar.high >= bottom (price enters gap from below)
      - Filled: bar.high >= top (price reaches far edge)
    """

    def __init__(self, min_gap_ticks: int = 1) -> None:
        self.min_gap = min_gap_ticks * TICK
        self._buf: list[Bar] = []
        self._active: list[_FVGState] = []

    def on_bar(self, bar: Bar) -> list[FVGCreated | FVGTouched | FVGFilled]:
        events: list[FVGCreated | FVGTouched | FVGFilled] = []

        # ── 1. Lifecycle updates for existing FVGs ───────────────────
        still_active: list[_FVGState] = []
        for fvg in self._active:
            if fvg.filled:
                continue
            if fvg.direction == "BULL":
                # Touched: low enters gap (low <= top)
                if not fvg.touched and bar.low <= fvg.top:
                    fvg.touched = True
                    events.append(FVGTouched(
                        confirmed_at=bar.ts_utc,
                        fvg_anchor=fvg.anchor,
                        direction="BULL",
                        top=fvg.top,
                        bottom=fvg.bottom,
                    ))
                # Filled: low reaches far edge (low <= bottom)
                if bar.low <= fvg.bottom:
                    fvg.filled = True
                    events.append(FVGFilled(
                        confirmed_at=bar.ts_utc,
                        fvg_anchor=fvg.anchor,
                        direction="BULL",
                        top=fvg.top,
                        bottom=fvg.bottom,
                    ))
                    continue
            else:  # BEAR
                # Touched: high enters gap from below (high >= bottom)
                if not fvg.touched and bar.high >= fvg.bottom:
                    fvg.touched = True
                    events.append(FVGTouched(
                        confirmed_at=bar.ts_utc,
                        fvg_anchor=fvg.anchor,
                        direction="BEAR",
                        top=fvg.top,
                        bottom=fvg.bottom,
                    ))
                # Filled: high reaches far edge (high >= top)
                if bar.high >= fvg.top:
                    fvg.filled = True
                    events.append(FVGFilled(
                        confirmed_at=bar.ts_utc,
                        fvg_anchor=fvg.anchor,
                        direction="BEAR",
                        top=fvg.top,
                        bottom=fvg.bottom,
                    ))
                    continue
            still_active.append(fvg)
        self._active = still_active

        # ── 2. Detect new FVG (needs 3 bars) ────────────────────────
        self._buf.append(bar)
        if len(self._buf) < 3:
            return events
        b0, b1, b2 = self._buf[-3], self._buf[-2], self._buf[-1]

        # Bullish FVG: low[i+2] > high[i]
        gap_bull = b2.low - b0.high
        if gap_bull >= self.min_gap:
            top = b2.low
            bottom = b0.high
            ce = (top + bottom) / 2
            fvg = _FVGState(anchor=b1.ts_utc, direction="BULL", top=top, bottom=bottom, ce=ce)
            self._active.append(fvg)
            events.append(FVGCreated(
                confirmed_at=b2.ts_utc,
                anchor=b1.ts_utc,
                direction="BULL",
                top=top,
                bottom=bottom,
                ce=ce,
            ))
        # Bearish FVG: high[i+2] < low[i]  (mutually exclusive with bullish if strict)
        gap_bear = b0.low - b2.high
        if gap_bear >= self.min_gap:
            top = b0.low
            bottom = b2.high
            ce = (top + bottom) / 2
            fvg = _FVGState(anchor=b1.ts_utc, direction="BEAR", top=top, bottom=bottom, ce=ce)
            self._active.append(fvg)
            events.append(FVGCreated(
                confirmed_at=b2.ts_utc,
                anchor=b1.ts_utc,
                direction="BEAR",
                top=top,
                bottom=bottom,
                ce=ce,
            ))

        return events
