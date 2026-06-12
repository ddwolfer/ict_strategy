# Model 7 — Universal Trading Model（賣方低阻力流動性追逐）

## 影片清單

| ID | 標題 |
|----|------|
| `_7oZZ2bhEGU` | ICT Charter Price Action Model 7 - Universal Trading Model |
| `oheyS8MUqno` | ICT Charter Price Action Model 7 - Supplementary Lesson（Tape Reading） |
| `G4lhid5dh0I` | ICT Charter Price Action Model 7 - Trade Plan & Algorithmic Theory |

---

## 模型定位

- **核心焦點**：Sell-side low resistance liquidity runs（賣方低阻力流動性追逐）與 fractal 結構
- **交易方向**：純做空（short only），專注市場向下的那一側
- **時間框架**：Universal — 適用所有週期（position / swing / short-term / day / scalping）；但核心 narrative 建立在 weekly / daily，進場精化至 4H、1H、15min、5min，執行級別可到 1min
- **適用市場**：所有市場（forex、index、commodity 皆適用，逐字稿以 USD/CHF、GBP/USD、crude oil 為例）
- **風格**：等待 Market Maker Sell Model 或 Market Maker Buy Model 的賣方展開段，利用 Stage 1 / Stage 2 redistribution 點做空
- **目標**：逐字稿未明確提及月度 % 目標或整體 R 目標；單筆交易目標見「具體參數」節

---

## 核心概念定義

### Market Maker Sell Model（MMSM）
ICT 定義的市場結構模板，包含：
1. **買方曲線（Buy side of the curve）**：整合 → 突破上漲 → Reaccumulation of Longs（第1次） → 再上漲 → Reaccumulation of Longs（第2次，最高那個） → 觸及高時間框架 Buy Side Liquidity（Premium PD Array） → Smart Money Reversal
2. **賣方曲線（Sell side of the curve）**：SMR 後開始向下，這就是 Model 7 的操作區段

### Sell-side Low Resistance Liquidity Run
市場下行時，由於多頭爭相退出（而非空頭推低），下跌速度比上漲更猛烈、更迅速、更暴力。這是 Model 7 專注捕捉的行情。

### Liquidity Distribution Profile
ICT 用來判斷市場結構的框架：不看 candlestick 本身，而是追蹤「哪裡有流動性」與「它已被觸及了沒有」。這個 profile 決定何謂真正的 Market Structure Break（MSS）。

### Stage 1 Redistribution（Point 0.1）
買方曲線最後一個整合區後，市場向上突破、觸及高時間框架流動性後回落，**第一次回到**原始整合區的位置，即為 Stage 1 Redistribution——做空的第一個機會點。

### Stage 2 Redistribution（Point 0.2）
若 Stage 1 的空單被洗出，或市場未回到 Stage 1 而進一步向下，再從某個 down-closed candle / OB 反彈至第二個可接受賣空點，即為 Stage 2 Redistribution。

### Market Structure Break / Shift（MSS）
特定定義：**高時間框架 Buy Side Liquidity 被觸及後**，買方曲線中「最高的那個 Reaccumulation of Longs」的 swing low 被跌破，才算真正的 MSS。並非任意的低點被跌破。

### Reaccumulation of Longs（最高點）
買方曲線中，在 Smart Money Reversal 之前出現的所有 swing low 中，**最高那一個**就是關鍵。一旦它被跌破，就是進場做空的訊號。

### Low-Risk Entry（低風險進場）
Market Structure Shift 確認後（最高 Reaccumulation of Longs 的 swing low 被跌破），等 sell stops 先被清空，然後價格反彈回 down-closed candle 的本體區域（即 fair value），在那裡做空。這是 Model 7 最核心的進場形式。

### Fair Value（公平價值）
在賣方展開背景下，fair value 由形成 swing low 的 **down-closed candle（s）的本體**來界定；價格反彈進入這些 candle 本體時，就是做空的 fair value 區。

