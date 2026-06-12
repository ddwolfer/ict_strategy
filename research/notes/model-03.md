# Model 3 — Swing Trading / Daily Liquidity Pool Targeting

## 影片清單

| ID | 標題 |
|----|------|
| E0sA_SWIxKM | ICT Charter Price Action Model 3 — Amplified Lecture |
| ze8jAMdmBqc | ICT Charter Price Action Model 3 — Trade Plan & Algorithmic Theory |

---

## 模型定位

- **交易風格**：Swing trading（中期至短期，非 intraday scalping）
- **主要時間框架**：Monthly bias → Weekly context → Daily chart 進出場規劃 → 4H/1H 精細化進場；最低可降至 15-min OTE 進場
- **適用市場**：任何市場（Forex、Futures、Commodities），影片以 CAD Futures / Dollar CAD、GBP/USD、British Pound Futures 為例
- **目標**：每筆交易 **100–300 Pips**（核心目標範圍）；若 monthly candle 大幅擴張可達 1,000+ Pips
- **交易頻率**：**每月 1–2 次**
- **進場日偏好**：星期一、二、三（Monday / Tuesday / Wednesday）
- **Kill Zone**：London Open 或 New York Open（擇一或兩者）

---

## 核心概念定義

### COT Hedging Program（ICT 版 Commitment of Traders 解讀）

- 只看 **Commercial Traders**，忽略 Large Specs 與 Small Specs
- 回溯 **最近 12 個月** 的 Commercial net position 的最高值與最低值
- 將該 12-month range **對半分**，取中點作為「ICT 自訂零線（custom midpoint）」
- **若目前 Commercial net position 高於中點** → 視為 bullish commercial buy program
- **若目前 Commercial net position 低於中點** → 視為 bearish commercial sell program
- 此中點不等於傳統 COT 圖表的 Net Zero 線；ICT 明確指出傳統 Net Zero 線對他無用

### Daily Liquidity Pool

- 日線圖上可辨識的 **Equal Highs**（buy stop liquidity）或 **Equal Lows**（sell stop liquidity）
- 亦可以是「ideal intermediate-term high/low」——明顯的前高/前低，外部有大量 stops 積累
- 必須出現在 **EPOD（如果 data range）look-back** 的範圍內：20 / 40 / 60 個交易日（不含週日）

### EPOD / IFPD Data Range（如果 data range）

- 以「今天」為基準回溯：先看 **20 個交易日**；若無明確 liquidity pool / PD array 則擴展至 **40 天**；最大 **60 天**
- 60 天為絕對上限；在上限範圍之外的 target 屬於「pip dream」，不納入規則
- 最佳 target 落在 **20–40 天** 回溯範圍內，命中率較高

### Optimal Trade Entry (OTE)

- Fibonacci retracement 工具，以某一 price swing 高低點為錨點
- 核心進場區：**62% Fibonacci retracement level**（bullish 時在 discount；bearish 時在 premium）
- OTE 停損設在 swing high/low 之外適當距離（通常 +/- 25 Pips 外，詳見「具體參數」）

### Premium / Discount PD Array（在此模型的語境）

- **Bullish**（月線預期上漲）：在 discount PD array 找 long entry；target 為 premium fair value gap 或 old high（buy stop liquidity pool）
- **Bearish**（月線預期下跌）：在 premium PD array 找 short entry；target 為 sell stop liquidity / old daily low

### Market Structure Shift (MSS)

- 在 15-min 時間框架上，先有 short-term low 被跌破，then retracement，此為觸發進場的 confirmation signal（ze8jAMdmBqc 中提及）

### Seasonal Tendency

- 在 opportunity discovery 階段使用：確認當前月份/季節歷史上傾向 bullish 還是bearish
- 與 COT Hedging Program + EPOD data range 共同構成「準備條件」

---

## 進場模型完整流程

### 前置條件（Preparation）

1. 查閱 **Economic Calendar**：標記未來一週所有 medium 及 high impact 事件；這些事件是「smoke screen」，為 central bank 造市提供 volatility
2. **COT Hedging Program** 確認方向：
   - 從 barchart.com 取得 Commercial-only net position（隱藏 Large Specs 與 Small Specs）
   - 回溯 12 個月取最高值與最低值，找中點
   - 目前讀數在中點 **以上** → bullish bias；在中點 **以下** → bearish bias
3. **月線偏向確認**：分析下一根月線 candle 是否有充分理由上漲或下跌；若無法明確判斷，放棄此模型，降至較低時間框架

### Setup 形成（Opportunity Discovery）

4. 確認 **Seasonal Tendency**（對齊當前月份的歷史傾向）
5. 在 **Daily chart** 上找 liquidity pool：
   - Bullish：equal highs 或 old daily high（buy stop liquidity）位於 20–60 天 look-back 範圍內
   - Bearish：equal lows 或 old daily low（sell stop liquidity）位於 20–60 天 look-back 範圍內
6. 確認 target liquidity pool 距離進場點具備 **至少 100 Pips** 的潛在利潤空間（首選 100–300 Pips）

### 觸發條件

