# Model 12 — Scalping Intraday Model（日內剝頭皮模型）

## 影片清單

| 影片 ID | 標題 |
|---------|------|
| 3xgtrXok-xs | ICT Charter Price Action Model 12 - Scalping Intraday Model |
| xi0N9BG1Qvs | ICT Charter Price Action Model 12 - Trade Plan & Algorithmic Theory |

---

## 模型定位

- **別稱**：Bread and Butter Setup、Hit and Run Trading
- **時間框架**：
  - Stage（大背景）：15 分鐘圖
  - Setup 形成：5 分鐘圖
  - 延伸應用：1 分鐘圖（ICT 提及可縮減至此）
- **交易風格**：純日內剝頭皮，不持倉過夜、不持倉過週末
- **適用市場**：外匯（原範例用 EURUSD、GBPUSD、GBPJPY、USDCHF）；指數期貨（NQ/ES）適用，此時以 ticks/handles 替代 pips
  - NQ/NASDAQ：20 ticks ≈ 5 handles（$250/mini contract）
  - S&P mini：5 handles = $250/mini；10 handles = $500/mini
- **目標定位**：每筆交易 20 Pips（或外匯等值單位）；並非高 R 倍數模型，定位為「每天都能找到機會」的基礎型模型
- **核心描述**：找到一個 Order Block，等待 Expansion Swing 確認後，進入 Expansion 內部的 Fair Value Gap（FVG），目標 20 pips 出場

---

## 核心概念定義

### Daily Range Expansion（每日區間擴張）
- 每日交易的重點是判斷當天 daily bar 最可能的擴張方向（多或空）
- 不需要精確預測收盤價，只需判斷方向

### Order Block（訂單塊）
- 本模型使用的 Order Block 不要求「必須有 FVG 直接附著在蠟燭上」（這與 high-probability OB 的嚴格定義不同）
- 多頭 Order Block：下跌走勢開始前的最後一根向下收盤蠟燭（down-closed candle），代表機構買入區域
- 空頭 Order Block：上漲走勢開始前的最後一根（或最後兩根）向上收盤蠟燭（up-closed candle），代表機構賣出區域
- 進場敏感區域：使用蠟燭的**上半部（high 到 midpoint）**而非整根蠟燭

### Expansion Swing（擴張波段）
- Order Block 被測試後，出現的加速方向性移動
- 三段結構：Impulse（初始位移）→ Retracement（回測 Order Block）→ Expansion（加速擴張，Model 12 的進場段）

### Fair Value Gap（公允價值缺口）
- 三根蠟燭結構：前一根蠟燭的 High（或 Low）與後一根蠟燭的 Low（或 High）之間的缺口
- 本模型的 FVG 形成於 Expansion Swing 內部，不一定直接附著於 Order Block
- 多頭進場：FVG 低點（前高到後低的缺口高點那根蠟燭的 low）= 進場價位
- 空頭進場：FVG 高點（那根蠟燭的 high）= 進場價位
- FVG 低點（多頭）或高點（空頭）是進場觸發，不需要 FVG 完全填滿

### Internal Range Liquidity（內部區間流動性）
- Expansion Swing 的內部流動性池，用於尋找 FVG 進場點

### External Range Liquidity（外部區間流動性）
- 前日高點（Previous Day's High）或前日低點（Previous Day's Low）
- 15 分鐘圖上的舊高點作為目標

### Institutional Order Flow Entry Drill（機構訂單流進場法）
- 空單：FVG 進場位 - 5 pips（sell limit）
- 多單：FVG 進場位 + 5 pips（buy limit）
- 觸及 FVG 邊緣前一根蠟燭的低點被刺穿一個 pip，即為 IOFED 確認

### Kill Zone（殺傷時段）
- Order Block 的形成可以在 Kill Zone 之外
- **但 Order Block 與 FVG 的回測（return）必須發生在 Kill Zone 內**

---

## 進場模型完整流程

### 前置條件（Preparation）

1. **週線方向判斷**：
   - 標記本週最可能擴張的方向（多或空）
   - 不需要預測收盤價，只需判斷方向偏向
   - 參考：本週日曆事件（高影響力財經數據）與當前市場結構