### Balanced Price Range（BPR）
某一根 candle 的高到下一根的低之間若只有 buy-side 成交，等後來 sell-side 也進入這個 range 後，它就「平衡」，之後會充當自然的支撐或壓力。

### Terminus
下行目標的終點，通常是折扣區（discount zone）的 PD Array（Bullish Order Block、Fair Value Gap、Old Low 等），必須**在進場前就先確認**，不是後見之明。

### Tape Reading（ICT 定義）
監控「微小 dealing range」的漲落，而非看 candlestick 形態。重點是識別買方曲線留下的累積區域（reaccumulation ranges），將那些 range 帶入賣方曲線一側，觀察 IPA（Interbank Price Algorithm）如何尊重它們。一分鐘 K 線的「噪音」本質上是 **distortion**（因 time 拉長），不是真正的噪音。

---

## 進場模型完整流程

### 前置條件（Preparation）

1. 查看近 20 / 40 / 60 個交易日（不含週日）的最高高點與最低低點，建立 **dealing range**
2. 確認高時間框架（週線/日線）偏空：Higher Time Frame 已觸及或預期觸及 Premium PD Array，且已出現 Smart Money Reversal 跡象，或最高 Reaccumulation swing low 已被跌破
3. 確認 **Terminus**：在 dealing range 下方找到 discount PD Array（Bullish OB、FVG、Old Low）作為目標
4. 查看 economic calendar，找出本週或下週的 medium / high impact 事件作為潛在 volatility injection 時間點

### Setup 形成（Opportunity Discovery）

5. 在 Market Maker Sell Model（或 Buy Model 的賣方曲線）中，識別 Stage 1 或 Stage 2 Redistribution 區域
6. **Stage 1 Setup**：原始整合區 → 市場上漲 → 觸及 buy side liquidity → 回落進入 down-closed candle 本體（原整合上緣 / 第一個 redistribution cycle）
7. **Stage 2 Setup**：若 Stage 1 未能跌到目標，或反彈更深進入另一個 OB / FVG，形成第二次賣空機會
8. 確認最高 Reaccumulation of Longs 的 swing low 已被跌破（MSS 確認）

### 觸發條件

9. Sell stops 先被清掃（price 跌破最高 reaccumulation swing low）
10. 價格反彈回 down-closed candle 本體（fair value），進入分配區
11. 在 **London Open** 或 **New York Open Killzone** 期間，5min chart 出現 Institutional Order Flow Entry Drill（IOFED）形態，或出現 buy stop raid

### 進場

12. 在 **15min 或 5min** 的 Premium Fair Value Gap / PD Array 做空，要求該 PD Array 與 **standard deviation +3** 以內收斂（convergence）
13. 使用 **Sell Limit Order**（非市價單）
14. 進場價 = Premium PD Array + Standard Deviation convergence 後的水平，**減 5 pips** 作為執行 limit 的確切點位
15. 若多筆訂單，全部使用**同一進場價**
16. 可選：在此段使用 scalping protocols 進一步降低風險

### 停損位置

17. 停損放在**進場前最後那個 Premium Array 的高點，再加 20 pips**（`stop = high of premium array + 20 pips`）
18. 若被洗出，可重新進場（secondary entries 正常）——「do not fear that」

### 停利 / 出場管理

19. **第一目標**：20 pips → 平掉一部份倉位（limit order）
20. **第二目標**：40 pips → 平掉另一部份（limit order）
21. **第三目標**：60 pips → 平掉 80% 剩餘倉位，剩餘 20% 繼續持有看是否有更多
22. 動態停損調整規則：
    - 盈利達到預期目標的 25% → 停損收緊 25%
    - 盈利達到 50% → 停損收緊 50%
    - 盈利達到 75% → 停損移至 **break even**
23. 最終出場：Terminus（discount PD Array），在此附近**關閉大部分或全部倉位**，因為不確定是否會 bounce 還是繼續崩

---

## 具體參數

