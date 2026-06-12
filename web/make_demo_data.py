"""make_demo_data.py — 產生 bar-by-bar 回放前端的示範資料。

用法（在專案根目錄執行）：
    python web/make_demo_data.py

輸出：
    web/replay_data/<YYYY-MM-DD>.json   （最近 3 個交易日各一份）
    web/replay_data/index.json
"""
from __future__ import annotations

import json
import sys
import os
from datetime import datetime, time, date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# ── 確保專案根目錄在 sys.path，讓 engine 可被匯入 ───────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.core.types import (
    Bar, TICK, POINT_VALUE,
    PoolCreated, PoolSwept, Raid,
    FVGCreated, FVGTouched, FVGFilled,
    MSS, Displacement, SwingConfirmed,
)
from engine.data.loader import load_bars
from engine.core.sessions import trading_date, is_in_window, ET
from engine.detectors.pools import LiquidityPoolTracker
from engine.detectors.fvg import FVGDetector
from engine.detectors.mss import MSSDetector

UTC = ZoneInfo("UTC")

# ── 輸出目錄 ────────────────────────────────────────────────────────────────
OUTPUT_DIR = _PROJECT_ROOT / "web" / "replay_data"

# ── 工具函式 ─────────────────────────────────────────────────────────────────

def ts(bar_or_dt) -> int:
    """回傳 epoch 秒（整數）。"""
    if isinstance(bar_or_dt, Bar):
        return int(bar_or_dt.ts_utc.timestamp())
    return int(bar_or_dt.timestamp())


def bar_to_dict(b: Bar) -> dict:
    return {"t": ts(b), "o": b.open, "h": b.high, "l": b.low, "c": b.close, "v": b.volume}


def et_time_of(bar: Bar) -> time:
    return bar.ts_utc.astimezone(ET).time()


def round_price(price: float, tick: float = TICK) -> float:
    return round(round(price / tick) * tick, 2)


# ── 尋找符合條件的交易日 ──────────────────────────────────────────────────────

def find_qualifying_days(all_bars: list[Bar], n: int = 3) -> list[date]:
    """找最近 n 個同時有 08:00–12:30 ET 窗口資料的交易日。"""
    # 依交易日分組
    from collections import defaultdict
    day_bars: dict[date, list[Bar]] = defaultdict(list)
    for b in all_bars:
        day_bars[trading_date(b.ts_utc)].append(b)

    qualifying = []
    for d in sorted(day_bars.keys(), reverse=True):
        bars = day_bars[d]
        has_early = any(
            time(8, 0) <= et_time_of(b) < time(9, 30) for b in bars
        )
        has_rth = any(
            time(9, 30) <= et_time_of(b) < time(12, 30) for b in bars
        )
        if has_early and has_rth:
            qualifying.append(d)
        if len(qualifying) >= n:
            break

    return list(reversed(qualifying))   # 升序（舊 → 新）


# ── 事件收集 ─────────────────────────────────────────────────────────────────

