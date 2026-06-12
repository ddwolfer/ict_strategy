# Model 10 — Swing Trading（外部區間流動性進出場模型）

## 影片清單

| ID | 標題 |
|----|------|
| CTS27DsveNs | ICT Charter Price Action Model 10 - Swing Trading（模型介紹） |
| E57WWIEjhvU | ICT Charter Price Action Model 10 - Trade Plan & Algorithmic Theory（交易計畫與演算法理論） |

---

## 模型定位

- **交易風格**：Swing Trading（波段交易），亦可降格為日內交易（intraday）或 one-shot-one-kill
- **時間框架**：多時間框架；逐字稿示範使用 4-Hour、15-minute、1-minute（E57WWIEjhvU 明確提到 1-minute 示範）。進出場觸發使用 15-minute chart
- **適用市場**：外匯（Cable、Euro Dollar、加元）、股指期貨（ES mini S&P、NQ implicitly）、股票、商品——逐字稿稱「任何時間框架、任何市場皆適用」
- **週目標**：**50 至 75 Pips per week**；主要在 50 Pips 鎖定大部分倉位，75 Pips 為剩餘倉位最佳情境

---

## 核心概念定義

### External Range Liquidity（外部區間流動性）
- 定義：超出當前「Dealing Range（交易區間）」範圍之外的流動性池。  
  - **Dealing Range**：市場在突破前維持整理的區間，以最高點（High）和最低點（Low）界定，邊界外即為 External Range。
  - Buy Side External Range Liquidity：Dealing Range 最高點之上方的買方止損（buy stops）
  - Sell Side External Range Liquidity：Dealing Range 最低點之下方的賣方止損（sell stops）
- 與 Internal Range Liquidity 的區別：同一個高低點範圍內的流動性屬 Internal；當定義的 Dealing Range 改變時，判定也隨之改變——ICT 特別說明「這看似混淆，但取決於你如何界定那個 range」

### Dealing Range（交易區間）
- 類似整理矩形（consolidation rectangle），以近期明確的高點與低點框定
- 具有 fractal 性質：大 Dealing Range 內部可再細分出小 Dealing Range（逐字稿：second charts 至 daily charts 皆可見）
- 進入 Dealing Range 時找方向，突破時執行進場

### Weekly Range Expansion（週區間擴張）
- 核心前提：每週需先判斷本週或下週 K 棒最可能向上或向下擴張的方向
- 方向確認後，所有日內 setup 都必須順著此方向操作

### External Range Liquidity Run（外部區間流動性奔跑）
- 模型的 Pattern 核心：等待市場「run」過前一個 short-term High（做空）或 short-term Low（做多），利用這個對方向的誘多/誘空進場
- 本質是 **Turtle Soup** 的應用：賣在舊高之上，買在舊低之下

### PD Array（Premium / Discount Array）
- Fair Value Gap（FVG）、Order Block、Breaker 等皆屬 PD Array
- 做空時，在 premium PD array 附近（Buy Side Liquidity Pool）建立空頭
- 做多時，在 discount PD array 附近（Sell Side Liquidity Pool）建立多頭

### Volatility Injection（波動注入）
- 對應到經濟行事曆的中高影響力事件
- 是觸發 low resistance liquidity run 的催化劑
- Trade Planning 階段需標記當週/下週的高影響事件，等待其作為進場時機

### Equity-to-Date Range（股本累計區間）
- 回溯 20、40、60 個交易日（不含週日）找出最高高點與最低低點
- 此為「Current Dealing Range」，用以判斷下一個流動性目標（draw on liquidity）

---

## 進場模型完整流程

### 前置條件（Preparation & Opportunity Discovery）

1. **標記高影響力經濟事件**：查閱本週/下週行事曆，判斷哪個事件最可能觸發週區間擴張
2. **確認週偏向（Weekly Bias）**：
   - 查看週線圖，確認 Bearish Order Block、Market Structure Break（MSS）等高時間框架訊號
   - 若看空：市場應已從 Bearish Order Block 向下擴張
   - 若看多：反向
