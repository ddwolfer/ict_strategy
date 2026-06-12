# Model 2 — 短期週範圍交易模型（Short-Term Weekly Range）

## 影片清單

| ID | 標題 |
|---|---|
| s1gCDuzcukU | ICT Charter Price Action Model 2 – Amplified Lecture |
| KQdsa7S1LoQ | ICT Charter Price Action Model 2 – Trade Plan & Algorithmic Theory |

---

## 模型定位

- **時間框架**：Weekly（方向偏向）→ Daily → 1H（或 15m 計時用）→ 5m（進場執行）
- **交易風格**：Short-term swing；持倉橫跨 Tuesday 至 Thursday NY open（最多約 2.5 天）
- **適用市場**：逐字稿以 Forex（Dollar/CAD、Euro/USD、GBP/USD）為例，概念可移植至其他市場
- **目標**：每筆交易 **50–100 pips**；達到 100 pips 立刻平倉，不貪
- **核心邏輯**：不嘗試捕捉完整週範圍，只取 Tuesday 4:00（Eastern Standard Time）→ Thursday NY open 這段「週中精華」；以週線判方向，以日線/小時線找 PD array，以分鐘線計時進場

---

## 核心概念定義

### 週方向偏向（Weekly Directional Bias）
必須先在週線圖上確立多/空偏向。判斷依據為三組 PD array：
- **多頭**：價格上方存在 Buy-side Liquidity Pool（舊高）、Fair Value Gap（FVG）、舊高
- **空頭**：價格下方存在 Sell-side Liquidity Pool（舊低）、FVG、舊低

### 20-Day IPA Data Range（Dealing Range）
往前數 **20 個交易日**（不計 Sunday），記錄最高高與最低低，定義為當前 Dealing Range。若 20 日內已雙向都走完、找不到乾淨 PD array，則延伸至 40 日，再延伸至 60 日；60 日仍找不到則換市場或觀望。

### Tuesday 4:00 Opening Price（主要進場基準）
使用 **Eastern Standard Time（EST）4:00**（固定不隨日光節約時間移動）的開盤價作為週內偏向過濾器：
- 多頭週：在此價格**之下**買進
- 空頭週：在此價格**之上**放空

> 當 Daylight Saving Time 生效時，EST 4:00 ≡ 紐約時間 5:00，但 ICT 明確表示**忽略夏令時，固定用 4:00（EST Standard）**。

### European Open / 6:00 Opening Price（反轉市場 / 輔助基準）
使用 **EST 6:00** 的開盤價；適用場景：
1. 當模型已達到多週目標（Premium / Discount array），**轉換為反轉 Market Profile** 時
2. 作為 4:00 基準的替代篩選器，精確度有時更高

### Asian Range（亞洲時段範圍）
定義：**Midnight（00:00 EST）→ 08:00 EST** 的高低範圍。
用途：
- 多頭：等價格突破 Asian Range High 後，於 2:00 AM EST 後放一個 Buy Stop 在 Asian Range High + 1 pip（「懶人進場」替代方案）
- 空頭：等價格拉到 Asian Range High 之後，在 Asian Range Low 下一個 Sell Stop（Asian Range Low − 1 pip）於 2:00 AM EST 後

> 賣出 breakout 須在 2:00 AM EST **之後**確認，Asian Range Low 被突破才算有效進場信號。

### Standard Deviation 限制（Max 3 SD）
使用 Asian Range、Central Bank Dealers Range 或 FLOUT 做 SD 投影時，進場點所在的 Premium / Discount array **不得超過 3 個標準差**，超過即不進場。

### Judas Swing（猶大擺盪）
進場前需出現的反向快速走勢（Market Protraction）：
- 多頭進場前，先看到急跌
- 空頭進場前，先看到急漲

### Consequent Encroachment
FVG 或 Imbalance 的 **50% 水準**，即價格重平衡的第一目標位。