| 項目 | 數值 |
|------|------|
| Dealing Range 看回期 | 最近 20、40 或 60 個交易日（不含週日） |
| 分析用最小時間框架（setup） | 15min / 5min |
| 進場觸發時間框架 | 5min（IOFED）；scalping 可到 1min |
| 進場偏差 | Limit 設在 PD Array 收斂水平 **minus 5 pips** |
| 停損 | Premium Array 高點 **+ 20 pips** |
| 目標 1 | **20 pips** |
| 目標 2 | **40 pips** |
| 目標 3 | **60 pips**（平 80% 剩餘，保留 20%） |
| 動態停損 #1 | 盈利達到預期的 25% → 停損收緊 25% |
| 動態停損 #2 | 盈利達到預期的 50% → 停損收緊 50% |
| 動態停損 #3 | 盈利達到預期的 75% → 停損移至 BE |
| Standard Deviation 上限 | **+3 standard deviations**（超過則不進場） |
| 頻率（風控） | 連輸 5 筆後降低風險 50% |
| 風險回收門檻 | 虧損金額回收 50% 後，才可回到原始 risk % |
| 位置大小公式 | `Position Size = (Account Equity × Risk%) / Stop Loss in Pips` |
| 示範風險參數 | Account $2,000，Risk 1.5%（$300），Stop 20 pips → 150 micro lots |
| Pip 目標參考（USD/CHF 例） | 30 pips 為「swing 潛力」（由 swing low 往下 30 pips 到 target zone） |
| 1分K 一分鐘 K 的 PIP 目標（GBP/USD 例） | 10 pips → 12260（實際低 12259，差 1 pip）；20 pips → 12250（實際低 12251，差 1 pip） |

---

## 時段規定（Killzone）

逐字稿明確提到的時段：

| 時段 | 用途 |
|------|------|
| **London Open** | 5min IOFED 進場窗口；scalping 協定可啟用 |
| **New York Open** | 5min IOFED 進場窗口；scalping 協定可啟用 |

> **注意**：逐字稿使用「London open」和「New York open」，但未具體標明 New York 時間的開始結束時刻（字幕不清：未出現例如「8:30–11:00 NY」之類的明確數字）。ICT 術語體系中 NY Kill Zone 通常指 7:00–10:00 NY 時間，但此逐字稿未出現這個數字，故此處不補入。

---

## 風控規定

1. **位置大小**：使用公式 `(Equity × Risk%) / Stop pips`，始終向下取整
2. **標準單位建議**：Micro lots > Mini lots > Standard lots；Standard lots 彈性最差，不建議新手使用
3. **連勝後降風險**：連續 5 筆獲利後，自動將 risk % 降低 50%（因為接下來可能輸）
4. **虧損後降風險**：虧一筆後，下一筆 risk % 減半；若下一筆又虧，再減半，如此類推；直到上一筆損失已回收 50%，才回到原始 risk %
5. **目標**：追求平滑向上的 equity curve（stair-step higher），避免大幅回撤
6. **Terminus 出場**：到達 discount PD Array 目標時，平掉大部分或全部倉位，不貪婪（「we don't know if it's going to create a bounce」）
7. **再進場**：一筆被停損出場後可重新進場，一天內多次嘗試是正常的，不需要恐懼

---

## 對「NQ 1分K、NY 開盤後 3 小時自動交易」的適用性

### 可以使用的面向

**與此場景高度吻合**：
- Model 7 的逐字稿（oheyS8MUqno）明確示範了在 **1 分鐘圖上操作**，並成功預測 10 pip / 20 pip 目標，誤差僅 1 pip，證明此模型在 1min chart 上可行
- 「Sell-side low resistance liquidity runs」下跌速度快、幅度大，1 分鐘 NQ 在 NY 開盤後的波動與此特性相符
- **New York Open Kill Zone** 是逐字稿明確列出的進場時段

