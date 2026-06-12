# Model 4 — Position Trading：季度轉換與季節性傾向

## 影片清單

| 影片 ID | 標題 |
|---------|------|
| 2CWIbdP1kZw | ICT Charter Price Action Model #4 Position Trading |
| SObhjCvXCNk | ICT Charter Price Action Model #4 Supplementary Lesson |
| H05w52zQGdQ | ICT Charter Price Action Model 4 — Trade Plan & Algorithmic Theory |

---

## 模型定位

- **交易風格**：Position Trading（倉位交易），持倉週期數週至數個月，最短目標為抓住月份範圍內的一至四週波段
- **主要時間框架**：Monthly（月線）→ Weekly → Daily → 4-Hour（輔助進場精化）
- **進場精化最低時間框架**：15-minute（機構訂單流程進場）；可下鑽至 1-minute（scalping 精化停損）
- **適用市場**：原始例子為 GBP/USD（British Pound Futures，代碼 B6）；第三支影片補充 EUR/USD；ICT 明確說可延伸至任何具有清晰 seasonal tendency 的主要貨幣對與商品
- **核心驅動**：Quarterly Shift（每約三個月出現一次的主要方向性轉換）+ Monthly Seasonal Tendency（月份季節性傾向）
- **目標**：每筆交易目標 **500 pips 以上**；ICT 說 GBP/USD 五月季節性傾向平均約 500 pips 下跌
- **R：R 目標**：例子中達到 5:1、8:1、7:1，進場精化後可達到 10:1 以上（見具體參數）

---

## 核心概念定義

### Quarterly Shift（季度轉換）
逐字稿：「every three months there's going to be a significant quarterly shift and price swing」。指每約三個月，市場會形成一次顯著的方向性轉換與價格擺動。不是每個貨幣對每次都會出現。

### Seasonal Tendency（季節性傾向）
逐字稿：「a general rule of principle in terms of direction... what generally happens more often than not」。指特定月份或季度市場傾向於朝某方向移動的統計規律，擁有 40 年以上數據支持（以英鎊五月為例）。不是 100% 保證，是高概率路線圖。不鎖定在特定日曆日，有時提前或延後數天到一週啟動。

### COT Hedging Program（承諾交易者對沖程式）
ICT 自行詮釋的 COT 應用方式，與傳統 COT 讀法不同。具體操作：
1. 只關注 **Commercials（商業交易者）** 那條線，忽略 large speculators 和 small specs
2. 取 **過去六個月** Commercials 淨部位的最高值與最低值
3. 以這個六個月範圍的中點為分界，中點以上 = 淨多（綠色陰影），中點以下 = 淨空（紅色陰影）
4. 若 Commercials 目前在六個月範圍的高端（淨空極值）→ 偏空；在低端（淨多極值）→ 偏多
5. 免費資源：barchart.com（互動圖，可隱藏 large specs）或 cotbase.com

### IFPD Data Range / EPOD Data Range（字幕出現多種拼法，均指同一概念）
逐字稿：「determining the ITA data range for the last 20 40 and... 60 trading days」。
指往回計算 **20、40、60 個交易日**（不計週日）的最高高點與最低低點，構成當前的 Dealing Range。這是模型的基礎定位框架。

### External Range Liquidity（外部範圍流動性）
指在 IFPD Data Range 之外的舊高或舊低，即市場需要超過目前 20/40/60 日高低點才能到達的流動性。在 Model 4 中作為進場觸發（買方流動性被掃出 → 轉空；賣方流動性被掃出 → 轉多）。

### SMT Divergence（Smart Money Technique Divergence）
有兩種形態：
1. **Correlated Pair SMT**：例如 GBP/USD 創新高，但 EUR/USD（同方向的相關對）未能同步創新高 → SMT 背離，確認 GBP 高點是操縱性假突破
2. **USDX SMT**：GBP/USD 創新高（即 USD 應創新低），但 DXY 未能創新低（反而創高低點）→ SMT 背離

### Judah Swing（猶大擺動）
逐字稿：「this is a Judah swing ... a turtle soup sell you know false breakout ... this is pairing orders with buy side liquidity」。指刻意製造的假突破擺動（Non-Farm Payroll 等高波動事件常作為觸發），用來在舊高上方配對機構空單的流動性。等同 Turtle Soup / Stop Run。