### Optimal Trade Entry（OTE）
在 Dealing Range 高點到低點之間，**62%–70.5% Fibonacci 回調**區間（逐字稿提及 62% 與 79%，79% 為超出 Imbalance 邊緣的非理想位置）。

### Rejection Block
週線 Swing Low 蠟燭（尾巴蠟燭）的 Open 到 Low 範圍，取 50% 作為精準價位。

---

## 進場模型完整流程

### 前置條件（Preparation）
1. 週末查閱**經濟日曆**，標記當週所有中高影響力新聞事件
2. 以週線 Power of Three（AMD）判斷本週預期為多/空（Close 預計高於或低於週開）
3. 計算 **20-day Dealing Range**（往前 20 交易日，排除 Sunday，取最高高與最低低）
4. 若 20 日無乾淨 PD array → 延伸 40 日 → 60 日 → 換市場
5. 在 Dealing Range 內找**下一個 Draw in Liquidity**：
   - 多頭 → 上方的 Buy-side Liquidity / Old Daily High / FVG
   - 空頭 → 下方的 Sell-side Liquidity / Old Daily Low / FVG

### Setup 形成條件
- **不交易 Monday**（Model 2 明確規定）
- Tuesday 或 Wednesday 方為有效進場日
- 若 Tuesday 沒有給到進場機會，則等 Wednesday（規則完全相同，把 Tuesday 換成 Wednesday）
- Setup 須在 London Open 或 New York Open Kill Zone 內形成

### 觸發條件（多頭標準版）
- 價格在 4:00 EST Tuesday Opening Price **之下**
- 出現向下的 Judas Swing（Market Protraction lower）
- 價格跌入 **15 分鐘 Discount PD array**（FVG / OB / OTE 區間）
- 該 PD array 與 Asian Range 或 Dealers Range 的標準差投影**在 5 pips 以內收斂**
- 標準差投影不超過 3 SD

### 觸發條件（空頭標準版）
- 價格在 4:00 EST Tuesday Opening Price **之上**
- 出現向上的 Judas Swing
- 價格漲入 **15 分鐘 Premium PD array**
- 該 PD array 與 SD 投影在 5 pips 以內收斂
- 不超過 3 SD

### 進場方式

**標準版（限價單進場）**
- 多頭：Buy Limit 在 SD + PD array 收斂點 **+ 5 pips**（加 5 pips 係因 spread 因素）
- 空頭：Sell Limit 在 SD + PD array 收斂點 **− 5 pips**

**替代版（停損單進場，"懶人進場"）**
- 多頭：2:00 AM EST 後，等 Asian Range High 被突破，於 Asian Range High 放 **Buy Stop + 1 pip**
- 空頭：2:00 AM EST 後，等 Asian Range High 被突破（Judas Swing 確認），於 Asian Range Low 放 **Sell Stop − 1 pip**；等破 Asian Range Low 被觸發進場

### 停損位置
- 標準版（Limit Order 進場）：進場點上方/下方 **+ 25 pips**
- 替代版（Stop Order 進場）：當日最高/最低點 **+ 50 pips**

### 停利 / 出場管理
1. **第一目標**：50 pips → 第一筆部位平倉
2. **第二目標**：75 pips → 第二筆部位平倉
3. **最大目標**：100 pips → **全部立刻平倉，交易結束**
4. **時間截止**：**Thursday NY Open**（無論盈虧，到點必須出場）
   - 即使尚未達到 50 pips，到點也關
5. **追蹤停損規則**（Trailing Stop Protocol）：
   - 盈利達預期目標的 25% → 停損移動縮小 25%
   - 盈利達 50% → 停損縮小 50%
   - 盈利達 75% → 停損**必須移至保本（break even）或以上**
6. **停損後不補單**：一筆一筆，One and Done。停損出場後可繼續觀察但不再進場

---

## 具體參數

