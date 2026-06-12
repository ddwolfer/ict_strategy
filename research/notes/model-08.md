# Model 8 — 6% Per Month / 25 Pips Per Week 週範圍擴展模型

## 影片清單

| ID | 標題 |
|----|------|
| fHp3JkxFFjU | ICT Charter Price Action Model 8 - Targeting 6% Per Month |
| F-8hPvSyIB4 | ICT Charter Price Action Model 8 - Trade Plan & Algorithmic Theory |

---

## 模型定位

- **時間框架**：週線確定方向 → 15 分鐘或 5 分鐘執行進場
- **交易風格**：日内/短波段，一週最多一次設置，取得目標後即收手
- **適用市場**：外匯貨幣對（影片以 USD/CHF、GBP/USD、EUR/USD 為例）；ICT 明確說明也適用於 E-mini S&P、E-mini NASDAQ（25 handles 或 25 ticks）
- **目標**：
  - 每週 25 pips（Forex）或 25 handles（指數期貨）
  - 每月 6% 賬戶成長
  - 長期目標：一個日曆年內資金翻倍（複利）
- **定位**：入門基礎模型，強調紀律訓練，不追求極值高低點

---

## 核心概念定義

### Weekly Range Expansion（週範圍擴展）
整週價格朝單一方向擴展；ICT 認為外匯貨幣對每週概然範圍約 150–200 pips（不是統計平均值，是 ICT 主觀估計的「概然情境」）。模型只需捕捉其中 25 pips。

### Day of Week Anchor Point（週日曆錨點）
- **多頭週**：等待週一、週二或週三的低點形成，作為 PD Matrix 框架的起點
- **空頭週**：等待週一、週二或週三的高點形成，作為 PD Matrix 框架的起點
- 錨點形成後才框架方向，不強求在週高/週低進場

### Judas Swing / Weekly Protraction（週假突破）
價格在週開盤價方向的反方向先行甩動，製造流動性誘騙後再轉向真實週擴展方向。

### Fair Value Gap (FVG) / Liquidity Void（公允價值缺口 / 流動性真空）
- FVG：三根 K 棒中第一根的高點與第三根的低點之間的空隙（或反之），代表失衡
- Liquidity Void：類似概念，價格快速穿越造成的未成交區域
- **Consequent Encroachment（後續侵蝕）**：FVG 的中點；價格回測到中點即算「填充公允價值」，不一定需要完整填滿

### Mean Threshold（均值閾值）
Order Block 的中點，即 Order Block 內的均衡價格點（等同 FVG 的 Consequent Encroachment 概念用於 Order Block）。

### Optimal Trade Entry (OTE)
Fibonacci 回撤約 61.8%–79% 區間（影片中以 premium/discount 框架描述），但 ICT 強調 OTE 須配合 FVG 或流動性真空才有效。

### Sell Side / Buy Side Liquidity（賣方/買方流動性）
- Buy Side Liquidity：舊高上方的 buy stops（觸及後散戶被迫買入，機構利用賣出）
- Sell Side Liquidity：舊低下方的 sell stops（觸及後散戶被迫賣出，機構利用買入）

### SMT Divergence（跨市場結構背離）
兩個相關資產（如 GBP/USD 與 USD Index）在相同時間出現高/低點背離，用於強化偏向判斷。影片範例：Dollar Index 創新低時 GBP/USD 未創新高 → 空頭訊號。

### Stage 1 / Stage 2 Redistribution & Reaccumulation
- Redistribution（再分配）：空頭情境中的盤整後繼續下跌
- Reaccumulation（再積累）：多頭情境中的盤整後繼續上漲

### Dealing Range（交易範圍）
過去 20 個交易日（不含週日）的最高高點到最低低點。用於確認當前流動性分布。

---

## 進場模型完整流程

### 前置條件（準備階段）

1. **標記重要新聞事件**：標記當週及下週所有中高影響力經濟日曆事件
2. **確定 Dealing Range**：計算過去 20 個交易日（不含週日）的最高高點與最低低點
3. **確定 Draw on Liquidity（流動性吸引目標）**：在 Dealing Range 內，判斷下一個最可能被觸及的舊高或舊低
4. **確定週偏向（Weekly Bias）**：
   - 在週線圖上應用 Institutional Order Flow 分析（多頭或空頭）
   - 確認是否有 Weekly FVG 或流動性真空待回補
   - 可利用季節性傾向輔助
5. **等待波動注入條件**：等待經濟日曆事件提供 Low Resistance Liquidity Run 條件

### Setup 形成（機會探索階段）

6. **等待週一錨點形成**（可選擇不交易週一，純觀察收集情報）
7. **確認週二或週三錨點**：
   - 空頭週：週一、二、三之一形成高點後無法突破，確認為本週可能高點
   - 多頭週：週一、二、三之一形成低點後未再破低，確認為本週可能低點
