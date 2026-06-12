"""每日偏向計算（§2 Buy/Sell Program）。

給定「截至昨日收盤的全部歷史 1 分 K bars」，輸出 DailyBias。

v2：新增 bias_mode 分派
- m13_raid：不做日線方向判定，回傳 direction="BOTH"（雙向等掃蕩）
            + 共用盤前計算（dealing range、水位清單、前時段/前日極值）
- m1_program：v1 原邏輯（Buy/Sell Program 日線程序）

共用盤前計算：
1. 聚合 RTH 日 K
2. 取最近 20 日
3. 計算 20 日 Dealing Range（equilibrium）
4. SwingDetector 確認的日 swing highs/lows
5. 前日極值（PDH/PDL）、隔夜極值（ONH/ONL 由 runner 餵入，bias 提供上一工作日資料）
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


Direction = Literal["LONG", "SHORT", "NO_TRADE", "BOTH"]


@dataclass
class DailyBias:
    """每日偏向結果。"""
    direction: Direction
    dealing_range: DealingRange | None      # 20 日 Dealing Range（可能無歷史）
    dol_level: float | None                 # Draw on Liquidity 水位（m1_program 模式；BOTH 模式為 None）
    reason: str                             # 人話說明（顯示在前端）
    swing_highs: list[SwingConfirmed]       # 20 日內確認的 swing highs（輔助除錯）
    swing_lows: list[SwingConfirmed]        # 20 日內確認的 swing lows
    # v2 新增：m13_raid 模式的水位階梯素材
    prev_day_high: float | None = None      # 前日 RTH high（PDH）
    prev_day_low: float | None = None       # 前日 RTH low（PDL）
    overnight_high: float | None = None     # 前日隔夜 high（ONH）
    overnight_low: float | None = None      # 前日隔夜 low（ONL）
    recent_daily_highs: list[float] = None  # 20 日各日 high（水位掃蕩素材）
    recent_daily_lows: list[float] = None   # 20 日各日 low

    def __post_init__(self):
        if self.recent_daily_highs is None:
            self.recent_daily_highs = []
        if self.recent_daily_lows is None:
            self.recent_daily_lows = []


def _aggregate_daily_bars(history_bars: list[Bar]) -> list[Bar]:
    """將 1 分 K 聚合為 RTH 日 K（09:30–16:00 ET）。"""
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


def _aggregate_overnight_bars(history_bars: list[Bar]) -> dict[date, tuple[float, float]]:
    """聚合隔夜 bars，回傳 {交易日: (ON_high, ON_low)}。

    隔夜定義：OVERNIGHT 時段（sessions.py 中定義的 17:00 前一日 – 09:30 當日）。
    """
    from collections import defaultdict

    day_bars: dict[date, list[Bar]] = defaultdict(list)
    for b in history_bars:
        if is_in_window(b.ts_utc, "OVERNIGHT"):
            d = trading_date(b.ts_utc)
            day_bars[d].append(b)

    result: dict[date, tuple[float, float]] = {}
    for d, bars in day_bars.items():
        h = max(b.high for b in bars)
        lo = min(b.low for b in bars)
        result[d] = (h, lo)
    return result


def _common_premarket(
    history_bars: list[Bar],
    cfg: StrategyConfig,
) -> tuple[DealingRange | None, list[SwingConfirmed], list[SwingConfirmed], list[Bar]]:
    """共用盤前計算：20 日 DR + swing highs/lows + recent_daily。

    Returns (dealing_range, swing_highs, swing_lows, recent_daily_bars)
    """
    if not history_bars:
        return None, [], [], []

    daily_bars = _aggregate_daily_bars(history_bars)
    if len(daily_bars) < 3:
        return None, [], [], []

    lookback = 20
    recent_daily = daily_bars[-lookback:] if len(daily_bars) > lookback else daily_bars

    # 20 日 Dealing Range（bodies）
    high_20 = max(max(b.open, b.close) for b in recent_daily)
    low_20 = min(min(b.open, b.close) for b in recent_daily)
    dr = DealingRange(high=high_20, low=low_20)

    # SwingDetector(n=1)
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

    return dr, all_swing_highs, all_swing_lows, recent_daily


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
        策略設定（取 bias_mode 等參數）。

    Returns
    -------
    DailyBias — direction / dealing_range / dol_level / reason
    """
    cfg = config or StrategyConfig()

    if cfg.bias_mode == "m13_raid":
        return _compute_m13_raid(history_bars, cfg)
    else:
        return _compute_m1_program(history_bars, cfg)