| 參數 | 數值 |
|---|---|
| 進場日 | Tuesday 或 Wednesday（不交易 Monday） |
| 方向基準開盤時間 | EST 4:00（固定 Standard Time，不調整 DST） |
| European Open 時間 | EST 6:00 |
| Asian Range 定義 | Midnight 00:00 → 08:00 EST |
| 替代進場啟動時間 | 2:00 AM EST 之後 |
| 最大 SD 進場上限 | 3 standard deviations（Asian Range / Dealers Range / FLOUT） |
| 標準版停損 | + 25 pips（相對進場點） |
| 替代版停損 | + 50 pips（相對進場點） |
| 第一停利 | 50 pips |
| 第二停利 | 75 pips |
| 最大停利（強制平倉） | 100 pips |
| 交易截止時間 | Thursday NY Open |
| 週目標範圍 | Tuesday 4:00 → Thursday NY Open（週中精華段） |
| Fibonacci OTE 區間 | 62% – 70.5%（逐字稿提及 62% 與 79%，79% 為邊界） |
| Dealing Range 回看 | 20 日（不足則 40 日 → 60 日） |
| PD array 收斂容許誤差 | 5 pips 以內 |
| 風險 R%（示範值） | 1.5%（示範帳戶 $20,000，stop 20 pips） |
| 停損後 R 縮減規則 | 連虧後 R 減半；連贏五筆後 R 亦主動減半 |
| 五級整數 / 零級校準 | 取最近 0 或 5 結尾的整數位（四捨五入至 5 pip 格）|

---

## 時段規定（Killzone）

| 時段 | EST（Standard Time） | 用途 |
|---|---|---|
| Asian Range | 00:00 – 08:00 | 定義 SD 投影基準 |
| 替代進場啟動 | 2:00 AM | 亞洲 Stop 進場的最早時間 |
| European Open | 6:00 AM | 反轉 Profile 基準；進場計時篩選器 |
| London Open Kill Zone | ~6:00 – 9:00（字幕不清，提及延伸至 9:00）| Setup 形成主窗口 |
| New York Open Kill Zone | 逐字稿提及 "11:00 – 13:00 EST"（標準時） | Setup 形成主窗口；+1 hr 夏令 = 11:00–14:00 |
| 出場截止 | Thursday NY Open | 無論盈虧強制平倉 |

> 逐字稿明確說明：Kill Zone 時間**不隨夏令時調整**，夏令時只在後端加 1 小時（如 NY Kill Zone 11–13 → 11–14），不移動前端起始時間。

---

## 風控規定

1. **Model 2 限 Demo 帳戶**（逐字稿多次強調，ICT 不建議直接用真實帳戶）
2. 停損出場後**不補單**（One and Done）
3. 連虧一筆 → R% 減半，直到虧損回收 50% 才恢復
4. 若縮小後的 R% 再虧 → 再減半
5. **連贏 5 筆 → 主動將 R% 減半**（避免大回撤，維持平滑資金曲線）
6. 倉位計算公式：`Position Size = (Account Equity × R%) ÷ (Stop in pips × pip value)`；永遠**向下取整**（round down）
7. 建議選能交易 Mini / Micro Lot 的券商，以便精確調整倉位

---

## 對「NQ 1分K、NY 開盤後 3 小時自動交易」的適用性

### 場景差異分析
| 維度 | Model 2 原設計 | NQ 1m NY 開盤場景 |
|---|---|---|
| 持倉週期 | Tuesday → Thursday NY Open（~2.5 天） | NY 開盤後 3 小時內（日內） |
| 時間框架 | Weekly + Daily + 1H/15m | 1m 執行，需對應更高 TF 偏向 |
| 計量單位 | Pips（Forex） | Handles/Ticks（Futures NQ） |
| 進場日 | Tuesday / Wednesday | 任何交易日 |

### 可機械化的規則

