"""每日偏向計算（§2 Buy/Sell Program）。

給定「截至昨日收盤的全部歷史 1 分 K bars」，輸出 DailyBias。

演算流程：
1. 從 1 分 K 聚合「RTH 日 K」（09:30–16:00 ET，用 open/close body，忽略週末）。
2. 取最近 20 個交易日的日 K。
3. 用 SwingDetector(n=1) 跑日 K，找出 swing high / swing low。
4. 判斷 Buy Program / Sell Program / NO_TRADE。
5. 計算 DOL（偏向方向上最近的未掃外部流動性水位）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from engine.core.types import Bar, SwingConfirmed
from engine.core.sessions import trading_date, is_in_window
from engine.detectors.swings import SwingDetector
from engine.detectors.ranges import DealingRange
from engine.model.config import StrategyConfig


Direction = Literal["LONG", "SHORT", "NO_TRADE"]


@dataclass
class DailyBias:
    """每日偏向結果。"""
    direction: Direction
    dealing_range: DealingRange | None      # 20 日 Dealing Range（可能無歷史）
    dol_level: float | None                 # Draw on Liquidity 水位（None = NO_TRADE）
    reason: str                             # 人話說明（顯示在前端）
    swing_highs: list[SwingConfirmed]       # 20 日內確認的 swing highs（輔助除錯）
    swing_lows: list[SwingConfirmed]        # 20 日內確認的 swing lows


def _aggregate_daily_bars(history_bars: list[Bar]) -> list[Bar]:
    """將 1 分 K 聚合為 RTH 日 K（09:30–16:00 ET）。

    每個交易日：
    - open = 第一根 RTH 的 open
    - close = 最後一根 RTH 的 close
    - high/low = 當日 RTH 最高 / 最低
    - ts_utc = 第一根 RTH 的 ts_utc（確認時點；無前視）
    - volume = 累計量
    """
    from collections import defaultdict

    day_bars: dict[date, list[Bar]] = defaultdict(list)
    for b in history_bars:
        if is_in_window(b.ts_utc, "RTH"):
            d = trading_date(b.ts_utc)
            day_bars[d].append(b)

    daily: list[Bar] = []
    for d in sorted(day_bars.keys()):
        bars = sorted(day_bars[d], key=lambda b: b.ts_utc)
        o = bars[0].open
        c = bars[-1].close
        h = max(b.high for b in bars)
        lo = min(b.low for b in bars)
        v = sum(b.volume for b in bars)
        daily.append(Bar(
            ts_utc=bars[0].ts_utc,
            open=o,
            high=h,
            low=lo,
            close=c,
            volume=v,
        ))
    return daily


def compute_bias(
    history_bars: list[Bar],
    config: StrategyConfig | None = None,
) -> DailyBias:
    """計算每日偏向。

    Parameters
    ----------
    history_bars:
        截至昨日收盤的全部 1 分 K（不含今日）。
    config:
        策略設定（取 min_dol_points 等參數）。

    Returns
    -------
    DailyBias — direction / dealing_range / dol_level / reason
    """
    cfg = config or StrategyConfig()

    # ── 0. 資料不足 ──────────────────────────────────────────────────────────
    if not history_bars:
        return DailyBias(
            direction="NO_TRADE",
            dealing_range=None,
            dol_level=None,
            reason="歷史 bars 為空，無法計算偏向",
            swing_highs=[],
            swing_lows=[],
        )

    # ── 1. 聚合日 K ──────────────────────────────────────────────────────────
    daily_bars = _aggregate_daily_bars(history_bars)

    if len(daily_bars) < 3:
        return DailyBias(
            direction="NO_TRADE",
            dealing_range=None,
            dol_level=None,
            reason=f"日 K 僅 {len(daily_bars)} 根，不足以計算 swing（需至少 3 根）",
            swing_highs=[],
            swing_lows=[],
        )

    # ── 2. 取最近 20 日 K ────────────────────────────────────────────────────
    lookback = 20
    recent_daily = daily_bars[-lookback:] if len(daily_bars) > lookback else daily_bars

    # ── 3. 計算 20 日 Dealing Range ─────────────────────────────────────────
    # 使用 bodies（open/close）以忠實 M1
    high_20 = max(max(b.open, b.close) for b in recent_daily)
    low_20 = min(min(b.open, b.close) for b in recent_daily)
    dr = DealingRange(high=high_20, low=low_20)

    # ── 4. SwingDetector(n=1) 掃描日 K ──────────────────────────────────────
    det = SwingDetector(n=cfg.swing_n)
    all_swing_highs: list[SwingConfirmed] = []
    all_swing_lows: list[SwingConfirmed] = []

    for b in recent_daily:
        evts = det.on_bar(b)
        for e in evts:
            if e.side == "HIGH":
                all_swing_highs.append(e)
            else:
                all_swing_lows.append(e)

    # 昨日收盤價 = 最後一根日 K 收盤
    last_close = recent_daily[-1].close

    # ── 5. Buy Program / Sell Program 判定 ──────────────────────────────────
    # Sell Program：日線收盤跌破 20 日內某 swing low，且現價不在 discount
    sell_program = False
    broken_sl_level: float | None = None
    for sl in all_swing_lows:
        if last_close < sl.level:
            sell_program = True
            broken_sl_level = sl.level
            break  # 最早的被破即觸發

    # Buy Program：日線收盤突破 20 日內某 swing high，且現價不在 premium
    buy_program = False
    broken_sh_level: float | None = None
    for sh in all_swing_highs:
        if last_close > sh.level:
            buy_program = True
            broken_sh_level = sh.level
            break

    # ── 6. 位置過濾 ──────────────────────────────────────────────────────────
    if sell_program:
        # 若現價在 discount（低於均衡點），取消（M1 規則）
        if dr.is_discount(last_close):
            sell_program = False
            broken_sl_level = None

    if buy_program:
        # 若現價在 premium（高於均衡點），取消
        if dr.is_premium(last_close):
            buy_program = False
            broken_sh_level = None

    # ── 7. NO_TRADE 判斷 ─────────────────────────────────────────────────────
    if not sell_program and not buy_program:
        reason_parts = []
        if not all_swing_lows and not all_swing_highs:
            reason_parts.append("20 日內無確認 swing，無法判斷程序")
        elif dr.is_discount(last_close) and any(last_close < sl.level for sl in all_swing_lows):
            reason_parts.append(f"Sell Program 候選但現價在 discount（均衡 {dr.equilibrium:.2f}），不符合條件")
        elif dr.is_premium(last_close) and any(last_close > sh.level for sh in all_swing_highs):
            reason_parts.append(f"Buy Program 候選但現價在 premium（均衡 {dr.equilibrium:.2f}），不符合條件")
        else:
            reason_parts.append(f"現價 {last_close:.2f} 未突破任何 swing（需 Buy 突破 swing high 或 Sell 跌破 swing low）")
        return DailyBias(
            direction="NO_TRADE",
            dealing_range=dr,
            dol_level=None,
            reason="；".join(reason_parts),
            swing_highs=all_swing_highs,
            swing_lows=all_swing_lows,
        )

    # ── 8. 確定方向 ───────────────────────────────────────────────────────────
    direction: Direction = "SHORT" if sell_program else "LONG"

    # ── 9. 計算 DOL ───────────────────────────────────────────────────────────
    # DOL = 偏向方向上，最近的未掃外部流動性（舊日高 or 舊日低）
    # 這裡用日 K 的 high（對應 PDH）和 low（對應 PDL）
    # SHORT → DOL 在下方（最近的日 K low，且低於現價）
    # LONG  → DOL 在上方（最近的日 K high，且高於現價）
    dol_level: float | None = None
    dol_reason = ""

    if direction == "SHORT":
        # 找日 K 中在現價下方、距離最近的 low（未掃過的外部流動性）
        candidates = [b.low for b in recent_daily if b.low < last_close]
        if candidates:
            dol_level = max(candidates)  # 最近（最高）的 low，在現價下方
            dist = last_close - dol_level
            if dist < cfg.min_dol_points:
                return DailyBias(
                    direction="NO_TRADE",
                    dealing_range=dr,
                    dol_level=None,
                    reason=(
                        f"Sell Program 成立（跌破 swing low {broken_sl_level:.2f}），"
                        f"但 DOL {dol_level:.2f} 距現價僅 {dist:.1f} 點 < min_dol_points({cfg.min_dol_points})"
                    ),
                    swing_highs=all_swing_highs,
                    swing_lows=all_swing_lows,
                )
            dol_reason = (
                f"Sell Program：跌破 swing low {broken_sl_level:.2f}，"
                f"DOL={dol_level:.2f}（距 {dist:.1f} 點），均衡 {dr.equilibrium:.2f}"
            )
        else:
            return DailyBias(
                direction="NO_TRADE",
                dealing_range=dr,
                dol_level=None,
                reason="Sell Program 成立但找不到下方 DOL（無低於現價的日 K low）",
                swing_highs=all_swing_highs,
                swing_lows=all_swing_lows,
            )

    else:  # LONG
        candidates = [b.high for b in recent_daily if b.high > last_close]
        if candidates:
            dol_level = min(candidates)  # 最近（最低）的 high，在現價上方
            dist = dol_level - last_close
            if dist < cfg.min_dol_points:
                return DailyBias(
                    direction="NO_TRADE",
                    dealing_range=dr,
                    dol_level=None,
                    reason=(
                        f"Buy Program 成立（突破 swing high {broken_sh_level:.2f}），"
                        f"但 DOL {dol_level:.2f} 距現價僅 {dist:.1f} 點 < min_dol_points({cfg.min_dol_points})"
                    ),
                    swing_highs=all_swing_highs,
                    swing_lows=all_swing_lows,
                )
            dol_reason = (
                f"Buy Program：突破 swing high {broken_sh_level:.2f}，"
                f"DOL={dol_level:.2f}（距 {dist:.1f} 點），均衡 {dr.equilibrium:.2f}"
            )
        else:
            return DailyBias(
                direction="NO_TRADE",
                dealing_range=dr,
                dol_level=None,
                reason="Buy Program 成立但找不到上方 DOL（無高於現價的日 K high）",
                swing_highs=all_swing_highs,
                swing_lows=all_swing_lows,
            )

    return DailyBias(
        direction=direction,
        dealing_range=dr,
        dol_level=dol_level,
        reason=dol_reason,
        swing_highs=all_swing_highs,
        swing_lows=all_swing_lows,
    )
