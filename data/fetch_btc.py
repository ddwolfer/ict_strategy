# -*- coding: utf-8 -*-
"""抓取 Binance BTCUSDT 歷史資料（BTC 短期策略研究用，spec: btc-short-research-spec.md）。

來源：data.binance.vision 官方歷史庫（免費、無需 API key）。
產出（data/cache/，不入版控）：
  btc_perp_5m.csv   USDT-M 永續 5m   2020-01 ~ 最新月（C3 ORB 用）
  btc_perp_1d.csv   USDT-M 永續 1d   2020-01 ~ 最新月（C2 動量用）
  btc_spot_1d.csv   現貨 1d          2018-01 ~ 最新月（C1 現貨腿 / B&H 基準）
  btc_funding.csv   資金費率逐筆     2020-01 ~ 最新月（C1 carry 用）

原始 zip 快取於 data/cache/btc_raw/，重跑只補缺月。
月檔缺（當月尚未發布）自動退回日檔補齊。
時戳正規化：>1e14 視為微秒（Binance 2025 起部分資料集改 µs），統一輸出 UTC ISO。

用法：python data/fetch_btc.py
"""
import io
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/cache"
RAW = CACHE / "btc_raw"
RAW.mkdir(parents=True, exist_ok=True)

BASE = "https://data.binance.vision/data"
KCOLS = ["open_time", "open", "high", "low", "close", "volume",
         "close_time", "quote_vol", "trades", "taker_base", "taker_quote", "ignore"]


def _months(y0: int, m0: int) -> list[str]:
    """y0-m0 起至上個月為止的 YYYY-MM 清單。"""
    today = date.today()
    out, y, m = [], y0, m0
    while (y, m) < (today.year, today.month):
        out.append(f"{y}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def _get(url: str, dest: Path) -> bool:
    if dest.exists():
        return True
    r = requests.get(url, timeout=60)
    if r.status_code == 404:
        return False
    r.raise_for_status()
    dest.write_bytes(r.content)
    return True


def _read_kline_zip(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        raw = z.read(z.namelist()[0])
    df = pd.read_csv(io.BytesIO(raw), header=None, names=KCOLS)
    # 新版檔案含 header 列 → 首欄非數字者剔除
    df = df[pd.to_numeric(df.open_time, errors="coerce").notna()].copy()
    for c in KCOLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    ts = df.open_time.astype("int64")
    ts = ts.where(ts < 1e14, ts // 1000)  # µs → ms
    df["ts"] = pd.to_datetime(ts, unit="ms", utc=True)
    return df[["ts", "open", "high", "low", "close", "volume"]]


def fetch_klines(market: str, interval: str, y0: int, m0: int, out_name: str) -> None:
    """market: 'spot' 或 'futures/um'。月檔缺 → 日檔補。"""
    frames, missing_months = [], []
    for ym in _months(y0, m0):
        url = f"{BASE}/{market}/monthly/klines/BTCUSDT/{interval}/BTCUSDT-{interval}-{ym}.zip"
        dest = RAW / f"{market.replace('/', '_')}_{interval}_{ym}.zip"
        if _get(url, dest):
            frames.append(_read_kline_zip(dest))
        else:
            missing_months.append(ym)
    for ym in missing_months:  # 當月未發布 → 逐日補
        y, m = int(ym[:4]), int(ym[5:7])
        d = date(y, m, 1)
        n_daily = 0
        while d.month == m and d < date.today():
            url = (f"{BASE}/{market}/daily/klines/BTCUSDT/{interval}/"
                   f"BTCUSDT-{interval}-{d.isoformat()}.zip")
            dest = RAW / f"{market.replace('/', '_')}_{interval}_{d.isoformat()}.zip"
            if _get(url, dest):
                frames.append(_read_kline_zip(dest))
                n_daily += 1
            d += timedelta(days=1)
        print(f"  {out_name}: 月檔 {ym} 缺，日檔補 {n_daily} 天")
    df = (pd.concat(frames).drop_duplicates("ts").sort_values("ts")
          .reset_index(drop=True))
    df.to_csv(CACHE / out_name, index=False)
    print(f"{out_name}: {len(df)} 列  {df.ts.min()} ~ {df.ts.max()}")


def fetch_funding() -> None:
    frames = []
    for ym in _months(2020, 1):
        url = f"{BASE}/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-{ym}.zip"
        dest = RAW / f"funding_{ym}.zip"
        if not _get(url, dest):
            print(f"  funding: 月檔 {ym} 缺（略過）")
            continue
        with zipfile.ZipFile(dest) as z:
            raw = z.read(z.namelist()[0])
        df = pd.read_csv(io.BytesIO(raw), header=None,
                         names=["calc_time", "interval_hours", "rate"])
        df = df[pd.to_numeric(df.calc_time, errors="coerce").notna()].copy()
        ts = df.calc_time.astype("int64")
        ts = ts.where(ts < 1e14, ts // 1000)
        df["ts"] = pd.to_datetime(ts, unit="ms", utc=True)
        df["rate"] = pd.to_numeric(df.rate, errors="coerce")
        frames.append(df[["ts", "rate"]])
    df = (pd.concat(frames).dropna().drop_duplicates("ts").sort_values("ts")
          .reset_index(drop=True))
    df.to_csv(CACHE / "btc_funding.csv", index=False)
    print(f"btc_funding.csv: {len(df)} 筆  {df.ts.min()} ~ {df.ts.max()}")


if __name__ == "__main__":
    fetch_klines("spot", "1d", 2018, 1, "btc_spot_1d.csv")
    fetch_klines("futures/um", "1d", 2020, 1, "btc_perp_1d.csv")
    fetch_funding()
    fetch_klines("futures/um", "5m", 2020, 1, "btc_perp_5m.csv")
    print("完成。")
