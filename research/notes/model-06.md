# Model 6 — Universal Trading Model（買方低阻力流動性運行與碎形）

## 影片清單

| ID | 標題 |
|----|------|
| BMYrtYMisnA | ICT Charter Price Action Model 6 - Universal Trading Model |
| fAcnhdaowME | ICT Charter Price Action Model 6 - Amplified Lesson (6.1) |
| V0TFp7AvZqw | ICT Charter Price Action Model 6.2 - Amplified Lesson |
| 5FTMSC4kLZM | ICT Charter Price Action Model 6.3 - Supplementary Lesson |
| yC-gQhvexGg | ICT Charter Price Action Model 6 - Buyside Trade Plan |
| beTnmkbuUjg | ICT Charter Price Action Model 6 - Algorithmic Theory |

---

## 模型定位

- **全名**：Buy Side Low Resistance Liquidity Runs with Fractals（買方低阻力流動性運行與碎形）
- **別稱**：Universal Trading Model — 「Universal」不是同時做日內/波段/長線，而是指這個框架可適用於**任何時間框架**
- **方向**：專注 buy side（多方），sell side 對應為 Model 7
- **適用市場**：所有市場（外匯、指數期貨、商品、股票）——逐字稿中明確指出 Forex pairs、S&P e-mini Futures、Gold、Dollar Index
- **交易風格覆蓋**：Scalp、Day Trade、One Shot One Kill、Swing Trade、Position Trade，同一框架不同時間框架對應不同風格
- **模型核心描述**：在 Market Maker Sell Model 或 Market Maker Buy Model 的 buy side of the curve 上，找到 stage 1 和/或 stage 2 reaccumulation，做多至 terminus（premium array / buyside liquidity pool）

---

## 核心概念定義

### Buy Side Low Resistance Liquidity Run
逐字稿：「buy side low resistance liquidity runs and fractals」——市場向上掃過 buy stops（買方止損）或 equal highs 上方流動性的運行，因路徑阻力低（sell stops 已被清除）而加速執行。

### Market Maker Sell Model（賣家做市商模型）
逐字稿：「consolidation → initial impulse higher → retracement to point 1 → second retracement to point 2 → run to premium array（terminus）→ then reversal/distribution」
- 結構：累積（consolidation）→ 初始上衝 → 回撤 point 1 → 再回撤 point 2 → 觸及 buy side liquidity → 反轉做空
- 在整個反轉發生前的**左側**，是 buy side of the curve，Model 6 專注於此段

### Market Maker Buy Model（買家做市商模型）
逐字稿：「consolidation at premium → break down to discount array → reversal → rally back above original consolidation」
- 結構：高位整理 → 跌破 → 在 discount array 反轉 → 上漲超越原始整理區（original consolidation = terminus）
- Model 6 同樣聚焦於此模型的 buy side of the curve（底部反轉後的上漲段）

### Stage 1 Reaccumulation（第一階段再累積）
逐字稿：「after the initial impulse swing higher forms, the first retracement — this is point 1」
- 初始上衝後的第一次回撤，落在上衝幅度的 **20–30%** 區間內（相對於從當前價到預期 terminus 的總區間）
- 圖形特徵：回撤到 fair value gap、order block，或跑 sell stops

### Stage 2 Reaccumulation（第二階段再累積）
逐字稿：「if it runs up and falls short and starts to correct, you have a built-in advantage... FIB projections like 127 or 168 extensions」
- 第二次回撤，位置比 stage 1 更深
- **過濾規則**：若 terminus 剩餘距離 ≤ 30 pips，**不會出現** stage 2，market 會直接跑至 terminus

### Terminus
逐字稿：「Terminus is where you think the Market's going to go up to stop and turn around」
- 本模型的利潤目標：premium array（bearish order block、old high、equal highs、FVG above market）
- Market Maker Sell Model 的 terminus = buy side liquidity pool above old highs
- Market Maker Buy Model 的 terminus = original consolidation high（被超越）

### Fair Value（FVG / Liquidity Void / Sell Stop Run）
逐字稿：「the pattern is fair value... fair value gap filling, liquidity void, or running sell stops — all three are fair value」
- 在 reaccumulation 期間，優先找 FVG；若無 FVG，則找 sell stop run；若 FVG 已存在且近 terminus（≤30 pips），不會再打 sell stops

### Range of Opportunity（機會範圍）
逐字稿：「the price level of the targeted liquidity — this is our range of opportunity」
- 從當前市場價格到預期 terminus（premium array）之間的整個區間

### Draw on Liquidity（流動性引力）
逐字稿：「between the moment and price we identify the liquidity the market will seek and the price level of the targeted liquidity」
- 市場被上方 buy stops / equal highs 吸引向上移動的方向性力量

