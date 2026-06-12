# Model 5 — Day Trading: Intraday Volatility Expansions

## 影片清單

| ID | 標題 |
|----|------|
| JN_uaDDZ0rc | ICT Charter Price Action Model 5 — Day Trading: Intraday Volatility Expansions（主課） |
| bcp19tiJZA0 | ICT Charter Price Action Model 5 — Supplementary Lesson |
| NB7Bku099tU | ICT Charter Price Action Model 5 — Trade Plan |
| 2fgXDt3T3XE | ICT Price Action Model 5 — Algorithmic Theory |

---

## 模型定位

- **類型**：Session Day Trading（盤中日內交易），非 swing / 週線交易
- **交易風格**：日內 scalping，聚焦單一交易時段（London open 或 New York open），不持倉跨時段
- **核心框架**：Higher time frame liquidity draw（方向偏差）+ 時段 killzone（時間濾網）+ Standard Deviations / IPA Intraday Volatility Expansions（目標價位）
- **適用時段（優先順序）**：London open Kill Zone > New York open Kill Zone；可延伸至 London close Kill Zone、Asian Kill Zone；North American traders 不易參與 London 者可用 NY session
- **適用市場**：原始教學以 Forex（GBP/USD、USD/CAD、AUD/USD、EUR/USD）為例；邏輯適用於任何 IPA 驅動市場
- **偏好交易日**：週二（最優先）、週三；週四為 wild card，週一與週五在 Trade Plan 中被過濾掉
- **利潤目標**：每筆交易 **40–50 pips**（低端目標 40 pips，平均 50 pips）；ICT 個人周目標 **50–75 pips/週**（有時需 2–4 筆交易達到）

---

## 核心概念定義

### Higher Time Frame Liquidity Draw（HTF 流動性吸引點）
日線圖上最具概率的價格最終去向。主要形式：equal lows（sell stop liquidity pool）、equal highs（buy stop liquidity pool）、rejection block 下方/上方。這是模型的**方向偏差**（bias）來源，決定做多或做空。

### IPA Data Range（20-day Dealing Range）
以最近 **20 個交易日**（不含週日）的最高點與最低點劃定的「當前操作範圍」。這是模型用於確定 draw on liquidity 位置的唯一 IPA 資料範圍。超出此範圍後，下一邊界為 40 天、再來 60 天。

### Standard Deviations（標準偏差展開）
以 Fibonacci Expansion Tool 對特定時間範圍高低點進行測量，向上/向下投影出 1、2、3…等倍數的展開級別，作為**日內價格目標**。關鍵規則：只用 15 分鐘時間框架（bell weather chart）進行測量，不切換 TF。偏差容許範圍：**3–5 pips**。

#### 測量範圍優先序（互斥，依序選擇）

| 優先 | 名稱 | 時間窗（New York 時間） | 最低 pips 門檻 | 過大門檻 |
|------|------|----------------------|--------------|---------|
| 1 | **Central Bank Dealers Range** | 4:00 PM — 8:00 PM NY | **> 15 pips** | （無明確上限，但若呈 trending 非 ranging 則不用） |
| 2 | **Asian Range** | 8:00 PM — Midnight NY | **> 20 pips**（且 ≤ 40 pips 為理想） | > 40 pips 時不建議（改用 flout） |
| 3 | **Flout** | 4:00 PM — Midnight NY（整段合併） | 無下限 | — |

**注意**：若某範圍呈 trending 而非明確盤整，即使 pips 達標也不應使用。

#### Flout 的測量方式
取 4:00 PM — Midnight NY 整段範圍，先用標準 Fibonacci Retracement 找到 **50% 中點（equilibrium）**，然後以上半段或下半段（各半）作為 Fibonacci Expansion Tool 的輸入，投影出以 **50% 為增量**的標準偏差級別（即 0.5 標準偏差、1.0、1.5…），而非使用整段範圍，目的是取得更細密的增量。

### Overlapping Standard Deviations（跨日偏差疊合）
模型最核心的「隱藏要素」：將**前一日**所有有效的標準偏差線段留在圖表上，當「今日標準偏差」某條線與「昨日標準偏差」某條線在 **3–5 pips 以內**相互重合，且發生在 Kill Zone 時間內，此疊合點即為高概率轉折點（進場或獲利了結訊號）。ICT 稱此為「the Grail」。