**可以機械化的規則**：
| 規則 | 可演算法化程度 |
|------|--------------|
| 識別 dealing range（20/40/60 日最高低） | ✅ 完全可量化 |
| 停損 = 進場前 Premium Array 高點 + 20 pips | ✅ 可量化（需先識別 array） |
| 停利目標 20 / 40 / 60 pips | ✅ 完全可量化 |
| 動態停損調整（25% / 50% / 75% 獲利時） | ✅ 可量化 |
| Limit order 進場（PD array level − 5 pips） | ✅ 可量化（需先識別 array） |
| Risk % 計算與 position sizing | ✅ 完全可量化 |
| 連勝 5 筆後降 risk 50% | ✅ 可量化 |
| 連敗後逐步降低 risk % | ✅ 可量化 |
| Standard Deviation +3 限制 | ✅ 可量化（需計算 SD） |
| NY Open / London Open 時段過濾 | ✅ 可量化 |

**需要主觀判斷的規則（演算法化難度高）**：
| 規則 | 難點 |
|------|------|
| 識別「最高的 Reaccumulation of Longs」的 swing low | 需判斷哪個 swing low 是「最高那個」，在整個買方曲線脈絡中定義，無固定 bar 數規則 |
| 確認 Market Maker Sell Model 的「曲線」起點與中點 | 主觀判斷整合區範圍 |
| 識別 Stage 1 vs Stage 2 redistribution 的位置 | 依賴對整個 fractal 的讀取 |
| 判斷是「controlled demolition（下到目標後反彈）」還是「cliff fall（崩盤式下跌）」 | 需結合總經/地緣政治分析，逐字稿明確說這需要主觀判斷 |
| Tape Reading 的 dealing range 監控 | 需識別前一段買方曲線留下的 range 邊界並帶入右側；1min 的 distortion 識別需要大量經驗 |
| Premium FVG 的識別與 SD 收斂確認 | 需界定 FVG 上下邊界，並確認它與 SD 水平收斂 |

### 結論
Model 7 **原則上適合** NQ 1min NY 開盤場景，但需要先在更高時間框架（日線/4H）確認好 narrative（偏空、最高 Reaccumulation 已破），再降到 1min 等待 NY Open kill zone 內的 redistribution 形態。**停損、目標、position sizing、時段過濾** 均可完全自動化；**setup 識別**（尤其是 swing low 的定性與 fractal 脈絡）則仍需程式化規則或 ML 輔助。

---

## 關鍵原文引述

1. > "Price action model number seven again this is Universal trading so it's applicable to every style of trading that means position trading swing trading short-term trading day trading and scalping."

2. > "Once the sell stops are ran out then I return back up into this level of liquidity in the form of the down closed candles that's where we're looking for to pair our orders for going short."

3. > "Underline this in your notes — if the highest reaccumulation of Longs on the buy side of the curve of a sell model... if again the market breaks down right to this one... we have the likelihood of a return back to fair value or optimal trade entry."

4. > "We will short premium fair value gaps or short buy stops in a stage one or stage two redistribution when we are bearish... we will frame a short entry when price has moved up into a 15-minute or 5-minute premium fair value gap PD array that converges with a standard deviation of no more than plus three standard deviation during London open or New York open."

5. > "When we are entering a short we will place our stop loss above this high plus 20 pips... we can re-enter if the trade stops out we can monitor it for secondary entries — day trades may require multiple attempts to secure a solid entry, do not fear that."

6. > "When we are in profit 25% of our expected objective stop loss can be reduced by 25%... when the position is at 75% of the expected profit objective stop must be at break even."

7. > "The sell side generally performs the most aggressive, the most ferocious, they're speedy, they're very quick, they're violent... the magnitude of the move tends to be much more exaggerated than that of a buy side low resistance liquidity run."

8. > "Tape reading in the clearest definition I can provide for you is understanding the ebb and flow of the micro dealing ranges that create — as time goes by — the floor traders would always have a little pad in their hands... they would monitor the intraday highs and lows every time they ticked up and made a new high for the day they'd write that number down." (oheyS8MUqno)