### Dealing Range
逐字稿：「determine the IPA data range for the last 20, 40, and 60 days... note the highest high and the lowest low in the past 20 Trading days — this is your current dealing range」
- 不計入週日。分割 dealing range 中點 = premium/discount 分界

### PD Array Matrix（Premium/Discount Array 矩陣）
逐字稿：「you have to use your PD array Matrix」
- 包含：Fair Value Gap、Order Block（Bullish/Bearish）、Liquidity Void、Breaker、Rejection Block、Propulsion Block 等
- 在 discount 區域找買入，在 premium 找目標

---

## 進場模型完整流程

### 前置條件（Preparation）

1. **標記 economic calendar**：記錄當週所有 medium/high impact 事件，判斷可能的 weekly profile（逐字稿：「note all medium and high impact events」）
2. **建立 Dealing Range**：取最近 20 / 40 / 60 個交易日（不含週日）的最高高點與最低低點，中點為 premium/discount 分界（scalp/日內 → 20日；swing/daily setup → 40日；weekly setup → 60日）
3. **頂下分析（Top-Down Analysis）**：從高時間框架到低時間框架找出：
   - 高時間框架的 Draw on Liquidity（premium array 在哪裡？equal highs / old high / bearish OB / FVG above）
   - 當前市場是 discount 還是 premium
   - 識別是 Market Maker Sell Model 還是 Market Maker Buy Model 正在展開
4. **確認方向框架**：
   - 若為 **Market Maker Sell Model**：在反轉前的 buy side of the curve 找 long（整理 → 上衝後的 reaccumulation）
   - 若為 **Market Maker Buy Model**：在低點反轉後的 buy side of the curve 找 long（跌到 discount → MSB → 做多至 original consolidation）

### Setup 形成條件

逐字稿：「the main points that you have to have is a period of consolidation that leaves an area of equal highs」

**Market Maker Sell Model 的 setup**：
- 可見的整理區段（consolidation / equal highs / triple highs）
- 初始上衝（initial impulse leg）離開整理區
- 回撤到 **point 1**（20–30% of range = stage 1 reaccumulation）
- 回撤期間尋找：FVG ＞ sell stop run（若 FVG 存在優先用 FVG）

**Market Maker Buy Model 的 setup**：
- 高位整理後下跌至明確的 discount array（weekly/daily bullish order block、old low）
- 市場出現 Market Structure Shift（MSS）到上方
- 進入 buy side of the curve，找 stage 1 reaccumulation

### 觸發（Trigger）

逐字稿：「we wait for price to find that reversal... once it creates it then we'll be looking for the buy side of the curve」和「short-term Market structure shift... fair value Gap going long stop loss below the swing low that's it」

- 確認 MSS（短期市場結構轉換）至上方
- FVG 或 order block 出現在 stage 1/2 reaccumulation 位置
- 等待 economic calendar 事件注入波動性（逐字稿：「This volatility injection is what we wait for」）

### 進場

逐字稿：「we will frame a long entry when price has moved down into a 15 or five minute discount fair value gap PD that converges with a standard deviation of no more than -3 standard deviations during London open or New York open」

- 使用 **buy limit order**（不是 market order）
- 進場時間：**London open** 或 **New York open** kill zones
- 進場價：standard deviation + PD array 收斂位置 **加 5 pips** 作為 buy limit 價格
- 若使用多筆訂單，所有訂單使用**相同進場價格**

### 停損位置

逐字稿：「we will place our stop loss below this low minus 20 Pips」

- 停損 = 所在 discount array（FVG / order block）低點 **減 20 pips**
- 若為 propulsion candle 重疊區域：停損在 propulsion candle 下方或 mean threshold 略下
- 若 reaccumulation 期間低點已被防守兩次（stop run 後繼續上漲）：停損移至被防守過的低點下方

### 停損縮減規則（Trailing Stop Reduction）

逐字稿（yC-gQhvexGg）：
- 達到預期目標的 **25%**：停損縮減 25%
- 達到預期目標的 **50%**：停損縮減 50%
- 達到預期目標的 **75%**：停損必須移至**盈虧平衡**

### 出場管理

逐字稿：「place a limit order to take 20 Pips as our objective on one position... second limit order to take 40 Pips... if you capture 60 pip objective, close 80% of the trade and see if it has more room to run」

- **Target 1**：+20 pips（平一筆）
- **Target 2**：+40 pips（平第二筆）
- **Target 3**：+60 pips → 平倉 80%，剩餘追 terminus
- Terminus = premium array（old high / equal highs / bearish OB）
- 若為 swing/position trade，保留部分至 terminus（可能跨日/跨週）

### 金字塔加碼（Pyramiding）

逐字稿：「if I have one here and goes about halfway or a little bit less and pulls back down then I know I have a chance to Pyramid... 10 contracts... then five here... and two or three」