7. 在 **星期一、二或三**（週一至週三），price 在 **London Open 或 New York Open kill zone** 出現以下之一：
   - 回檔進入 15-min discount PD array（bullish）或 15-min premium PD array（bearish）
   - 15-min Equal Lows 被掃（bullish 時等待 sell stop raid + rejection）
   - 15-min Equal Highs 被掃（bearish 時等待 buy stop raid + rejection）
8. **15-min MSS 確認**：short-term low 被打破後反彈回 PD array（bullish）；short-term high 被打破後回落至 PD array（bearish）

### 進場

9. 在 **15-min 時間框架** 上量出 OTE（以 kill zone 形成的 swing low/high 為錨點拉 Fibonacci）
10. **進場價格**：
    - Long：Standard Deviation 收斂點 **+5 Pips** 下 buy limit order（PD array 與 -3 SD 收斂，誤差不超過 5 Pips）
    - Short：Standard Deviation 收斂點 **-5 Pips** 上 sell limit order（PD array 與 +3 SD 收斂，誤差不超過 5 Pips）
    - 精確入場：62% Fibonacci level 必須與 Standard Deviation 收斂於 **5 Pips 以內**
11. **可降至 5-min 或 1-min** 進一步精細化進場（scalping protocols），以壓縮 stop loss

### 替代進場（Alternative Execution）

- 若 OTE 未成交：
  - **Bullish**：記錄週二 Asian Range High，在該水平 **+1 pip** 掛 buy stop（必須在 2:00 AM EST 之後）；等待 price 先跌破 Asian Range Low 或 European Opening Price 做出當日低點後，再買入
  - **Bearish**：記錄週二 Asian Range Low，在該水平 **-1 pip** 掛 sell stop（2:00 AM EST 之後）；等待 price 先漲過 Asian Range High 或 European Opening Price 做出當日高點後，再做空
- **European Opening Price（週二）**：
  - Bullish 時，僅接受 **在或低於** 週二 European Opening Price 的 long entry
  - Bearish 時，僅接受 **在或高於** 週二 European Opening Price 的 short entry

### 停損設置

- Short 進場：停損置於進場點對應 premium array / Standard Deviation 收斂點的 **高點 +25 Pips**
- Long 進場：停損置於進場點對應 discount array / Standard Deviation 收斂點的 **低點 -25 Pips**
- 若使用日線/4H 判斷（不進入 intraday），停損設在最近 swing low（多）/ swing high（空）之下/上約 10 Pips 外（逐字稿舉例：stop at 13115 = swing low 13126 - 11 pips）
- **允許再次進場**：被停損後可重新嘗試，因 swing trade 可能需多次嘗試

### 停利 / 出場管理

**Partial scaling 時間表（以 short 為例，long 對稱）**：

| 停利目標 | 說明 |
|---------|------|
| 第 1 單：50 Pips | 低端初始目標（「週級 one-shot one-kill」低標） |
| 第 2 單：75 Pips | ICT 個人常用高端初始目標 |
| 第 3 單：100–300 Pips | 留倉追蹤；對應 20/40-day look-back 內的 old daily low/high |
| 可選殘倉：300+ Pips | 若月線大幅擴張，可開放至 500 Pips 甚至 1,000+ Pips open-ended |
- 實際停利點以 **日線圖** 標記（不在 4H / 1H / 15-min 標記）；對應 old daily high/low 或 fair value gap
- 若捕捉到 **300 Pip** 目標：關閉 **80%** 倉位，剩餘 20% 續跑
- **Fibonacci extension levels（手動抄寫，原文僅口述）**：
  -2.768、-1.27、-1.68、-2.0、-2.27、-2.68、-3.0、-3.273、-3.68、-4.0、-4.274、-4.68、-5.0（均為負號標示，代表向外延伸）
  - 兩組 Fib 的 extension level 若有**重疊（Confluence）**，視為強力目標

---

## 具體參數

| 參數 | 數值 |
|------|------|
| 目標 Pip 範圍 | 100–300 Pips（核心），可至 1,000+ Pips |
| 交易頻率 | 每月 1–2 次 |
| 進場日 | 週一、週二、週三 |
| Kill Zone | London Open / New York Open |
| OTE Fibonacci 進場水平 | 62% retracement |
| Standard Deviation 收斂誤差上限 | 5 Pips |
| Stop Loss buffer（Short） | Premium array 高點 +25 Pips |
| Stop Loss buffer（Long） | Discount array 低點 -25 Pips |
| 第 1 停利目標 | 50 Pips（或對應 20-day look-back 內最近 old high/low） |
| 第 2 停利目標 | 75 Pips（ICT 個人偏好），或對應 40-day look-back |
| 中段停利 | 130 Pips（ICT 個人偏好口述） |
| 300 Pip 達到後 | 關閉 80% 倉位 |
| EPOD look-back 最佳 | 20–40 天；最大 60 天 |
| COT 回溯期 | 12 個月（Swing Trading 標準；亦可用 6 個月） |
| Alternative entry 時間 | 2:00 AM EST 之後（Asian Range High/Low 掛單） |
| 最大風險（單筆）建議 | 1% 或以下（Swing Trading 場景） |
| 5 連勝後風控 | 減半 R% |
| 虧損後風控 | 每虧一筆將 R% 減半；須回補前次虧損 50% 才能恢復 |