def collect_events_for_day(
    target_day: date,
    all_bars: list[Bar],
) -> tuple[
    list[Bar],          # window bars (08:00–12:30 ET)
    list,               # all events with confirmed_at in window
    list,               # MSS events
    list,               # Raid events
    list,               # FVG events (FVGCreated)
    list,               # PoolCreated events
    list,               # PoolSwept events
]:
    """從頭餵所有 bar，只收集 confirmed_at 落在當日 08:00–12:30 ET 窗口的事件。"""

    # 計算窗口時間邊界（UTC）
    window_start_et = datetime(target_day.year, target_day.month, target_day.day,
                               8, 0, 0, tzinfo=ET)
    window_end_et = datetime(target_day.year, target_day.month, target_day.day,
                             12, 30, 0, tzinfo=ET)
    window_start_utc = window_start_et.astimezone(UTC)
    window_end_utc = window_end_et.astimezone(UTC)

    pool_tracker = LiquidityPoolTracker()
    fvg_detector = FVGDetector()
    mss_detector = MSSDetector()

    window_bars: list[Bar] = []
    all_events: list = []
    mss_events: list[MSS] = []
    raid_events: list[Raid] = []
    fvg_created_events: list[FVGCreated] = []
    pool_created_events: list[PoolCreated] = []
    pool_swept_events: list[PoolSwept] = []

    for bar in all_bars:
        # 只餵到當日窗口結束
        if bar.ts_utc >= window_end_utc:
            # 還是要收集窗口結束前最後幾根確認的事件，已在迴圈內處理
            break

        # 執行偵測器
        pool_evts = pool_tracker.on_bar(bar)
        fvg_evts = fvg_detector.on_bar(bar)
        mss_evts = mss_detector.on_bar(bar)

        # 只收集 confirmed_at 落在窗口的事件
        for ev in pool_evts + fvg_evts + mss_evts:
            if window_start_utc <= ev.confirmed_at < window_end_utc:
                all_events.append(ev)
                if isinstance(ev, MSS):
                    mss_events.append(ev)
                elif isinstance(ev, Raid):
                    raid_events.append(ev)
                elif isinstance(ev, FVGCreated):
                    fvg_created_events.append(ev)
                elif isinstance(ev, PoolCreated):
                    pool_created_events.append(ev)
                elif isinstance(ev, PoolSwept):
                    pool_swept_events.append(ev)

        # 收集窗口內的 bar
        if window_start_utc <= bar.ts_utc < window_end_utc:
            window_bars.append(bar)

    return (
        window_bars, all_events,
        mss_events, raid_events,
        fvg_created_events, pool_created_events, pool_swept_events,
    )


# ── annotations 建構 ──────────────────────────────────────────────────────────

def build_annotations(
    all_events: list,
    window_bars: list[Bar],
    day_idx: int,   # 0-based，用於 id prefix
) -> tuple[list, list, list]:
    """回傳 (levels, zones, markers)。"""
    levels = []
    zones = []
    markers = []

    level_id = [0]
    zone_id = [0]

    def next_lid():
        level_id[0] += 1
        return f"L{day_idx+1}_{level_id[0]}"

    def next_zid():
        zone_id[0] += 1
        return f"Z{day_idx+1}_{zone_id[0]}"

    # 用 dict 追蹤 swept 狀態
    level_by_kind_price: dict[tuple, dict] = {}
    # zone anchor -> zone dict
    zone_by_anchor: dict[object, dict] = {}

    for ev in all_events:
        t = int(ev.confirmed_at.timestamp())

        # ── 水位 ──────────────────────────────────────────────
        if isinstance(ev, PoolCreated):
            key = (ev.kind, ev.level)
            if key not in level_by_kind_price:
                lvl = {
                    "id": next_lid(),
                    "kind": ev.kind,
                    "price": ev.level,
                    "from_t": t,
                    "to_t": None,
                    "swept_t": None,
                    "label": f"{ev.kind} {ev.level:.2f}",
                }
                levels.append(lvl)
                level_by_kind_price[key] = lvl

        elif isinstance(ev, PoolSwept):
            key = (ev.kind, ev.level)
            if key in level_by_kind_price:
                level_by_kind_price[key]["swept_t"] = t

        # ── Raid 標記 ──────────────────────────────────────────
        elif isinstance(ev, Raid):
            side = "BULL" if ev.side == "BUY" else "BEAR"
            markers.append({
                "t": t,
                "kind": "RAID",
                "side": side,
                "price": ev.level,
                "text": f"奇襲 {ev.kind} {ev.level:.2f}",
            })

        # ── FVG 區 ─────────────────────────────────────────────
        elif isinstance(ev, FVGCreated):
            zd = {
                "id": next_zid(),
                "kind": f"FVG_{ev.direction}",
                "top": ev.top,
                "bottom": ev.bottom,
                "from_t": t,
                "to_t": None,
                "status_changes": [{"t": t, "status": "fresh"}],
            }
            zones.append(zd)
            zone_by_anchor[ev.anchor] = zd

        elif isinstance(ev, FVGTouched):
            zd = zone_by_anchor.get(ev.fvg_anchor)
            if zd:
                zd["status_changes"].append({"t": t, "status": "touched"})

        elif isinstance(ev, FVGFilled):
            zd = zone_by_anchor.get(ev.fvg_anchor)
            if zd:
                zd["status_changes"].append({"t": t, "status": "filled"})
                zd["to_t"] = t

        # ── MSS 標記 ───────────────────────────────────────────
        elif isinstance(ev, MSS):
            side = "BULL" if ev.direction == "BULL" else "BEAR"
            arrow = "↑" if ev.direction == "BULL" else "↓"
            markers.append({
                "t": t,
                "kind": "MSS",
                "side": side,
                "price": ev.broken_swing_level,
                "text": f"MSS{arrow} 破 {ev.broken_swing_level:.2f}",
            })

    return levels, zones, markers


