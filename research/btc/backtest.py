# -*- coding: utf-8 -*-
"""BTC 短期策略回測器（spec: docs/strategy/btc-short-research-spec.md）。

三個策略族，全部淨費後、無前視：
  C1 資金費率 carry（月調倉、50/50 delta 中性、1x）
  C2 一週動量 long-flat（日頻、lookback=7、只做多、1x）
  C3 美股開盤 ORB 移植（perp 5m、ET 時區、風險 1%/筆）

各函式回傳 pandas.Series：UTC 日期 → 當日策略報酬（小數），
供等權組合與統一指標計算。指標見 metrics()。
"""
from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/cache"
NY = ZoneInfo("America/New_York")

# 費用（spec §2；每邊，佔名目比例）
PERP_TAKER = 0.0005
SPOT_TAKER = 0.0010
SLIP = 0.0001

# C1
C1_FUNDING_GATE_ANN = 0.05   # 前 30 日均資金費率年化 > 5% 才部署
C1_NOTIONAL_FRAC = 0.5       # 永續空單名目 = 0.5×權益（50/50 delta 中性）
C1_DEPLOY_COST = 0.5 * (SPOT_TAKER + SLIP) + 0.5 * (PERP_TAKER + SLIP)  # 佔權益

# C2
C2_LOOKBACK = 7
C2_FLIP_COST = PERP_TAKER + SLIP  # 每次狀態切換一邊

# C3（沿用 NQ ORB；0.30% 最小停損為費用門檻）
C3_RISK_PCT = 0.01
C3_MIN_STOP_FRAC = 0.0030
C3_MAX_NOTIONAL_X = 2.0
C3_MIN_NOTIONAL = 100.0
C3_SIDE_COST = PERP_TAKER + SLIP


# ── 資料載入 ─────────────────────────────────────────────────────────────────

def load_csv(name: str) -> pd.DataFrame:
    df = pd.read_csv(CACHE / name, parse_dates=["ts"])
    return df.sort_values("ts").reset_index(drop=True)


def clip(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """[start, end] 含端點（UTC 日期字串）。"""
    m = (df.ts >= pd.Timestamp(start, tz="UTC")) & \
        (df.ts < pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1))
    return df[m].reset_index(drop=True)


# ── C1 資金費率 carry ────────────────────────────────────────────────────────

def run_c1(funding: pd.DataFrame, start: str, end: str,
           always_on: bool = False) -> pd.Series:
    """月調倉 carry。funding 需含 [start-30d, end] 供暖機；回傳日報酬。

    無前視：月初決策只用該時點之前的資金費率。
    delta 中性 → 價格損益 ≈ 0（基差漂移不建模，報告註記）。
    """
    f = funding.copy()
    win_start = pd.Timestamp(start, tz="UTC")
    win_end = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)

    months = pd.date_range(win_start, win_end, freq="MS", tz="UTC")
    if not len(months) or months[0] > win_start:
        months = months.insert(0, win_start)

    deployed_prev = False
    daily: dict[pd.Timestamp, float] = {}
    cost_events: list[tuple[pd.Timestamp, float]] = []
    for i, m0 in enumerate(months):
        m1 = months[i + 1] if i + 1 < len(months) else win_end
        if m1 > win_end:
            m1 = win_end
        hist = f[(f.ts < m0) & (f.ts >= m0 - pd.Timedelta(days=30))]
        ann = hist.rate.mean() * 3 * 365 if len(hist) else 0.0
        deployed = True if always_on else bool(ann > C1_FUNDING_GATE_ANN)
        if deployed != deployed_prev:
            cost_events.append((m0, C1_DEPLOY_COST))
            deployed_prev = deployed
        if deployed:
            seg = f[(f.ts >= m0) & (f.ts < m1)]
            for _, r in seg.iterrows():
                d = r.ts.normalize()
                daily[d] = daily.get(d, 0.0) + r.rate * C1_NOTIONAL_FRAC
    if deployed_prev:  # 期末平倉成本（誠實計入）
        cost_events.append((win_end - pd.Timedelta(days=1), C1_DEPLOY_COST))

    idx = pd.date_range(win_start, win_end - pd.Timedelta(days=1), freq="D", tz="UTC")
    ret = pd.Series(0.0, index=idx)
    for d, v in daily.items():
        if d in ret.index:
            ret[d] += v
    for d, c in cost_events:
        d = d.normalize()
        if d in ret.index:
            ret[d] -= c
    return ret


# ── C2 一週動量 long-flat ────────────────────────────────────────────────────

def run_c2(perp_1d: pd.DataFrame, start: str, end: str) -> pd.Series:
    """日 K ts=UTC 00:00 開盤時間。訊號用第 t 日收盤，部位持有第 t+1 日。"""
    df = perp_1d.copy()
    df["sig"] = (df.close > df.close.shift(C2_LOOKBACK)).astype(int)
    df["pos"] = df.sig.shift(1).fillna(0)          # 無前視：昨日訊號→今日部位
    df["mkt_ret"] = df.close.pct_change().fillna(0.0)
    df["flip"] = (df.pos != df.pos.shift(1).fillna(0)).astype(int)
    df["ret"] = df.pos * df.mkt_ret - df.flip * C2_FLIP_COST
    df = clip(df, start, end)
    s = pd.Series(df.ret.values, index=df.ts.dt.normalize())
    return s