| 規則 | 演算法化難度 |
|---|---|
| Asian Range（00:00–08:00 EST）高低計算 | 低 — 固定時間窗，自動取 H/L |
| 2:00 AM EST 後放 Stop 進場（Sell Stop / Buy Stop） | 低 — 條件單 |
| European Open 6:00 EST 開盤價計算 | 低 — 固定時間 |
| 4:00 EST 開盤價計算 | 低 — 固定時間 |
| 最大 3 SD 過濾（SD 投影上限） | 中 — 需先計算 Asian Range SD |
| 50 / 75 / 100 pip 停利梯 → 對應 NQ Handles 換算 | 中 — 固定數字，需換算 |
| 停損 25 / 50 pip（標準 / 替代） | 低 |
| Thursday NY Open 強制出場（時間截止） | 低 |
| 追蹤停損 25%-50%-75% 規則 | 中 |
| 20-day Dealing Range 計算 | 低 |

### 主觀判斷成分

| 要素 | 說明 |
|---|---|
| 週方向偏向確立 | 需人工判讀週線 PD array；可規則化為「上週收在哪裡、下一個 Draw 是什麼」 |
| Weekly Profile 選擇（結合經濟日曆） | 高主觀性，難以純演算法處理 |
| Premium / Discount PD array 識別 | 需定義 FVG、OB 的機器識別邏輯 |
| Judas Swing 的「信任度」 | 逐字稿坦承這是主觀判斷 |
| 反轉 Market Profile 切換時機 | 主觀，需識別是否已到達長期 Premium/Discount |

### 結論
Model 2 的**時間架構（Asian Range Stop、4:00/6:00 開盤過濾、2:00 AM 啟動）與進出場數字（25/50 pip stop、50/75/100 pip 目標）均可演算法化**。然而原設計是 Forex 週內交易；移植到 **NQ 1m NY 開盤場景**需做以下調整：
- 持倉邏輯從「週內持倉至 Thursday」改為「日內 3 小時窗口」
- Pips 換算為 NQ Handles（1 handle = 4 ticks = $20/contract）
- 週方向偏向仍是前置人工作業（或以規則化的週線趨勢過濾器替代）
- Asian Range Stop 進場邏輯（2:00 AM 後，等 Judas Swing，破 Asian Range Low 放 Sell Stop）**最適合機械化**，且高度契合 NY 開盤前後的市場行為

---

## 關鍵原文引述

1. **模型目標與時間窗**
   > "We are seeking the range within or inside the weekly range between Tuesday 4:00 candle opening price and Thursday's New York open as a minimum objective for time and price theory."

2. **為什麼用 4:00 EST（不調夏令時）**
   > "The 4:00 opening price... in Standard Time Eastern Standard Time that's going to represent the midnight candle in New York... I don't care about 5:00 okay I'm staying on 4:00 because other countries are not going to observe that."

3. **停損與目標數字**
   > "We will place a stop loss above this high plus 25 pips... when we are entering a short we will place a limit order to take 50 pips as our objective on one position, we will place a second limit order to take 75 pips as our second objective. If you capture a 100 pip objective close the trade and be content."

4. **替代進場（Asian Range Stop）觸發條件**
   > "After 2 o'clock in the morning you're waiting for a rally to take out the Asian Range High. Once it does that... you can put a sell stop down here [Asian Range Low]... you're selling weakness once the move has already established the intraday high."

5. **最大 3 SD 過濾**
   > "When we are bearish we will frame a short entry when the price has moved up into a 15-minute premium PD that converges with a standard deviation of no more than three standard deviations."

6. **不交易 Monday**
   > "We do not trade on Monday in this model... the idea starts on Tuesday."

7. **Thursday 出場截止**
   > "Thursday is the day of the week that we have to close based on time, it doesn't matter where you are with the trade okay, if it's more than 50 pips you close it okay, if you ever get to 100 pips even if you do not have time to hold till Thursday New York open — New York open is where you close the trade for this model."

8. **20-day Dealing Range**
   > "We're determining the EPOD data range for the last 20 days, we do not count Sundays, we note the highest high and the lowest low of the past 20 days and this is going to be your current dealing range."