# ── 交易模擬 ─────────────────────────────────────────────────────────────────

def fabricate_trades(
    window_bars: list[Bar],
    mss_events: list[MSS],
    raid_events: list[Raid],
    fvg_events: list[FVGCreated],
    day_scenario: int,   # 0=win, 1=loss, 2=win
    day_idx: int,
) -> tuple[list, list, list, list]:
    """
    根據事件產生 1 筆合理的模擬交易。
    回傳 (trades, orders, state_timeline, equity)。
    """
    if not window_bars:
        return [], [], [], []

    session_bars = [b for b in window_bars if et_time_of(b) >= time(9, 30)]
    if not session_bars:
        session_bars = window_bars

    # ── 選擇觸發事件 ──────────────────────────────────────────
    trigger_event = None
    trigger_kind = None

    if mss_events:
        trigger_event = mss_events[0]
        trigger_kind = "MSS"
    elif raid_events:
        trigger_event = raid_events[0]
        trigger_kind = "RAID"

    # ── 決定方向 ──────────────────────────────────────────────
    if trigger_event:
        if trigger_kind == "MSS":
            direction = trigger_event.direction   # "BULL" or "BEAR"
        else:
            # Raid: side "BUY" → 被掃了 BUY 水位（賣方流動性）→ 看跌後反轉向上 → BULL
            direction = "BULL" if trigger_event.side == "BUY" else "BEAR"
    else:
        # 無事件 fallback：看第一小時整體方向
        first_bar = session_bars[0]
        ref_idx = min(30, len(session_bars) - 1)
        ref_bar = session_bars[ref_idx]
        direction = "BULL" if ref_bar.close > first_bar.open else "BEAR"

    # ── 決定進場 bar（觸發後 3–5 根）──────────────────────────
    if trigger_event:
        trigger_t = trigger_event.confirmed_at
        trigger_bar_idx = next(
            (i for i, b in enumerate(window_bars) if b.ts_utc >= trigger_t),
            len(window_bars) // 3,
        )
    else:
        trigger_bar_idx = len(session_bars) // 4

    entry_bar_offset = min(trigger_bar_idx + 4, len(window_bars) - 10)
    entry_bar_offset = max(entry_bar_offset, 1)
    entry_bar = window_bars[entry_bar_offset]

    # ── 進場價（取近整數）──────────────────────────────────────
    raw_entry = (entry_bar.high + entry_bar.low) / 2
    entry_price = round_price(raw_entry)

    # ── 停損 8 點，目標 1R=8pts / 2R=16pts ───────────────────
    stop_dist = 8.0
    if direction == "BULL":
        stop_initial = round_price(entry_price - stop_dist)
        target1 = round_price(entry_price + stop_dist)    # 1R
        target2 = round_price(entry_price + stop_dist * 2)  # 2R
    else:
        stop_initial = round_price(entry_price + stop_dist)
        target1 = round_price(entry_price - stop_dist)
        target2 = round_price(entry_price - stop_dist * 2)

    # ── 找 target1 hit bar ───────────────────────────────────
    bars_after_entry = window_bars[entry_bar_offset + 1:]

    def hits_target1(b: Bar) -> bool:
        if direction == "BULL":
            return b.high >= target1
        return b.low <= target1

    def hits_target2(b: Bar) -> bool:
        if direction == "BULL":
            return b.high >= target2
        return b.low <= target2

    def hits_stop(b: Bar) -> bool:
        if direction == "BULL":
            return b.low <= stop_initial
        return b.high >= stop_initial

    t1_bar = next((b for b in bars_after_entry if hits_target1(b)), None)
    t2_bar = next((b for b in bars_after_entry if hits_target2(b)), None)
    stop_bar = next((b for b in bars_after_entry if hits_stop(b)), None)

    # ── 根據情境決定結果 ──────────────────────────────────────
    # day_scenario 0,2 = win (hit T1+T2), 1 = loss (T1 then stop at BE or full loss)
    exit_fills = []
    stop_timeline = [{"t": ts(entry_bar), "price": stop_initial}]

    # target1 partial exit (0.5 qty => we model as qty=1 then second 1)
    # Simplify: 2 contracts total
    qty_total = 2

    if day_scenario in (0, 2):
        # Win: hit T1, move stop to BE, then hit T2
        if t1_bar:
            exit_fills.append({
                "t": ts(t1_bar), "price": target1, "qty": 1, "reason": "TARGET"
            })
            # Move stop to breakeven after T1
            be_stop = entry_price
            stop_timeline.append({"t": ts(t1_bar), "price": be_stop})

            if t2_bar and ts(t2_bar) > ts(t1_bar):
                exit_fills.append({
                    "t": ts(t2_bar), "price": target2, "qty": 1, "reason": "TARGET"
                })
            else:
                # EOD exit on last window bar
                eod_bar = window_bars[-1]
                exit_fills.append({
                    "t": ts(eod_bar), "price": eod_bar.close, "qty": 1, "reason": "EOD"
                })
        else:
            # Couldn't hit T1 — EOD exit
            eod_bar = window_bars[-1]
            eod_price = eod_bar.close
            exit_fills.append({"t": ts(eod_bar), "price": eod_price, "qty": 2, "reason": "EOD"})
    else:
        # Loss: maybe hit T1, then stop
        if t1_bar and (stop_bar is None or ts(t1_bar) < ts(stop_bar)):
            exit_fills.append({
                "t": ts(t1_bar), "price": target1, "qty": 1, "reason": "TARGET"
            })
            # Move stop to breakeven
            be_stop = entry_price
            stop_timeline.append({"t": ts(t1_bar), "price": be_stop})
            # Then stop
            if stop_bar:
                exit_fills.append({
                    "t": ts(stop_bar), "price": be_stop, "qty": 1, "reason": "STOP"
                })
            else:
                eod_bar = window_bars[-1]
                exit_fills.append({
                    "t": ts(eod_bar), "price": eod_bar.close, "qty": 1, "reason": "EOD"
                })
        elif stop_bar:
            exit_fills.append({
                "t": ts(stop_bar), "price": stop_initial, "qty": 2, "reason": "STOP"
            })
        else:
            eod_bar = window_bars[-1]
            exit_fills.append({
                "t": ts(eod_bar), "price": eod_bar.close, "qty": 2, "reason": "EOD"
            })

    # ── PnL 計算 ─────────────────────────────────────────────
    total_pnl_pts = 0.0
    for fill in exit_fills:
        if direction == "BULL":
            total_pnl_pts += (fill["price"] - entry_price) * fill["qty"]
        else:
            total_pnl_pts += (entry_price - fill["price"]) * fill["qty"]

    total_pnl_usd = total_pnl_pts * POINT_VALUE
    r_multiple = total_pnl_pts / stop_dist if stop_dist else 0.0

    trade = {
        "id": f"T{day_idx+1}_1",
        "side": "BUY" if direction == "BULL" else "SELL",
        "entry_t": ts(entry_bar),
        "entry_price": entry_price,
        "qty": qty_total,
        "stop_initial": stop_initial,
        "stop_timeline": stop_timeline,
        "targets": [
            {"price": target1, "qty": 1},
            {"price": target2, "qty": 1},
        ],
        "exit_fills": exit_fills,
        "pnl_pts": round(total_pnl_pts, 2),
        "pnl_usd": round(total_pnl_usd, 2),
        "r_multiple": round(r_multiple, 2),
        "ambiguous": False,
    }

    # ── 進場訂單 ──────────────────────────────────────────────
    orders = [{
        "id": f"O{day_idx+1}_1",
        "t_submit": ts(entry_bar),
        "type": "LIMIT",
        "side": "BUY" if direction == "BULL" else "SELL",
        "price": entry_price,
        "qty": qty_total,
        "status": "FILLED",
        "t_fill": ts(entry_bar),
        "fill_price": entry_price,
    }]

    # ── 狀態機時間線 ──────────────────────────────────────────
    state_timeline = _build_state_timeline(
        window_bars, entry_bar, entry_bar_offset,
        trigger_event, trigger_kind, direction,
        fvg_events, exit_fills, entry_price, stop_initial,
    )

    # ── 權益時間線 ─────────────────────────────────────────────
    equity = _build_equity(window_bars, entry_bar, direction, entry_price, exit_fills)

    return [trade], orders, state_timeline, equity


