# -*- coding: utf-8 -*-
"""合併權益模擬（方法同報告附錄 C）：多策略 trades.csv 按進場時間排序、
單一帳戶時序復利，每筆風險 = 檔位 × 當下權益，開不出 1 口即跳過（誠實風控）。

用法：
  python research/window_audit/portfolio_sim.py <tier_pct> <label:path> [label:path ...]
例：
  python research/window_audit/portfolio_sim.py 1.0 \
      orb:reports/window_runs/orb_win_eod_r10_OOS/trades.csv \
      gapgo:reports/window_runs/gapgo_win_eod_r10_OOS/trades.csv

輸出：合併年化 / MaxDD(%) / 各策略貢獻 / 月 R 相關性 / 最大同時持倉數。
點值：MNQ $2/pt（本研究窗內策略皆 MNQ）。
"""
import sys
import math
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POINT_VALUE = 2.0
START_EQ = 50_000.0

def main():
    tier = float(sys.argv[1]) / 100.0
    sources = []
    for a in sys.argv[2:]:
        label, p = a.split(":", 1)
        df = pd.read_csv(ROOT / p, parse_dates=["date"])
        df["entry_ts"] = pd.to_datetime(df.entry_time_utc, utc=True)
        df["exit_reason"] = df.exit_reason.fillna("?")
        df["strategy"] = label
        # 每口損益（原 run 的 pnl 含手續費、按原口數）
        df["pnl_per_ct"] = df.pnl_usd / df.qty
        sources.append(df)
    allt = pd.concat(sources).sort_values("entry_ts").reset_index(drop=True)

    eq = START_EQ
    peak = eq
    max_dd_pct = 0.0
    rows = []
    open_iv = []   # (entry_ts, exit approx) 近似同時持倉檢查：用進場日粒度
    for _, t in allt.iterrows():
        risk_budget = eq * tier
        qty = int(risk_budget / (t.stop_dist * POINT_VALUE))
        if qty < 1:
            rows.append(dict(ts=t.entry_ts, strategy=t.strategy, qty=0, pnl=0.0,
                             r=0.0, skipped=True, date=t.date))
            continue
        pnl = qty * t.pnl_per_ct
        eq += pnl
        peak = max(peak, eq)
        dd = (peak - eq) / peak
        max_dd_pct = max(max_dd_pct, dd)
        rows.append(dict(ts=t.entry_ts, strategy=t.strategy, qty=qty, pnl=pnl,
                         r=t.r_multiple, skipped=False, date=t.date))

    sim = pd.DataFrame(rows)
    days = (allt.date.max() - allt.date.min()).days
    years = days / 365.25
    cagr = (eq / START_EQ) ** (1 / years) - 1 if years > 0 else float("nan")

    print(f"期間: {allt.date.min().date()} ~ {allt.date.max().date()}（{years:.2f} 年）  檔位: {tier*100:.1f}%")
    print(f"合併: 終值 ${eq:,.0f}  年化 {cagr*100:+.2f}%  MaxDD {max_dd_pct*100:.1f}%  "
          f"跳過(開不出1口) {int(sim.skipped.sum())}/{len(sim)}")
    for lab, g in sim[~sim.skipped].groupby("strategy"):
        print(f"  {lab:8s} n={len(g):4d}  PnL={g.pnl.sum():+12,.0f}  總R={g.r.sum():+8.2f}")

    # 月 R 相關性（需 >=2 策略）
    labs = sim.strategy.unique()
    if len(labs) >= 2:
        sim["ym"] = pd.to_datetime(sim.date).dt.to_period("M")
        piv = sim.pivot_table(index="ym", columns="strategy", values="r", aggfunc="sum").fillna(0)
        if piv.shape[1] >= 2:
            corr = piv.corr().iloc[0, 1]
            print(f"  月 R 相關性: {corr:+.2f}")

    # 同日雙策略持倉（保證金重疊提示）
    if len(labs) >= 2:
        per_day = sim[~sim.skipped].groupby(["date"]).strategy.nunique()
        both = int((per_day >= 2).sum())
        print(f"  同日兩策略都有交易的日子: {both} 天（保證金重疊未建模，影子模式驗證）")

if __name__ == "__main__":
    main()
