"""MSSDetector：§6 市場結構轉換。

MSS = displacement candle close breaks most recent unbroken swing low (bearish)
      or most recent unbroken swing high (bullish).
"""
from __future__ import annotations
from engine.core.types import Bar, MSS, SwingConfirmed, Displacement
from engine.detectors.swings import SwingDetector
from engine.detectors.displacement import DisplacementDetector


class MSSDetector:
    """組合 SwingDetector + DisplacementDetector。

    Bearish MSS: displacement BEAR candle, close < most recent unbroken swing low
    Bullish MSS: displacement BULL candle, close > most recent unbroken swing high
    The broken swing is removed from the unbroken list after MSS fires.
    """

    def __init__(self, n: int = 1, window: int = 20, mult: float = 2.0) -> None:
        self._swing = SwingDetector(n=n)
        self._disp = DisplacementDetector(window=window, mult=mult)
        self._swing_highs: list[SwingConfirmed] = []  # unbroken highs
        self._swing_lows: list[SwingConfirmed] = []   # unbroken lows

    def on_bar(self, bar: Bar) -> list[MSS]:
        events: list[MSS] = []
        swing_evts = self._swing.on_bar(bar)
        disp_evts = self._disp.on_bar(bar)

        # Collect new swings
        for ev in swing_evts:
            if ev.side == "HIGH":
                self._swing_highs.append(ev)
            else:
                self._swing_lows.append(ev)

        # Check displacement events for MSS
        for ev in disp_evts:
            if not isinstance(ev, Displacement):
                continue
            left_fvg = ev.left_fvg
            if ev.direction == "BEAR" and self._swing_lows:
                recent = self._swing_lows[-1]
                if bar.close < recent.level:
                    events.append(MSS(
                        confirmed_at=bar.ts_utc,
                        direction="BEAR",
                        broken_swing_level=recent.level,
                        broken_swing_anchor=recent.anchor,
                        displacement_anchor=bar.ts_utc,
                        left_fvg=left_fvg,
                    ))
                    self._swing_lows.remove(recent)
            elif ev.direction == "BULL" and self._swing_highs:
                recent = self._swing_highs[-1]
                if bar.close > recent.level:
                    events.append(MSS(
                        confirmed_at=bar.ts_utc,
                        direction="BULL",
                        broken_swing_level=recent.level,
                        broken_swing_anchor=recent.anchor,
                        displacement_anchor=bar.ts_utc,
                        left_fvg=left_fvg,
                    ))
                    self._swing_highs.remove(recent)

        # Prune swings already closed through without displacement — they are
        # no longer "unbroken" and must not anchor a future MSS.
        self._swing_lows = [s for s in self._swing_lows if bar.close >= s.level]
        self._swing_highs = [s for s in self._swing_highs if bar.close <= s.level]

        return events