def _build_state_timeline(
    window_bars, entry_bar, entry_bar_offset,
    trigger_event, trigger_kind, direction,
    fvg_events, exit_fills, entry_price, stop_initial,
) -> list:
    tl = []

    if not window_bars:
        return tl

    first_bar = window_bars[0]
    tl.append({
        "t": ts(first_bar),
        "state": "IDLE",
        "waiting_for": "初始化，等待市場開盤",
        "detail": {},
    })

    # WAIT_SWEEP — 在 09:30 或第 1/4 位置發出
    rth_bars = [b for b in window_bars if et_time_of(b) >= time(9, 30)]
    sweep_bar = rth_bars[0] if rth_bars else window_bars[len(window_bars)//4]

    level_hint = ""
    if trigger_event:
        if trigger_kind == "MSS":
            level_hint = f"{trigger_event.broken_swing_level:.2f}"
        else:
            level_hint = f"{trigger_event.level:.2f}"
    sweep_label = f"ONH/PDH {level_hint}" if level_hint else "ONH/PDH 水位"

    tl.append({
        "t": ts(sweep_bar),
        "state": "WAIT_SWEEP",
        "waiting_for": f"等待掃蕩 {sweep_label}",
        "detail": {"direction": direction},
    })

    # WAIT_MSS — 觸發事件後
    if trigger_event:
        tl.append({
            "t": int(trigger_event.confirmed_at.timestamp()),
            "state": "WAIT_MSS",
            "waiting_for": "等待 MSS 確認" if trigger_kind == "MSS" else "等待奇襲後 MSS",
            "detail": {"trigger": trigger_kind},
        })

    # WAIT_RETRACE — 找 FVG 回測區間
    retrace_bar_idx = max(0, entry_bar_offset - 3)
    retrace_bar = window_bars[retrace_bar_idx]
    fvg_hint = ""
    if fvg_events:
        fvg = fvg_events[0]
        fvg_hint = f"FVG {fvg.bottom:.2f}–{fvg.top:.2f}"
    tl.append({
        "t": ts(retrace_bar),
        "state": "WAIT_RETRACE",
        "waiting_for": f"等待回測 {fvg_hint}" if fvg_hint else "等待價格回測進場區",
        "detail": {},
    })

    # IN_POSITION — 進場
    tl.append({
        "t": ts(entry_bar),
        "state": "IN_POSITION",
        "waiting_for": f"已持倉 {entry_price:.2f}，停損 {stop_initial:.2f}",
        "detail": {
            "entry_price": entry_price,
            "stop": stop_initial,
            "direction": direction,
        },
    })

    # DONE — 最後一筆出場後
    if exit_fills:
        last_exit = max(exit_fills, key=lambda x: x["t"])
        tl.append({
            "t": last_exit["t"],
            "state": "DONE",
            "waiting_for": "交易完成",
            "detail": {"reason": last_exit["reason"]},
        })

    return tl


def _build_equity(window_bars, entry_bar, direction, entry_price, exit_fills) -> list:
    """每根 bar 收盤後的 realized + unrealized 權益（點數）。"""
    equity = []
    realized = 0.0
    remaining_qty = sum(f["qty"] for f in exit_fills)  # 總數量
    fills_sorted = sorted(exit_fills, key=lambda x: x["t"])
    fill_ptr = 0
    in_position_qty = 0
    entry_t = ts(entry_bar)

    # 重建倉位：初始 qty = total
    total_qty = sum(f["qty"] for f in exit_fills)
    open_qty = 0

    for bar in window_bars:
        bar_t = ts(bar)

        # 進場
        if bar_t >= entry_t and open_qty == 0 and bar_t == entry_t:
            open_qty = total_qty

        # 出場（逐一處理）
        while fill_ptr < len(fills_sorted) and fills_sorted[fill_ptr]["t"] <= bar_t:
            fill = fills_sorted[fill_ptr]
            if direction == "BULL":
                pnl = (fill["price"] - entry_price) * fill["qty"]
            else:
                pnl = (entry_price - fill["price"]) * fill["qty"]
            realized += pnl
            open_qty = max(0, open_qty - fill["qty"])
            fill_ptr += 1

        # Unrealized
        if open_qty > 0:
            if direction == "BULL":
                unrealized = (bar.close - entry_price) * open_qty
            else:
                unrealized = (entry_price - bar.close) * open_qty
        else:
            unrealized = 0.0

        equity.append({
            "t": bar_t,
            "realized": round(realized * POINT_VALUE, 2),
            "total": round((realized + unrealized) * POINT_VALUE, 2),
        })

    return equity


# ── stats 計算 ────────────────────────────────────────────────────────────────

def compute_stats(trades: list) -> dict:
    wins = [t for t in trades if t["pnl_pts"] > 0]
    losses = [t for t in trades if t["pnl_pts"] <= 0]
    gross_profit = sum(t["pnl_pts"] for t in wins) * POINT_VALUE
    gross_loss = sum(t["pnl_pts"] for t in losses) * POINT_VALUE
    total_pnl = gross_profit + gross_loss
    profit_factor = (gross_profit / abs(gross_loss)) if gross_loss != 0 else 0.0
    total_r = sum(t["r_multiple"] for t in trades)

    # Max drawdown from equity
    peak = 0.0
    max_dd = 0.0
    for t in trades:
        val = t["pnl_usd"]
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_dd:
            max_dd = dd

    return {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades), 3) if trades else 0,
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "profit_factor": round(profit_factor, 3),
        "total_r": round(total_r, 2),
        "pnl_usd": round(total_pnl, 2),
        "max_drawdown_usd": round(max_dd, 2),
        "ambiguous_count": sum(1 for t in trades if t.get("ambiguous")),
    }