3. **計算 Equity-to-Date Dealing Range**：回溯 20、40、60 交易日，標記最高高點與最低低點
4. **識別下一個 Draw on Liquidity**：
   - 看空時：識別哪個舊低（old low）是下一個 sell side liquidity target
   - 看多時：識別哪個舊高（old high）是下一個 buy side liquidity target
5. **確認 50-75 pip 空間**：在 Dealing Range 內確認入場點到目標之間有足夠的 50-75 pips 空間

### Setup 形成條件

- **日期限制**：Setup 錨點（anchor point）需在 **Monday、Tuesday、或 Wednesday** 形成（「day of week specific」）
- **看空 Setup**：
  - 在 weekly bearish 情境下，等待市場向上「run」過一個 short-term high 或 double top
  - 這個「run above」需發生在 Killzone 時段
- **看多 Setup**：
  - 在 weekly bullish 情境下，等待市場向下「run」過一個 short-term low 或 double bottom
  - 同樣需在 Killzone 時段

### 觸發條件（Trigger）

- **看空觸發**：15-minute chart 出現 **buy side liquidity pool raid**（價格在 London Open 或 New York Open Killzone 向上掃過舊高/double top）
- **看多觸發**：15-minute chart 出現 **sell side liquidity pool raid**（價格在 London Open 或 New York Open Killzone 向下掃過舊低/double bottom）

### 進場（Entry）

- **做空（Sell Limit Order）**：
  - 掛 Sell Limit 在 PD array convergence 點位，**減 5 Pips** 作為入場價（PD array convergence minus 5 pips）
  - 可選：Institutional level（大整數關口）、Big Figure、Mid Figure、nearest round 10-level 或 5-level，結合 FVG 或 Liquidity Void 區間
- **做多（Buy Limit Order）**：
  - 掛 Buy Limit 在 PD array convergence 點位，**加 5 Pips** 作為入場價（PD array convergence plus 5 pips）

### 停損位置（Stop Loss）

- **明確數字**：停損 = **20 Pips**（逐字稿 E57WWIEjhvU 停損計算範例明確使用 20 pips stop）
- 不使用 5 pips 或 10 pips 的超緊停損（逐字稿明確說「don't even think like that」）

### 停利 / 出場管理（Profit Taking / Exit）

**兩單分批出場系統（Two-Order System）：**

1. **Order 1**：目標 **50 Pips**，以 Limit Order 鎖定
2. **Order 2**：目標 **50 至 75 Pips** 之間，以 Limit Order 鎖定；若達 75 pips 則以 Limit Order 平倉，等待下一機會

**停損移動規則：**
- 當未實現盈利達到預期目標的 **50%** 時，停損可向入場方向縮減 **25%**
- 當未實現盈利達到預期目標的 **75%** 時，停損可移至 **Break Even**

**逐步分批出場（Partial Exit，適用於更大波段持倉）：**
- **第一批次（Partial 1）**：當第一個 short-term low（做空）或 short-term high（做多）在入場後形成，且價格突破該點位時，出場部分倉位
- **第二批次（Partial 2）**：下一個 short-term low/high 被突破時，再出場部分
- **第三批次（最終出場）**：「On your second partial, the next take profit you have to be out of the entire position」——第三次出場必須清空全部剩餘倉位
- **優先對象**：舊低（old lows to the left）優先於新形成的短期低點；舊低旁有更大流動性池
- **規則限制（做空）**：不得在舊低/新 short-term low 之上平倉；必須在其**下方**才能出場
- **規則限制（做多）**：不得在舊高/新 short-term high 之下平倉；必須在其**上方**才能出場

**一次性出場（One-Shot-One-Kill）選項：**
- 看空時：若 50 pips 為週目標，在入場後直接掛 50-pip Limit；25-pip 可先出場一半，75-pip 出場另一半加尾單
- Thursday New York Open 通常為週低點（bearish 週）——「one-shot-one-kill trading, generally cover on Thursdays at New York open because that typically will make the low of the week」