### Power of Three（P3）
開盤後先出現反向操縱（Judas Swing），製造多方或空方假象後急速反轉，展開真實方向的 range expansion。在日線、週線及日內均適用。

### Session Swings（時段 Swing 高低點）
每個交易時段（London、New York）形成的高點與低點，是識別 P3 及 FVG 的基礎結構單元。

### Premium / Discount Fair Value Gap（溢價/折價 FVG）
- **看空**情境：高概率 FVG（短進場）位於**前一日交易範圍的下半 50%**（lower half of previous daily range）
- **看多**情境：高概率 FVG（多進場）位於**前一日交易範圍的上半 50%**（upper half of previous daily range）

### Institutional Order Flow Entry Drill（機構流進場技術）
5 分鐘圖的精細進場方式。看空進場：使用**最高進場點（highest point of bearish FVG）**，即不等待 gap 完全填補，也不使用 consequent encroachment，而是在 FVG 高端賣出。看多相反。

### Stop Sweep Extension（止損掃盤延伸）
當價格突破一個 intraday swing high/low 時，延伸規則：
- 基本掃盤：**10 pips、20 pips、30 pips** 以上（三個目標等級）
- 若突破整數大關（full figure，如 1.3100）：額外延伸 **40 pips**
- 若突破中間關（mid figure，如 1.3050）：不需額外 40 pips 延伸
- 目標校準：若預期向上突破某個高點，取最近的 5 或 0 結尾整數**向上校準**；若向下突破某低點，向下校準（取最近的 10 或 5 的倍數，且在目標**以上**）

### Low Hanging Fruit Calibration（低垂果實校準）
對於任何已知的流動性目標（old high/low），不追求精確到 1 pip，而是校準至最近的**10 pips 或 5 pips 的整數位**，以確保目標具有高到達概率且考量差價（spread）。

---

## 進場模型完整流程

### 前置條件（Preparation / Bias Formation）

1. **標記 economic calendar**：記錄當週所有 medium 及 high impact 事件，考量事件與市場結構的組合是否支持特定週線形態（weekly profile）。
2. **確定 20-day IPA Dealing Range**：計算最近 20 個交易日（不含週日）的最高高點與最低低點，此為本週操作邊界。
3. **在 Daily chart 確定方向偏差（HTF Bias）**：
   - 識別 20-day range 內的 draw on liquidity（equal highs / equal lows / rejection block）
   - 確認 Power of Three 方向（週線預期是漲還是跌）
   - 確認相關 correlated market（如 DXY）不形成對抗性阻力
4. **選擇交易對與目標**：確認 bias 指向的 PDArray（discount/premium）能提供**至少 40 pips** 空間，否則不進場。
5. **選擇時間**：偏好**週二或週三**；週四視前兩天情況判斷（wild card）；週一與週五**過濾**。

### Setup 形成（Opportunity Discovery）

6. **識別日線 intraday draw**：
   - 看空：確認前一日低點或 intra-week 低點，預期 daily range 向下展開
   - 看多：確認前一日高點或 intra-week 高點，預期 daily range 向上展開
7. **識別 FVG（在 15 分鐘圖）**：
   - 看空：FVG 必須位於前一日 daily range 的**下半 50%**
   - 看多：FVG 必須位於前一日 daily range 的**上半 50%**
8. **識別 European open price（週二）**：
   - 看空：篩選條件為只考慮**在 European open price 以上**的 FVG
   - 看多：篩選條件為只考慮**在 European open price 以下**的 FVG

### 觸發條件（Trade Planning）

9. **等待 Kill Zone 時間窗**：London open Kill Zone 或 New York open Kill Zone（具體時間見下方「時段規定」）
10. **確認 Standard Deviation Confluence**：15 分鐘圖上，FVG/PD Array 的位置必須與標準偏差（≤ 3 個標準偏差）相互疊合；更強的信號是同時疊合**前一日的標準偏差線**（3–5 pips 以內）
11. **確認 P3 Judas Swing**：看空時先看到短暫的向上假突破（buy stop raid / run above old high），然後才反轉向下

