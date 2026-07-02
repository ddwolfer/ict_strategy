# -*- coding: utf-8 -*-
"""F3 Gap-Go 路徑感知模擬（IS 段）——用 1 分 K 逐棒檢查停損觸發。

規則（照預登記規格，零參數自由度）：
  觸發：|gap| >= 0.3 x 昨日ATR(14)
  確認：09:30-09:34 首根 5 分 K 收盤順缺口方向
  進場：09:35 首棒 open（市價）
  停損：5 分 K 對側（多=m5_low、空=m5_high），停損優先於出場
  出場：win_eod=15:55 前最後收盤 / win_flat=11:30 前最後收盤
  未含手續費滑價（MNQ 約 -0.01R/筆量級，不影響 go/no-go）
"""
import pandas as pd
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
ET = ZoneInfo("America/New_York")

feat = pd.read_csv(ROOT / "reports/window_runs/daily_features.csv", parse_dates=["date"])
feat = feat.dropna(subset=["gap_atr", "m5_close", "m5_high", "m5_low"])
IS = feat[feat.date <= "2024-12-31"].copy()
IS["dir"] = (IS.gap_pts > 0).astype(int) * 2 - 1
trig = IS[IS.gap_atr.abs() >= 0.3]

print("載入 NQ 1m ...", flush=True)
px = pd.read_csv(ROOT / "data/cache/nq_1m.csv", parse_dates=["ts"])
px["ts_et"] = px.ts.dt.tz_convert(ET)
px["tdate"] = (px.ts_et + pd.Timedelta(hours=6)).dt.date
px["hm"] = px.ts_et.dt.hour * 60 + px.ts_et.dt.minute
px = px[(px.hm >= 575) & (px.hm < 955)]          # 09:35–15:54
by_day = dict(tuple(px.groupby("tdate")))

rows = []
for _, d in trig.iterrows():
    dirn = int(d.dir)
    confirmed = (d.m5_close > d.open_930) if dirn == 1 else (d.m5_close < d.open_930)
    if not confirmed:
        continue
    stop = d.m5_low if dirn == 1 else d.m5_high
    day = by_day.get(d.date.date())
    if day is None or len(day) == 0:
        continue
    entry = day.iloc[0].Open
    stop_d = (entry - stop) * dirn
    if stop_d < 3:
        continue
    r_flat = r_eod = None
    for _, b in day.iterrows():
        hit = (b.Low <= stop) if dirn == 1 else (b.High >= stop)
        if hit:
            r = -1.0
            if r_flat is None and b.hm >= 575:
                r_flat = r if b.hm < 690 else r_flat
            if b.hm < 690 and r_flat is None:
                r_flat = r
            r_eod = r
            break
        if b.hm >= 689 and r_flat is None:          # 11:29 棒收盤 = 11:30 平
            r_flat = (b.Close - entry) * dirn / stop_d
    else:
        last = day.iloc[-1]
        r_eod = (last.Close - entry) * dirn / stop_d
        if r_flat is None:
            r_flat = r_eod
    if r_eod is None:
        continue
    if r_flat is None:
        r_flat = r_eod
    rows.append(dict(date=d.date, dir=dirn, stop_d=stop_d, r_eod=r_eod, r_flat=r_flat,
                     year=d.date.year))

sim = pd.DataFrame(rows)
print(f"成交: {len(sim)} 筆（多 {(sim['dir']==1).sum()} / 空 {(sim['dir']==-1).sum()}），"
      f"停損中位 {sim.stop_d.median():.1f}pt")
for col, label in [("r_eod", "EOD 出場"), ("r_flat", "11:30 平")]:
    s = sim[col]
    print(f"  {label}: 勝率={(s>0).mean()*100:5.1f}%  期望={s.mean():+.3f}R  總R={s.sum():+.1f}")
print("\n分年:")
for y, gy in sim.groupby("year"):
    print(f"  {y}: n={len(gy):3d}  EOD={gy.r_eod.mean():+.3f}R(總{gy.r_eod.sum():+.1f})  "
          f"11:30={gy.r_flat.mean():+.3f}R(總{gy.r_flat.sum():+.1f})")
