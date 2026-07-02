# -*- coding: utf-8 -*-
"""IS（2020-01-01 ~ 2024-12-31）審計與閘門判定（spec §3）。

只跑 IS 段。閘門（三條全過才進 OOS）：
  1. 年化 ≥ +3%
  2. MaxDD ≤ 20%
  3. 分年報酬非單一年份貢獻 > 90%（以「移除最佳年後仍為正」近似檢驗，
     並列印分年供人工判讀）

輸出：reports/btc_runs/is_*.csv（日報酬曲線）、is_summary.txt。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout.reconfigure(encoding="utf-8")

from research.btc import backtest as bt

IS0, IS1 = "2020-01-01", "2024-12-31"
OUT = bt.ROOT / "reports/btc_runs"
OUT.mkdir(parents=True, exist_ok=True)

funding = bt.load_csv("btc_funding.csv")
perp_1d = bt.load_csv("btc_perp_1d.csv")
perp_5m = bt.load_csv("btc_perp_5m.csv")

print("══════ IS 2020-01-01 ~ 2024-12-31（淨費後）══════\n")

results = {}

c1 = bt.run_c1(funding, IS0, IS1)
results["C1_carry"] = c1
c1_on = bt.run_c1(funding, IS0, IS1, always_on=True)  # 審計參考（非閘門對象）

c2 = bt.run_c2(perp_1d, IS0, IS1)
results["C2_momentum"] = c2

c3, c3_trades = bt.run_c3(perp_5m, IS0, IS1)
results["C3_orb"] = c3
c3_trades.to_csv(OUT / "is_c3_trades.csv", index=False)

lines = []
for name, s in results.items():
    m = bt.metrics(s, name)
    lines.append(bt.fmt(m))
    s.rename("ret").to_csv(OUT / f"is_{name}.csv")

    yearly = m["yearly"]
    total = m["final"] - 1
    gate1 = m["cagr"] >= 0.03
    gate2 = m["max_dd"] <= 0.20
    # 閘門3：移除最佳年後（幾何）仍為正
    if total > 0 and yearly:
        best_y = max(yearly, key=yearly.get)
        rest = (m["final"] / (1 + yearly[best_y])) - 1
        gate3 = rest > 0
    else:
        best_y, rest, gate3 = None, 0.0, False
    verdict = "進 OOS" if (gate1 and gate2 and gate3) else "淘汰"
    lines.append(f"  閘門: 年化≥3% {'✓' if gate1 else '✗'} | MaxDD≤20% "
                 f"{'✓' if gate2 else '✗'} | 移除最佳年({best_y})後其餘 "
                 f"{rest * 100:+.1f}% {'✓' if gate3 else '✗'}  → **{verdict}**")

lines.append("")
lines.append("[審計參考] C1 always-on（不設門檻）: " + bt.fmt(bt.metrics(c1_on, "C1_always_on")))
if len(c3_trades):
    t = c3_trades
    lines.append(f"[審計參考] C3 交易數 {len(t)}、勝率 {(t.pnl > 0).mean() * 100:.1f}%、"
                 f"總R {t.r.sum():+.1f}、停損距離中位數 "
                 f"{(abs(t.entry - t.stop) / t.entry).median() * 100:.2f}%")

text = "\n".join(lines)
print(text)
(OUT / "is_summary.txt").write_text(text, encoding="utf-8")