# ── 每日 JSON 建構 ────────────────────────────────────────────────────────────

def build_day_json(
    target_day: date,
    all_bars: list[Bar],
    day_idx: int,
) -> dict:
    """建構單日完整 JSON。"""
    print(f"  處理 {target_day} ...")

    (
        window_bars, all_events,
        mss_events, raid_events,
        fvg_events, pool_created_events, pool_swept_events,
    ) = collect_events_for_day(target_day, all_bars)

    if not window_bars:
        print(f"    警告：{target_day} 無 window bars，跳過。")
        return {}

    # session_start_t / session_end_t
    rth_bars = [b for b in window_bars if et_time_of(b) >= time(9, 30)]
    pre_rth_bars = [b for b in window_bars if et_time_of(b) < time(9, 30)]

    session_start_t = ts(rth_bars[0]) if rth_bars else ts(window_bars[0])
    session_end_t = ts(window_bars[-1])

    # annotations
    levels, zones, markers = build_annotations(all_events, window_bars, day_idx)

    # trades
    # Scenario: day_idx=0 → win, 1 → loss, 2 → win
    scenario = 1 if day_idx == 1 else 0
    trades, orders, state_timeline, equity = fabricate_trades(
        window_bars=window_bars,
        mss_events=mss_events,
        raid_events=raid_events,
        fvg_events=fvg_events,
        day_scenario=scenario,
        day_idx=day_idx,
    )

    # 在 markers 中加入進場/出場標記
    for trade in trades:
        side = trade["side"]
        arrow = "↑" if side == "BUY" else "↓"
        markers.append({
            "t": trade["entry_t"],
            "kind": "ENTRY",
            "side": "BULL" if side == "BUY" else "BEAR",
            "price": trade["entry_price"],
            "text": f"進場{arrow} {trade['entry_price']:.2f}",
        })
        for fill in trade["exit_fills"]:
            kind_map = {"TARGET": "EXIT_TARGET", "STOP": "EXIT_STOP", "EOD": "EXIT_EOD"}
            markers.append({
                "t": fill["t"],
                "kind": kind_map.get(fill["reason"], "EXIT_EOD"),
                "side": "BULL" if side == "BUY" else "BEAR",
                "price": fill["price"],
                "text": f"出場 {fill['price']:.2f} ({fill['reason']})",
            })

    stats = compute_stats(trades)

    day_json = {
        "meta": {
            "symbol": "NQ=F",
            "date": target_day.isoformat(),
            "window": "RTH_OPEN_3H",
            "tick": TICK,
            "point_value": POINT_VALUE,
            "config": {},
        },
        "bars": [bar_to_dict(b) for b in window_bars],
        "session_start_t": session_start_t,
        "session_end_t": session_end_t,
        "annotations": {
            "levels": levels,
            "zones": zones,
            "markers": sorted(markers, key=lambda m: m["t"]),
        },
        "state_timeline": state_timeline,
        "orders": orders,
        "trades": trades,
        "equity": equity,
        "stats": stats,
    }

    return day_json


