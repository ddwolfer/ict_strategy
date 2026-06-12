# Model 1 — Intraday Scalping：Previous Day High & Low

## 影片清單

| ID | 標題 |
|----|------|
| vCvRrINpknI | ICT Charter Price Action Model 1（基礎講義） |
| rNn0JkItAGo | ICT Charter Price Action Model 1 — Amplified Lecture（2019年深化版） |
| 4f1vjQMlV50 | ICT Charter Price Action Model 1 — Trade Plan & Algorithmic Theory（交易計畫與演算法理論） |

---

## 模型定位

- **交易風格**：Intraday scalping（日內剝頭皮）
- **時間框架執行層**：5分鐘K棒（偶爾用15分鐘輔助）
- **偏向分析層**：Daily chart → 4H → 1H（由高往低確認）
- **適用市場**：外匯（Forex）為主，亦適用 Futures、Bonds、Metals、Crypto（演算法理論中提及）
- **交易頻率**：一週一次核心設置（求穩不求多）
- **目標**：每筆交易捕捉 **15~20 pips**；目標月報酬 **6%**（週 1.5% 複利）
- **年化目標**：若每週做到 2% 複利，理論上超過 100%/年
- **交易日**：Monday–Wednesday 為理想；Thursday 有條件可入場；**Friday 不交易**
- **持倉方式**：純 Scalp（不隔夜），必要時可留一小部分 leader 部位捕捉額外延伸

---

## 核心概念定義

### IPTA Data Range（IPA/IFTO Data Range）
逐字稿中反覆出現「ipto/ifto/ipa data range」，根據上下文推斷為「Interbank Price Delivery Algorithm（IPDA）Data Range」。定義為：向前回溯 **20個交易日**（不計算 Sunday），形成當前的 dealing range。可延伸至 40日或 60日 look-back。

### Dealing Range（Premium / Discount / Equilibrium）
- 20日最高收盤高點 = **Premium**（溢價區）
- 20日最低收盤低點 = **Discount**（折價區）
- 兩者中點 = **Equilibrium**（50%均衡）
- 計算 Optimal Trade Entry 時，Fibonacci 以**K棒實體**（body）的高低計算，**不用影線**

### Previous Day High / Low（PDH / PDL）
- 定義：20日 IPTA data range 內任一交易日的最高/最低點，**不限定為前一日**
- 用途：作為 bullish 目標（PDH）或 bearish 目標（PDL），亦為 liquidity pool 所在
- 延伸目標：突破 PDH/PDL 後再延伸 **10、20 或 30 pips**

### Buy Program（多方程序）
條件：
1. Daily 已向上突破 20日 IPTA range 內的某一 Swing High
2. 價格**不在 Premium** 區域（在 Discount 或 Equilibrium 才買）
3. 目標為向上掃過 PDH 及其上方的 liquidity pool
4. Parabolic expansion run 出現在 Equilibrium 以上，奔向 PDH

### Sell Program（空方程序）
條件：
1. Daily 已向下突破 20日 IPTA range 內的某一 Swing Low
2. 價格**不在 Discount** 區域（在 Premium 或 Equilibrium 才賣）
3. 目標為向下掃過 PDL 及其下方的 liquidity pool
4. Parabolic expansion run 出現在 Equilibrium 以下，奔向 PDL

### Optimal Trade Entry（OTE）
使用 Fibonacci 工具，以**K棒實體**（非影線）定義波動範圍：
- **核心 entry level：62% retracement**
- 做多：62% level + 5 pips（補償 spread）
- 做空：62% level − 5 pips（補償 spread）
- 不使用 70.5% 或 79%（此模型精確鎖定 62%）

### Symmetrical Price Swing（對稱價格擺動）
以 OTE 的量程（swing low 到 swing high 之距離）向交易方向延伸等距，形成 measured move / 第一出場目標上限。

### Bullish / Bearish Breaker
市場結構破壞後回測的區域：
- 多方：下跌低點被突破後反彈，突破某一 swing high，回測至該 swing high 區域 = bullish breaker（買點）
- 空方：上漲高點被突破後反彈，跌破某一 swing low，回測至該 swing low 區域 = bearish breaker（賣點）

### Market Structure Shift（MSS）
市場結構轉換：關鍵 swing high/low 被突破，代表 institutional order flow 改變方向。

