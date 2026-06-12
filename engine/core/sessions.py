"""時段判斷工具（America/New_York 夏令時）。"""
from __future__ import annotations
from datetime import datetime, time, date, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("utc")

SESSIONS: dict[str, tuple[time, time]] = {
    "NY_AM_KILLZONE":   (time(7, 0),  time(10, 0)),
    "RTH_OPEN_3H":      (time(9, 30), time(12, 30)),
    "SILVER_BULLET_AM": (time(10, 0), time(11, 0)),
    "RTH":              (time(9, 30), time(16, 0)),
    # §2.4 多時段
    "NY_PM":            (time(13, 30), time(15, 55)),
    "LONDON":           (time(2, 0),   time(5, 30)),
    # OVERNIGHT spans midnight; handled specially
}


def _to_et(ts: datetime) -> datetime:
    """UTC datetime → ET datetime（保留同一時刻）。"""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(ET)


def sessions_at(ts: datetime) -> list[str]:
    """回傳 ts 所屬的所有 session 名稱列表。"""
    et = _to_et(ts)
    et_time = et.time()
    result = []
    for name, (start, end) in SESSIONS.items():
        if start <= et_time < end:
            result.append(name)
    # OVERNIGHT: prev 18:00 ET – today 09:29 ET
    # = et_time >= 18:00 OR et_time < 09:30
    if et_time >= time(18, 0) or et_time < time(9, 30):
        result.append("OVERNIGHT")
    return result


def trading_date(ts: datetime) -> date:
    """回傳 bar 所屬交易日（ET 日曆日；18:00 ET 之後屬於下一交易日）。"""
    et = _to_et(ts)
    if et.time() >= time(18, 0):
        return (et + timedelta(days=1)).date()
    return et.date()


def is_in_window(ts: datetime, window_name: str) -> bool:
    """判斷 ts 是否在指定 session 窗內。"""
    return window_name in sessions_at(ts)