# ── C3 美股開盤 ORB ──────────────────────────────────────────────────────────

def run_c3(perp_5m: pd.DataFrame, start: str, end: str,
           start_equity: float = 50_000.0):
    """回傳 (日報酬 Series, 交易明細 DataFrame)。

    OR=09:30–10:00 ET 6 根 5m；10:00 起首次收盤突破→次根開盤進場；
    停損=OR 對側（停損優先、含滑價）；15:55 bar 收盤強平；
    進場 bar 開盤時間 ≤ 11:30；週一~五。
    """
    df = clip(perp_5m, start, end).copy()
    et = df.ts.dt.tz_convert(NY)
    df["et_date"] = et.dt.date
    df["et_min"] = et.dt.hour * 60 + et.dt.minute
    df["dow"] = et.dt.dayofweek
    df = df[(df.dow < 5) & (df.et_min >= 570) & (df.et_min < 960)]  # 09:30–16:00 ET

    equity = start_equity
    trades = []
    for d, g in df.groupby("et_date", sort=True):
        g = g.sort_values("et_min")
        orb = g[(g.et_min >= 570) & (g.et_min < 600)]
        if len(orb) < 6:
            continue
        or_hi, or_lo = orb.high.max(), orb.low.min()
        sess = g[g.et_min >= 600].reset_index(drop=True)

        side, entry_i = 0, None
        for i, b in sess.iterrows():
            if b.et_min > 685:  # 訊號 bar 收盤 > 11:25 → 進場會晚於 11:30
                break
            if b.close > or_hi:
                side, entry_i = 1, i + 1
                break
            if b.close < or_lo:
                side, entry_i = -1, i + 1
                break
        if side == 0 or entry_i is None or entry_i >= len(sess):
            continue
        eb = sess.iloc[entry_i]
        if eb.et_min > 690:  # 進場 bar 開盤 > 11:30
            continue
        entry = eb.open * (1 + SLIP * side)
        stop = or_lo if side == 1 else or_hi
        stop_dist = abs(entry - stop)
        if stop_dist < C3_MIN_STOP_FRAC * entry:
            continue

        qty = (C3_RISK_PCT * equity) / stop_dist
        notional = qty * entry
        cap = C3_MAX_NOTIONAL_X * equity
        if notional > cap:
            qty *= cap / notional
            notional = cap
        if notional < C3_MIN_NOTIONAL:
            continue

        exit_px, exit_reason = None, "eod"
        for _, b in sess.iloc[entry_i:].iterrows():
            hit = (b.low <= stop) if side == 1 else (b.high >= stop)
            if hit:  # 停損優先（保守）
                exit_px = stop * (1 - SLIP * side)
                exit_reason = "stop"
                break
            last = b
        if exit_px is None:
            exit_px = last.close * (1 - SLIP * side)

        gross = side * (exit_px - entry) * qty
        fees = (entry + exit_px) * qty * PERP_TAKER
        pnl = gross - fees
        r = pnl / (C3_RISK_PCT * equity)
        equity += pnl
        trades.append(dict(date=str(d), side=side, entry=entry, stop=stop,
                           exit=exit_px, reason=exit_reason, qty=qty,
                           notional=notional, pnl=pnl, r=r, equity=equity))
        if equity <= 0:
            break

    tr = pd.DataFrame(trades)
    idx = pd.date_range(pd.Timestamp(start, tz="UTC"),
                        pd.Timestamp(end, tz="UTC"), freq="D", tz="UTC")
    ret = pd.Series(0.0, index=idx)
    if len(tr):
        eq = start_equity
        for _, t in tr.iterrows():
            d = pd.Timestamp(t.date, tz="UTC")
            if d in ret.index:
                ret[d] += t.pnl / eq
            eq = t.equity
    return ret, tr


# ── 指標與組合 ───────────────────────────────────────────────────────────────

def metrics(daily_ret: pd.Series, label: str = "") -> dict:
    eq = (1 + daily_ret).cumprod()
    days = (daily_ret.index[-1] - daily_ret.index[0]).days + 1
    cagr = eq.iloc[-1] ** (365.25 / days) - 1
    peak = eq.cummax()
    max_dd = ((peak - eq) / peak).max()
    yearly = daily_ret.groupby(daily_ret.index.year).apply(
        lambda s: (1 + s).prod() - 1)
    return dict(label=label, final=eq.iloc[-1], cagr=cagr, max_dd=max_dd,
                yearly={int(k): float(v) for k, v in yearly.items()})


def combine(series: list[pd.Series]) -> pd.Series:
    """日報酬等權平均（隱含每日再平衡，spec §4）。"""
    df = pd.concat(series, axis=1).fillna(0.0)
    return df.mean(axis=1)


def fmt(m: dict) -> str:
    ys = "  ".join(f"{y}:{v * 100:+.1f}%" for y, v in m["yearly"].items())
    return (f"{m['label']:22s} 年化 {m['cagr'] * 100:+7.2f}%  "
            f"MaxDD {m['max_dd'] * 100:5.2f}%  [{ys}]")