---

## 具體參數

| 參數 | 數值 | 來源 |
|------|------|------|
| 週目標（主要） | 50 pips | E57WWIEjhvU |
| 週目標（最佳情境） | 75 pips | E57WWIEjhvU |
| 停損標準 | 20 pips | E57WWIEjhvU |
| 進場偏移（做空 Sell Limit） | PD array - 5 pips | E57WWIEjhvU |
| 進場偏移（做多 Buy Limit） | PD array + 5 pips | E57WWIEjhvU |
| 停損縮減觸發點 | 當盈利達目標 50% | E57WWIEjhvU |
| 停損縮減幅度 | 縮減 25% | E57WWIEjhvU |
| Break Even 觸發點 | 當盈利達目標 75% | E57WWIEjhvU |
| 錨點形成日 | Monday / Tuesday / Wednesday | CTS27DsveNs |
| 做空最終出場日（建議） | Thursday New York Open | CTS27DsveNs |
| 最大分批出場次數 | 3 次（第 3 次清空全部） | CTS27DsveNs |
| 分批比例（建議選項之一） | 50% / 25% / 25% | CTS27DsveNs |
| Equity-to-Date 回溯期 | 20、40、60 個交易日 | E57WWIEjhvU |
| 風控：大整數以下容忍度 | 最多 20 pips below big figure | CTS27DsveNs |
| 停損超低值（明確禁止） | 5 pips 或 10 pips | CTS27DsveNs |
| R:R（依 50-pip 目標 / 20-pip 停損） | 2.5R | 計算得出 |
| R:R（依 75-pip 目標 / 20-pip 停損） | 3.75R | 計算得出 |
| 標準帳戶風險% | 1% per trade（示範值） | E57WWIEjhvU |
| 連虧後降低 R% | 虧損後降至 50%，回復 50% 時才恢復 | E57WWIEjhvU |
| 連贏後降低 R% | 連贏 5 筆後降至 50% | E57WWIEjhvU |

**Position Size 公式：**
```
Position Size = (Account Equity × R%) / (Stop Loss in Pips × Pip Value)
```
示範（$10,000 帳戶，1%，20-pip 停損，mini lots $1/pip）：
- $10,000 × 1% = $100 risk
- 20 pips × $1 = $20 per trade unit
- $100 / $20 = 5 mini lots（永遠向下取整）

---

## 時段規定（Killzone）

| 觸發時段 | 用途 |
|----------|------|
| **London Open Killzone** | 15-min chart buy/sell side liquidity pool raid 觸發進場 |
| **New York Open Killzone** | 15-min chart buy/sell side liquidity pool raid 觸發進場（主要） |
| **Thursday New York Open** | 建議做空出場時段（bearish week 的週低點通常形成於此） |
| London Close | 日內交易（day trading）可於此出場（逐字稿提及但非主要規則） |

注意：逐字稿中時間皆為 **New York Time**（EST/EDT）。具體 Killzone 開始/結束時間未在這兩份逐字稿中明確列出，需參考 ICT 其他資料（此處標注「字幕不清」——逐字稿僅稱「London open」、「New York open」未給具體時刻）。

---

## 風控規定

1. **單筆風險**：不超過帳戶資金的 R%（建議從 1% 起步，示範值）
2. **連虧保護**：
   - 任何一筆虧損達到全額 R%：將下一筆 R% 降低 50%
   - 以降低後的 R% 再度虧損：再降 50%
   - 直到前一筆虧損回收 50% 才可恢復至原 R%
3. **連贏保護**：
   - 連續 5 筆獲利：主動將 R% 降低 50%（目的：建立 equity leveling，避免大回撤）
4. **倉位計算原則**：永遠向下取整（always round down）
5. **標準口大小警告**：以 $10,000 帳戶、1% 風險、20-pip 停損，標準口 ($10/pip) 需要 $200 風險 > 可用 $100，故不適用
6. **停損移動**：不得使用 5 pips 或 10 pips 超緊停損；進入盈利 50% 才開始縮停損