8. **在錨點附近找 PD Array**：
   - FVG / Liquidity Void
   - Order Block
   - 確認位於 Premium（空頭用）或 Discount（多頭用）區域
   - OTE 需在錨點高低定義的 Fibonacci 範圍的 61.8%–79% 區域（equilibrium 以上為 premium，以下為 discount）

### 觸發條件

9. **等待 Kill Zone 時段內**（London Open 或 New York Open）回測 PD Array
10. **確認 5 分鐘圖 Institutional Order Flow Entry Drill**（5 分鐘圖顯示 IOF 進場型態形成）
11. **可加強訊號**：SMT Divergence 確認

### 進場執行

- **空頭進場**：下掛 Sell Limit Order at PD Array — 5 pips（即 FVG 下緣或 Order Block 入口減 5 pips）
- **多頭進場**：下掛 Buy Limit Order at PD Array + 5 pips（即 FVG 上緣或 Order Block 入口加 5 pips）
- 一次只下一個訂單管理一個交易想法

### 停損位置

- **標準停損**：15 pips（5 分鐘圖操作；全文中提到 20 pips 用於較早的模型，此模型改為 15 pips）
- 空頭：止損置於 PD Array 上方（rejection block / 上影線收盤高點上方）
- 多頭：止損置於 PD Array 下方
- 停損具體位置：整個 PD Array 結構外側約 1 pipet

### 停利與出場管理

**標準模式（單一目標）：**
- 下掛 Limit Order 鎖定 25 pips 目標，到達即全部出場，等待下週機會
- 25 pips 是最低目標，不是上限

**停損移動規則：**
- 盈利達到預期目標的 50%（即 +12.5 pips）時：停損縮減 25%（由 15 pips 縮至約 11 pips）
- 盈利達到預期目標的 75%（即 +18.75 pips）時：停損移至 Break Even

**進階出場（超過 25 pips 後）：**
- 25 pips 目標鎖定後，繼續持有剩餘部位
- 40 pips、60 pips、80 pips 處分批出場
- 觸及舊低（空頭）或舊高（多頭）時可出場部分或全部
- 每下一個 10 pips 里程碑皆可出場一部分（10 pips below target → take some off，20 pips below → take some off，30 pips below → take some off）

---

## 具體參數

| 參數 | 數值 |
|------|------|
| 週目標 | 25 pips（Forex）/ 25 handles（NQ/ES）/ 25 ticks（其他期貨） |
| 月目標 | 6% |
| 年目標 | 翻倍（複利） |
| 最低週範圍（概然估計） | 150–200 pips |
| 關注範圍（每週） | 下一個 50–75 pips 方向性移動（另一處說 50–100 pips） |
| Dealing Range 回顧天數 | 過去 20 個交易日（不含週日） |
| 進場 Limit Order 偏移 | PD Array ± 5 pips |
| 標準停損 | 15 pips（5 分鐘圖） |
| 停損移動觸發點 1 | 盈利 50% 目標 → 停損縮 25% |
| 停損移動觸發點 2 | 盈利 75% 目標 → 停損移至 BE |
| 風險比例（範例） | 1%–1.5% 每筆交易 |
| 倉位計算公式 | 倉位大小 = 賬戶資金 × R% ÷ 停損 pips 數 |
| 範例賬戶 | $20,000，風險 1.5% = $300 |
| 微型合約停損成本 | 15 pips × $0.10 = $1.50 |
| 微型合約倉位 | $300 ÷ $1.50 = 200 micro lots |
| 標準合約停損成本 | 15 pips × $10 = $150 |
| 標準合約倉位 | $300 ÷ $150 = 2 standard lots |
| 連勝後降倉 | 連贏 5 筆後，R% 減半 |
| 虧損後降倉 | 全額虧損後 R% 減半，直到損失回補 50% |
| 虧損後再降倉 | 降倉後再虧損，繼續再減半 |
| OTE 區間（隱含） | Fibonacci 61.8%–79%（equilibrium 以上為 premium，以下為 discount） |

---

## 時段規定（Killzone）

| 時段 | 說明 |
|------|------|
| **London Open Kill Zone** | 進場窗口之一（New York 時間請換算：倫敦開盤通常為 NY 時間 03:00–05:00） |
| **New York Open Kill Zone** | 進場窗口之一（通常為 NY 時間 07:00–10:00，影片未給精確數字） |
| **交易日**（優先順序） | 週二、週三最優先；週四也可交易（若週三確認錨點）；週五有降低優先級的意味 |
| **週一** | 建議僅觀察收集情報，不強制交易；ICT 說「you can elect to let Monday trade without you」 |
| **範疇外時段** | 影片提到「outside beyond the scope of the New York session」的走勢不計入有效觸發 |

> **注意**：影片原文未給出 Kill Zone 的精確 New York 時間範圍數字，以上為 ICT 課程體系中對應時段的通用描述，但本逐字稿未明確標注，使用時請交叉比對其他資料。(字幕不清)

