# Model 13 — ICT 2022 YouTube Free Mentorship 精華版（Index Futures 專用）

## 影片清單

- kNlySn81dmo — Charter Lecture On 2022 YouTube Model（本筆記來源）
- 原始 2022 YouTube 免費 mentorship：共 41 支影片（ICT YouTube 頻道公開）

---

## 模型定位

| 項目 | 說明 |
|------|------|
| 時間框架 | 5 分鐘降至 1 分鐘（5m / 4m / 3m / 2m / 1m，FVG 在哪個出現就用哪個） |
| 交易風格 | 日內（Intraday）；可擴展至任意時框（fractal / scalable） |
| 適用市場 | **主要：Index Futures**（本講座聚焦）；亦提 Forex（另有獨立時窗） |
| 目標 | 交易日內 Market Structure，目標為對向 PD Array（bearish → Discount PD array；bullish → Premium PD array） |

---

## 核心概念定義

### Liquidity Raid（流動性掃盪）
- **Buy Side Liquidity Raid**：價格向上掃過 Relative Equal Highs 或單一高點，將買側停損單清除（purge）。
- **Sell Side Liquidity Raid**：價格向下掃過 Relative Equal Lows 或單一低點，將賣側停損單清除。

### Market Structure Shift（MSS，市場結構轉換）
- Bearish：Liquidity Raid 後，價格急速跌破近期 5m～1m 低點 → 確認下行位移。
- Bullish：Liquidity Raid 後，價格急速突破近期 5m～1m 高點 → 確認上行位移。

### Displacement（位移）
- Liquidity purge 後的急速、單向走勢，形成 FVG（Fair Value Gap）。

### Fair Value Gap（FVG，公允價值缺口）
- 三根 K 棒形成：中間 K 棒的實體/wick 與第一根和第三根之間存在 gap。
- Bearish 用 FVG：缺口應位於 **Equilibrium 之上**（Premium 區）→ 回補時做空。
- Bullish 用 FVG：缺口應位於 **Equilibrium 之下**（Discount 區）→ 回補時做多。

### PD Array（Premium / Discount Array）
- Premium PD Arrays：位於 Dealing Range Equilibrium 以上（目標/停利用於多頭）。
- Discount PD Arrays：位於 Equilibrium 以下（目標/停利用於空頭）。

### Dealing Range Equilibrium
- 交易區間的 50% 中點，區分 Premium（以上）與 Discount（以下）。

### Relative Equal Highs / Lows
- 兩個以上接近等高的頂（或等低的底），為流動性聚集點，為 ICT 掃盪優先目標。

---

## 進場模型完整流程

### Bearish（做空）

```
Step 1｜前置條件（Bias）
  確認 bearish 偏向：尋找 Buy Side Liquidity 可被掃的位置
  → 目標：Relative Equal Highs 或單一高點上方

Step 2｜觸發：Buy Side Liquidity Raid
  價格快速拉高，掃過 Buy Side（REH 或單一高點），完成 purge

Step 3｜確認：Market Structure Shift（MSS）
  掃盪後，5m 或往下到 1m 出現 Rapid Market Structure Shift
  → 價格跌破 5m～1m 的近期低點 → 確認 bearish displacement

Step 4｜理想條件
  displacement 腿形成 FVG，且該 FVG 位於 Equilibrium 之上（Premium 區）

Step 5｜進場
  在形成 FVG 的 5m～1m 中，找到三根 K 棒的最低那根（Discount Low of FVG）
  → 在「該 K 棒的 High」掛 Sell Limit Order

Step 6｜停損
  FVG 三根 K 棒中最高那根（Premium High of FVG）的 High
  → 停損直接放在那根 K 棒的 High（不加 1 tick，不加 1 handle）

Step 7｜停利 / 出場目標（由近至遠，可做 partials）
  1. Dealing Range 以下最近的 Discount PD Array
  2. Previous Session Low（AM session → 前一天 PM session low；PM session → AM session low）
  3. Previous Day Low
  4. 以上目標之下若有額外 FVG，可作為更遠目標
```

### Bullish（做多）

