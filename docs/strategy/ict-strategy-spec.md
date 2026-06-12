# ICT NQ 1分K 策略規格 — NY 開盤 3 小時統一日內模型

狀態：**v2 草稿待審**（綜合全部 34 部影片筆記，Model 1–13）

研究素材：`research/notes/model-01..13.md`（每條規則標注出處模型）。

v2 變更（Model 12/13 字幕到手後）：
- **Model 13（2022 Model，Index Futures 專用）證實了 §3 狀態機的鏈路**
  （Raid → MSS+位移 → FVG 限價回踩），並給出更精確的進出場定義，採納為預設
- 偏向改為 M13 盤中雙向模式（掃哪邊做反邊），解決 M1 日線程序過嚴導致
  全 NO_TRADE 的問題；M1 程序降為可選過濾器
- 進場窗對齊 M13 AM session：新倉 09:30–11:00 ET，11:00 後僅週四五（config）
- 停損改 M13 精確定義：FVG 形成三根 K 棒遠端那根的極值，**不加 buffer**
- 停利預設改 M13 流動性階梯（對側 PD array → 前時段極值 → 前日高低）
- 換算修正：M12 明示指數期貨「20 pips ≈ 20 ticks = 5 handles」（非 M8 的 1:1），
  固定點數模式僅作為備選

---

## 0. 一條主線：整個系列其實是同一個模板

Model 1–11 的 Trade Plan & Algorithmic Theory 影片用的是**同一份演算法模板**，
只是換時間框架與目標尺度：

1. 用 **20 日 Dealing Range** 確立大方向與流動性目標（全系列一致）
2. 在 **Killzone 時間窗**內等待（London open / NY open，全系列一致）
3. 等**流動性掃蕩**（Judas swing / raid 舊高舊低）（M1 深化版、M5、M7、M10）
4. 等**位移 + 結構轉換（MSS）**確認反轉（M1 深化版、M6、M7）
5. 回踩 **FVG / PD Array** 用**限價單**進場，「PD array ± 5 pips」（M5/6/7/8/10 原文同句）
6. 停損放**操縱極值外側 + 緩衝**（M1：session 極值 ±5 pips；M5：高點 +15；M7：+20）
7. **分批停利 20/40/60**，到 60 平 80% 留尾單（M6/M7 原文同句；M8 明示 NQ 用 handles 1:1）
8. **浮盈 25%/50%/75% 階梯收停損**，75% 必須移 BE（M1/5/6/7/8/10/11 全部同句）
9. **虧損後 R% 減半直到回補 50%；連勝 5 筆 R% 減半**（全系列同句）

NQ 換算依據：M8 原文「E-mini NASDAQ you could look for 25 handles」——
**pips → NQ points 按 1:1 對映**，這是系列內唯一明示的指數期貨換算。

1 分 K 的正當性：M6/M7/M10 的 Algorithmic Theory 都直接在 1-minute chart
示範（M10 用 1-min ES mini；M7 在 1-min 上預測誤差 1 pip）。模板降到 1 分 K
是系列內建的 fractal 用法，不是我們的發明。

---

## 1. 交易範圍

- 商品：NQ（CME，tick 0.25、每點 $20）
- 執行框架：1 分 K
- **新倉時間窗：09:30–11:00 ET**（M13 AM session 子窗 9:30 / 10:00 / 10:30；
  10:30 後不積極找新 setup，11:00–11:30 僅週四五開放，config
  `late_window_thu_fri`）。引擎記錄每筆落在哪個子窗供統計
- 部位管理至 **12:30 ET 強制平倉**（使用者的 3 小時窗；M5「不持倉跨時段」、
  M13 lunch 12:00–13:00 為死水時段不進新倉）
- 交易日過濾：預設全開（M13 為每日模型）；M1/M5/M8 的「週一–三優先、
  週五迴避」保留為 config `day_filter`，回測階段先全開蒐集樣本

## 2. 方向決定（Bias）—— 兩種模式

`bias_mode` config，預設 `m13_raid`：

**模式 A：`m13_raid`（預設，M13 盤中雙向）**
方向不在盤前鎖死，由「哪一側流動性先被掃」決定：
- 掃了上方流動性（REH/ONH/PDH/盤中高）→ 只找做空 setup
- 掃了下方流動性 → 只找做多 setup
- M13 原文：「if we're bearish we look for a buy side liquidity raid」——
  自動化版把因果反轉為觸發器（掃蕩本身就是 setup 的第一步），
  這是 2022 Model 社群實作的標準做法，於規格 §5 偏離清單揭示
- 同一時段兩個方向都可能各有一次機會（受 max_trades 限制）

**模式 B：`m1_program`（可選嚴格過濾）**
v1 的 M1 Buy/Sell Program 日線程序（已實作）。對短資料集過嚴
（21 個交易日全 NO_TRADE），保留供更長歷史時啟用。

**共用盤前計算**（兩模式都做）：
- 20 日 Dealing Range、equilibrium（M1，目標與 premium/discount 判定用）
- 標記水位：PDH/PDL、ONH/ONL、20 日內各日高低、等高等低（raid 觸發源 +
  停利階梯素材）
