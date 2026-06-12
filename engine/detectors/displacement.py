"""DisplacementDetector：§5 機構式快速移動。

window=20 根移動平均實體；mult=2.0 倍觸發。
left_fvg = True if the displacement candle (as bar i+2) caused a FVGCreated event
in the same on_bar call.
"""
from __future__ import annotations
from engine.core.types import Bar, Displacement, FVGCreated
from engine.detectors.fvg import FVGDetector


class DisplacementDetector:
    """window=20 根移動平均實體；mult=2.0 倍觸發。"""

    def __init__(self, window: int = 20, mult: float = 2.0) -> None:
        self.window = window
        self.mult = mult
        self._buf: list[Bar] = []
        self._fvg = FVGDetector()

    def on_bar(self, bar: Bar) -> list[Displacement]:
        self._buf.append(bar)
        # Run FVG detector first — it uses its own internal buffer
        fvg_events = self._fvg.on_bar(bar)
        events: list[Displacement] = []

        # Need at least window+1 bars to compute avg body of previous `window` bars
        if len(self._buf) < self.window + 1:
            return events

        # avg body of previous `window` bars (not including current)
        prev = self._buf[-(self.window + 1):-1]
        avg_body = sum(abs(b.close - b.open) for b in prev) / self.window
        body = abs(bar.close - bar.open)

        if avg_body > 0 and body >= self.mult * avg_body:
            # left_fvg: True if this bar (as i+2) triggered a FVG creation
            left_fvg = any(isinstance(e, FVGCreated) for e in fvg_events)
            direction: str = "BULL" if bar.close > bar.open else "BEAR"
            events.append(Displacement(
                confirmed_at=bar.ts_utc,
                anchor=bar.ts_utc,
                direction=direction,
                body_size=body,
                avg_body=avg_body,
                left_fvg=left_fvg,
            ))

        return events
