# -*- coding: utf-8 -*-
"""最終 OOS 一次性驗收（ny-window-research-spec §5）——2026-07-02 已執行。

組合 = F1'（ORB 限窗 win_eod，排除 FOMC 日＝IS 預登記決策）
     + F3 （GapGo win_eod）
結果：預登記組合 1% 檔 OOS 年化 -2.04%、MaxDD 15.4% → 未達標。
F3 OOS 陣亡（-12.8R）；F1' 單獨 +10.03%/9.8%（事後敏感度，非主答案）。
詳見 reports/window-report-2026-07-02.md。

重跑注意：GapGo OOS 已產出（reports/window_runs/gapgo_win_eod_*_OOS/），
腳本會跳過既有 trades.csv 的引擎段，只重算合併模擬。
"""
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import engine.backtest.runner as R
from engine.model.config import StrategyConfig

_orig_load = R.load_bars
_cache: dict = {}
R.load_bars = lambda p: _cache.setdefault(str(p), _orig_load(p))

OUT = ROOT / "reports/window_runs"
POINT_VALUE = 2.0
START_EQ = 50_000.0

# ── 1. GapGo OOS（一次性）────────────────────────────────────────────────────
D0, D1 = date(2025, 1, 1), date(2026, 6, 12)
for tname, tier in [("r05", 0.5), ("r10", 1.0)]:
    key = f"gapgo_win_eod_{tname}_OOS"
    if not (OUT / key / "trades.csv").exists():
        cfg = StrategyConfig.for_gapgo(risk_per_trade_pct=tier)
        s = R.run_all(config=cfg, out_dir=OUT / key, verbose=False,
                      json_days=1, start_date=D0, end_date=D1)
        print(f"{key:26s} n={s['total_trades']:4d} win={s['win_rate']*100:5.1f}% "
              f"R={s['total_r']:+8.2f} PnL={s['pnl_usd']:+10.0f} "
              f"MaxDD={s['max_drawdown_usd']:8.0f}", flush=True)

# ── 2. 合併權益模擬（附錄 C 方法）────────────────────────────────────────────
cal = pd.read_csv(ROOT / "data/econ_calendar.csv")
FOMC = set(cal[cal.event == "FOMC"].date)

def load_trades(run_key, label, exclude_fomc=False):
    df = pd.read_csv(OUT / run_key / "trades.csv")
    if exclude_fomc:
        before = len(df)
        df = df[~df.date.isin(FOMC)]
        print(f"  [{label}] 排除 FOMC 日交易 {before - len(df)} 筆（{run_key}）")
    df["entry_ts"] = pd.to_datetime(df.entry_time_utc, utc=True)
    df["strategy"] = label
    df["pnl_per_ct"] = df.pnl_usd / df.qty
    return df

def merged_sim(dfs, tier_pct, label=""):
    allt = pd.concat(dfs).sort_values("entry_ts").reset_index(drop=True)
    tier = tier_pct / 100.0
    eq, peak, max_dd = START_EQ, START_EQ, 0.0
    rows = []
    for _, t in allt.iterrows():
        qty = int(eq * tier / (t.stop_dist * POINT_VALUE))
        if qty < 1:
            rows.append(dict(date=t.date, strategy=t.strategy, pnl=0.0, r=0.0, skip=True))
            continue
        pnl = qty * t.pnl_per_ct
        eq += pnl
        peak = max(peak, eq)
        max_dd = max(max_dd, (peak - eq) / peak)
        rows.append(dict(date=t.date, strategy=t.strategy, pnl=pnl, r=t.r_multiple, skip=False))
    sim = pd.DataFrame(rows)
    d0, d1 = pd.to_datetime(allt.date.min()), pd.to_datetime(allt.date.max())
    years = (d1 - d0).days / 365.25
    cagr = (eq / START_EQ) ** (1 / years) - 1
    print(f"\n>> {label}  檔位 {tier_pct}%  （{d0.date()} ~ {d1.date()}, {years:.2f}y）")
    print(f"  終值 ${eq:,.0f}  年化 {cagr*100:+.2f}%  MaxDD {max_dd*100:.1f}%  "
          f"跳過 {int(sim.skip.sum())}/{len(sim)}")
    for lab, g in sim[~sim.skip].groupby("strategy"):
        print(f"    {lab:10s} n={len(g):4d}  PnL={g.pnl.sum():+12,.0f}  R={g.r.sum():+8.2f}")
    sim["ym"] = pd.to_datetime(sim.date).dt.to_period("M")
    piv = sim.pivot_table(index="ym", columns="strategy", values="r", aggfunc="sum")
    if piv.shape[1] >= 2:
        print(f"    月R相關性 {piv.fillna(0).corr().iloc[0,1]:+.2f}")
    return dict(final_eq=eq, cagr=cagr, max_dd=max_dd)

print("\n══════ IS（2021-06-13 ~ 2024-12-31）══════")
for tname, tier in [("r05", 0.5), ("r10", 1.0)]:
    orb = load_trades(f"orb_win_eod_{tname}_IS", "ORB限窗", exclude_fomc=True)
    gg  = load_trades(f"gapgo_win_eod_{tname}_IS", "GapGo")
    merged_sim([orb, gg], tier, label=f"組合 IS {tname}")

print("\n══════ OOS（2025-01-01 ~ 2026-06-12）— 一次性驗收 ══════")
summary = {}
for tname, tier in [("r05", 0.5), ("r10", 1.0)]:
    orb = load_trades(f"orb_win_eod_{tname}_OOS", "ORB限窗", exclude_fomc=True)
    gg  = load_trades(f"gapgo_win_eod_{tname}_OOS", "GapGo")
    summary[tname] = merged_sim([orb, gg], tier, label=f"組合 OOS {tname}")

print("\n══════ 敏感度：ORB 單獨（事後分析，非預登記主答案）══════")
for tname, tier in [("r05", 0.5), ("r10", 1.0)]:
    orb_f = load_trades(f"orb_win_eod_{tname}_OOS", "ORB限窗", exclude_fomc=True)
    merged_sim([orb_f], tier, label=f"F1'（排FOMC）單獨 OOS {tname}")
    orb0 = load_trades(f"orb_win_eod_{tname}_OOS", "ORB限窗")
    merged_sim([orb0], tier, label=f"F1（含FOMC）單獨 OOS {tname}")

orb_raw = pd.read_csv(OUT / "orb_win_eod_r10_OOS/trades.csv")
fomc_tr = orb_raw[orb_raw.date.isin(FOMC)]
print(f"\nFOMC 排除的 OOS 影響：{len(fomc_tr)} 筆，總R {fomc_tr.r_multiple.sum():+.2f}，"
      f"PnL {fomc_tr.pnl_usd.sum():+.0f}（1% 檔原口徑）")

print("\n══════ 驗收判定（預登記組合 F1'+F3）══════")
r10 = summary["r10"]
ok = r10["cagr"] >= 0.10 and r10["max_dd"] <= 0.10
print(f"1% 檔 OOS 年化 {r10['cagr']*100:+.2f}%（門檻 +10%）、"
      f"MaxDD {r10['max_dd']*100:.1f}%（門檻 10%）→ {'達標' if ok else '未達標'}")