### 進場執行

12. **掛 Limit Order（不用市價）**：
    - 看空：Sell Limit，進場價 = PD Array + Standard Deviation 疊合點 **minus 5 pips**
    - 看多：Buy Limit，進場價 = PD Array + Standard Deviation 疊合點 **plus 5 pips**
    - 若同時用多張 limit 單，所有單使用**相同進場價**
13. **在 5 分鐘圖確認精細進場**：使用 Institutional Order Flow Entry Drill，在 FVG 高端（看空）或低端（看多）精確進場，可降低實際風險

### 停損位置

14. **看空停損**：設於 premium array + standard deviation 疊合點對應的**高點以上 +15 pips**
15. **看多停損**：設於 discount array + standard deviation 疊合點對應的**低點以下 -5 pips**
16. **允許再進場**：若被止損，可監控二次進場機會，日內交易可能需要多次嘗試

### 獲利與出場管理

17. **三段式部位管理**（以三張單為例）：
    - **第一張**：40 pips 限價獲利了結
    - **第二張**：50 pips 限價獲利了結
    - **第三張**：抵達 50 pips 後，關閉 **80%**，剩餘 20% 持倉跟蹤進一步走勢
18. **動態停損調整**：
    - 浮盈達預期目標的 **25%** → 停損收緊 25%
    - 浮盈達預期目標的 **50%** → 停損收緊 50%（此時停損仍在虧損側，不強制移到 break even）
    - 浮盈達預期目標的 **75%** → 停損**必須移至 break even**
19. **時段限制**：在 London open 結束前或 New York open 開始前平倉，因為 NY open 通常有反轉/重新蓄力

---

## 具體參數

### 時間參數（均為 New York 時間）

| 參數 | 數值 |
|------|------|
| Central Bank Dealers Range 開始 | 4:00 PM |
| Central Bank Dealers Range 結束 | 8:00 PM |
| Asian Range 開始 | 8:00 PM |
| Asian Range 結束 | Midnight（00:00） |
| Flout 完整範圍 | 4:00 PM — Midnight |
| MT4 日線開盤（用於 P3 參考） | 約 8:00 PM NY（day divider） |
| 次日開盤（另一個重要開盤參考） | Midnight NY（0:00） |
| 每日交易接近結束 | 約 18:00（1800 hour）|

### Pips / Range 參數

| 參數 | 數值 |
|------|------|
| Central Bank Dealers Range 最低 pips 門檻 | > 15 pips |
| Asian Range 最低 pips 門檻 | > 20 pips |
| Asian Range 建議上限 | ≤ 40 pips（超過改用 flout） |
| 標準偏差疊合容許誤差 | **3–5 pips** |
| 傳統 PDA 疊合容許誤差（其他方法） | 約 15 pips（本模型不同，只需 3–5） |
| 每筆交易低端目標 | **40 pips** |
| 每筆交易平均目標 | **50 pips** |
| 週目標（ICT 個人） | 50–75 pips/週 |
| 進場價調整（看空 sell limit） | PDA 疊合點 − 5 pips |
| 進場價調整（看多 buy limit） | PDA 疊合點 + 5 pips |
| 看空停損（高點以上） | + 15 pips |
| 看多停損（低點以下） | − 5 pips |
| Stop Sweep 延伸等級 | 10 pips、20 pips、30 pips |
| Full Figure 突破額外延伸 | + 40 pips |
| Mid Figure 突破額外延伸 | 不適用（無額外 40 pips） |
| 最低 draw on liquidity 空間 | ≥ 40 pips（否則不進場） |

### Fibonacci / 標準偏差目標等級

| 等級 | 描述 |
|------|------|
| SD 1, 2, 3 | 正常目標區間（模型最多使用 3 個 SD） |
| SD 4, 5 | 延伸目標，出現時多為 Confluence |
| SD 7 | 極端延伸（在週四翻轉案例中出現） |
| Flout 測量單位 | 以整段 flout 的 **50% 為一個增量**（SD 0.5, 1.0, 1.5, 2.0… 或使用半段再投影） |