# ── 主程式 ────────────────────────────────────────────────────────────────────

def main() -> None:
    print("載入 K 棒資料 ...")
    all_bars = load_bars()
    print(f"  共載入 {len(all_bars)} 根 bar。")

    print("尋找符合條件的交易日 ...")
    days = find_qualifying_days(all_bars, n=3)
    if not days:
        print("錯誤：找不到符合條件的交易日。")
        sys.exit(1)
    print(f"  找到 {len(days)} 個交易日：{[str(d) for d in days]}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    index_days = []

    for day_idx, day in enumerate(days):
        day_json = build_day_json(day, all_bars, day_idx)
        if not day_json:
            continue

        out_path = OUTPUT_DIR / f"{day.isoformat()}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(day_json, f, ensure_ascii=False, indent=2)
        print(f"  寫出 {out_path}")

        trades = day_json.get("trades", [])
        total_pnl = sum(t["pnl_usd"] for t in trades)
        total_r = sum(t["r_multiple"] for t in trades)
        index_days.append({
            "date": day.isoformat(),
            "trades": len(trades),
            "pnl_usd": round(total_pnl, 2),
            "total_r": round(total_r, 2),
        })

    # index.json
    index = {
        "days": index_days,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    index_path = OUTPUT_DIR / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"  寫出 {index_path}")
    print("完成。")


if __name__ == "__main__":
    main()