def _compute_m13_raid(
    history_bars: list[Bar],
    cfg: StrategyConfig,
) -> DailyBias:
    """m13_raid 模式：不做日線方向判定，雙向等掃蕩。

    回傳 direction="BOTH"，填入盤前素材（DR / 水位清單 / 前日/隔夜極值）。
    資料不足時回 NO_TRADE。
    """
    if not history_bars:
        return DailyBias(
            direction="NO_TRADE",
            dealing_range=None,
            dol_level=None,
            reason="歷史 bars 為空，無法計算偏向",
            swing_highs=[],
            swing_lows=[],
        )

    dr, swing_highs, swing_lows, recent_daily = _common_premarket(history_bars, cfg)

    if dr is None:
        return DailyBias(
            direction="NO_TRADE",
            dealing_range=None,
            dol_level=None,
            reason="日 K 不足 3 根，無法計算 Dealing Range",
            swing_highs=[],
            swing_lows=[],
        )

    # 前日極值
    prev_day_high = recent_daily[-1].high if recent_daily else None
    prev_day_low = recent_daily[-1].low if recent_daily else None

    # 隔夜極值（最後一個交易日的 ON 數據）
    on_map = _aggregate_overnight_bars(history_bars)
    overnight_high: float | None = None
    overnight_low: float | None = None
    if on_map:
        last_on_day = max(on_map.keys())
        overnight_high, overnight_low = on_map[last_on_day]

    # 波動率門檻（M11：可用範圍不足非高機率日）：
    # 今晨隔夜波幅 < 近 20 日隔夜波幅均值 × ratio → NO_TRADE
    if cfg.min_on_range_ratio > 0 and on_map and overnight_high is not None:
        ranges = [h - l for _d, (h, l) in sorted(on_map.items())]
        recent = ranges[-21:-1] if len(ranges) > 1 else []
        if recent:
            avg_range = sum(recent) / len(recent)
            today_range = overnight_high - overnight_low
            if today_range < avg_range * cfg.min_on_range_ratio:
                return DailyBias(
                    direction="NO_TRADE",
                    dealing_range=dr,
                    dol_level=None,
                    reason=(f"隔夜波幅 {today_range:.1f} 點 < 近20日均值 "
                            f"{avg_range:.1f} × {cfg.min_on_range_ratio}（低波動日不交易）"),
                    swing_highs=swing_highs,
                    swing_lows=swing_lows,
                )

    # 20 日各日高低列表（水位素材）
    daily_highs = [b.high for b in recent_daily]
    daily_lows = [b.low for b in recent_daily]

    reason = (
        f"m13_raid：雙向等掃蕩；DR={dr.low:.2f}–{dr.high:.2f} eq={dr.equilibrium:.2f}；"
        f"PDH={prev_day_high:.2f} PDL={prev_day_low:.2f}"
        if prev_day_high is not None else
        f"m13_raid：雙向等掃蕩；DR={dr.low:.2f}–{dr.high:.2f} eq={dr.equilibrium:.2f}"
    )

    return DailyBias(
        direction="BOTH",
        dealing_range=dr,
        dol_level=None,   # m13 模式無預設 DOL，由掃蕩後動態決定
        reason=reason,
        swing_highs=swing_highs,
        swing_lows=swing_lows,
        prev_day_high=prev_day_high,
        prev_day_low=prev_day_low,
        overnight_high=overnight_high,
        overnight_low=overnight_low,
        recent_daily_highs=daily_highs,
        recent_daily_lows=daily_lows,
    )


