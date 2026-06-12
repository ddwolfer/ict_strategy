"""CSV 資料載入器。"""
from __future__ import annotations
from datetime import date
from pathlib import Path
import pandas as pd
from engine.core.types import Bar
from engine.core.sessions import trading_date, is_in_window

_DEFAULT_CSV = Path(__file__).parent.parent.parent / "data" / "cache" / "nq_1m.csv"


def load_bars(csv_path: Path | str = _DEFAULT_CSV) -> list[Bar]:
    """載入 CSV，回傳按時間排序的 Bar 列表。"""
    df = pd.read_csv(csv_path, parse_dates=["ts"])
    # ensure tz-aware UTC
    if df["ts"].dt.tz is None:
        df["ts"] = df["ts"].dt.tz_localize("UTC")
    else:
        df["ts"] = df["ts"].dt.tz_convert("UTC")
    df.sort_values("ts", inplace=True)
    bars = [
        Bar(
            ts_utc=row.ts.to_pydatetime(),
            open=float(row.Open),
            high=float(row.High),
            low=float(row.Low),
            close=float(row.Close),
            volume=float(row.Volume),
        )
        for row in df.itertuples(index=False)
    ]
    return bars


def list_trading_days(csv_path: Path | str = _DEFAULT_CSV) -> list[date]:
    """回傳資料中所有交易日（排序）。"""
    bars = load_bars(csv_path)
    days = sorted({trading_date(b.ts_utc) for b in bars})
    return days


def load_session_bars(
    day: date,
    window: str,
    csv_path: Path | str = _DEFAULT_CSV,
) -> list[Bar]:
    """取某交易日某時段的 bars。"""
    bars = load_bars(csv_path)
    return [
        b for b in bars
        if trading_date(b.ts_utc) == day and is_in_window(b.ts_utc, window)
    ]