### Dealing Range（交易範圍）
以初始賣出信號的那根 K 線高點到低點定義。具體定義：「the initial sell signal right here once this sell signal happens and it starts to deliver price on the downside that is where you start and you define the dealing range」。只有在 Dealing Range 上半段（Premium 區）才可加倉或新進場；下半段（Discount 區）勝率下降。

### Offset Distribution（偏移分配）
逐字稿：「finding that low and then waiting for the price to go down below once more」。市場先打破一個短期低點，整固/小幅回調（引誘買盤、在下方積累新的 sell stops），然後再次突破更低 → 以新生成的那個低點下方作為目標出場。

### Premium / Discount PD Array
Premium = 高於 Dealing Range 中點（放空區）；Discount = 低於中點（做多區）。Model 4 空頭進場必須在 Premium 區，具體對應到 4-Hour Premium Fair Value Gap。

---

## 進場模型完整流程

### 空頭版本（以 GBP/USD 五月為例；多頭版本邏輯相反）

#### 第一步：前置條件確認（每年年初或季初規劃）
1. 確認目標月份有強烈 **bearish seasonal tendency**（例如英鎊五月）
2. 拉出 COT Hedging Program（六個月回看），確認 Commercials 在六個月範圍處於 **淨空極端**（即圖表上半段紅色陰影）
3. 在年曆上標記每個月最佳季節性傾向的市場，建立每月觀察名單

#### 第二步：建立 IFPD Data Range
1. 從當日起往回數 20、40、60 個交易日（不計週日）
2. 找出每個範圍的 **最高高點（old high）** 和 **最低低點（sell-side liquidity pool）**
3. 確認潛在利潤空間 ≥ 500 pips（通常需要 60 日範圍才夠）

#### 第三步：Setup 形成條件（所有條件必須同時滿足）
1. 市場在 20/40/60 日範圍內**突破一個舊高**（至少超過一個 pip）
2. 同時出現 **SMT Divergence**（相關對或 DXY 未能同步確認）
3. 突破發生在 **seasonal tendency 啟動窗口**（以英鎊五月為例：四月最後一週至六月第二週）
4. COT 仍顯示 Commercials 淨空極端

#### 第四步：進場觸發（兩種方式）

**方式 A — 位置交易者掛單方式（不需要盯盤）**
- 找到突破舊高的那根 K 棒（Daily 圖）
- 找到「最後一根上升收盤 K 棒（last up-closed candle）」= 即 Bearish Order Block 的開盤價
- 在該開盤價**掛 Sell Stop 訂單**（賣入停損，等市場下來觸發）
- 停損放在突破高點上方（第一支影片範例：130 pips 停損）

**方式 B — 精化進場（4-Hour 圖 + FVG，停損縮至約 50 pips）**
- 在 4-Hour Premium Fair Value Gap 收斂位置進場
- 確認進場點在 Dealing Range 中點以上（Premium 區）
- 進場方式：Sell Limit，入場價 = 標準差收斂點 **減 5 pips**
- 停損 = 進場相關高點 + 25 pips
- 可進一步下鑽至 15-minute 圖找 Institutional Order Flow Entry Drill 精化

#### 第五步：停損位置
- **方式 A**：突破高點上方（影片例子：130~145 pips）
- **方式 B（精化）**：相關 Premium PD Array 高點 + 25 pips（影片例子：約 50 pips）
- 停損管理：
  - 達到預期目標 25% → 停損縮小 25%
  - 達到預期目標 50% → 停損縮小 50%
  - 達到預期目標 75% → 停損移至 **損益平衡點**（BE）

#### 第六步：停利與出場管理
- **第一目標**：100 pips（一筆訂單退出）
- **第二目標**：250 pips（一筆訂單退出）
- **第三目標**：500 pips（**在此點關閉 80% 的剩餘倉位**，只留 20% 讓其繼續運行）
- **最終目標**：IFPD Data Range 內的 sell-side liquidity pool（20/40/60 日最低低點，或其下方的舊低）
- 觀察 Offset Distribution：等市場在短期低點下方整固後再次突破，以新低作為最終目標
- 如果市場仍在 seasonal tendency 窗口內且流動性未被完全清除，可繼續持倉