### Accumulation / Manipulation / Distribution（AMD）
逐字稿中明確描述：
- Accumulation：低能量積累
- Manipulation：突破假突破（Judas Swing），吸引散戶追高/追低
- Distribution：真實方向大幅運動

---

## 進場模型完整流程

### 前置條件（Preparation — 每週開市前）

1. 查閱 Forex Factory 或等效經濟日曆，標記當週所有 medium/high impact 事件（時間、市場）
2. 在 Daily chart 定義 20日 IPTA dealing range（最高高點 / 最低低點，不計 Sunday）
3. 判斷當前價格在 dealing range 的位置：Premium / Discount / Equilibrium
4. 標記 20日內所有 PDH（多方目標） 或 PDL（空方目標）
5. 確認 institutional order flow 方向（daily swing point 是否已突破）
6. 決定本週方向偏向：Buy Program 還是 Sell Program

### Setup 形成條件

**Buy Program（多方）：**
- Daily 已向上 break 20日內某一 swing high ✓
- 當前價格不在 Premium（在 Discount 或 Equilibrium）✓
- 識別 discount PD array（bullish order block、bullish breaker、fair value gap）✓
- 有至少一個 PDH 在上方作為目標，距離能提供 ≥15–20 pips ✓

**Sell Program（空方）：**
- Daily 已向下 break 20日內某一 swing low ✓
- 當前價格不在 Discount（在 Premium 或 Equilibrium）✓
- 識別 premium PD array（bearish order block、bearish breaker、fair value gap）✓
- 有至少一個 PDL 在下方作為目標，距離能提供 ≥15–20 pips ✓

**深化版（rNn0JkItAGo）補充的更高層次 pattern：**
- 價格進入 premium/discount PD array 後，出現 Judas swing（假突破相反方向）
- 隨後 displacement 突破 swing point（MSS 確認）
- 回測至 breaker 區域 = 最佳進場窗口
- 進階：不需等待 swing point 完整形成（第三根K棒確認），看到 fair value gap 填補即可視為確認

### 觸發條件

- New York Kill Zone 開啟：**07:00 AM New York time**
- 5分鐘 K棒 形成 OTE retracement pattern（London session 趨勢方向的回測）
- **做多**：5分鐘回測低點後反彈，在 62% retracement level + 5 pips 掛 buy limit
- **做空**：5分鐘回測高點後下跌，在 62% retracement level − 5 pips 掛 sell limit

### 進場

- 使用**limit order**（非 market order）
- 多單：buy limit @ 5分鐘 swing 的 62% retracement level + 5 pips
- 空單：sell limit @ 5分鐘 swing 的 62% retracement level − 5 pips
- 多個 orders 可用同一進場價格分批佈局（見風控規定中的倉位分配）

### 停損位置

**多單：**
- Stop loss = 07:00–10:00 AM New York session 區間最低點（FIB anchor low）**− 5 pips**

**空單：**
- Stop loss = 07:00–10:00 AM New York session 區間最高點（FIB anchor high）**+ 5 pips**

- **重要：停損不移動，直到完成第一次部分出場（first partial）**

### 停利 / 出場管理

分三步驟出場（多單為例，空單完全對稱）：

| 步驟 | 出場位置 | 動作 |
|------|----------|------|
| First partial | OTE anchor high（FIB 錨定的 swing high） | 出場部分倉位，同時將停損上移鎖定 5–10 pips 利潤 |
| Second partial | Target 1 on FIB tool（FIB 延伸第一目標） 或 前一個 PDH/PDL | 出場第二批 |
| Third partial / Close all | Target 2 on FIB tool 或 Symmetrical price swing | 全部出場；若有 leader 部位留至對稱擺動則完全平倉 |

補充規則：
- 達到 symmetrical price swing → **全部出場，無論後續**
- 若 News 將在正午後發布，可留小部分 leader 看是否達到 symmetrical swing
- **被止損出場後：當日不再重新入場（no re-entry）**

### 停損漸進管理（4f1vjQMlV50 — Stop Loss Management）

| 獲利進度 | 停損調整 |
|----------|----------|
| 獲利達目標的 25% | 停損縮減 25% |
| 獲利達目標的 50% | 停損縮減 50% |
| 獲利達目標的 75% | 停損移至 break even（含交易成本） |

---

## 具體參數

