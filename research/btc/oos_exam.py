# -*- coding: utf-8 -*-
"""一次性 OOS 驗收（2025-01-01 ~ 2026-06-30，spec §4）。

通過 IS 閘門者僅 C1 carry → 組合 = C1。
C2/C3 已於 IS 淘汰，依規格**不跑 OOS**（保持其 OOS 乾淨）。
基準：BTC 現貨 B&H、標普 500（ES 1m 快取重採樣日線）。
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout.reconfigure(encoding="utf-8")

from research.btc import backtest as bt

OOS0, OOS1 = "2025-01-01", "2026-06-30"
OUT = bt.ROOT / "reports/btc_runs"

funding = bt.load_csv("btc_funding.csv")

print("══════ OOS 2025-01-01 ~ 2026-06-30（一次性驗收）══════\n")

c1 = bt.run_c1(funding, OOS0, OOS1)
c1.rename("ret").to_csv(OUT / "oos_C1_carry.csv")
m = bt.metrics(c1, "C1_carry（＝組合）")
print(bt.fmt(m))

# 部署狀態審計（多少個月在場上）
f_oos = funding[(funding.ts >= pd.Timestamp(OOS0, tz="UTC")) &
                (funding.ts < pd.Timestamp(OOS1, tz="UTC") + pd.Timedelta(days=1))]
ann_oos = f_oos.rate.mean() * 3 * 365
deployed_days = int((c1 != 0).sum())
print(f"  OOS 資金費率平均年化 {ann_oos * 100:+.2f}%（{len(f_oos)} 筆）；"
      f"有損益日 {deployed_days}/{len(c1)}")

# ── 基準 ─────────────────────────────────────────────────────────────────────
spot = bt.load_csv("btc_spot_1d.csv")
spot = bt.clip(spot, OOS0, OOS1)
btc_ret = spot.set_index(spot.ts.dt.normalize()).close.pct_change().fillna(0.0)
print("\n" + bt.fmt(bt.metrics(btc_ret, "BTC 現貨 B&H")))

es = pd.read_csv(bt.ROOT / "data/cache/es_1m.csv", parse_dates=["ts"],
                 usecols=["ts", "Close"])
es = es[(es.ts >= OOS0) & (es.ts <= OOS1 + " 23:59")]
es_d = es.set_index("ts").Close.resample("1D").last().dropna()
es_ret = es_d.pct_change().fillna(0.0)
if es_ret.index.tz is None:
    es_ret = es_ret.tz_localize("UTC")
print(bt.fmt(bt.metrics(es_ret, "標普500（ES 近似）")))

# ── 驗收判定 ─────────────────────────────────────────────────────────────────
ok = m["cagr"] >= 0.10 and m["max_dd"] <= 0.10
print(f"\n══════ 驗收（spec §0）══════")
print(f"組合 OOS 年化 {m['cagr'] * 100:+.2f}%（門檻 +10%）、"
      f"MaxDD {m['max_dd'] * 100:.2f}%（門檻 10%）→ {'達標' if ok else '未達標'}")
