# ICT NQ 1分K 策略規格 — NY 開盤 3 小時統一日內模型

狀態：**草稿待審**（綜合 Model 1–11 共 31 部影片筆記；Model 12 Scalping 與
Model 13「2022 YouTube Model」字幕因 YouTube 限流尚未到手，到手後補充對照，
若有出入會明確標注差異）

研究素材：`research/notes/model-01..11.md`（每條規則標注出處模型）。

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
- 執行框架：1 分 K；偏向框架：日線（自動計算）
- 可進場窗：**09:30–12:30 ET**（= 台灣 21:30–00:30）。
  NY Open Killzone（07:00–10:00，M1）與其重疊段 09:30–10:00 是「A 級時段」，
  10:00–11:00 為 Silver Bullet 段；引擎記錄每筆交易落在哪個子時段供統計
- 強制平倉：12:30 ET（不留倉，M5「不持倉跨時段」）
- 交易日過濾：預設「週一–週三進場、週四減半倉、週五不進場」（M1/M5/M8/M10/M11）；config 可關

## 2. 每日偏向（Bias）—— 全自動

每個交易日 09:30 前計算：

1. **20 日 Dealing Range**（M1 IPDA data range；排除週末）：最高高點 / 最低低點 /
   equilibrium
2. **方向程序**（M1 Buy/Sell Program，唯一給出完整機械化偏向規則的模型）：
   - Sell Program：日線已收破 20 日內某 swing low，且現價**不在 discount**
     （在 equilibrium 或 premium）→ 今日只做空
   - Buy Program：日線已收破 20 日內某 swing high，且現價**不在 premium** → 今日只做多
   - 兩者皆不成立 → 今日 NO TRADE（規格忠實於 M1「price in premium, no trade」）
3. **Draw on Liquidity**（M5/M11）：偏向方向上最近的未掃外部流動性
   （舊日高/低），距離須 ≥ `min_dol_points`（預設 30 點，對應 M11
   「距離不足不是高機率」），不足 → NO TRADE
4. 標記水位：PDH/PDL、ONH/ONL、20 日內各日高低、等高等低

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

**WAIT_RETRACE**：在 MSS 位移段的 bearish FVG 掛 **Sell Limit**：
- 進場價 = FVG 近端（proximal edge）（M5 IOFED：「在 FVG 高端賣出，
  不等完全回補」）；config 可改 CE（50%）或 OTE 62%（M1/M11）
- 高機率過濾（M5）：FVG 須位於**前日 range 下半 50%**（看空時）——
  config `fvg_half_filter`，預設開
- 停損 = 掃蕩極值 + `stop_buffer`（預設 8 ticks = 2 點）（M1
  「session 極值 ±5 pips」的結構對應；不採 M7 的 +20 pips 字面值，
  因該值為 forex 15 分框架校準，1 分 K NQ 按結構放停損）
- 限價單壽命 `entry_timeout`（預設 20 根）或 FVG 被收盤穿越失效 → 撤單回 WAIT_SWEEP

**IN_POSITION**：
- 分批停利（M6/M7 模板，pips→points 1:1）：預設
  TP1 = +20 點平 50%、TP2 = +40 點平 25%、TP3 = +60 點平 80% 之剩餘，
  尾單目標 = Draw on Liquidity（對側外部流動性，M9/M11
  「internal range 進場、external range 出場」），到 DOL 前 `dol_early_exit`
  （預設 10 ticks）提前全平（M11「不當 Mr. Wizard，提前 10-15 pips 出場」）
- 若停損距離 × RR 規則使 TP1 不合理（停損 > 20 點），改用 R 模式：
  TP1=1R/TP2=2R/TP3=3R（config `targets_mode: fixed_points | r_multiple`，
  預設 fixed_points 忠實原文）
- 階梯收停損（全系列模板）：浮盈達「預期目標」（= TP2 距離）的
  25% → 停損收 25%；50% → 收 50%；75% → 移 BE
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
| 主框架 1 分 K（系列主示範 5/15 分） | 使用者指定場景；系列在 M6/M7/M10 已示範 1 分可行 |
| 停損用結構式（掃蕩極值+緩衝）而非固定 pips | forex pip 值不可直接搬到 1 分 NQ；結構式忠實 M1 錨點邏輯 |
| Weekly bias 以 M1 日線程序替代人工判讀 | 全自動需要；M1 是系列唯一完整機械化的偏向規則 |
| 經濟日曆過濾未實作 | 回測階段無日曆資料源；列入未來工作 |
| SMT divergence（ES/NQ 背離）未實作 | 需第二商品資料流；列入未來工作 |
| SD（standard deviation projections，M5 核心）未實作 | M5 的 CBDR/Asian range 為 forex 時段概念，NQ 對應待 M12/13 確認後評估 |

## 6. Config 預設值總表

```python
StrategyConfig(
  window="RTH_OPEN_3H",            # 09:30–12:30 ET
  day_filter=("Mon","Tue","Wed","Thu"),  # Thu 減半倉，Fri 排除
  thursday_size_factor=0.5,
  min_dol_points=30.0,
  raid_recover_bars=3,
  mss_timeout_bars=15,
  entry_timeout_bars=20,
  entry_level="proximal",          # proximal | ce | ote62
  fvg_half_filter=True,
  stop_buffer_ticks=8,
  targets_mode="fixed_points",     # fixed_points | r_multiple
  tp_points=(20, 40, 60),
  tp_fractions=(0.5, 0.25, 0.8),   # 0.8 = TP3 平剩餘的 80%
  dol_early_exit_ticks=10,
  objective_for_trailing="tp2",
  max_trades_per_session=2,
  daily_loss_limit_r=-2.0,
  risk_per_trade_pct=0.5,
)
```

## 7. 驗收方式

1. 逐日決策日誌在回放介面人工檢視：每一步狀態轉換有據可查
2. 20 個交易日回測統計（勝率、PF、總 R、最大回撤、ambiguous 筆數）
3. 無前視：截斷重餵一致性測試擴展到完整策略引擎