- M13 目標階梯素材：前一時段（隔夜）極值、前日極值

## 2.4 交易時段（session，v3 擴充）

`session` config，三個時段共用同一條狀態機鏈路（M13 fractal 用法）：

| session | context 起點 | 新倉窗（ET） | 強平 | Raid 觸發水位 | 出處 |
|---|---|---|---|---|---|
| `NY_AM`（預設） | 08:00 | 09:30–11:00 | 12:30 | ONH/ONL、PDH/PDL、盤中極值、等高低 | M13 AM |
| `NY_PM` | 08:00（需 AM 水位） | 13:30–15:00 | 15:55 | AM session 高低、午休高低（以盤中極值與 swing 涵蓋）、PDH/PDL | M13 PM（13:30 首窗、14:00 PM trends、掃 AM/lunch stops） |
| `LONDON` | 00:00 | 02:00–05:00 | 05:30 | 隔夜（亞洲段）極值、PDH/PDL、等高低 | M1/M11 London Open Killzone 02:00–05:00 |

v1 簡化（誠實偏離）：PM 的 m13_liquidity T2 仍用 ONH/ONL（M13 原文為
「同日 AM session 極值」）；London 的亞洲區間以隔夜極值近似。
評估方法：三時段各跑 5 年 baseline（不調參），分年 + IS/OOS 切分檢視。

## 2.5 Silver Bullet 模式（preset，使用者交易員朋友建議 + ICT Silver Bullet）

`StrategyConfig.silver_bullet()` preset，與預設並存、回測 A/B：

- 進場窗 **10:00–11:00 ET**（Silver Bullet 上午時段；9:30–10:00 只觀察、
  其高低點照常列入流動性水位）
- **每日只做 10:00 後第一個確認的 MSS**（`first_setup_only=True`：第一個
  MSS 鏈路無論成交、過濾被拒或掛單失效，當日即收工）
- **min_rr = 2.0**：T1 流動性目標距離不足 2R → 放棄 setup（每口都至少 1:2）
- **SMT 過濾（`smt_filter="require"`）**：掃蕩當下比對 ES——
  NQ 掃過水位但 ES「未同步創對應極值」（lookback 同水位形成期間）→
  背離成立才可進場；ES 同步創極值 → 真突破嫌疑，放棄。
  資料：data/cache/es_1m.csv（與 NQ 同步抓取，分鐘對齊，缺分鐘沿用前值）

## 3. 盤中狀態機（1 分 K）

```
IDLE ─(09:30)→ WAIT_SWEEP ─(掃蕩反向流動性)→ WAIT_MSS ─(位移+MSS)→
WAIT_RETRACE ─(限價單成交)→ IN_POSITION ─(出場)→ 視筆數→ WAIT_SWEEP / DONE
                                └─(超時/失效)→ WAIT_SWEEP
```

以 Sell Program 為例（Buy 完全對稱）：

**WAIT_SWEEP**：等任一根 K 棒 high 掃過「反向流動性水位」（ONH、PDH、
盤中 session high、等高，由近至遠）且**收盤回到水位下方**（Raid 判定，
偵測器 r=3 根內收回）。出處：M10「sell above a previous short-term high」、
M5 Judas swing、M7 buy stop raid。

**WAIT_MSS**：Raid 成立後 `mss_timeout`（預設 15 根）內，等位移 K 棒
**收盤跌破**掃蕩段起漲的最近 swing low（M7「最高 reaccumulation 的
swing low 被破才算 MSS」的 1 分 K 對應），且位移留下 bearish FVG
（M6/M7「pattern is fair value」）。超時 → 回 WAIT_SWEEP。

**WAIT_RETRACE**：在 MSS 位移段的 bearish FVG 掛 **Sell Limit**（M13 精確定義）：
- 進場價 = **FVG 近端 K 棒邊緣，不加 buffer**（M13：「sell limit at the high
  of the discount low of the fair value gap」「貼緊邊緣確保成交」）；
  config `entry_level` 可改 CE（50%）或 OTE 62%（M1/M11）
- FVG 位置過濾（M13）：bearish FVG 須位於**位移段 equilibrium 之上**
  （premium 區）；config `fvg_filter: leg_equilibrium | prev_day_half | none`，
  預設 leg_equilibrium（M13），prev_day_half 為 M5 變體
- 停損（M13 精確定義）：**FVG 形成三根 K 棒中遠端那根的極值**
  （空單 = 第一根的 high），**不加 1 tick**（M13 原文）；config
  `stop_mode: fvg_candle | sweep_extreme`，後者 = 掃蕩極值 + buffer（M1 結構式）
- 限價單壽命 `entry_timeout`（預設 20 根）或 FVG 被收盤穿越失效 → 撤單回 WAIT_SWEEP

