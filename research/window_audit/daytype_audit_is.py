# -*- coding: utf-8 -*-
"""H2 日型審計（IS 段）：F1（ORB 限窗）在 8:30 重磅日 / FOMC 日 / 一般日的表現。

預登記決策點（ny-window-research-spec §4 F2）：
  - FOMC 日期望 R < 0 且 n>=20 → 組合版 F1 排除 FOMC 日
  - 重磅日期望 R >= 2x 非重磅日 → 只記錄，不行動
"""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
cal = pd.read_csv(ROOT / "data/econ_calendar.csv", parse_dates=["date"])
cal["date"] = cal.date.dt.date

AM830 = {"CPI", "NFP", "PPI", "GDP", "RETAIL"}
news_days = set(cal[cal.event.isin(AM830)].date)
fomc_days = set(cal[cal.event == "FOMC"].date)

tr = pd.read_csv(ROOT / "reports/window_runs/orb_win_eod_r05_IS/trades.csv",
                 parse_dates=["date"])
tr["d"] = tr.date.dt.date
tr["is_news"] = tr.d.isin(news_days)
tr["is_fomc"] = tr.d.isin(fomc_days)

def show(df, label):
    if len(df) == 0:
        print(f"  {label:14s} n=0")
        return 0.0
    m = df.r_multiple.mean()
    print(f"  {label:14s} n={len(df):4d}  期望={m:+.3f}R  總R={df.r_multiple.sum():+7.1f}  "
          f"勝率={(df.r_multiple>0).mean()*100:.1f}%")
    return m

print("F1（ORB 限窗 win_eod r05）IS 分日型：")
m_news  = show(tr[tr.is_news & ~tr.is_fomc], "8:30 重磅日")
m_none  = show(tr[~tr.is_news & ~tr.is_fomc], "一般日")
m_fomc  = show(tr[tr.is_fomc], "FOMC 日")

n_fomc = int(tr.is_fomc.sum())
print("\n預登記決策：")
if n_fomc >= 20 and m_fomc < 0:
    print(f"  → FOMC 日期望 {m_fomc:+.3f}R < 0（n={n_fomc}）：組合版 F1 排除 FOMC 日")
else:
    print(f"  → FOMC 排除條件不成立（n={n_fomc}, 期望={m_fomc:+.3f}R）：F1 不變")
if m_none > 0 and m_news >= 2 * m_none:
    print(f"  → H2a 成立（重磅 {m_news:+.3f} vs 一般 {m_none:+.3f}）：記錄，不行動")
else:
    print(f"  → H2a 不成立（重磅 {m_news:+.3f} vs 一般 {m_none:+.3f}）")