| 參數 | 數值 |
|------|------|
| 進場 Fibonacci level | **62% retracement**（精確，非 70.5% 或 79%） |
| 多單 entry 調整 | +5 pips（補 spread） |
| 空單 entry 調整 | −5 pips（補 spread） |
| 多單停損 | session 低點 −5 pips |
| 空單停損 | session 高點 +5 pips |
| 目標延伸（PDH/PDL 之外） | 10 / 20 / 30 pips beyond |
| 每筆交易目標 | **15–20 pips**（primary）；symmetrical swing 為上限 |
| 月度目標 | **6%** |
| 週複利目標 | **1.5%/週** |
| 年化理論值（週 2% 複利） | >100% |
| 20日 IPTA look-back | 20 個交易日（不計 Sunday） |
| 延伸 look-back | 40日 / 60日（當 20日 range 過窄時） |
| Thursday leverage | 正常的 25%–40%（late-week discount） |
| 首次部分出場後停損移動 | 鎖定 5–10 pips 利潤 |
| 最大單筆風險（示例帳戶） | Equity × R%（推薦 1–1.5%） |
| 連贏 5 筆後 | 下一筆風險降至 50% |
| 虧損後 | 下一筆風險降至 50%，直到虧損回補 50% |

**倉位分配公式：**
```
Position Size = Account Equity × R% ÷ Stop Loss in Pips
```
多筆訂單時：每筆訂單的風險 = 總風險 ÷ 訂單數量

---

## 時段規定（Killzone）

| 時段 | New York 時間 | 說明 |
|------|--------------|------|
| **New York Kill Zone（核心）** | **07:00 – 10:00 AM** | 主要進場窗口；5分鐘 OTE 必須在此形成 |
| New York Kill Zone（延伸） | 07:00 – 11:00 AM | 當 10:30 有 Crude Oil Inventory 或其他新聞時延伸 |
| **入場截止** | **10:00 AM**（一般）/ 11:00 AM（新聞日） | 超過此時間「No Trade」 |
| London session | 供判斷當日動能方向 | OTE 是「對 London 動能的回測」 |
| Afternoon（12:00 PM + | Bond 收市（約 14:00–15:00 NY）、London close | Symmetrical swing 出場時機參考 |

**星期規定：**
- Monday–Wednesday：**最佳進場日**
- Thursday：有條件可入（liquidity pool 尚未被掃）
- Friday：**不交易**
- Sunday：**計算 IPTA Data Range 時不計入**

---

## 風控規定

1. **No re-entry**：被止損出場當日不再進場，等下一個 NY session
2. **No Friday trading**：週五不交易
3. **Thursday leverage reduction**：若週四才進場，倉位縮至正常的 25%–40%
4. **連贏 5 筆 → 下一筆 R 降 50%**：防止過度自信累積大虧損
5. **虧損後 R 降 50%**，直到虧損金額回補 50% 才可恢復原始 R
6. **連續兩筆虧損 → R 再次降 50%**，持續此機制直到回補
7. **停損不提前移動**：必須先完成第一次 partial exit 後才可移動停損
8. **不強迫交易**：若被止損，代表動能減弱，應等待下一日 NY session
9. **倉位上限**：總風險 = 帳戶淨值 × R%，多訂單時風險均分不可疊加
10. **不使用 Sundays**：20日回溯計算排除週日數據

---

## 對「NQ 1分K、NY 開盤後3小時自動交易」的適用性

### 可機械化（演算法可完整執行）的規則

| 規則 | 機械化難度 | 說明 |
|------|------------|------|
| 交易日篩選（Mon–Wed，Thu 有條件，Fri 禁止） | 極低 | 純日期判斷 |
| Kill Zone 時間窗（07:00–10:00 AM NY） | 極低 | 時間條件 |
| 20日 IPTA range 計算（排除 Sunday） | 低 | 取最近20個非Sunday交易日的 high/low |
| PDH / PDL 標記（20日內各交易日的日高/日低） | 低 | 歷史K棒資料 |
| Premium / Discount 位置判斷（現價 vs 20日 range 中點） | 低 | 價格比較 |
| 62% Fibonacci entry level 計算 | 低 | 以5分鐘實體K棒計算 |
| Entry ±5 pips 調整 | 極低 | 固定偏移 |
| 停損位置（session high/low ±5 pips） | 低 | 07:00–10:00 NY 區間內的 extreme |
| Stop loss 漸進管理（25%/50%/75% milestone） | 低 | 獲利百分比條件 |
| 15 / 20 pips 目標出場（limit order） | 極低 | 固定pip目標 |
| Symmetrical swing 計算 | 低 | measured move = 來回等距 |
| No re-entry 規則 | 極低 | 狀態旗標 |
| 連贏/連虧 R% 調整 | 低 | 交易紀錄計數 |