- 前提：市場已運行至不超過 stage 1 到 terminus 距離的 50%
- 若已超過 50% 則**不可加碼**（只有一個 stage of accumulation）
- 範例：首單 10 contracts → stage 2 加碼 5 → 最終加碼 2–3

---

## 具體參數

### 時間框架對應（Top-Down Fractal）

| Stage（展開框架）| Setup 出現的框架 | Entry Pattern 框架 |
|---|---|---|
| Weekly | Daily / 4H | 4H |
| Daily | 4H / 60min | 60min / 15min |
| 4H | 60min / 15min | 15min / 5min |
| 60min | 15min | 5min / 1min |

逐字稿：「higher time frame is going to be the stage... setup is going to be on your lower time frame... entry pattern will be found on the next lower」

### 關鍵百分比

- Stage 1 reaccumulation 位置：整體預期區間的 **20–30%** 處（從起點量起）
- Stage 2 判斷閾值：回撤至 stage 1 以下（stage 1 低點被破）
- 單一 stage 判斷：若 terminus 剩餘 **≤ 30 pips**，只有一個 reaccumulation stage
- 若 terminus 剩餘 **10–20 pips** 或 **30 pips**：使用 stop sweep 過濾器（逐字稿：「10 20 or 30 pip stop sweeps」）

### Fib 水平

逐字稿：「FIB projections like 127 or 168 extensions... if they start aligning with that premium array」
- 用於 stage 2 reaccumulation 時確認 terminus 的精確度
- 若 1.27 或 1.68 extension 與 premium array 重合 → 高度確認的進場

### Dealing Range 回顧期

- Scalp / 日內：**20 個交易日**
- Daily setup：**40 個交易日**（有時 60）
- Weekly setup：**60 個交易日**

### 進場參數（來自 Trade Plan 影片）

- 進場確認時間框架：**5 分鐘** 或 **15 分鐘** chart 上的 discount FVG
- Standard deviation 限制：**-3 standard deviations** 以內（不超過 -3 SD）
- Buy limit offset：PD array 收斂點 **+ 5 pips**

### 停損

- 固定：discount array 低點 **- 20 pips**
- 範例計算（Trade Plan）：$20,000 帳戶 × 1.5% = $300 風險；20 pip 停損；micro lots $0.10/pip → 可開 150 micro lots

### 出場目標（pips）

- TP1：**+20 pips**
- TP2：**+40 pips**
- TP3：**+60 pips**（達到後平 80%，剩餘追 terminus）

### 帳戶風險規則

逐字稿：「if your demo account takes a loss on a trade and is at a full R percent... drop your R percent by 50% and when the loss is recovered by 50% you're permitted to return to the maximum r%」

- 單筆最大風險：依個人設定（範例用 1–2%）
- 多筆訂單分攤：風險 % ÷ 訂單數（例如 2% ÷ 4筆 = 0.5%/筆）
- 虧損後：R% 降低 50%，直到虧損回復 50% 才恢復原始 R%
- 連勝 5 筆後：主動降低 R% 50%（預防即將到來的虧損）

---

## 時段規定（Killzone）

逐字稿：「London open or New York open kill zones」、「New York open and I'll be honest with you when I look at the market for the last year everything I've done on Twitter publicly this is the model I've used」

- **主要進場時段**：London open kill zone 或 New York open kill zone（New York 時間，具體小時數逐字稿未明確給出精確邊界——字幕不清）
- Stage 1 reaccumulation 傾向在 **London** 形成，stage 2 在 **New York** 形成（4H 框架範例）：
  逐字稿：「if we started the move in London and we haven't met where we anticipate stage two reaccumulation we can look for New York to create a continuation」
- 日內買入窗口：**Monday、Tuesday、Wednesday**（逐字稿：「framing out one shot one kill with the weekly idea... look for one shot one kill for Monday, Tuesday, or Wednesday」）
- 週高點傾向：**Thursday New York open** 形成高點（逐字稿：「Wednesday anticipate a run up into Thursday creating the high generally Thursday New York open and then the reversal」）
- **Friday** 或 **Monday** 可能設置下一段買入機會

---

## 風控規定

逐字稿摘要（yC-gQhvexGg）：

1. 使用 **demo account** 執行（Trade Plan 影片明確要求，字幕：「we will execute with our demo account」）
2. 停損設定：進場前決定，不可跳過
3. 虧損後立即降槓桿（R% × 50%），不可頻繁重進場——但逐字稿明確允許「重進場」：「we will re-enter if the trade stops out, we can monitor it for secondary entry, day trades may require multiple attempts」
4. 連贏 5 筆後主動降低 R% 50%，防止回落
5. 不強迫進場（逐字稿：「I don't want you to feel that I'm inviting you to overtrade... if the setup is there you should be able to identify it」）
6. 停損逐步縮減（見上方停損縮減規則）
7. 不要用 standard lot 操作，建議 mini lots（更靈活分批出場）

