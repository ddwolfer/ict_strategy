"""核心資料型別：Bar 與事件體系。"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

TICK = 0.25
POINT_VALUE = 20.0


@dataclass(frozen=True)
class Bar:
    """1 分鐘 K 棒，ts_utc 為開盤時間（tz-aware UTC）。"""
    ts_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


# ─── Events ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SwingConfirmed:
    confirmed_at: datetime
    anchor: datetime          # bar i 的 ts_utc
    side: Literal["HIGH", "LOW"]
    level: float

@dataclass(frozen=True)
class PoolCreated:
    confirmed_at: datetime
    kind: str                 # PDH/PDL/ONH/ONL/SESSION_HIGH/SESSION_LOW/SWING_HIGH/SWING_LOW/EQUAL_HIGHS/EQUAL_LOWS
    side: Literal["BUY", "SELL"]
    level: float

@dataclass(frozen=True)
class PoolSwept:
    confirmed_at: datetime
    kind: str
    side: Literal["BUY", "SELL"]
    level: float

@dataclass(frozen=True)
class Raid:
    confirmed_at: datetime
    kind: str
    side: Literal["BUY", "SELL"]
    level: float

@dataclass(frozen=True)
class FVGCreated:
    confirmed_at: datetime
    anchor: datetime          # bar i+1 的 ts_utc
    direction: Literal["BULL", "BEAR"]
    top: float
    bottom: float
    ce: float

@dataclass(frozen=True)
class FVGTouched:
    confirmed_at: datetime
    fvg_anchor: datetime
    direction: Literal["BULL", "BEAR"]
    top: float
    bottom: float

@dataclass(frozen=True)
class FVGFilled:
    confirmed_at: datetime
    fvg_anchor: datetime
    direction: Literal["BULL", "BEAR"]
    top: float
    bottom: float

@dataclass(frozen=True)
class Displacement:
    confirmed_at: datetime
    anchor: datetime
    direction: Literal["BULL", "BEAR"]
    body_size: float
    avg_body: float
    left_fvg: bool

@dataclass(frozen=True)
class MSS:
    confirmed_at: datetime
    direction: Literal["BULL", "BEAR"]   # BEAR = bearish MSS
    broken_swing_level: float
    broken_swing_anchor: datetime
    displacement_anchor: datetime
    left_fvg: bool

@dataclass(frozen=True)
class SessionBoundary:
    confirmed_at: datetime
    session: str
    event_type: Literal["OPEN", "CLOSE"]

Event = (
    SwingConfirmed | PoolCreated | PoolSwept | Raid |
    FVGCreated | FVGTouched | FVGFilled |
    Displacement | MSS | SessionBoundary
)