2. **20 日交易區間（Dealing Range）標記**：
   - 計算最近 20 個交易日（不含週日）的最高高點與最低低點
   - 這是當前 Dealing Range
   - 在此區間內尋找下一個 Draw on Liquidity（向哪個舊高/舊低移動）
   - 結合週線偏向選擇 PD Array 方向

3. **每日方向判斷**：
   - 判斷當天是否更可能突破前日高點或前日低點
   - 也可參考 London session 的方向，判斷 New York session 是否延續

4. **新聞日曆**：
   - 標注中高影響力事件，這些波動注入（Volatility Injection）是等待的觸發時機
   - 避免在 NFP 週的週三後 New York session 交易（字幕提及 ICT 本人亦如此）

### Setup 形成（Opportunity Discovery）

5. **在 15 分鐘圖上**，尋找能夠實現 20 pip 走勢的區間，目標為：
   - 多頭：Buy Side Liquidity（舊高）
   - 空頭：Sell Side Liquidity（舊低）

6. **識別 Order Block**：
   - 在價格走勢的初始位移（Impulse Swing）開始處，找最後一根反向收盤蠟燭
   - 多頭：最後一根 down-closed candle（即將大漲前的最後一根陰線）
   - 空頭：最後一或兩根 up-closed candle（即將大跌前的最後一或兩根陽線）
   - 注意：此時 OB 不必有 FVG 直接附著

7. **等待 Retracement 回測 Order Block**：
   - 價格必須回到 Order Block 區域（使用 high 到 midpoint 的上半區域作為參考）
   - 此時不立刻進場，等待確認

8. **等待 Expansion Swing 形成**（關鍵確認）：
   - Order Block 被測試後，價格必須展現出 Expansion（加速遠離 OB 的移動）
   - 此擴張波段必須形成，才能進入下一步
   - 同時觀察市場結構（MSS / Market Structure Shift）：Expansion 打破短期高點或低點即為確認

9. **在 5 分鐘圖的 Expansion Swing 內部尋找 FVG**：
   - 在 Expansion Swing 的三根蠟燭結構中找 Fair Value Gap
   - 多頭 FVG：前根蠟燭 High → 後根蠟燭 Low 之間的缺口；使用「後根蠟燭 Low」（即 FVG 的高點邊緣那根蠟燭的 low）作為進場基準
   - 空頭 FVG：前根蠟燭 Low → 後根蠟燭 High 之間的缺口；使用「後根蠟燭 High」（即 FVG 的低點邊緣那根蠟燭的 high）作為進場基準
   - FVG 不應過度延伸、過遠；尋找擴張段內「距離合理」的 FVG

### 觸發（Trade Planning）

10. **時段確認**：
    - 回測 Order Block 與 FVG 的時間必須在 **London Open Kill Zone 或 New York Open Kill Zone** 內
    - OB 本身可以在 Kill Zone 之外形成（包括 5:00–7:00 NY 時間的安靜時段）
    - 若回測不在 Kill Zone 內，此設置不符合交易資格

11. **市場偏向確認**：
    - 多頭時：尋找 15 分鐘 discount FVG + bullish Order Block（在 15 分鐘下跌回調中形成）
    - 空頭時：尋找 15 分鐘 premium FVG + bearish Order Block（在 15 分鐘上漲回調中形成）

### 進場（Trade Execution）

12. **掛 Limit Order**（不追市價）：
    - 空單：Sell Limit 掛在 FVG 高點（空頭 FVG 的那根蠟燭 high）；或使用 IOFED = FVG 觸發價 - 5 pips
    - 多單：Buy Limit 掛在 FVG 低點（多頭 FVG 的那根蠟燭 low）；或使用 IOFED = FVG 觸發價 + 5 pips
    - 進場後立刻同時設置：止損 + 20 pip 獲利目標（counter limit order）
    - 不再主動干預，讓單子自行運作

### 停損位置

13. **預設停損：進場點 ± 20 pips**
    - 停損位在 FVG 另一側之外（上方若空單，下方若多單），涵蓋 FVG 可能完全回填的情況
    - 若 FVG 被回填甚至超過，需有心理準備但不提前離場，相信停損機制
    - **最低停損建議：15 pips**（ICT 個人使用），不低於此