def _compute_m1_program(
    history_bars: list[Bar],
    cfg: StrategyConfig,
) -> DailyBias:
    """m1_program 模式：v1 的 M1 Buy/Sell Program 日線程序（原邏輯保留）。"""
    if not history_bars:
        return DailyBias(
            direction="NO_TRADE",
            dealing_range=None,
            dol_level=None,
            reason="歷史 bars 為空，無法計算偏向",
            swing_highs=[],
            swing_lows=[],
        )

    dr, all_swing_highs, all_swing_lows, recent_daily = _common_premarket(history_bars, cfg)

    if dr is None or not recent_daily:
        n = len(_aggregate_daily_bars(history_bars))
        return DailyBias(
            direction="NO_TRADE",
            dealing_range=None,
            dol_level=None,
            reason=f"日 K 僅 {n} 根，不足以計算 swing（需至少 3 根）",
            swing_highs=[],
            swing_lows=[],
        )

    last_close = recent_daily[-1].close

    # ── 前日極值 ─────────────────────────────────────────────────────────────
    prev_day_high = recent_daily[-1].high if recent_daily else None
    prev_day_low = recent_daily[-1].low if recent_daily else None
    on_map = _aggregate_overnight_bars(history_bars)
    overnight_high = overnight_low = None
    if on_map:
        last_on_day = max(on_map.keys())
        overnight_high, overnight_low = on_map[last_on_day]

    # ── Sell Program 判定 ─────────────────────────────────────────────────────
    sell_program = False
    broken_sl_level: float | None = None
    for sl in all_swing_lows:
        if last_close < sl.level:
            sell_program = True
            broken_sl_level = sl.level
            break

    # ── Buy Program 判定 ─────────────────────────────────────────────────────
    buy_program = False
    broken_sh_level: float | None = None
    for sh in all_swing_highs:
        if last_close > sh.level:
            buy_program = True
            broken_sh_level = sh.level
            break

    # ── 位置過濾 ─────────────────────────────────────────────────────────────
    if sell_program and dr.is_discount(last_close):
        sell_program = False
        broken_sl_level = None

    if buy_program and dr.is_premium(last_close):
        buy_program = False
        broken_sh_level = None

    # ── NO_TRADE ─────────────────────────────────────────────────────────────
    if not sell_program and not buy_program:
        reason_parts = []
        if not all_swing_lows and not all_swing_highs:
            reason_parts.append("20 日內無確認 swing，無法判斷程序")
        elif dr.is_discount(last_close) and any(last_close < sl.level for sl in all_swing_lows):
            reason_parts.append(
                f"Sell Program 候選但現價在 discount（均衡 {dr.equilibrium:.2f}），不符合條件"
            )
        elif dr.is_premium(last_close) and any(last_close > sh.level for sh in all_swing_highs):
            reason_parts.append(
                f"Buy Program 候選但現價在 premium（均衡 {dr.equilibrium:.2f}），不符合條件"
            )
        else:
            reason_parts.append(
                f"現價 {last_close:.2f} 未突破任何 swing（需 Buy 突破 swing high 或 Sell 跌破 swing low）"
            )
        return DailyBias(
            direction="NO_TRADE",
            dealing_range=dr,
            dol_level=None,
            reason="；".join(reason_parts),
            swing_highs=all_swing_highs,
            swing_lows=all_swing_lows,
            prev_day_high=prev_day_high,
            prev_day_low=prev_day_low,
            overnight_high=overnight_high,
            overnight_low=overnight_low,
        )

    direction: Direction = "SHORT" if sell_program else "LONG"

    # ── DOL ──────────────────────────────────────────────────────────────────
    dol_level: float | None = None
    dol_reason = ""

    if direction == "SHORT":
        candidates = [b.low for b in recent_daily if b.low < last_close]
        if candidates:
            dol_level = max(candidates)
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
            dol_level = min(candidates)
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
        prev_day_high=prev_day_high,
        prev_day_low=prev_day_low,
        overnight_high=overnight_high,
        overnight_low=overnight_low,
    )