### 三段式利潤管理數字

| 倉位 | 目標 |
|------|------|
| 第一張 | 40 pips 全數平倉 |
| 第二張 | 50 pips 全數平倉 |
| 第三張 | 50 pips 平掉 80%，剩 20% 持倉跑 |

### 動態停損調整

| 浮盈達目標% | 停損收緊幅度 |
|------------|------------|
| 25% | 縮小 25% |
| 50% | 縮小 50%（仍可在虧損側） |
| 75% | **強制移至 break even** |

---

## 時段規定（Kill Zone）

逐字稿中明確提及的 Kill Zone（以 New York 時間為準）：

| Kill Zone | 描述 | 在本模型的用途 |
|-----------|------|-------------|
| **London Open Kill Zone** | 早晨 London 開盤時段（字幕未給出具體開始/結束時間，依 ICT 術語一般為約 2:00 AM — 5:00 AM NY，但本逐字稿未明確給出，需參考其他課程）| **首選進場時段**，可形成當日高低點並啟動 range expansion |
| **New York Open Kill Zone** | NY 市場開盤時段（字幕未給出具體時間）| **次要進場時段**；若 London setup 錯過可用；Thursday NY open 常有 reversal profile |
| **London Close Kill Zone** | London 收盤時段（字幕稱為「London close profit taking kill zone」）| 可用於 continuation 進場或短線 fade；更適合持倉延續而非全新進場 |
| **Asian Kill Zone** | 亞洲時段（約對應 Asian Range 8:00 PM — Midnight NY）| 可用，但非本模型主要時段；適合 North American traders 無法參與前兩時段時使用 |

> 字幕補充：ICT 在 Supplementary Lesson 中展示一個 Asian session setup 範例，說明亞洲時段內的 FVG + bearish order block 組合可提供 40 pips 機會，但強調「not just limited to New York and London」。

---

## 風控規定

### 單筆風險

- 使用 Limit Order（非市價單），明確停損位於 PDA + SD 疊合點**高點以上 15 pips（看空）**或**低點以下 5 pips（看多）**
- 模型鼓勵使用**多張 limit 單**（至少 3 張）進行分批管理，不建議全倉一次性持有
- 若停損觸發，**允許再次進場**（secondary entry）

### 虧損後調整規則

| 事件 | 行動 |
|------|------|
| 單筆完整 R 止損 | 下一筆 R% 減半（50% of original R） |
| 虧損從高點回復 **50%** | 允許恢復原始 R% |
| 連續 **5 筆獲利** | 主動將 R% 減半（為平滑 equity curve，預防即將到來的虧損） |
| 減倉後再次虧損 | 再次減半，直到前次虧損回復 50% |

### 準確率管理（原文含警示）
- 目標準確率約 **65–70%**（不追求 90%+ 顯性表現）
- 理由：Broker 若發現持續高精準度交易，可能會終止帳戶（字幕中 ICT 明確警告，此為 broker 保護機制）
- 建議偶爾在非最佳時間進行低槓桿「煙霧」交易以遮蔽真實交易行為（此段純為原文陳述，僅供記錄）

---

## 對「NQ 1分K、NY 開盤後3小時自動交易」的適用性

### 整體適用評估：**中高度適用，但需要轉換**

**可直接機械化的規則：**
1. **時間濾網**：只在 NY Open Kill Zone 內交易，對應 NY 開盤後約前 1–3 小時 — **完全可算法化**
2. **方向偏差**：Daily chart + 20-day IPA Range 確認方向，一日一次計算 — **可自動化**
3. **FVG 位置篩選**：前一日 range 上半 50% 或下半 50% 的 FVG 判斷 — **可算法化**
4. **Standard Deviation 計算**：依據 Central Bank Dealers Range / Asian Range / Flout 的 pips 門檻選擇，再以 Fib Expansion 計算 — **可算法化，但 Flout 的 50% 半段測量需要明確編碼邏輯**
5. **跨日 SD 疊合偵測**：「前一日 SD 線 ± 3–5 pips 與今日 SD 線相交」— **可算法化**（純數值比對）
6. **進場 Limit 單**：SD + PDA 疊合點 ±5 pips 掛單 — **完全機械化**
7. **停損設置**：高點 +15 pips / 低點 -5 pips — **完全機械化**
8. **三段式獲利**：40 pips / 50 pips / 剩餘 20% — **完全機械化**
9. **動態停損移動**：浮盈 25/50/75% 三個觸發點 — **完全機械化**

