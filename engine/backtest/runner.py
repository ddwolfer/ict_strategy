"""回測 Runner — run_day / run_all / CLI。

使用方式：
    python -m engine.backtest.runner        # 跑全量回測
"""
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from engine.core.types import Bar, TICK, POINT_VALUE
from engine.core.sessions import trading_date, is_in_window, _to_et, ET
from engine.data.loader import load_bars, list_trading_days
from engine.detectors.fvg import FVGDetector
from engine.detectors.pools import LiquidityPoolTracker
from engine.model.config import StrategyConfig
from engine.model.bias import DailyBias, compute_bias
from engine.model.strategy import ICTStrategy, StateChanged
from engine.sim.broker import SimBroker, BrokerConfig
from engine.sim.risk import RiskManager, RiskConfig, SessionState
from engine.backtest.decision_log import DayResult, _ts

_REPLAY_DIR = Path(__file__).parent.parent.parent / "web" / "replay_data"
_DEFAULT_CSV = Path(__file__).parent.parent.parent / "data" / "cache" / "nq_1m.csv"


def _et_hm(h: int, m: int) -> time:
    return time(h, m)


def _bars_for_day_window(all_bars: list[Bar], day: date) -> list[Bar]:
    """取某交易日 08:00–12:30 ET 的 bars（含 context 段 08:00–09:29）。"""
    result = []
    for b in all_bars:
        if trading_date(b.ts_utc) != day:
            continue
        et = _to_et(b.ts_utc)
        t = et.time()
        # 08:00 <= t < 12:30
        if time(8, 0) <= t < time(12, 30):
            result.append(b)
    return sorted(result, key=lambda b: b.ts_utc)


def run_day(
    day: date,
    config: StrategyConfig,
    all_bars: list[Bar],
    initial_equity: float = 50_000.0,
) -> DayResult:
    """跑單日回測，回傳 DayResult。

    Parameters
    ----------
    day         : 交易日（ET）
    config      : 策略設定
    all_bars    : 全部歷史 bars（包含今日之前的所有資料）
    initial_equity : 起始權益（帳戶累計；通常由 run_all 傳入）
    """
    # ── 歷史 bars（截至昨日）────────────────────────────────────────────────
    history_bars = [b for b in all_bars if trading_date(b.ts_utc) < day]

    # ── 計算偏向 ─────────────────────────────────────────────────────────────
    bias = compute_bias(history_bars, config)

    # ── 今日 bars（08:00–12:30 ET）──────────────────────────────────────────
    day_bars = _bars_for_day_window(all_bars, day)
    if not day_bars:
        # 此交易日無資料
        return DayResult(
            date=day, bars=[], session_start_t=0, session_end_t=0,
            state_timeline=[], closed_trades=[], pool_events=[], fvg_snapshots=[],
            broker=SimBroker(), strategy=None,  # type: ignore[arg-type]
            bias=bias, config=config, equity_points=[],
        )

    # ── session 時間戳 ──────────────────────────────────────────────────────
    session_start_t = 0
    session_end_t = 0
    for b in day_bars:
        et = _to_et(b.ts_utc)
        if et.time() >= time(9, 30) and session_start_t == 0:
            session_start_t = _ts(b.ts_utc)
        if et.time() >= time(12, 29):
            session_end_t = _ts(b.ts_utc)
            break

    # ── 建立 broker / risk / strategy ───────────────────────────────────────
    broker_cfg = BrokerConfig(
        slippage_ticks=config.slippage_ticks,
        commission_per_side=config.commission_per_side,
    )
    broker = SimBroker(broker_cfg)

    risk_cfg = RiskConfig(
        risk_per_trade_pct=config.risk_per_trade_pct,
        account_equity=initial_equity,
        max_trades_per_session=config.max_trades_per_session,
        daily_loss_limit_r=config.daily_loss_limit_r,
    )
    risk_mgr = RiskManager(risk_cfg)

    strategy = ICTStrategy(config=config, bias=bias, broker=broker, risk_manager=risk_mgr)

    # ── 獨立 pool / fvg 追蹤（用於 annotations 輸出）────────────────────────
    ann_pool = LiquidityPoolTracker(n=config.swing_n, r=config.raid_recover_bars)
    ann_fvg = FVGDetector()
    all_pool_evts: list = []
    all_fvg_evts: list = []

    # ── 餵歷史 context 給 annotation detectors（可選：建立正確 PDH/PDL）──────
    for b in history_bars[-200:]:  # 最多 200 根避免太慢
        ann_pool.on_bar(b)

    # ── 逐根跑 ───────────────────────────────────────────────────────────────
    equity_points: list[tuple[int, float, float]] = []
    running_equity = initial_equity

    for b in day_bars:
        # 今日 bars 先餵 annotation detectors
        pool_evts = ann_pool.on_bar(b)
        fvg_evts = ann_fvg.on_bar(b)
        all_pool_evts.extend(pool_evts)
        all_fvg_evts.extend(fvg_evts)

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
) -> dict:
    """跑全量回測，寫出 replay_data JSON，回傳統計摘要。"""
    cfg = config or StrategyConfig()
    out_dir = out_dir or _REPLAY_DIR

    all_bars = load_bars(csv_path)
    trading_days = list_trading_days(csv_path)

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

    for day in trading_days:
        result = run_day(day, cfg, all_bars, initial_equity=running_equity)

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

        summary = {
            "date": str(day),
            "bias": result.bias.direction,
            "trades": stats["trades"],
            "wins": stats["wins"],
            "pnl_usd": stats["pnl_usd"],
            "total_r": stats["total_r"],
            "ambiguous": stats["ambiguous_count"],
        }
        day_summaries.append(summary)

        # 寫出 JSON
        result.write_json(out_dir)

        if verbose:
            flag = "RED" if stats["pnl_usd"] < 0 else ("---" if stats["trades"] == 0 else "GRN")
            print(f"  {day} [{result.bias.direction:8s}] {flag} "
                  f"T={stats['trades']} W={stats['wins']} "
                  f"R={stats['total_r']:+.2f} PnL={stats['pnl_usd']:+.0f}")

    # 寫 index.json
    index = {
        "days": day_summaries,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    idx_path = out_dir / "index.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

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
    run_all(verbose=True)