**IN_POSITION**：
- 停利預設 `targets_mode: m13_liquidity`（M13 階梯，由近至遠）：
  T1 = 位移段對側最近的未回補 FVG / swing 水位（內部流動性）平 50%、
  T2 = 前一時段極值（AM 空單 → 隔夜低點）平 25%、
  T3 = 前日極值（PDL/PDH）平剩餘；每個目標前 `dol_early_exit`
  （預設 10 ticks）提前掛單（M11「不當 Mr. Wizard」）；
  缺某層目標時順延下一層，全缺時 fallback 到 r_multiple 模式；
  各層距離上限 `max_target_r`（預設 5R）——極端日（大跌隔天）的隔夜/前日
  極值可能在 10R 外，掛在那裡尾倉永不出場，超限改用 R 倍數 fallback
- 備選模式：`fixed_points`（M6/M7 模板 20/40/60 點；注意 M12 的指數換算為
  20 ticks = 5 handles，兩種尺度衝突，故僅作備選並於回測比較）、
  `r_multiple`（TP1=1R/TP2=2R/TP3=3R）
- 階梯收停損（全系列模板 + M12 量化）：浮盈達 T1 距離的 50% → 停損收一半
  （M12「+10 pips 收一半」的比例化）；達 75% → 移 BE（M12「+15 移 BE」）
- 12:30 收盤強平（EOD）

**筆數與再進場**：`max_trades_per_session` 預設 2（M5/M7 允許再進場；
M1 禁止——取中間值，config 可改 1 忠實 M1）。日虧 `daily_loss_limit_r`
預設 -2R 停手。

## 4. 風控（engine/sim/risk.py 已實作）

- 每筆風險 `risk_per_trade_pct` 預設 0.5%（系列示範 1–1.5%，NQ 槓桿大取保守）
- 口數 = 風險美元 ÷ (停損點數 × $20)，向下取整；0 口 → 放棄該筆
- 虧損後 R% 減半，回補虧損 50% 後恢復；再虧再減半（M1/M10）
- 連勝 5 筆 R% 減半，虧損歸零連勝後解除（M5/M7/M10）

## 5. 已知與原系列的偏離（誠實清單）

| 偏離 | 原因 |
|---|---|
| 主框架 1 分 K（系列主示範 5/15 分） | 使用者指定場景；M13 明示 5m→1m、M6/M7/M10 已示範 1 分可行 |
| m13_raid 把「偏向→等掃蕩」反轉為「掃蕩→定方向」 | M13 原文先有 bias 再等 raid；全自動需可計算的觸發器，掃蕩事件本身就是模型的第一步，反轉後鏈路相同 |
| 停損用結構式（掃蕩極值+緩衝）而非固定 pips | forex pip 值不可直接搬到 1 分 NQ；結構式忠實 M1 錨點邏輯 |
| Weekly bias 以 M1 日線程序替代人工判讀 | 全自動需要；M1 是系列唯一完整機械化的偏向規則 |
| 經濟日曆過濾未實作 | 回測階段無日曆資料源；列入未來工作 |
| SMT divergence（ES/NQ 背離）未實作 | 需第二商品資料流；列入未來工作 |
| SD（standard deviation projections，M5 核心）未實作 | M5 的 CBDR/Asian range 為 forex 時段概念，NQ 對應待 M12/13 確認後評估 |

## 6. Config 預設值總表

```python
StrategyConfig(
  bias_mode="m13_raid",            # m13_raid | m1_program
  entry_window=("09:30", "11:00"), # 新倉窗（ET）
  late_window_thu_fri=True,        # 週四五新倉延至 11:30
  flatten_time="12:30",            # 強平（ET）
  day_filter=None,                 # None=全開；可設 ("Mon","Tue","Wed")
  thursday_size_factor=1.0,
  raid_recover_bars=3,
  mss_timeout_bars=15,
  entry_timeout_bars=20,
  entry_level="proximal",          # proximal(M13) | ce | ote62
  fvg_filter="leg_equilibrium",    # leg_equilibrium(M13) | prev_day_half(M5) | none
  stop_mode="fvg_candle",          # fvg_candle(M13 無buffer) | sweep_extreme(+buffer)
  stop_buffer_ticks=8,             # 僅 sweep_extreme 模式用
  targets_mode="m13_liquidity",    # m13_liquidity | fixed_points | r_multiple
  tp_points=(20, 40, 60),          # 僅 fixed_points 模式用
  tp_fractions=(0.5, 0.25, 1.0),   # 各層平倉比例（最後一層=剩餘全部）
  dol_early_exit_ticks=10,
  trail_half_at=0.5,               # 浮盈達 T1 距離 50% → 停損收一半（M12）
  trail_be_at=0.75,                # 達 75% → BE（M12）
  max_trades_per_session=2,
  daily_loss_limit_r=-2.0,
  risk_per_trade_pct=0.5,
  min_stop_points=3.0,             # 停損距離下限（防 FVG 過窄滑價失真）
  max_stop_points=40.0,            # 上限（防異常 setup）
)
```

## 7. 驗收方式

1. 逐日決策日誌在回放介面人工檢視：每一步狀態轉換有據可查
2. 20 個交易日回測統計（勝率、PF、總 R、最大回撤、ambiguous 筆數）
3. 無前視：截斷重餵一致性測試擴展到完整策略引擎
