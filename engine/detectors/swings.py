"""SwingDetector：依 §2 定義，n 根確認延遲。"""
from __future__ import annotations
from engine.core.types import Bar, SwingConfirmed, TICK


class SwingDetector:
    """逐根餵入，n=1 即 3-bar fractal。

    Swing High: high[i] > high[i-k] AND high[i] > high[i+k] for k=1..n  (strict)
    Confirmed at bar i+n close; anchor = bar i.
    """

    def __init__(self, n: int = 1) -> None:
        self.n = n
        self._buf: list[Bar] = []

    def on_bar(self, bar: Bar) -> list[SwingConfirmed]:
        self._buf.append(bar)
        events: list[SwingConfirmed] = []
        needed = 2 * self.n + 1
        if len(self._buf) < needed:
            return events

        window = self._buf[-needed:]
        i = self.n  # candidate index within window
        candidate = window[i]
        confirm_bar = window[-1]  # bar i+n

        # check swing high: strict greater-than on both sides
        is_high = all(
            candidate.high > window[i - k].high and candidate.high > window[i + k].high
            for k in range(1, self.n + 1)
        )
        # check swing low: strict less-than on both sides
        is_low = all(
            candidate.low < window[i - k].low and candidate.low < window[i + k].low
            for k in range(1, self.n + 1)
        )

        if is_high:
            events.append(SwingConfirmed(
                confirmed_at=confirm_bar.ts_utc,
                anchor=candidate.ts_utc,
                side="HIGH",
                level=candidate.high,
            ))
        if is_low:
            events.append(SwingConfirmed(
                confirmed_at=confirm_bar.ts_utc,
                anchor=candidate.ts_utc,
                side="LOW",
                level=candidate.low,
            ))
        return events
