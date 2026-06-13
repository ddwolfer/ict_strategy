"""多策略回放資料生成驅動。

對前端策略切換器要展示的每一套策略，用「與驗證報告完全一致的 config」
跑滿歷史，輸出到各自的 web/replay_data_<key>/ 目錄，並印出總筆數/總R，
供與 reports/strategy-report-2026-06-13.md 的數字做忠實度比對。

忠實度關鍵（前端絕不偽造資料）：
- 倫敦時段「大NQ」：必須 instrument="NQ"（$20/pt），否則退回 MNQ 會被手續費
  吃光、顯示出與報告不符的假象（報告附錄 A 已診斷此陷阱）。
- ORB：MNQ（for_orb 預設），qty 1~2 口，pnl 對 $2/pt。

用法：
    python -m engine.backtest.gen_replay                 # 全部 5 年、4 策略
    python -m engine.backtest.gen_replay --strategies london orb
    python -m engine.backtest.gen_replay --recent-days 25   # 小範圍快速驗證
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from engine.model.config import StrategyConfig
from engine.backtest.runner import run_all, load_bars, _DEFAULT_CSV
from engine.core.sessions import trading_date

_WEB = Path(__file__).parent.parent.parent / "web"


def _strategy_specs() -> dict[str, dict]:
    """策略 key -> {label, status, config, dir}。

    label/status 與前端策略選單一致（驗證狀態誠實標註）。
    """
    return {
        "nyam": {
            "label": "NY_AM ICT",
            "status": "regime",          # ⚠ 制度依賴
            "config": StrategyConfig(),  # 原始預設模型
            "dir": _WEB / "replay_data_nyam",
        },
        "london": {
            "label": "倫敦 ICT（大NQ）",
            "status": "validated",       # ✅ 已驗證
            # 忠實度：大NQ 合約（$20/pt），與報告附錄 A 的通過版一致
            "config": StrategyConfig.for_session("LONDON", instrument="NQ"),
            "dir": _WEB / "replay_data_london",
        },
        "orb": {
            "label": "ORB 30分",
            "status": "validated",       # ✅ 已驗證
            "config": StrategyConfig.for_orb(),   # MNQ 預設即正確
            "dir": _WEB / "replay_data_orb",
        },
        "sb": {
            "label": "Silver Bullet",
            "status": "insufficient",    # ⓘ 樣本不足
            "config": StrategyConfig.silver_bullet(),
            "dir": _WEB / "replay_data_sb",
        },
    }


def main() -> None:
    specs = _strategy_specs()
    parser = argparse.ArgumentParser(description="多策略回放資料生成")
    parser.add_argument(
        "--strategies", nargs="+", choices=list(specs.keys()),
        default=list(specs.keys()),
        help="要生成的策略（預設全部）",
    )
    parser.add_argument(
        "--recent-days", type=int, default=0,
        help="僅生成最近 N 個交易日（0=全部；小範圍快速驗證用）",
    )
    args = parser.parse_args()

    # 小範圍模式：用 start_date 限制回測範圍（暖機歷史仍由 runner 內部回看）
    start_date: date | None = None
    if args.recent_days > 0:
        all_bars = load_bars(_DEFAULT_CSV)
        days = sorted({trading_date(b.ts_utc) for b in all_bars})
        if len(days) > args.recent_days:
            start_date = days[-args.recent_days]
        print(f"[小範圍] 僅 {start_date} 起共 {args.recent_days} 個交易日")

    results: dict[str, dict] = {}
    for key in args.strategies:
        spec = specs[key]
        print(f"\n{'='*60}\n[{key}] {spec['label']}  ->  {spec['dir'].name}\n{'='*60}")
        summary = run_all(
            config=spec["config"],
            out_dir=spec["dir"],
            verbose=True,
            json_days=0,                 # 全歷史輸出
            start_date=start_date,
        )
        results[key] = summary

    # 忠實度比對摘要
    print(f"\n{'#'*60}\n# 生成完成 — 總計\n{'#'*60}")
    print(f"{'策略':<22}{'筆數':>8}{'勝率':>8}{'總R':>10}{'PnL':>12}")
    for key in args.strategies:
        s = results[key]
        print(f"{specs[key]['label']:<22}{s['total_trades']:>8}"
              f"{s['win_rate']:>7.1%}{s['total_r']:>+10.2f}{s['pnl_usd']:>+12.0f}")
    print("\n比對基準（reports/strategy-report-2026-06-13.md 全期，0.5% 檔）：")
    print("  倫敦 ICT（大NQ）約 663 筆 / +58~82R   |   ORB 約 879 筆 / +114R")


if __name__ == "__main__":
    main()