### 停利 / 出場管理

14. **主要目標：20 pips**
    - 單一倉位：達到 20 pips 後全數出場（以 counter limit order 執行）
    - 等待下一個機會

15. **分批出場（Scaling，使用 10 mini = 1 standard lot 的範例）**：
    - **80% 倉位（8 mini）在 20 pips 第一目標出場**
    - **剩餘 20% 倉位（2 mini）繼續持有**，尋找下一個 PD Array 目標
      - 多頭：尋找上方 premium PD array
      - 空頭：尋找下方 discount PD array
    - 進階延伸：打破舊高/低後 10–20–30 pips 上方/下方的區域可作為延伸目標

16. **動態停損調整**：
    - 盈利達 10 pips 時：停損縮小 10 pips（風險減半）
    - 盈利達 15 pips 時：停損移至 Break Even（此後最差結果為保本）
    - 理由：ICT 練習時常見行情給出 12–15 pips 後反轉，若不鎖定則變成虧損

---

## 具體參數

| 參數 | 數值 |
|------|------|
| **主要獲利目標** | 20 pips（外匯）/ 20 ticks 或 5 handles（指數期貨） |
| **預設停損** | 20 pips |
| **最低停損** | 15 pips（ICT 個人最低，不建議學生更短） |
| **Dealing Range 回看週期** | 最近 20 個交易日（不含週日） |
| **5 分鐘圖 OB 使用部位** | 蠟燭 High 到 Midpoint（上半部，敏感度最高） |
| **進場調整（IOFED）** | 空單：FVG 高 - 5 pips；多單：FVG 低 + 5 pips |
| **第一分批出場比例** | 80% 倉位在 20 pips 目標 |
| **剩餘持倉比例** | 20% 作為 runner |
| **Stop 縮減門檻 1** | 盈利 10 pips → 停損縮 10 pips |
| **Stop 縮減門檻 2** | 盈利 15 pips → 停損移至 Break Even |
| **風險百分比（示範帳戶）** | 1% per trade |
| **止損後風控規則** | 單次全額虧損後，R% 降 50%；待虧損回復 50% 後恢復原 R% |
| **連勝後風控規則** | 連贏 5 筆後，R% 主動降 50%（預防即將到來的虧損） |
| **指數期貨替代參數** | 20 pips ≈ 20 ticks；5 handles（NQ/ES 1 mini = $250 per 5 handles） |
| **持倉時長** | 純日內，不持倉過夜、不持倉過週末 |

---

## 時段規定（Kill Zone）

| 規定 | 細節 |
|------|------|
| **Order Block 形成時段** | 不限，可在 Kill Zone 外形成（含 NY 時間 5:00–7:00 安靜時段、Central Bank Dealing Range 時段） |
| **回測 OB + 回測 FVG 的時段** | **必須**在 ICT Kill Zone 內，否則不構成有效交易 |
| **有效 Kill Zone（明確提及）** | London Open Kill Zone 或 New York Open Kill Zone |
| **避免交易時機** | NFP 週的週三之後 New York session（字幕原文：「nonfarm payroll weeks after Wednesday New York session」） |

---

## 風控規定

### 停損設置
- 標準停損：20 pips（含蓋 FVG 完全填滿的情境）
- 絕對最低：15 pips（不接受 5 pips 或 2 pips 停損）
- 停損後不主動干預，若 FVG 被填滿繼續持有直到停損或目標

### 資金管理公式
```
Position Size = (Account Equity × R%) ÷ Stop-Loss in Pips
```

- R%：每筆願意承擔的帳戶百分比風險（示範用 1%）
- 帳戶 $10,000、1% 風險 = $100 可承擔虧損
  - Micro lots（$0.10/pip）：50 micro lots = 1% 風險
  - Mini lots（$1/pip）：5 mini lots = 1% 風險
  - Standard lot：**20 pips + 1% 不允許使用標準手**
- 永遠向下取整（round down）

### 動態風控規則
1. 虧損 full R% → 下筆 R% 降 50%
2. 降低後的 R% 再次虧損 → 再降 50%
3. 上述虧損回復 50% → 可恢復原始 R%
4. **連贏 5 筆 → 主動降 R% 50%**（建立 equity leveling，避免大回撤）
5. 目標：平滑向上的權益曲線，而非高波動分佈