#### 第七步：加倉規則（Pyramiding）
- 只在 Dealing Range **中點以上（Premium 區）** 加倉
- 加倉比例遞減（例：第一次 5 口 → 第二次 3 口 → 第三次 1 口）
- 任何時候所有倉位的總風險不超過預設最大風險（例如 1%）

---

## 具體參數

### 時間參數
- **IFPD Data Range**：20、40、60 **交易日**（不計週日）
- **COT 回看期**：**6 個月**（也提到 12 個月與多年，但主要應用是 6 個月）
- **季節性傾向窗口（英鎊五月空頭範例）**：四月中旬至六月第二週（約 8 週窗口）；ICT 偏好使用四月最後一週至六月第二週；嚴格版：僅四月最後一週起
- **Quarterly Shift 頻率**：每約 **3 個月**
- **每年規劃時間**：十二月耶誕假期或一月前兩週

### Pip / Price 參數
- **最小目標**：500 pips
- **英鎊五月季節性傾向歷史平均**：約 500 pips
- **停損範例（Daily 方式 A）**：130~145 pips
- **停損範例（4H 方式 B 精化）**：約 50 pips
- **第三支影片精化停損標準**：入場點相關高點 + **25 pips**
- **偏多進場 Sell Limit 偏移**：PD Array 標準差收斂點 - **5 pips**
- **偏空進場 Buy Limit 偏移**：PD Array 標準差收斂點 + **5 pips**

### RR 參數
- 第一支影片（GBP 方式 A）：5:1（第一目標）、8:1（最終目標）
- 第二支影片（GBP 方式 B 精化）：10:1 以上
- 第三支影片（EUR/USD）：7:1（單目標），若風險 2% 則單筆獲利可達 14%

### 百分比 / 風控參數（見風控規定章節）

### Fibonacci / 標準差
- 進場條件：「4-Hour premium fair value gap PD that converges with a standard deviation of no more than plus three standard deviation」（空頭）；「no more than -3 standard deviation」（多頭）
- 具體 Fib 水平未在逐字稿中提及（字幕不清）

### 第三支影片 EUR/USD 具體數字範例
- 進場：1.10865
- 停損：1.11850（約 985 pips？字幕標示為「pipets」= pipettes，即 0.1 pip 單位，實際停損約 98.5 pips）
- 目標：1.04 大整數關口

---

## 時段規定（Killzone）

Model 4 主要是 **Daily/Weekly** 級別的倉位模型，對於初始進場（方式 A）**不需要特定的盤中時段**（ICT 明確說「we don't need to get up and look at kill zones」）。

但對於精化進場（方式 B），逐字稿明確提到：

| 條件 | 時段 |
|------|------|
| 空頭精化進場 | London Open 或 **New York Open** Kill Zone 期間的 retracement higher |
| 多頭精化進場 | London Open 或 **New York Open** Kill Zone 期間的 retracement lower |
| 多頭週 LOD 形成窗口 | **週二**（70% 機率）；備用：週一或週三 New York Open 前後 |
| 空頭週 HOD 形成窗口 | **週一、週二或週三** European Open 附近（逐字稿：「note the European opening price on Monday Tuesday or Wednesday」）|
| 使用 15-minute 進場 | IOF Entry Drill 在上述 Kill Zone 內執行 |

注意：逐字稿中提到「Tuesday creates a low of the week when the market is bullish... 70% chance」；FOMC 前的週二需特別注意。

---

## 風控規定

逐字稿中明確提到的風控規則：

1. **基礎最大風險**：建議 **1%** per trade（ICT 說對新手 1% 不應超過；自身使用 3.5% 但不建議複製）
2. **停損後降低 R%**：任何一筆全額虧損後，**將 R% 降低 50%**，直到虧損回收 50% 後才可恢復原始 R%
3. **連勝後降低 R%**：連續五筆獲利後，**將 R% 降低 50%**（防止均值回歸大虧損破壞資金曲線）
4. **加倉限制**：只在 Dealing Range Premium 區（中點以上）加倉；加倉量遞減（5→3→1 口）
5. **部分出場**：達 500 pips 目標時 **必須關閉 80% 倉位**，只留 20% 繼續持有
6. **總風險上限**：加倉後所有倉位的總風險不得超過個人最大 R%
7. **反覆嘗試**：「position trades may require multiple attempts to secure a solid entry do not fear this」—— 停損後可重新進場

---