---

## 對「NQ 1分K、NY 開盤後3小時自動交易」的適用性

### 可適用性評估

**正面因素**：
- 逐字稿在 Algorithmic Theory 影片中明確提到可用於 **1分鐘 chart**（「here's the one minute chart... same consolidation... first stage accumulation, second stage reaccumulation」），並示範 15 秒 chart 亦可使用同一框架
- NY open 是明確指定的 kill zone 進場時段
- 使用 buy limit order（可機械化設定）
- 停損 = PD array 低點 - 20 pips（可量化）
- 出場 TP1/TP2/TP3 = +20 / +40 / +60 pips（可量化）
- 模型明確支援 S&P e-mini Futures 日內框架（NQ 同類）

**挑戰／主觀判斷部分**：
1. **識別 Market Maker Model 的類型**（Sell Model vs Buy Model）：需要高時間框架判斷，難以純機械化；需要 4H/daily 的 context
2. **識別 terminus（premium array）**：需要判斷 old high / bearish OB / FVG above，無固定公式
3. **判斷 stage 1 vs stage 2**：依賴 30-pip 過濾規則（可機械化）+ 整體框架位置（需主觀判斷）
4. **Dealing range 設定**：20日 highest/lowest 可程式化計算
5. **Standard deviation 計算**：-3 SD 收斂（可量化，但需知道是哪種 SD——字幕不清具體計算方式）

### 可機械化的規則

| 規則 | 機械化可行性 |
|------|------------|
| Dealing range（20日 H/L 中點）| 可完全自動化 |
| FVG 識別 | 可自動化 |
| Buy limit = PD array + 5 pips | 可自動化 |
| Stop loss = swing low - 20 pips | 可自動化 |
| TP1 = +20 / TP2 = +40 / TP3 = +60 | 可自動化 |
| 停損縮減（25/50/75% 規則）| 可自動化 |
| 30 pip terminus 過濾器（判斷 stage 數）| 可自動化 |
| Kill zone 時間窗（NY open）| 可自動化 |
| R% 虧損後縮減規則 | 可自動化 |

### 需要人工判斷的規則

| 規則 | 原因 |
|------|------|
| 高時間框架 draw on liquidity 識別 | 需 4H/daily 判斷 premium array 位置 |
| Market Maker Model 類型識別 | 需判斷整體市場結構（buy vs sell model） |
| Seasonal tendency 確認 | 需外部資料（COT data、seasonal charts） |
| Institutional orderflow（bullish/bearish trend）確認 | 需看 4H down-close candles / up-close candles 序列 |

### 結論

Model 6 對「NQ 1分K、NY 開盤後3小時」場景**部分適用**：進場執行規則（limit order、SL、TP1-3）可完全機械化；但上層框架判斷（terminus 識別、market maker model 識別）需要人工設定每日偏見或以更高時間框架規則輔助自動化。最小可行自動化策略：預先在 4H/daily 上標記 draw on liquidity 水平，讓系統在 NY open kill zone 內的 1min FVG 觸發 buy limit 進場。

---

## 關鍵原文引述

1. **模型核心定義**：「buy side low resistance liquidity runs and fractals... the stage is a liquidity draw... the setup is going to be a buy side liquidity draw or buy stops within a market maker profile... the pattern is fair value」（fAcnhdaowME）

2. **Stage 判斷**：「higher time frame tends to give us two opportunities... anything less than 4 Hour it can create just one opportunity to get to the premium array and then it creates the reversal」（fAcnhdaowME）

3. **30 pip 過濾器**：「if your Terminus is predetermined here... if we rally up and leave 30 Pips or less when it starts to consolidate there isn't going to be a second one so whatever you're going to do for your trade do it all on that one entry」（fAcnhdaowME）

4. **進場條件**：「we will frame a long entry when price has moved down into a 15 or five minute discount fair value gap PD that converges with a standard deviation of no more than -3 standard deviations during London open or New York open」（yC-gQhvexGg）

5. **停損規則**：「we will place our stop loss below this low minus 20 Pips」（yC-gQhvexGg）

6. **1分鐘框架明確適用**：「here's the one minute chart... smart money reversal lowrisk buy, accumulation, reaccumulation second stage and then you see the extrapolated price run... the buy side is targeted there」（beTnmkbuUjg）

7. **Pyramiding 條件**：「if I have one here and goes about halfway or a little bit less and pulls back down then I know I have a chance to Pyramid... if it runs up at least above 50% of the run... then it retraces I'm going to assume at that moment that we're only going to have one stage of accumulation that means I can't do any pyramiding」（beTnmkbuUjg）

8. **模型定位宣言**：「this model is you know the closest thing to what I actually doing in my trading without actually giving you my actual trading model」（beTnmkbuUjg）