```
Step 1｜前置條件（Bias）
  確認 bullish 偏向：尋找 Sell Side Liquidity 可被掃的位置
  → 目標：Relative Equal Lows 或單一低點下方

Step 2｜觸發：Sell Side Liquidity Raid
  價格快速下破，掃過 Sell Side，完成 purge

Step 3｜確認：Market Structure Shift（MSS）
  掃盪後，5m 或往下到 1m 出現 Rapid Market Structure Shift
  → 價格突破 5m～1m 的近期高點 → 確認 bullish displacement

Step 4｜理想條件
  displacement 腿形成 FVG，且該 FVG 位於 Equilibrium 之下（Discount 區）

Step 5｜進場
  FVG 三根 K 棒中最高那根（Premium High of FVG）的 Low
  → 在「該 K 棒的 Low」掛 Buy Limit Order

Step 6｜停損
  FVG 三根 K 棒中最低那根（Discount Low of FVG）的 Low
  → 停損直接放在那根 K 棒的 Low

Step 7｜停利 / 出場目標（由近至遠，可做 partials）
  1. Dealing Range 以上最近的 Premium PD Array
  2. Previous Session High（AM session → 前一天 PM session high；PM session → AM session high）
  3. Previous Day High
  4. 以上目標之上若有額外 FVG（Order Block），可作為更遠目標
```

---

## 具體參數

| 參數 | 數值 |
|------|------|
| 進場限價單精確度 | FVG Discount Low（bearish）或 Premium High（bullish）的那根 K 棒邊緣，不加任何 buffer |
| 停損精確度 | FVG 對向邊緣那根 K 棒的 High/Low，**不加 1 tick，不加 1 handle** |
| 執行時框 | FVG 從 5m 往下找，第一個出現 FVG 的時框就使用（5m / 4m / 3m / 2m / 1m） |
| 最大單筆風險 | **2% 以下**（總帳戶淨值），**建議 1% 或 0.5%** |
| 理想單筆風險 | 0.5%（因 setup 頻率高，避免 punch drunk） |
| 最低目標命中率 | 模型設計可承受 50% 命中率依然獲利（風控邏輯保護） |
| 進場精確度備註 | ICT 提及有時差 0.25 point 的 limit 就未成交；建議貼緊邊緣確保成交 |
| 勝率預期 | 逐字稿未給明確 RR 比，但隱含「low risk, high reward」（停損=最小 FVG buffer） |

---

## 時段規定（Killzone）

### AM Session（Index Futures）
時窗：**8:30 AM — 11:00 AM New York（Eastern Time）**

| 時間（ET） | 意義 |
|-----------|------|
| **8:30 AM** | 新聞/Embargo 解禁；高/中影響力新聞發布；**第一優先 setup 窗口** |
| **9:30 AM** | 美國股市開盤（US Equities Open）；Judas Swing 最常在此後成形 |
| **10:00 AM** | 開盤後首 30 分鐘 sentiment 確立；若 9:30 未成形，此時再找 |
| **10:30 AM** | 開盤後首 60 分鐘 Opening Range 確立；若 10:00 仍未成形，此為 AM session **最後機會** |
| **11:00 AM** | 僅在**週四、週五**考慮（市場逆轉日 / TGIF 條件 / London Close）；其他日不積極尋找 |

> Forex 另有獨立窗口：7:00 AM — 10:00 AM ET（本模型不作主要聚焦）

### PM Session
| 時間（ET） | 意義 |
|-----------|------|
| **12:00 — 1:00 PM** | Lunch Hour：監控 AM session highs/lows 或午休小時內的 Swing High/Low |
| **1:30 PM** | 午休量能結束，波動性返回；PM session 第一個 setup 窗口 |
| **2:00 PM** | PM Trends 開始；AM session stops 可能被清除；也可能清除 lunch hour stops |
| **2:30 PM** | 日場最後 2 小時開始（New York 日場） |
| **3:00 PM** | 日場最後 1 小時 |
| **3:30 PM** | Market-on-Close 條件啟動（高精度 scalper 適用，1m 圖） |

### PM Session Setup 規則
- **Bearish**：尋找 AM session highs 或 Lunch Hour Highs（12:00–1:00 PM）被掃；Relative Equal Highs from AM session 優先於午休單一高點。
- **Bullish**：尋找 AM session lows 或 Lunch Hour Lows 被掃；同上邏輯。
- 若 AM session 無 REH / REL，則使用 12:00–1:00 PM 內的 swing high/low（罕見情況）。

---

## 風控規定

### 基本風險上限
- 單筆最大：**2%** 總帳戶淨值
- 建議：**1% 或 0.5%**（因 setup 出現頻率高，過度槓桿風險大）