**需要主觀判斷或難以算法化的部分：**
1. **「Ranging vs Trending」判斷**：Central Bank Dealers Range 和 Asian Range 是否為「clear discernible trading range（非 trending）」— 字幕沒有給出量化判斷標準（如 ATR、波動率閾值），此條件在逐字稿中是主觀的，**需要額外定義**
2. **「Asian Range > 40 pips 時改用 Flout」**：此規則明確，但「trending vs ranging」的判斷還是主觀
3. **Correlated Market 確認**（如 DXY 反向確認）：ICT 在範例中手動交叉確認多個市場，自動化需要額外 DXY 資料流
4. **Entry Pattern 選擇**：逐字稿明確說「plug and play」— OTE、turtle soup、FVG、order block 都可，模型本身不限定，算法需要選定一種
5. **Weekly Profile / Day of Week 過濾**：週四 wild card 的判斷依據（「前兩天是否有大範圍獲利」）需要回顧前幾日交易結果，可程式化但需要狀態追蹤

**NQ 1分K 特殊考量：**
- 本模型所有 SD 計算都在 **15 分鐘圖**進行，而不是 1 分鐘圖；1 分鐘圖只用於精細進場（Institutional Order Flow Entry Drill 在 5 分鐘圖）
- NQ 使用 **handles/points**（非 pips），所有 40–50 pips 的 Forex 目標需要轉換為等值的 NQ handles
- NY 開盤後 3 小時（9:30 AM — 12:30 PM ET）完整覆蓋 NY Open Kill Zone，適合本模型
- 40–50 pip Forex 目標約等同 NQ 的 **（字幕不清）**（Forex pips 對 NQ handles 的換算比例在逐字稿中未提及）

**結論**：本模型的**核心邏輯（SD 疊合 + Kill Zone 時間 + FVG 進場 + 三段出場）70% 以上可機械化**，剩餘主觀判斷集中於「ranging vs trending」的範圍定義。NQ NY 開盤場景與本模型的 NY Open Kill Zone 完全對應，是此模型應用的最佳場景之一。

---

## 關鍵原文引述

1. 方向偏差的核心邏輯：
   > "The daily chart will highlight the most probable draw on liquidity — this is where price is most apt to trade to and over the near-term horizon. Using this directional bias we can anticipate the daily ranges expanding in that same direction."

2. 模型的時段定義：
   > "I'm looking for a move in London or a move in New York, that's it. We're going to get in during London open sometime and get out towards the end of London open or right before New York open."

3. SD 疊合為模型核心：
   > "The overlapping of previous days deviations is how I do weekly highs and lows and how I do daily highs and lows. I don't always know what the daily high and low is because I have to wait for time — time is the Kill Zone."

4. 模型的利潤目標：
   > "This model specifically aims for 40 to 50 pips per setup — that's the premise or the focus if you will of this particular model."

5. FVG 高概率條件（看空）：
   > "The high probability fair value gaps are going to be in the lower 50% of the previous daily range when the market's bearish — fair value gaps that you would look to sell into, go short."

6. 進場時機的精確條件：
   > "When we are bearish we will frame a short entry when the price has moved up into a 15-minute premium fair value gap PD array that converges with a standard deviation of no more than three standard deviations during London open or New York open."

7. 此模型的「聖杯」聲明：
   > "This right here what I just showed you in this model is the Grail — this is what everybody will never ever ever see or understand. When I saw this and I discovered this pattern, okay, of how the standard deviations should be used and how the overlap with previous days — it unlocked everything."

8. 停損管理規則：
   > "We will place our stop loss above this high plus 15 pips. We will re-enter if the trade stops out — we can monitor it for a secondary entry. Day trades may require multiple attempts to secure a solid entry, do not fear this."