## 對「NQ 1分K、NY 開盤後3小時自動化交易」的適用性

### 直接評估

**Model 4 整體不適合直接套用於 NQ 1分K NY 開盤 3 小時自動化交易場景。** 原因如下：

1. **時間尺度完全不同**：Model 4 以 Daily/Weekly/Monthly K 棒為決策框架，目標 500 pips（外匯），持倉數週至數月。NQ 1 分 K 是日內 scalp 場景，時間尺度差距達 3~4 個數量級。
2. **市場不同**：Model 4 所有範例均為外匯（GBP、EUR）。NQ 是股指期貨，雖然 ICT 原則可通用（ICT 說「it doesn't have to be a currency」），但 seasonal tendency、COT 數據等需重新校準，且逐字稿中未提及 NQ 的具體參數。
3. **季節性傾向評估週期**：COT 6 個月回看、每年規劃一次 → 非適合日內自動化的週期性邏輯。

### 可從 Model 4 提取並機械化用於 NQ 1 分 K 的元素

| 元素 | 可機械化程度 | 說明 |
|------|-------------|------|
| IFPD Data Range（20/40/60 日高低點）計算 | ✅ 高 | 純計算，可演算法化 |
| 進場觸發：突破舊高 + 回落至 last up-closed candle open | ✅ 高 | 可翻譯為 K 棒邏輯條件 |
| FVG 精化進場（4H Premium FVG）| ✅ 中 | 可縮小到 1M/5M 時間框架的 FVG 邏輯 |
| 停利分段出場（100/250/500 pips，或對應 NQ 的 handles 目標）| ✅ 高 | 純訂單管理邏輯 |
| 停損在高點 + N pips | ✅ 高 | 參數化停損 |
| 停損縮小規則（25%/50%/BE at 75%）| ✅ 高 | 可實作為追蹤停損邏輯 |
| New York Open Kill Zone 時段過濾 | ✅ 高 | 時間條件 |

### 主觀判斷、無法直接機械化的元素

| 元素 | 問題 |
|------|------|
| COT Hedging Program 讀取 | 需人工每週評估 Commercials 六個月範圍；非即時數據 |
| Seasonal Tendency 選擇 | 每年年初人工規劃，非演算法決策 |
| SMT Divergence 確認 | 需同時監看相關對（NQ 對應什麼相關對？逐字稿未提） |
| Quarterly Shift 時機判斷 | 「every three months or so」不精確，需主觀確認 |
| Judah Swing / 操縱識別 | 需結合多個背景條件主觀確認 |
| Offset Distribution 目標形成 | 需等待短期低點形成後才能確認（非預設目標）|

### 建議

若目標是 NQ 1 分 K NY 開盤後 3 小時自動化，Model 4 的框架元素（FVG 進場、IFPD 高低點作為流動性目標、分段停利、NY Open Kill Zone 觸發）可作為 **更短週期模型（如 Model 1、2、3）的輔助過濾層**，但 Model 4 本身不是合適的主執行模型。

---

## 關鍵原文引述

1. > "every three months there's going to be a significant quarterly shift and price swing not every single currency is going to have that unfold"

2. > "when GBP USD or cable runs an old high inside a 20 40 or 60-day iPad dat range and there is a smt Divergence in either the dollar Index or the euro dollar ... we look to short the open of the last up closed candle on a stop"

3. > "the month of May that monthly range we expect it to expand lower have a strong impulse move lower inside that monthly range or candle there are four weekly ranges or candles all we're trying to do is we're seeking some range inside that monthly range before the candle completes"

4. > "you can only add or enter at the midpoint or higher when price is in a premium and you can only pyramid when it's in a premium down here the probabilities fall off precipitously"

5. > "if you capture a 500 pip objective make sure you close 80% of the trade ... then see if you have any more room to run in price"

6. > "when we are bearish we will frame a short entry when price has moved up into a 4-Hour premium fair value Gap PD that converges with a standard deviation of no more than plus three standard deviation during London or New York open"

7. > "if you take a series of five winning trades in a row drop your r% by 50% you're likely to assume a loss eventually and this will build in equity leveling and reduce the likelihood of a large draw down"

8. > "it's bullish bearish foreign currency using seasonal tensy April look at your seasonal tensy for your dollar it's exactly what you're seeing here folks right out of that page that I gave you those are treasure maps"
