"""StrategyConfig — ICT 策略全域參數（§6 預設值總表 v2）。

v2 新增：bias_mode, entry_window, late_window_thu_fri, flatten_time,
         fvg_filter, stop_mode, targets_mode=m13_liquidity, trail_half_at,
         trail_be_at, min_stop_points, max_stop_points。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class StrategyConfig:
    """ICT 策略設定，預設值完全忠實規格 §6 v2。

    參數說明：
    ----------
    bias_mode : str
        偏向模式。"m13_raid"（預設，盤中雙向掃蕩觸發）或 "m1_program"（舊版日線程序）。§2

    entry_window : tuple[str, str]
        新倉時間窗（ET，HH:MM 格式）。§1 預設 09:30–11:00。

    late_window_thu_fri : bool
        週四五是否延長新倉窗至 11:30。§1。

    flatten_time : str
        強平時間（ET，HH:MM）。§1 預設 12:30。

    day_filter : tuple[str, ...] | None
        允許進場的星期名稱（英文縮寫）。None=全開（m13_raid 預設）。§1。

    thursday_size_factor : float
        週四口數乘數，預設 1.0（v2 不減倉）。§1。

    raid_recover_bars : int
        Raid 判定：掃蕩後 r 根內收回水位即確認。§3 r=3。

    mss_timeout_bars : int
        Raid 成立後等 MSS 的最多 K 棒數。§3 預設 15 根。

    entry_timeout_bars : int
        WAIT_RETRACE 掛限價單壽命（根數）。§3 預設 20 根。

    entry_level : str
        進場價選擇："proximal"（FVG 近端，M13 預設）、"ce"（50%）、"ote62"（OTE 62%）。§3。

    fvg_filter : str
        FVG 位置過濾模式：
        - "leg_equilibrium"（M13 預設）：FVG proximal 須在位移段 equilibrium 以上（空單）
        - "prev_day_half"（M5）：FVG 須在前日 range 的正確半段
        - "none"：不過濾。§3。

    stop_mode : str
        停損計算模式：
        - "fvg_candle"（M13 預設）：空單停損 = FVG 三根中第一根的 high，無 buffer
        - "sweep_extreme"：掃蕩極值 + stop_buffer_ticks（v1 行為）。§3。

    stop_buffer_ticks : int
        停損緩衝（tick 數）。僅 stop_mode="sweep_extreme" 使用。§3 預設 8 ticks。

    targets_mode : str
        停利模式：
        - "m13_liquidity"（預設）：M13 流動性階梯（內部流動性→前時段→前日極值）
        - "fixed_points"：M6/M7 固定點數 20/40/60
        - "r_multiple"：1R/2R/3R。§3。

    tp_points : tuple[float, float, float]
        固定點數模式下 TP1/TP2/TP3 距離（點數）。§3 M6/M7 20/40/60 點。

    tp_fractions : tuple[float, float, float]
        各 TP 平倉比例（最後一層=剩餘全部）。§3 預設 0.5/0.25/1.0。

    dol_early_exit_ticks : int
        到達目標水位前提前出場的 tick 數。§3 M11 預設 10 ticks。

    trail_half_at : float
        浮盈達 T1 距離的此比例時，停損收至初始距離一半處。§3 M12 預設 0.5（50%）。

    trail_be_at : float
        浮盈達 T1 距離的此比例時，移至 BE。§3 M12 預設 0.75（75%）。

    min_stop_points : float
        停損距離下限（點數）。低於此值放棄 setup。§3 預設 3.0 點。

    max_stop_points : float
        停損距離上限（點數）。高於此值放棄 setup。§3 預設 40.0 點。

    max_trades_per_session : int
        每節最多交易筆數。§3 預設 2。

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

    min_dol_points : float
        m1_program 模式下 DOL 最小距離（點數）。§2 M11 預設 30 點。

    use_day_filter : bool
        是否啟用星期過濾。§1 預設 False（m13_raid 全開）。
    """

    # ── 偏向模式 ──────────────────────────────────────────────────────────────
    bias_mode: Literal["m13_raid", "m1_program"] = "m13_raid"

    # ── 時間窗 ────────────────────────────────────────────────────────────────
    entry_window: tuple[str, str] = ("09:30", "11:00")   # 新倉窗（ET）§1
    late_window_thu_fri: bool = True                      # 週四五延至 11:30 §1
    flatten_time: str = "12:30"                           # 強平（ET）§1
    day_filter: tuple[str, ...] | None = None             # None=全開 §1
    thursday_size_factor: float = 1.0                     # v2 不減倉

    # ── Bias（m1_program 模式用） ─────────────────────────────────────────────
    min_dol_points: float = 30.0

    # ── 狀態機 ───────────────────────────────────────────────────────────────
    raid_recover_bars: int = 3
    mss_timeout_bars: int = 15
    entry_timeout_bars: int = 20
    # 位移判定（偵測器 §5）：實體 >= mult × 近 window 根平均實體
    displacement_window: int = 20
    displacement_mult: float = 2.0
    # MSS 確認方式：
    #   displacement  = 位移棒（實體 z-score 門檻）收破 swing（v2 預設）
    #   fvg_evidence  = 收破 swing 即可，但位移段必須留下 FVG（M13 原文的
    #                   「rapid MSS + displacement 形成 FVG」——FVG 本身就是
    #                   位移證據，不另設實體門檻）
    mss_confirm: Literal["displacement", "fvg_evidence"] = "displacement"
    entry_level: Literal["proximal", "ce", "ote62"] = "proximal"

    # ── FVG / 停損過濾 ────────────────────────────────────────────────────────
    fvg_filter: Literal["leg_equilibrium", "prev_day_half", "none"] = "leg_equilibrium"
    stop_mode: Literal["fvg_candle", "sweep_extreme"] = "fvg_candle"
    stop_buffer_ticks: int = 8   # 僅 sweep_extreme 用

    # ── 停利 / 停損 ──────────────────────────────────────────────────────────
    targets_mode: Literal["m13_liquidity", "fixed_points", "r_multiple"] = "m13_liquidity"
    # m13_liquidity 各層流動性目標的距離上限（R 倍數）。超過視為缺層、
    # 改用 R 倍數 fallback——防止極端日（大跌隔天）把尾倉掛在 10R 外的
    # 前日低點，浮盈全程不落袋最後被移動停損收走。
    max_target_r: float = 5.0
    tp_points: tuple[float, float, float] = (20.0, 40.0, 60.0)
    tp_fractions: tuple[float, float, float] = (0.5, 0.25, 1.0)
    dol_early_exit_ticks: int = 10
    trail_half_at: float = 0.5    # 浮盈達 T1 距離 50% → 停損收一半 §3 M12
    trail_be_at: float = 0.75     # 浮盈達 T1 距離 75% → BE §3 M12
    min_stop_points: float = 3.0  # 停損下限 §3
    max_stop_points: float = 40.0 # 停損上限 §3

    # ── Silver Bullet 新增 ────────────────────────────────────────────────────
    min_rr: float = 0.0          # 0=off; T1 dist < min_rr×stop_dist → abandon setup
    first_setup_only: bool = False  # True: after first MSS chain ends (any way), → DONE
    smt_filter: Literal["off", "require"] = "off"
    smt_lookback_bars: int = 30   # SMT reference window when pool_created_t unavailable

    # ── 風控 ──────────────────────────────────────────────────────────────────
    max_trades_per_session: int = 2
    daily_loss_limit_r: float = -2.0
    risk_per_trade_pct: float = 0.5
    account_equity: float = 50_000.0

    # ── 商品與撮合 ────────────────────────────────────────────────────────────
    # MNQ = 微型那斯達克期貨（同 NQ100 指數，1/10 合約，每點 $2）。
    # $50k 帳戶以 0.5% 風險做 1 分 K ICT，大 NQ（每點 $20）只付得起 12.5 點
    # 停損，幾乎所有 setup 都開不出 1 口；MNQ 才是此資金規模的合理工具。
    instrument: Literal["MNQ", "NQ"] = "MNQ"
    slippage_ticks: int = 1

    @property
    def point_value(self) -> float:
        return 2.0 if self.instrument == "MNQ" else 20.0

    @property
    def commission_per_side(self) -> float:
        return 0.74 if self.instrument == "MNQ" else 2.25

    # ── 偵測器參數 ───────────────────────────────────────────────────────────
    swing_n: int = 1   # SwingDetector n=1 → 3-bar fractal

    # ── 相容性（v1 欄位，保留供舊測試不改） ──────────────────────────────────
    use_day_filter: bool = False   # v2 預設 False；True 時用 day_filter
    # fvg_half_filter 已被 fvg_filter 取代，保留為 alias（v1 測試用）
    fvg_half_filter: bool = False  # deprecated, 由 fvg_filter 控制
    # window 舊欄位（runner.py EOD 邏輯仍引用）
    window: str = "RTH_OPEN_3H"

    @classmethod
    def silver_bullet(cls) -> "StrategyConfig":
        """Silver Bullet preset (§2.5)."""
        return cls(
            entry_window=("10:00", "11:00"),
            late_window_thu_fri=False,
            max_trades_per_session=1,
            first_setup_only=True,
            min_rr=2.0,
            smt_filter="require",
        )

    def as_dict(self) -> dict:
        """序列化為 JSON-friendly dict（供 meta.config snapshot）。"""
        import dataclasses
        d = dataclasses.asdict(self)
        # tuple -> list for JSON
        if d.get("day_filter") is not None:
            d["day_filter"] = list(d["day_filter"])
        d["tp_points"] = list(d["tp_points"])
        d["tp_fractions"] = list(d["tp_fractions"])
        d["entry_window"] = list(d["entry_window"])
        return d
