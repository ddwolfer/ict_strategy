"""Incrementally fetch NQ=F 1-minute bars from yfinance into data/cache/.

yfinance limits 1m data to the last ~30 days, max 8 days per request.
Each run merges new bars into a single parquet+csv cache keyed by UTC timestamp,
so running it daily/weekly accumulates history beyond the 30-day window.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

CACHE = Path(__file__).parent / "cache"
CACHE.mkdir(exist_ok=True)
import sys
SYMBOL = sys.argv[1] if len(sys.argv) > 1 else "NQ=F"
CSV = CACHE / (sys.argv[2] if len(sys.argv) > 2 else "nq_1m.csv")
WINDOW_DAYS = 29  # stay inside yfinance's ~30d limit
CHUNK_DAYS = 7    # stay inside the 8d-per-request limit


def fetch_range(start: datetime, end: datetime) -> pd.DataFrame:
    df = yf.download(
        SYMBOL, start=start, end=end, interval="1m",
        progress=False, auto_adjust=False, prepost=True, multi_level_index=False,
    )
    if df.empty:
        return df
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.index = df.index.tz_convert("UTC")
    df.index.name = "ts"
    return df


def main() -> None:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=WINDOW_DAYS)
    chunks = []
    cur = start
    while cur < now:
        nxt = min(cur + timedelta(days=CHUNK_DAYS), now)
        part = fetch_range(cur, nxt)
        print(f"  {cur:%Y-%m-%d} -> {nxt:%Y-%m-%d}: {len(part)} bars")
        if not part.empty:
            chunks.append(part)
        cur = nxt
    if not chunks:
        raise SystemExit("No data returned by yfinance")
    new = pd.concat(chunks)

    if CSV.exists():
        old = pd.read_csv(CSV, index_col="ts", parse_dates=["ts"])
        old.index = old.index.tz_convert("UTC")
        merged = pd.concat([old, new])
    else:
        merged = new
    merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    merged.to_csv(CSV)
    print(f"Cache now: {len(merged)} bars, {merged.index[0]} .. {merged.index[-1]}")


if __name__ == "__main__":
    main()