---

## 時段規定（Killzone）

| Kill Zone | 作用 |
|-----------|------|
| London Open | 首選 OTE 形成時段 |
| New York Open | 備選 OTE 形成時段 |
| 2:00 AM EST 之後 | Alternative entry（Asian Range High/Low 掛單）的啟動時間 |

- 模型並不指定「僅限某一個 Kill Zone」，London 或 New York 皆可（"London open **and or** New York open"）
- 不需要等待特定日內時段觀察月線；但進場本身需落在 Kill Zone 內

---

## 風控規定

1. **初始 R%**：Swing Trading 建議最高 1%（絕不超過 2%）
2. **虧損遞減**：每次虧損將 R% 減半（1% → 0.5% → 0.25%）；停在 0.25% 直到回補前一損失的 50%
3. **連贏遞減**：5 連勝後同樣將 R% 減半，避免在最大暴露時遭遇逆轉
4. **再入場允許**：Swing Trade 允許多次嘗試進場
5. **停損不頻繁調整**：不主動追蹤停損位；等 position 達到期望獲利百分比後才移動：
   - 達到目標 25% → stop 可縮減 25%
   - 達到目標 50% → stop 可縮減 50%
   - 達到目標 75% → **stop 必須移至 break-even 或更好**

---

## 對「NQ 1分K、NY 開盤後 3 小時自動交易」的適用性

### 適合程度：**低度適合（不建議直接套用）**

**原因**：

| 面向 | 說明 |
|------|------|
| 時間框架錯配 | Model 3 是 swing trading 模型，核心為月線偏向 + 日線 liquidity pool；1-min chart 僅在最末階段用於精細化進場，不是主要分析框架 |
| 主觀判斷成分高 | COT Hedging Program 需人工計算 12-month commercial range 中點，並作出「月線偏向判斷」——這是主觀解讀，難以機械化 |
| 進場頻率極低 | 每月 1–2 次，與「NY 開盤自動掃描進場」的高頻需求不符 |
| Seasonal Tendency | 需依月份查閱歷史傾向，動態變動，不易硬編碼 |
| Kill Zone 可對應 NY Open | 這是唯一與「NY 開盤後 3 小時」高度重疊的部分：NY Open kill zone 是 Model 3 的有效進場窗口 |

### 哪些規則可機械化

- EPOD look-back（20/40/60 天最高最低值）→ 可程式計算
- Equal Highs / Equal Lows 識別 → 可程式化掃描
- Fibonacci 62% level 計算 → 全自動
- Stop Loss placement（+/- 25 Pips from entry convergence） → 全自動
- Partial profit ladders（50 / 75 / 130 Pips）→ 全自動
- Kill Zone 時間窗（NY Open）→ 全自動
- Alternative entry：Asian Range High/Low +/- 1 pip at 2:00 AM EST → 全自動
- Stop-loss management trail（25% / 50% / 75% milestone）→ 全自動

### 哪些靠主觀判斷（難以機械化）

- COT Hedging Program 的月度偏向判斷
- Seasonal Tendency 的識別與加權
- Monthly candle expansion 的「判讀」（不要求 close near high/low，只要 range 擴展——需主觀評估）
- PD array 的優先排序（多個老高老低同時存在時，選哪個）
- Standard Deviation 工具（Asian Range / CBDR / Flout 三擇一的規則，逐字稿中未完整說明，需參照 core content）

---

## 關鍵原文引述

1. *"This model will be teaching the swing trading ICT approach... its primary focus is going to be attacking daily liquidity pools."* （E0sA_SWIxKM）

2. *"The coot hedging program... we take the last 12 months of commitment of traders report data on just commercial traders only, getting its highest high and its lowest low in terms of their net position, dividing that range in half — if it's above the midpoint... we're going to be looking at that as a bullish commercial buy program."* （E0sA_SWIxKM）

3. *"The trade objectives are going to be 100 to 300 pips on average... the trade frequency generally will be one to two times per month."* （E0sA_SWIxKM）

4. *"If we're buying, okay, and we're swing trading, we want to be doing what — trying to buy on a Monday, Tuesday or Wednesday. If we're selling short and we're bearish, what are we going to be doing — looking to sell short on Monday, Tuesday or Wednesday. And the kill zones are London open and or New York open primarily."* （E0sA_SWIxKM）

5. *"We will frame a short entry when price has moved up into a 15-minute premium PD array that converges at a standard deviation of no more than plus three standard deviation... during London open and or New York open at the 62% FIB level of the optimal trade entry."* （ze8jAMdmBqc）

6. *"When we are entering a short we will place our stop loss above this high plus 25 pips. We will re-enter if the trade stops out — swing trades may require multiple attempts to secure a solid entry."* （ze8jAMdmBqc）

7. *"When we are in profit 75% of the expected profit objective, stop must be at break even or better."* （ze8jAMdmBqc）

8. *"If you capture a 300 pip objective close 80% of the trade and see if it has any more room to run."* （ze8jAMdmBqc）
