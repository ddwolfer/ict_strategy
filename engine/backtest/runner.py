"""回測 Runner — run_day / run_all / CLI。

使用方式：
    python -m engine.backtest.runner        # 跑全量回測
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from engine.core.types import Bar, TICK, POINT_VALUE
from engine.core.sessions import trading_date, is_in_window, _to_et, ET
from engine.data.loader import load_bars, list_trading_days
from engine.data.loader import load_bars as _load_bars_generic
from engine.detectors.fvg import FVGDetector
from engine.detectors.mss import MSSDetector
from engine.detectors.pools import LiquidityPoolTracker
from engine.model.config import StrategyConfig
from engine.model.bias import DailyBias, compute_bias
from engine.model.strategy import ICTStrategy, StateChanged
from engine.model.orb import ORBStrategy
from engine.sim.broker import SimBroker, BrokerConfig
from engine.sim.risk import RiskManager, RiskConfig, SessionState
from engine.backtest.decision_log import DayResult, _ts

_REPLAY_DIR = Path(__file__).parent.parent.parent / "web" / "replay_data"
_DEFAULT_CSV = Path(__file__).parent.parent.parent / "data" / "cache" / "nq_1m.csv"
_DEFAULT_ES_CSV = Path(__file__).parent.parent.parent / "data" / "cache" / "es_1m.csv"
_SB_REPLAY_DIR = Path(__file__).parent.parent.parent / "web" / "replay_data_sb"


def _et_hm(h: int, m: int) -> time:
    return time(h, m)


def _parse_hm(s: str) -> time:
    """'HH:MM' → time。"""
    h, m = int(s[:2]), int(s[3:])
    return time(h, m)


def _bars_for_day_window(
    all_bars: list[Bar],
    day: date,
    config: "StrategyConfig | None" = None,
) -> list[Bar]:
    """取某交易日 context_start–flatten_time ET 的 bars。

    context_start 預設 "08:00"（NY_AM/NY_PM）；LONDON 為 "00:00"。
    flatten_time 預設 "12:30"（NY_AM）。
    """
    if config is not None:
        t_start = _parse_hm(config.context_start)
        t_end   = _parse_hm(config.flatten_time)
    else:
        t_start = time(8, 0)
        t_end   = time(12, 30)

    result = []
    for b in all_bars:
        if trading_date(b.ts_utc) != day:
            continue
        et = _to_et(b.ts_utc)
        t = et.time()
        if t_start <= t < t_end:
            result.append(b)
    return sorted(result, key=lambda b: b.ts_utc)


def run_day(
    day: date,
    config: StrategyConfig,
    all_bars: list[Bar],
    initial_equity: float = 50_000.0,
    es_bars_map: dict | None = None,
    history_bars: list[Bar] | None = None,
    day_all_bars: list[Bar] | None = None,
) -> DayResult:
    """跑單日回測，回傳 DayResult。

    Parameters
    ----------
    day         : 交易日（ET）
    config      : 策略設定
    all_bars    : 全部歷史 bars（包含今日之前的所有資料）
    initial_equity : 起始權益（帳戶累計；通常由 run_all 傳入）
    history_bars / day_all_bars : run_all 預先分組的切片（效能用）；
        不給時退回逐根掃描（相容舊呼叫，僅適合小資料集）
    """
    # ── 歷史 bars（截至昨日）────────────────────────────────────────────────
    if history_bars is None:
        history_bars = [b for b in all_bars if trading_date(b.ts_utc) < day]

    # ── 計算偏向 ─────────────────────────────────────────────────────────────
    bias = compute_bias(history_bars, config)

    # ── 今日 bars（context_start–flatten_time ET）──────────────────────────
    t_ctx_start = _parse_hm(config.context_start)
    t_flatten   = _parse_hm(config.flatten_time)
    if day_all_bars is not None:
        day_bars = []
        for b in day_all_bars:
            t = _to_et(b.ts_utc).time()
            if t_ctx_start <= t < t_flatten:
                day_bars.append(b)
        day_bars.sort(key=lambda b: b.ts_utc)
    else:
        day_bars = _bars_for_day_window(all_bars, day, config=config)
    if not day_bars:
        # 此交易日無資料
        return DayResult(
            date=day, bars=[], session_start_t=0, session_end_t=0,
            state_timeline=[], closed_trades=[], pool_events=[], fvg_snapshots=[],
            broker=SimBroker(), strategy=None,  # type: ignore[arg-type]
            bias=bias, config=config, equity_points=[],
        )

    # ── session 時間戳（entry_window 開始到 flatten_time 前）──────────────
    t_entry_start = _parse_hm(config.entry_window[0])
    # flatten 前一分鐘作為 session_end_t 標記（前端分隔線用）
    _ft_h, _ft_m = int(config.flatten_time[:2]), int(config.flatten_time[3:])
    from datetime import timedelta as _td
    import datetime as _dt
    _ft_minus1 = (_dt.datetime(2000, 1, 1, _ft_h, _ft_m) - _td(minutes=1)).time()
    session_start_t = 0
    session_end_t = 0
    for b in day_bars:
        et = _to_et(b.ts_utc)
        if et.time() >= t_entry_start and session_start_t == 0:
            session_start_t = _ts(b.ts_utc)
        if et.time() >= _ft_minus1:
            session_end_t = _ts(b.ts_utc)
            break

    # ── 建立 broker / risk / strategy ───────────────────────────────────────
    broker_cfg = BrokerConfig(
        slippage_ticks=config.slippage_ticks,
        commission_per_side=config.commission_per_side,
        point_value=config.point_value,
    )
    broker = SimBroker(broker_cfg)

    risk_cfg = RiskConfig(
        risk_per_trade_pct=config.risk_per_trade_pct,
        account_equity=initial_equity,
        max_trades_per_session=config.max_trades_per_session,
        daily_loss_limit_r=config.daily_loss_limit_r,
        point_value=config.point_value,
    )
    risk_mgr = RiskManager(risk_cfg)

    # Build ES bars slice for this day (only feed bars within the day window)
    day_es_bars: dict = {}
    if es_bars_map:
        for b in day_bars:
            es_b = es_bars_map.get(b.ts_utc)
            if es_b is not None:
                day_es_bars[b.ts_utc] = es_b
        # Also include history for SMT lookback (last 200 bars before day)
        history_es = {b_h.ts_utc: es_bars_map[b_h.ts_utc]
                      for b_h in history_bars[-200:] if b_h.ts_utc in es_bars_map}
        day_es_bars.update(history_es)

    if config.strategy_type == "orb":
        strategy: ICTStrategy | ORBStrategy = ORBStrategy(
            config=config, bias=bias, broker=broker, risk_manager=risk_mgr
        )
    else:
        strategy = ICTStrategy(config=config, bias=bias, broker=broker, risk_manager=risk_mgr,
                               es_bars=day_es_bars if day_es_bars else None)

    # ── 獨立 pool / fvg 追蹤（用於 annotations 輸出）────────────────────────
    ann_pool = LiquidityPoolTracker(n=config.swing_n, r=config.raid_recover_bars)
    ann_fvg = FVGDetector()
    ann_mss = MSSDetector(
        n=config.swing_n,
        window=config.displacement_window,
        mult=config.displacement_mult,
    )
    all_pool_evts: list = []
    all_fvg_evts: list = []
    all_mss_evts: list = []

    # ── 餵歷史 context 給 annotation detectors（可選：建立正確 PDH/PDL）──────
    for b in history_bars[-200:]:  # 最多 200 根避免太慢
        ann_pool.on_bar(b)
        ann_mss.on_bar(b)

    # ── 逐根跑 ───────────────────────────────────────────────────────────────
    equity_points: list[tuple[int, float, float]] = []
    running_equity = initial_equity

    for b in day_bars:
        # 今日 bars 先餵 annotation detectors
        pool_evts = ann_pool.on_bar(b)
        fvg_evts = ann_fvg.on_bar(b)
        all_pool_evts.extend(pool_evts)
        all_fvg_evts.extend(fvg_evts)
        all_mss_evts.extend(ann_mss.on_bar(b))

        # 策略 on_bar
        strategy.on_bar(b)

        # 當棒收盤後記錄 equity
        realized = broker._equity
        unrealized = (
            broker.position.unrealized_pnl_usd
            if broker.position is not None else 0.0
        )
        total = running_equity + realized + unrealized
        equity_points.append((_ts(b.ts_utc), running_equity + realized, total))

    # ── EOD 強平（若還有持倉）────────────────────────────────────────────────
    if broker.position is not None and day_bars:
        broker.flatten(day_bars[-1], reason="EOD")

    return DayResult(
        date=day,
        bars=day_bars,
        session_start_t=session_start_t,
        session_end_t=session_end_t,
        state_timeline=strategy.state_timeline,
        closed_trades=broker.trades,
        pool_events=all_pool_evts,
        fvg_snapshots=all_fvg_evts,
        mss_events=all_mss_evts,
        broker=broker,
        strategy=strategy,
        bias=bias,
        config=config,
        equity_points=equity_points,
    )


def run_all(
    config: StrategyConfig | None = None,
    csv_path: Path | str = _DEFAULT_CSV,
    out_dir: Path | None = None,
    verbose: bool = True,
    es_csv_path: Path | str | None = None,
    json_days: int = 60,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """跑全量回測，寫出 replay_data JSON，回傳統計摘要。

    json_days：只為最近 N 個交易日輸出回放 JSON（統計仍涵蓋全部交易日；
    大歷史下 1,250 份 JSON 會塞爆 repo）。0 = 全部輸出。
    """
    cfg = config or StrategyConfig()
    out_dir = out_dir or _REPLAY_DIR

    # Load ES bars if SMT filter active
    es_bars_map: dict = {}
    if cfg.smt_filter != "off":
        _es_path = es_csv_path or _DEFAULT_ES_CSV
        if Path(_es_path).exists():
            es_bars_list = _load_bars_generic(_es_path)
            es_bars_map = {b.ts_utc: b for b in es_bars_list}
            if verbose:
                print(f"載入 ES {len(es_bars_list):,} 根 1 分 K（SMT 過濾器）")
        else:
            if verbose:
                print(f"警告：ES CSV 不存在（{_es_path}），SMT 過濾器停用")

    all_bars = load_bars(csv_path)

    # 交易日分組一次算完（trading_date 含時區轉換，逐日全掃會是 O(N×D)）
    from collections import OrderedDict
    days_map: "OrderedDict[date, list[Bar]]" = OrderedDict()
    for b in all_bars:
        days_map.setdefault(trading_date(b.ts_utc), []).append(b)
    trading_days = list(days_map.keys())
    # IS/OOS 切分用日期範圍（history 分組仍含範圍前資料，偏向計算不受影響）
    all_days_ordered = trading_days
    if start_date or end_date:
        trading_days = [d for d in trading_days
                        if (start_date is None or d >= start_date)
                        and (end_date is None or d <= end_date)]

    # 偏向/暖機只需要近期歷史：取最近 HISTORY_DAYS 個交易日的 bars
    HISTORY_DAYS = 40   # m1_program 需 20 日 dealing range，40 日綽綽有餘

    if verbose:
        print(f"載入 {len(all_bars):,} 根 1 分 K，共 {len(trading_days)} 個交易日")

    # 累計帳戶權益（跨日繼承）
    running_equity = cfg.account_equity
    day_summaries: list[dict] = []

    total_trades = 0
    total_wins = 0
    total_r = 0.0
    total_pnl = 0.0
    total_ambiguous = 0
    peak_equity = running_equity
    max_dd = 0.0

    all_trade_rows: list[dict] = []

    day_pos = {d: k for k, d in enumerate(all_days_ordered)}
    for i, day in enumerate(trading_days):
        pos = day_pos[day]
        hist_days = all_days_ordered[max(0, pos - HISTORY_DAYS):pos]
        history_bars = [b for d in hist_days for b in days_map[d]]
        result = run_day(day, cfg, all_bars, initial_equity=running_equity,
                         es_bars_map=es_bars_map if es_bars_map else None,
                         history_bars=history_bars,
                         day_all_bars=days_map[day])

        for t in result.closed_trades:
            all_trade_rows.append({
                "date": str(day),
                "side": t.side,
                "entry_time_utc": t.entry_time.isoformat(),
                "entry_price": t.entry_price,
                "exit_price": t.exit_fills[-1].price if t.exit_fills else None,
                "exit_reason": t.exit_reason,
                "qty": t.qty,
                "stop_dist": round(t.initial_stop_distance, 2),
                "r_multiple": round(t.r_multiple, 4),
                "pnl_usd": round(t.pnl_usd, 2),
                "ambiguous": t.ambiguous,
            })

        # 更新權益
        day_pnl = sum(t.pnl_usd for t in result.closed_trades)
        running_equity += day_pnl

        stats = result.stats()
        total_trades += stats["trades"]
        total_wins += stats["wins"]
        total_r += stats["total_r"]
        total_pnl += stats["pnl_usd"]
        total_ambiguous += stats["ambiguous_count"]

        # 全局最大回撤
        if running_equity > peak_equity:
            peak_equity = running_equity
        dd = peak_equity - running_equity
        if dd > max_dd:
            max_dd = dd

        # 無時段 K 棒的日子（例如資料只到當日盤前）不輸出，
        # 避免前端載入空資料
        if not result.bars:
            if verbose:
                print(f"  {day} [skip] 無時段 K 棒，不輸出")
            continue

        summary = {
            "date": str(day),
            "bias": result.bias.direction,
            "bias_reason": result.bias.reason[:60] if result.bias.reason else "",
            "trades": stats["trades"],
            "wins": stats["wins"],
            "pnl_usd": stats["pnl_usd"],
            "total_r": stats["total_r"],
            "ambiguous": stats["ambiguous_count"],
        }
        day_summaries.append(summary)

        # 寫出 JSON（僅最近 json_days 個交易日；0=全部）
        if json_days <= 0 or i >= len(trading_days) - json_days:
            result.write_json(out_dir)

        if verbose:
            flag = "RED" if stats["pnl_usd"] < 0 else ("---" if stats["trades"] == 0 else "GRN")
            bias_label = result.bias.direction
            if bias_label == "BOTH":
                bias_label = "BOTH    "
            print(f"  {day} [{bias_label:8s}] {flag} "
                  f"T={stats['trades']} W={stats['wins']} "
                  f"R={stats['total_r']:+.2f} PnL={stats['pnl_usd']:+.0f}")

    # 寫 index.json（只列出有 JSON 檔的日子，避免前端選到 404）
    listed = day_summaries if json_days <= 0 else day_summaries[-json_days:]
    index = {
        "days": listed,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    idx_path = out_dir / "index.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    # 完整交易日誌（全部交易日，供統計分析）
    if all_trade_rows:
        import csv as _csv
        with open(out_dir / "trades.csv", "w", newline="", encoding="utf-8") as f:
            w = _csv.DictWriter(f, fieldnames=list(all_trade_rows[0].keys()))
            w.writeheader()
            w.writerows(all_trade_rows)

    summary = {
        "total_days": len(trading_days),
        "total_trades": total_trades,
        "total_wins": total_wins,
        "win_rate": total_wins / total_trades if total_trades else 0.0,
        "total_r": round(total_r, 4),
        "pnl_usd": round(total_pnl, 2),
        "final_equity": round(running_equity, 2),
        "max_drawdown_usd": round(max_dd, 2),
        "ambiguous_count": total_ambiguous,
    }

    if verbose:
        print("\n═══ 全量回測統計 ═══")
        print(f"  交易日  : {len(trading_days)}")
        print(f"  交易筆數: {total_trades}")
        print(f"  勝率    : {summary['win_rate']:.1%}")
        print(f"  總 R    : {total_r:+.2f}")
        print(f"  PnL     : {total_pnl:+,.0f} USD")
        print(f"  最大回撤: {max_dd:,.0f} USD")
        print(f"  Ambiguous: {total_ambiguous}")

    return summary


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ICT NQ 1m 回測 Runner")
    parser.add_argument(
        "--preset",
        choices=["silver_bullet"],
        default=None,
        help="使用 preset config（如 silver_bullet）",
    )
    parser.add_argument(
        "--session",
        choices=["NY_AM", "NY_PM", "LONDON"],
        default=None,
        help="交易時段（§2.4）：NY_AM（預設）/ NY_PM / LONDON",
    )
    parser.add_argument(
        "--strategy",
        choices=["ict", "orb"],
        default=None,
        help="策略類型：ict（預設）/ orb（Opening Range Breakout）",
    )
    args = parser.parse_args()

    if args.strategy == "orb":
        cfg = StrategyConfig.for_orb()
        print("[ORB] Using Opening Range Breakout strategy")
        run_all(config=cfg, verbose=True)
    elif args.preset == "silver_bullet":
        cfg = StrategyConfig.silver_bullet()
        print("[SB] Using Silver Bullet preset")
        run_all(config=cfg, out_dir=_SB_REPLAY_DIR, verbose=True)
    elif args.session and args.session != "NY_AM":
        cfg = StrategyConfig.for_session(args.session)
        print(f"[SESSION] {args.session}: entry={cfg.entry_window} flatten={cfg.flatten_time}")
        run_all(config=cfg, verbose=True)
    else:
        run_all(verbose=True)