### 連續虧損遞減規則（Mitigating Drawdown Protocol）
```
1. 若某筆交易虧損滿 2%（停損全出）
   → 下一筆交易槓桿縮減為前一筆的 50%（即最多 1%）

2. 若第二筆也虧損
   → 再減半（0.5%），以此類推

3. 最低降至某點後保持該倉量，直到回補前一筆虧損的 50%

4. 回補 50% 後可恢復至前一級別

5. 理論序列：2% → 1% → 0.5% → 0.25% → 0.25% ...（保持直到回補）
```
> 目的：製造「階梯上升」效果，防止帳戶 roller coaster 式爆倉。

---

## 對「NQ 1分K、NY 開盤後 3 小時自動交易」的適用性

### 適用窗口對照

| 本模型時窗 | NQ 1m 開盤後 3 小時場景（8:30–11:30 AM ET） |
|-----------|---------------------------------------------|
| 8:30 AM（新聞窗） | 直接命中：最強 setup 窗口，波動大，FVG 形成快 |
| 9:30 AM（開盤） | 直接命中：Judas Swing 常在此後完成，1m FVG 大量出現 |
| 10:00 AM | 直接命中：30 分鐘 sentiment 確立，setup 仍有效 |
| 10:30 AM | 直接命中：AM session 最後可靠窗口 |
| 11:00 AM | 邊緣（週四/五才考慮）；3 小時窗口末段 |

**本模型是為此場景量身設計的**：8:30–11:00 AM ET 是其明確定義的 AM session Killzone，與「NY 開盤後 3 小時」高度重疊。

### 自動化關鍵要素（可演算法化的條件）

| 要素 | 可量化程度 |
|------|-----------|
| 時間過濾（8:30/9:30/10:00/10:30 ET） | 完全可硬編碼 |
| Buy/Sell Side Liquidity Raid 識別 | 需定義「relative equal highs/lows」門檻（距離百分比或 handle 數） |
| MSS（跌破近期 5m/1m 低點） | 可定義：N 根 K 棒內的 swing low/high 被突破 |
| FVG 識別（三 K 棒結構） | 可量化（gap 大小門檻建議設定） |
| FVG 位於 Premium/Discount 區判斷 | 需定義 Dealing Range（前 N 根或前 session 的 range） |
| 進場限價位置 | 精確：FVG 第三根 K 棒 High（bearish）或第一根 K 棒 Low（bullish） |
| 停損位置 | 精確：FVG 第一根 K 棒 High（bearish）或第三根 K 棒 Low（bullish） |
| 出場目標 | 需定義前 session high/low、Dealing Range 等前置資料 |

### 注意事項
- 模型本身未給出 FVG 最小 gap 大小（handles/points）的量化門檻，需自行回測設定。
- 停損精度要求很高（無任何 buffer），1m NQ 的 ATR 需納入 position sizing 計算。
- ICT 強調只找「一個好 setup」，不是每個時窗都進場；自動化版本需有嚴格過濾條件。

---

## 關鍵原文引述

1. **模型邏輯核心**：
   > "we are looking to trade intraday Market structure that targets opposing PD array Matrix objectives"

2. **時間框架定義**：
   > "we're monitoring five down to one minute charts after a liquidity rate occurs and short-term shift in Market structure unfolds"

3. **Bearish setup 條件**：
   > "if we're bearish we look for a buy side liquidity raid...price quickly jumps up into it once it takes that buy side then we're waiting to see rapid Market structure shift below a recent five or down to a one minute chart low that's displacement"

4. **理想 FVG 位置**：
   > "ideally the fair value Gap is going to be at or above the equilibrium for bearish and at or below equilibrium for bullish"

5. **Bearish 進場精確規則**：
   > "place a sell limit order at the high of the discount low of the fair value gap on the five down to one minute chart...I'm taking it right at that high because if the structure is there and the idea is there and the narratives in play I want to make sure I'm getting filled"

6. **停損精確規則**：
   > "stop loss is placed at theow low of the premium high of the fair value Gap used for the setup...right at the high so we're using the lowest risk parameters that you can use"

7. **AM session 時窗明確說明**：
   > "8:30 a.m. to 11:00 a.m. eastern time for index Futures which is the am session index Futures morning session"

8. **單筆風險規定**：
   > "we use 2% or less preferably less per setup of the total Equity of the trading account...ideally 1% or a half percent because these setups form a lot the frequency of trade can tend to make you one to get punch drunk"
