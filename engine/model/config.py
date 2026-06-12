"""StrategyConfig — ICT 策略全域參數（§6 預設值總表）。

每個欄位均標注規格出處（§ 節號或 Model 編號），方便審計與調參。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class StrategyConfig:
    """ICT 策略設定，預設值完全忠實規格 §6。

    參數說明：
    ----------
    window : str
        可進場時段名稱，對應 sessions.py 中的 key。§1 09:30–12:30 ET。

    day_filter : tuple[str, ...]
        允許進場的星期名稱（英文縮寫）。§1 週一–週三全倉、週四減半倉、週五不進場。
        預設包含 Thu（由 thursday_size_factor 控制減半）、排除 Fri。

    thursday_size_factor : float
        週四口數乘數。§1 「Thursday 減半倉」，預設 0.5。

    min_dol_points : float
        Draw on Liquidity 最小距離（點數）。§2 M11「距離不足不是高機率」，預設 30 點。

    raid_recover_bars : int
        Raid 判定：掃蕩後 r 根內收回水位即確認。§3 WAIT_SWEEP，對應 pools.py r=3。

    mss_timeout_bars : int
        Raid 成立後等 MSS 的最多 K 棒數。§3 「mss_timeout 預設 15 根」。

    entry_timeout_bars : int
        WAIT_RETRACE 掛限價單壽命（根數）。§3 「entry_timeout 預設 20 根」。

    entry_level : str
        進場價選擇："proximal"（FVG 近端）、"ce"（50% 中點）、"ote62"（OTE 62%）。
        §3 M5 IOFED 預設 proximal。

    fvg_half_filter : bool
        FVG 須位於前日 range 看空時下半 50%（看多時上半）。§3 M5 高機率過濾，預設開。

    stop_buffer_ticks : int
        停損緩衝（tick 數）。§3 M1「session 極值 ±5 pips」結構對應，預設 8 ticks = 2 點。

    targets_mode : str
        停利模式："fixed_points"（M6/M7 固定點數）或 "r_multiple"（R 倍數）。
        §3 預設 fixed_points。

    tp_points : tuple[float, float, float]
        固定點數模式下 TP1/TP2/TP3 距離（點數）。§3 M6/M7 20/40/60 點。

    tp_fractions : tuple[float, float, float]
        各 TP 平倉比例。§3 TP1=50%、TP2=25%、TP3=剩餘的 80%（約 20% 尾單全平）。

    dol_early_exit_ticks : int
        到達 DOL 前提前出場的 tick 數。§3 M11「不當 Mr. Wizard，提前 10-15 pips」，預設 10 ticks。

    objective_for_trailing : str
        階梯收停損的目標基準（"tp2" 表示以 TP2 距離為 100%）。§3 全系列模板。

    max_trades_per_session : int
        每節最多交易筆數。§3 預設 2（M5/M7 允許再進場；config 可改 1 忠實 M1）。

    daily_loss_limit_r : float
        單日最大虧損（R，負值）。§3 預設 -2R 停手。

    risk_per_trade_pct : float
        每筆風險佔帳戶淨值比例（%）。§4 預設 0.5%。

    account_equity : float
        初始帳戶淨值（美元）。§4 模擬用，預設 50,000 美元。

    slippage_ticks : int
        STOP/MARKET 滑價（tick 數）。BrokerConfig 預設值 1 tick。

    commission_per_side : float
        每口每邊手續費（美元）。BrokerConfig 預設 2.25 美元。

    swing_n : int
        SwingDetector n 值（fractal 確認延遲）。偵測器預設 n=1（3-bar fractal）。

    use_day_filter : bool
        是否啟用星期過濾。config 可關（設為 False 則 Mon–Fri 全開）。§1。
    """

    # ── 時間窗 ────────────────────────────────────────────────────────────────
    window: str = "RTH_OPEN_3H"
    day_filter: tuple[str, ...] = ("Mon", "Tue", "Wed", "Thu")
    thursday_size_factor: float = 0.5
    use_day_filter: bool = True

    # ── Bias ──────────────────────────────────────────────────────────────────
    min_dol_points: float = 30.0

    # ── 狀態機 ───────────────────────────────────────────────────────────────
    raid_recover_bars: int = 3
    mss_timeout_bars: int = 15
    entry_timeout_bars: int = 20
    entry_level: Literal["proximal", "ce", "ote62"] = "proximal"
    fvg_half_filter: bool = True
    stop_buffer_ticks: int = 8

    # ── 停利 / 停損 ──────────────────────────────────────────────────────────
    targets_mode: Literal["fixed_points", "r_multiple"] = "fixed_points"
    tp_points: tuple[float, float, float] = (20.0, 40.0, 60.0)
    tp_fractions: tuple[float, float, float] = (0.5, 0.25, 0.8)
    dol_early_exit_ticks: int = 10
    objective_for_trailing: str = "tp2"   # tp2 = TP2 距離作為 100%

    # ── 風控 ──────────────────────────────────────────────────────────────────
    max_trades_per_session: int = 2
    daily_loss_limit_r: float = -2.0
    risk_per_trade_pct: float = 0.5
    account_equity: float = 50_000.0

    # ── 撮合 ──────────────────────────────────────────────────────────────────
    slippage_ticks: int = 1
    commission_per_side: float = 2.25

    # ── 偵測器參數 ───────────────────────────────────────────────────────────
    swing_n: int = 1   # SwingDetector n=1 → 3-bar fractal

    def as_dict(self) -> dict:
        """序列化為 JSON-friendly dict（供 meta.config snapshot）。"""
        import dataclasses
        d = dataclasses.asdict(self)
        # tuple -> list for JSON
        d["day_filter"] = list(d["day_filter"])
        d["tp_points"] = list(d["tp_points"])
        d["tp_fractions"] = list(d["tp_fractions"])
        return d
