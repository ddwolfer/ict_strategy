# -*- coding: utf-8 -*-
"""每日特徵表建置（嚴格無前視：所有 *_prev 欄位只用昨日為止的資料）。

輸出 reports/window_runs/daily_features.csv，欄位：
  date            交易日（ET）
  dow             星期（0=一）
  prev_rth_close  昨日 RTH 收盤（15:59 棒 close）
  open_930        今日 09:30 首棒 open
  gap_pts         open_930 - prev_rth_close
  atr14_prev      昨日為止的日線 ATR(14)（全時段高低收）
  gap_atr         gap_pts / atr14_prev
  on_high/on_low  隔夜高低（今日 18:00 前夜～09:29）
  or_high/or_low  09:30–09:59 開盤區間
  or_range        OR 大小（點）
  m5_close        09:34 棒收盤（首根 5 分 K 收盤）
  close_1130      11:30 前最後一棒 close
  rth_close       15:59 棒 close
  vix_prev        昨日 VIX 收盤
用法：python research/window_audit/build_daily_features.py
"""
import pandas as pd
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
ET = ZoneInfo("America/New_York")

print("載入 NQ 1m ...", flush=True)
df = pd.read_csv(ROOT / "data/cache/nq_1m.csv", parse_dates=["ts"])
df["ts_et"] = df.ts.dt.tz_convert(ET)
# 交易日：18:00 ET 之後屬次日 → +6h 取日期
df["tdate"] = (df.ts_et + pd.Timedelta(hours=6)).dt.date
df["hm"] = df.ts_et.dt.hour * 60 + df.ts_et.dt.minute

g = df.groupby("tdate")
day_full = g.agg(full_high=("High", "max"), full_low=("Low", "min"),
                 full_close=("Close", "last")).reset_index()

# ATR(14)（全時段日線；shift(1) → 昨日為止）
prev_close = day_full.full_close.shift(1)
tr = pd.concat([
    day_full.full_high - day_full.full_low,
    (day_full.full_high - prev_close).abs(),
    (day_full.full_low - prev_close).abs(),
], axis=1).max(axis=1)
day_full["atr14_prev"] = tr.rolling(14).mean().shift(1)

def _sub(mask, name_prefix, cols):
    sub = df[mask].groupby("tdate").agg(**cols).reset_index()
    return sub

RTH   = (df.hm >= 570) & (df.hm < 960)          # 09:30–15:59
ON    = df.hm.pipe(lambda h: (h >= 1080) | (h < 570))  # 18:00–09:29
OR30  = (df.hm >= 570) & (df.hm < 600)          # 09:30–09:59
PRE   = (df.hm >= 510) & (df.hm < 570)          # 08:30–09:29（窗口盤前段）

rth = _sub(RTH, "rth", dict(open_930=("Open", "first"), rth_close=("Close", "last"),
                            rth_high=("High", "max"), rth_low=("Low", "min")))
on_ = _sub(ON, "on", dict(on_high=("High", "max"), on_low=("Low", "min")))
orr = _sub(OR30, "or", dict(or_high=("High", "max"), or_low=("Low", "min")))
m5  = _sub((df.hm >= 570) & (df.hm < 575), "m5", dict(m5_close=("Close", "last"),
                                                      m5_high=("High", "max"),
                                                      m5_low=("Low", "min")))
c1130 = _sub((df.hm >= 570) & (df.hm < 690), "c", dict(close_1130=("Close", "last")))

feat = day_full[["tdate", "atr14_prev"]].copy()
for part in (rth, on_, orr, m5, c1130):
    feat = feat.merge(part, on="tdate", how="left")

feat["prev_rth_close"] = feat.rth_close.shift(1)
feat["gap_pts"] = feat.open_930 - feat.prev_rth_close
feat["gap_atr"] = feat.gap_pts / feat.atr14_prev
feat["or_range"] = feat.or_high - feat.or_low
feat["dow"] = pd.to_datetime(feat.tdate).dt.dayofweek

vix = pd.read_csv(ROOT / "data/cache/vix_1d.csv", parse_dates=["date"])
vix["tdate"] = vix.date.dt.date
vix = vix.sort_values("tdate")
vix["vix_prev"] = vix.Close.shift(1)
feat = feat.merge(vix[["tdate", "vix_prev"]], on="tdate", how="left")

# 只保留有 RTH 的正常交易日
feat = feat.dropna(subset=["open_930", "rth_close"])
out = ROOT / "reports/window_runs/daily_features.csv"
out.parent.mkdir(parents=True, exist_ok=True)
feat.rename(columns={"tdate": "date"}).to_csv(out, index=False)
print(f"寫出 {out}（{len(feat)} 個交易日）")