---

## 風控規定

1. **每週只需一個 Setup**：找到並執行一次後，剩餘時間不交易（測試自我紀律的核心練習）
2. **風險比例**：每筆 1%–1.5%（範例使用 1.5%）
3. **連勝保護**：連贏 5 筆後將 R% 減半，防止帳戶曲線出現大波動
4. **虧損後降倉機制**：
   - 全 R 虧損 → R% 減半
   - 損失回補 50% 前不恢復
   - 降倉後再虧 → 再減半
5. **目標**：平滑上升的資金曲線（階梯狀向上），避免鋸齒形或深回撤
6. **不在低波動範圍市場強行交易**（例如英鎊在盤整週不強求 25 pips）
7. **倉位計算一律無條件捨入（round down）**
8. **不在 Monday 就急著進場**（可選擇純觀察）

---

## 對「NQ 1 分 K、NY 開盤後 3 小時自動交易」的適用性

### 可適用之處

| 規則 | 機械化可行性 |
|------|------------|
| NQ / E-mini NASDAQ 明確被提及（25 handles） | 高，ICT 原文直接說「E mini NASDAQ」 |
| 方向偏向：週線 institutional order flow + Dealing Range | 高，可程式化判斷高低點與流動性位置 |
| 進場時段：New York Open Kill Zone | 高，時間窗可硬編碼 |
| 進場方式：Limit Order at FVG ± 5 pips | 高，可自動計算 FVG 邊界 |
| 停損：15 pips / handles（1 分鐘圖需換算 tick 數） | 高 |
| 停損移動規則（50% → 縮 25%；75% → BE） | 高，可用盈利追蹤邏輯 |
| 分批出場（25/40/60/80 handles 里程碑） | 高 |
| 倉位計算公式 | 高 |

### 主觀判斷成分（自動化困難點）

| 規則 | 問題 |
|------|------|
| 週線偏向判斷（「market structure analysis」） | 需定義 swing high/low 演算法，邊緣案例仍有模糊空間 |
| 週一/週二/週三「錨點形成」的認定 | 何時算「高點已確認不再突破」需要定義等待邏輯 |
| FVG 品質篩選（哪個 FVG 最相關） | 多個 FVG 同時存在時，選哪個需要優先順序規則 |
| Judas Swing 識別 | 需定義「反向誘騙後轉向」的觸發條件 |
| SMT Divergence（跨市場確認） | 需同時餵入 NQ 與相關資產（如 ES）的資料 |
| 「避免低波動盤整週」的判斷 | 需 ATR 或週範圍閾值過濾條件 |
| Kill Zone 內 5 分鐘 IOF Entry Drill | 需定義 5 分鐘圖上 MSS（Market Structure Shift）與 FVG 的複合識別 |

### 結論

**Model 8 對「NQ 1 分 K、NY 開盤後 3 小時自動化」具中高適用性**。核心邏輯（週偏向 → FVG 進場 → 固定停損/目標）可演算法化；主要障礙在於「週錨點形成」的程式化定義，以及 Kill Zone 內的 5 分鐘 IOF 觸發條件。建議先將週線偏向由更高層系統決定，再讓此模型在 NY Open Kill Zone 負責執行進場邏輯。

---

## 關鍵原文引述

1. **模型目標定義**（fHp3JkxFFjU）：
   > "This is price action model number eight the 6% trading model building the career on 25 Pips per week."

2. **週目標規模感**（fHp3JkxFFjU）：
   > "If we're only looking for 25 Pips or if I'm trying to instill in you the thought process that you're only looking for 25 Pips amongst 150 to 200 Pips a week, are you expecting a whole lot? No you're not."

3. **進場日規則**（fHp3JkxFFjU）：
   > "We're looking for the daily high or Monday Tuesday or Wednesday to form and also provide that overlap of the weekly higher low."

4. **Kill Zone 進場方式**（F-8hPvSyIB4）：
   > "When we are bearish we'll anticipate a 5 minute chart institutional orderflow entry drill trade entry to form inside of a retracement higher during the London open and or New York open kill zones or buy stop raid that we will go short when it unfolds."

5. **FVG 進場偏移**（F-8hPvSyIB4）：
   > "We will use the PD array convergence minus 5 Pips as our entry price when using the sell limit order."

6. **停損移動規則**（F-8hPvSyIB4）：
   > "When we are in profit 50% of our expected objective stop-loss can be reduced by 25%. When we're in profit 75% of our expected objective stop loss can be reduced by break even."

7. **指數期貨適用性**（F-8hPvSyIB4）：
   > "This could be 25 handles or 25 ticks in index Futures so don't think it's limited obviously to Forex... E mini S&P or E mini NASDAQ you could look for 25 handles for the week."

8. **紀律核心**（F-8hPvSyIB4）：
   > "If you can only just make 6% a month don't let anybody tell you that is not good enough that is a phenomenal rate of return."