---

## 對「NQ 1 分 K、NY 開盤後 3 小時自動交易」的適用性

### 適合之處

| 可機械化規則 | 說明 |
|-------------|------|
| **進場時段**：New York Open Killzone | 完全符合「NY 開盤後 3 小時」場景 |
| **觸發條件**：15-min 或 1-min buy/sell side liquidity pool raid | 逐字稿 E57WWIEjhvU 直接以 1-minute ES mini 示範，NQ 同類市場完全適用 |
| **進場類型**：Sell/Buy Limit at PD array ± 5 pips | 可以 limit order 自動掛單，無需人工 |
| **停損**：固定 20 pips（handles for NQ）| 可直接以數字入演算法 |
| **停利**：50 pips / 75 pips Limit Order | 可以雙 limit order 自動出場 |
| **停損移動**：盈利 50% 縮 25%、75% 移 B/E | 可用條件單或演算法邏輯實作 |
| **出場規則**：只在 old low/old high 以外出場 | 可掃描歷史 swing high/low 自動判斷 |
| **Dealing Range 識別** | 可演算法識別整理區間邊界 |
| **週偏向**：以週線高時間框架結構判斷 | 週初一次性判斷後，當週固定方向，可機械化為參數 |

### 主觀判斷部分（較難機械化）

| 主觀元素 | 說明 |
|---------|------|
| **PD Array 精確點位識別** | FVG、Order Block 的邊界確認需人工或複雜演算法辨識 |
| **Dealing Range 邊界選擇** | 逐字稿承認「one could argue」範圍定義有歧義，取決於交易者選擇哪個 range |
| **Weekly Bias 判斷**（高時間框架 MSS、Bearish OB） | 需人工或高時間框架演算法，非簡單技術指標可替代 |
| **錨點日期（Mon/Tue/Wed）過濾** | 相對容易機械化，但若 setup 在 Thursday/Friday 形成需人工判斷是否忽略 |
| **分批出場百分比**（逐字稿明確說「completely personal」） | 演算法可設定固定比例，但最佳比例無定論 |

### 結論

**模型適合 NQ 1 分 K NY 開盤場景**，理由：
- E57WWIEjhvU 已明確以 1-minute ES mini 示範此模型
- NY Open Killzone 是逐字稿明確指定的進場時段之一
- 停損（20 pips/handles）、停利（50/75 pips）、進場偏移（±5 pips）均為固定數字，可直接硬編碼
- 最大挑戰在於「Dealing Range 邊界」與「PD Array 精確點位」的自動識別，建議先以固定規則（如最近 N 根 K 棒的最高/最低點）近似處理，再回測驗證

---

## 關鍵原文引述

1. **模型核心定義**：  
   *"the setup is going to be day of week specific and the pattern is going to be external range liquidity runs"*

2. **進場規則核心**：  
   *"you cannot sell short unless you're selling short above a previous short-term high… in that short position you cannot cover unless you cover below old low or a new short-term low"*

3. **出場規則核心**：  
   *"on your second partial the next time you take profit you have to be out of the entire position"*

4. **One-Shot-One-Kill 建議日**：  
   *"if you're one shot one kill trading you want to be doing a cover generally on Thursdays at New York open because that typically will make the low of the week when we're bearish"*

5. **演算法理論**：  
   *"it's not buying pressure that pushes it up there it's a matter of algorithmic price delivery"*

6. **進場具體偏移**：  
   *"we will use the PD array convergence minus 5 pips as our entry price when using the sell limit order"*

7. **停損移動規則**：  
   *"when we are in profit 50% of our expected objective stop loss can be reduced by 25%; when we are in profit 75% of our expected objective stop loss can be reduced by Break Even"*

8. **風控降 R 規則**：  
   *"if you take a series of five winning trades in a row drop your R percent by 50%... this will build in equity leveling and reduce the likelihood of a large drawdown"*
