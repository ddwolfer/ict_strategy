# -*- coding: utf-8 -*-
"""IS 段缺口審計（F3 Gap-Go 前提檢驗；門檻 0.3×ATR 為預登記值，不掃描）。

近似 R 估算（非正式回測，僅 go/no-go 判斷）：
  多單：進場≈m5_close、停損=m5_low、出場=rth_close（EOD）
  R = (rth_close - m5_close) / (m5_close - m5_low)
"""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
f = pd.read_csv(ROOT / "reports/window_runs/daily_features.csv", parse_dates=["date"])
f = f.dropna(subset=["gap_atr", "m5_close", "m5_high", "m5_low", "rth_close", "close_1130"])

IS = f[f.date <= "2024-12-31"].copy()
print(f"IS 交易日: {len(IS)}（{IS.date.min().date()} ~ {IS.date.max().date()}）")
print(f"|gap_atr| 分位: 50%={IS.gap_atr.abs().quantile(.5):.3f}  "
      f"75%={IS.gap_atr.abs().quantile(.75):.3f}  90%={IS.gap_atr.abs().quantile(.9):.3f}")

IS["dir"] = (IS.gap_pts > 0).astype(int) * 2 - 1
trig = IS[IS.gap_atr.abs() >= 0.3].copy()
ctrl = IS[IS.gap_atr.abs() < 0.3].copy()
print(f"\n觸發日（|gap|>=0.3 ATR）: {len(trig)}（{len(trig)/len(IS)*100:.0f}% 的日子，"
      f"約 {len(trig)/3.55:.0f} 天/年）")

def follow_stats(d, label):
    if len(d) == 0:
        print(f"  {label}: n=0"); return
    mv_eod  = (d.rth_close - d.open_930) * d.dir
    mv_1130 = (d.close_1130 - d.open_930) * d.dir
    print(f"  {label}: n={len(d)}  P(EOD順向)={(mv_eod>0).mean()*100:.1f}%  "
          f"均值={mv_eod.mean():+.1f}pt({(mv_eod/d.atr14_prev).mean():+.3f}ATR)  "
          f"P(11:30順向)={(mv_1130>0).mean()*100:.1f}%  均值1130={mv_1130.mean():+.1f}pt")

print("\n── 開盤價→順缺口方向的後續走勢 ──")
follow_stats(trig, "觸發日")
follow_stats(ctrl, "對照(小缺口)")

# ── F3 進場規則近似模擬（5 分 K 確認）────────────────────────────────────────
print("\n── F3 規則近似（5 分 K 順向確認才進場）──")
long_ok  = trig[(trig.dir == 1) & (trig.m5_close > trig.open_930)].copy()
short_ok = trig[(trig.dir == -1) & (trig.m5_close < trig.open_930)].copy()
long_ok["stop_d"]  = long_ok.m5_close - long_ok.m5_low
short_ok["stop_d"] = short_ok.m5_high - short_ok.m5_close
long_ok["r_eod"]   = (long_ok.rth_close - long_ok.m5_close) / long_ok.stop_d
short_ok["r_eod"]  = (short_ok.m5_close - short_ok.rth_close) / short_ok.stop_d
long_ok["r_1130"]  = (long_ok.close_1130 - long_ok.m5_close) / long_ok.stop_d
short_ok["r_1130"] = (short_ok.m5_close - short_ok.close_1130) / short_ok.stop_d
sim = pd.concat([long_ok, short_ok])
sim = sim[sim.stop_d >= 3]   # min_stop_points=3 同 F1
sim["year"] = sim.date.dt.year
print(f"  成交日: {len(sim)}（多 {len(long_ok)} / 空 {len(short_ok)}）  "
      f"停損中位 {sim.stop_d.median():.1f}pt")
print(f"  EOD 出場: 勝率={(sim.r_eod>0).mean()*100:.1f}%  期望={sim.r_eod.mean():+.3f}R  "
      f"總R={sim.r_eod.sum():+.1f}")
print(f"  11:30 平: 勝率={(sim.r_1130>0).mean()*100:.1f}%  期望={sim.r_1130.mean():+.3f}R  "
      f"總R={sim.r_1130.sum():+.1f}")
print("\n  分年（EOD 口徑）:")
for y, gy in sim.groupby("year"):
    print(f"    {y}: n={len(gy):3d}  期望={gy.r_eod.mean():+.3f}R  總R={gy.r_eod.sum():+.1f}")

# 註：此近似無滑價/手續費/盤中停損觸發路徑（停損若盤中被掃、EOD 收回來，
# 這裡會高估）。僅供 go/no-go；正式數字須引擎實作。
print("\n[注意] 近似模擬未含盤中停損觸發——若 m5_low 在收盤前被跌破，"
      "實際是 -1R 出場，此處仍以 EOD 計。正式判定以引擎為準。")