### 部位管理紀律
- 進場後立即設置停損 + 獲利 limit order，不再觸碰
- 不過度關注帳戶，讓計劃自行運作

---

## 對「NQ 1 分 K、NY 開盤後 3 小時自動交易」的適用性

### 正向對應
- ICT 明確提及模型可縮減至 1 分鐘圖（「it's completely up to you ... down to a one minute chart」）
- 指數期貨（NQ/NASDAQ）明確被提及，20 ticks / 5 handles 作為等價目標
- New York Open Kill Zone 是兩個有效 Kill Zone 之一，NY 開盤後 3 小時完全覆蓋此 Kill Zone
- 模型以 daily range expansion 方向為基礎，NY 開盤前可確立當日方向偏向
- 每日必有機會（"something like this every single trading day"），適合每日固定時段自動掃描
- 前日高低點作為 external range liquidity 目標，可程式化計算

### 需要注意的自動化挑戰
- Stage 用 15 分鐘圖，Setup 在 5 分鐘圖；若用 1 分鐘圖，需調整時間框架對應關係（原始模型未明確規定 1 分鐘的對應框架）
- Order Block 的「上半部敏感區」需程式化定義（high 到 midpoint）
- FVG 識別需在 Expansion Swing **內部**，不是任意 FVG，邏輯順序不能打亂
- Kill Zone 時段限制需嚴格編碼（OB 可在外，但回測必須在內）
- NFP 週的週三後 NY session 需設定自動停止交易

### 演算法化精確順序
1. 計算前 20 日 Dealing Range，標記下一個 Draw on Liquidity
2. 確認當日方向（前日高/低哪個更可能被突破）
3. 確認是否在有效 Kill Zone 時段內
4. 識別 Expansion Swing 開始前的 Order Block（最後一根反向蠟燭）
5. 等待回測 Order Block（使用蠟燭 high 到 midpoint 範圍）
6. 等待 Expansion Swing 形成（MSS 確認，舊高/低被突破）
7. 在 Expansion Swing 內部尋找 FVG
8. 掛 limit order 在 FVG 邊緣（± 5 pips IOFED 調整）
9. 同步設置 20 pip 停損 + 20 pip 獲利目標
10. 10 pips 時縮停損，15 pips 時移至 break even，20 pips 自動全部出場

---

## 關鍵原文引述

1. **模型核心定義**：
   > "we are waiting for an order block to facilitate a expansion swing so while we qualify valid order blocks or high probability order blocks with fair value gaps sometimes an order block will form a down closed candle near an important key level from a higher time frame level and that down closed candle may not necessarily have a fair value gap so we're filtering that with any down closed candle that was at the beginning of a initial expansion price swing then it has to be retested"

2. **三段結構**：
   > "the impulse price swing is the initial displacement the retracement is the retest of the order block then the expansion move where price really starts to get accelerated this is where we do not chase it we just simply wait for the fair value gap to form"

3. **進場規則（FVG 邊緣）**：
   > "for a bearish fair value gap it would be the low the gap that's what you're looking for for your entry ... at the high of the fair value gap for longs"

4. **Kill Zone 回測規定**：
   > "the return to the order block and fair value gap that must that absolutely must be during an ICT kill zone otherwise it's not a viable trade"

5. **停損動態調整**：
   > "when we are in profit 15 pips of our expected 20 pip objective stop loss can be reduced to break even"

6. **進場執行紀律**：
   > "long story short we're entering on a limit and we as soon as we enter we have our profit objective in the form of a counter limit and the order sits there we don't monkey around with it we don't think about it we don't obsessively compulsively worry we put the stop in we put the limit order in for 20 pips and we let it go"

7. **NQ/指數期貨適用性**：
   > "if you're comfortable with trading index futures you can use that 20 as a 20 tick or 20 handles or 10 handles okay whatever you want it to be"

8. **模型適用 1 分鐘圖**：
   > "you can expand them or reduce them to lower time frames down to a one minute chart it's completely up to you but the theory behind it and the narrative that's used is the same"