### 需要主觀判斷的規則（較難完全機械化）

| 規則 | 難度 | 說明 |
|------|------|------|
| **Institutional order flow 方向判斷** | 高 | Daily swing point 是否已被突破，但「swing high/low」定義需人工設定或用固定lookback |
| **OTE pattern 識別（5分鐘）** | 中 | 可用固定條件：price retraces to 62% of most recent 5min swing in Kill Zone；但辨識「有效 swing」有主觀性 |
| **Swing High/Low 定義** | 中 | ICT 未在逐字稿中給出精確的K棒數量定義（如：左右各幾根K棒確認），需補充 |
| **PD Array 識別**（order block、breaker 等） | 高 | 深化版增加了 breaker/order block 進場條件，識別本身需規則化 |
| **Judas Swing 識別** | 高 | 深化版特徵，逐字稿未給精確量化定義 |
| **40日 look-back 的切換時機** | 中 | 「20日 range 太窄」屬定性判斷，需設定 range 寬度閾值 |
| **Leader 留倉決策** | 高 | 是否留 leader 依交易員判斷，不可完全自動化 |

### 結論：NQ 1分K NY 開盤場景適用性評估

**基礎版（vCvRrINpknI）適用性：中高**
- 核心流程（OTE at 62% in Kill Zone → 固定停損 → 15/20 pip 目標）可完全機械化
- NQ 為 Futures，不需 ±5 pip spread 調整（可改為 ±1–2 ticks 或依實際 spread 設定）
- 本模型原始設計為 **5分鐘**，用於 1分鐘K棒需注意：
  - OTE swing 辨識區間縮短，False signal 頻率上升
  - 建議：在 5分鐘上辨識 OTE level，在 1分鐘上精確執行入場
- **「3小時內」（07:00–10:00 NY）完全符合模型的 Kill Zone 定義**，不需任何修改

**需補充的量化定義（用於 NQ 自動化）：**
1. Swing High/Low 判定：建議設定「左右各至少 N 根K棒（5分鐘框架）為局部高低」
2. 20日 range 的 session type：NQ 以 CME 交易日為準（排除非交易日，不止 Sunday）
3. PDH/PDL 以 Regular Trading Hours（RTH）09:30–16:00 還是全日定義
4. Pips 換算為 NQ handles（ticks）：NQ 1 handle = 4 ticks = $20

---

## 關鍵原文引述

> "Between 7:00 a.m. to 11:00 a.m. New York time on a 5 minute chart we're going to be looking for a retracement lower against the London session momentum of the day using the bullish optimal trade entry pattern and keying off of the 62% level." — vCvRrINpknI

> "Monday through Wednesday is ideal buy days in New York session. Thursday can still be considered as long as the liquidity remains for low resistance liquidity runs... if I did my leverage would be dialed way back I'd probably be doing anywhere between 25% to 40% of what I would normally be trading." — vCvRrINpknI

> "If prices run to your stop do not take a re-entry on the trade." — vCvRrINpknI

> "Buying only when the daily has taken out a swing high in the last 20 days if the data range and not in a premium... buying can be considered at equilibrium of the daily range of the 20-day IPTA data range." — vCvRrINpknI

> "If institutional order flow is bullish and price has broken a swing high on the daily, and price is not in a premium — if price is in a premium there is no trade — and today is Monday, Tuesday, or Wednesday conditions are ideal... then look for a bullish optimal trade entry in the 7 a.m. to 10:00 a.m. local New York time window on a five minute chart." — 4f1vjQMlV50

> "If time of day is after 10:00 a.m. there is no trade." — 4f1vjQMlV50

> "When we are in profit by 25% of our expected objective stop loss can be reduced by 25%; when we are in profit 50% of our expected objective stop-loss can be reduced by 50%... when the position is at 75% of the expected profit objective stop must be at break even." — 4f1vjQMlV50

> "The underlying pattern that sets up key institutional volatility... we have a high, run the high, break down, a short-term low is taken out, and then we trade back up into here — essentially it's the breaker." — rNn0JkItAGo

---

*筆記依據：三份逐字稿原始內容。僅使用 ICT 術語知識解讀字幕錯字（如 ipto/ifto/ipa → IPDA），不補充逐字稿以外的交易規則。*
