# Model 11 — 30 Pips 日內交易模型（內部範圍流動性對外部範圍流動性）

## 影片清單

| ID | 標題 |
|---|---|
| UtdXo9HJHKU | ICT Charter Price Action Model 11 - Day Trading |
| pblXxWhnRz4 | ICT Charter Price Action Model 11 - Trade Plan & Algorithmic Theory |

---

## 模型定位

- **類型**：Day Trading（日內交易），ICT 稱之為「bread and butter model」（與 Model 12 並列）
- **目標**：每筆交易 **30 pips**（最低可接受 15 pips 部分獲利，進階可留倉至更遠 Terminus）
- **時間框架**：多時間框架，以 Weekly → Daily → 60分鐘 → 15分鐘 / 5分鐘 逐層向下
- **交易風格**：在 Internal Range Liquidity 進場、以 External Range Liquidity 出場的短線順勢交易
- **適用市場**：Forex pairs、Futures（含 Index Futures）、Bonds、Commodities；影片亦提及 Crypto 可能適用
- **核心績效目標**：每月複利 **6%**，理論上每年帳戶翻倍（以 1% 單筆風險計）
- **定位說明**：Model 11 & 12 setups 形成頻率最高，但需要最紮實的 ICT 基礎知識方可操作；不適合初學者作為第一個模型使用

---

## 核心概念定義

> 僅包含逐字稿中明確出現的定義

**Weekly Range Expansion（週線範圍擴張）**
市場在週線尺度上有 50–100 pips 的可用移動空間，向上或向下移動至流動性目標。這是本模型高機率的**前置條件**。低於 50 pips 可用空間時，本模型不符合高機率條件。

**Internal Range Liquidity（內部範圍流動性）**
在當前擺動高低點所定義的「範圍」內部的流動性池，包括：
- Fair Value Gap（FVG）
- Liquidity Void（CBISI = Cell Side Imbalance Buy Side Inefficiency，或 BSISI = Buy Side Imbalance Sell Side Inefficiency）
- Order Block（OB）

進場時使用這些結構，因為它們代表機構未完成的訂單。

**External Range Liquidity（外部範圍流動性）**
位於當前範圍**外部**的流動性：舊日線高點之上的 Buy Stops（看空時目標），舊日線低點之下的 Sell Stops（看多時目標）。這是本模型的出場目標。

**Dealing Range（交易範圍）**
過去 **20 個交易日**（不計算週日）的最高高點與最低低點。這是 Model 11 使用的主要參考區間。

**Optimal Trade Entry (OTE)**
使用 Fibonacci 回測工具，在 **62% 回測位**附近進場（空單：62% 減 5 pips；多單：62% 加 5 pips）。

**Low Resistance Liquidity Run（低阻力流動性奔跑）**
當市場在無重大障礙的條件下直接跑向目標，不需要多次嘗試。逐字稿將其定義為模型等待的**波動注入條件**。

**Consequent Encroachment（後繼侵入）**
進入 FVG 或 Liquidity Void 的中間點（50% 水平），是可接受的填補程度，不需要完全填滿。

**Terminus（終點）**
模型預設移動目標的到達點（如舊日線低點/高點）。抵達 Terminus 後，可考慮轉換為反轉交易模式。

---

## 進場模型完整流程

### 前置條件（Preparation Stage）

1. **標記經濟日曆**：記錄該週所有中/高影響力新聞事件
2. **確認週線偏向**：分析週線圖 Institutional Order Flow 方向，預期週線範圍 **50–100 pips** 向上或向下擴張
   - 若週線距舊週線低點不足 30 pips → **不符合**高機率條件
3. **計算 Dealing Range**：標記過去 **20 個交易日**（不計週日）的最高高點與最低低點
4. **確認 Draw on Liquidity（DOL）**：
   - 看多：舊日線高點之上（buy stops 所在）
   - 看空：舊日線低點之下（sell stops 所在）
5. **確認週日開盤至 DOL 距離 ≥ 50 pips**，若是則觸發高機率閾值

### Opportunity Discovery（機會發現）

6. 在 **60 分鐘圖**上尋找：
   - 看空：市場向上回測進入 Premium 區域（高於 50% 範圍），找到 Internal Range Liquidity（FVG / OB / Void）作為空頭入場區
   - 看多：市場向下回測進入 Discount 區域（低於 50% 範圍），找到 Internal Range Liquidity 作為多頭入場區
7. 確認回測符合 **Internal Range Liquidity** 定義（非突破後的 re-test，是在範圍內的回撤）
8. 確認市場是**快速**填入 FVG / CBISI（快速代表機構主導）而非緩慢爬升

### Setup 形成

9. 在 **60 分鐘圖**上辨識 Premium OTE（空頭）或 Discount OTE（多頭）
10. 縮小至 **15 分鐘或 5 分鐘圖**精確定位進場點
11. 確認進場時段在 **London Open Kill Zone** 或 **New York Open Kill Zone**（見下方時段規定）
12. 確認有**經濟日曆事件**支撐當日波動注入

### 觸發（Entry Trigger）

13. 等待 15 分鐘或 5 分鐘圖上的 Premium/Discount OTE 位置
    - **空單**：設定 Sell Limit Order @ **62% Fib 回測 − 5 pips**
    - **多單**：設定 Buy Limit Order @ **62% Fib 回測 + 5 pips**

### 停損位置

14. 初始停損：**20 pips**（固定，開單即設）
    - 最低可接受停損：12 pips（過窄；因 spread 影響，ICT 本人通常使用 15–20 pips）
    - 停損位置應在關鍵擺動高/低點之上/之下

### 停利 / 出場管理

**階段式出場（推薦）：**

| 階段 | 獲利 | 動作 |
|---|---|---|
| 第一目標（初學者） | +15 pips | 部分獲利，降低心理壓力 |
| 主要目標 | +30 pips | 關閉主要倉位（Sell Limit / Buy Limit） |
| 停損調整 A | 浮盈達 +15 pips 時 | 停損收緊 5 pips |
| 停損調整 B | 浮盈達 +20 pips 時 | 停損移至**Break Even（BEP）** |
| 尾倉（進階） | 部分倉位留倉 | 等待抵達 Terminus（舊日線高/低點） |

**出場細節：**
- **不要等價格精確碰到舊日線高/低點**再出場；應在目標前 **10–15 pips** 開始出場主要部位（因 retail broker spread/data 差異，等到最後一刻容易無法成交）
- 到達 Terminus 後可考慮反方向進場（Model 11 反轉模式），但此為進階用法

---

## 具體參數

| 項目 | 數值 |
|---|---|
| 目標 pips | **30 pips**（主目標）；進階可留尾至 Terminus |
| 最小可接受部分獲利 | **15 pips** |
| 初始停損 | **20 pips** |
| 最小停損（不建議更緊） | **12 pips** |
| ICT 個人常用停損 | **15–20 pips** |
| OTE Fibonacci 水平 | **62%** 回測（空單：62% − 5 pips；多單：62% + 5 pips）|
| Weekly Range 最低可用空間 | **50 pips**（低於此不符合高機率條件） |
| 理想 Weekly Range 可用空間 | **50–100 pips**（越接近 100 pips 越佳）|
| 最近 Dealing Range 天數 | **20 個交易日**（不計週日）|
| 月度目標收益 | **6%**（複利，理論上每年帳戶翻倍）|
| 單筆風險 R% | **1%**（範例帳戶為 $10,000；激進上限 2%）|
| 停損調整：浮盈 +15 pips | 停損收緊 **5 pips** |
| 停損調整：浮盈 +20 pips | 停損移至 **Break Even** |
| 主要分析 / 方向確認時間框架 | **Weekly Chart** |
| 機會發現時間框架 | **60 分鐘圖** |
| 精確進場時間框架 | **15 分鐘或 5 分鐘圖** |
| 出場提前量（接近 Terminus 時） | **10–15 pips** 提前出場主倉 |
| 偏向最佳操作日 | **週一、週二、週三**（有提及，當日擊中目標後可留小部位） |
| 五連勝後 | R% **減半**（防止 Equity Drawdown） |
| 全損後 | R% **減半**，待回復損失 50% 後才可恢復 |

---

## 時段規定（Kill Zones）

逐字稿明確提及的 Kill Zones：

| Kill Zone | 時間（New York 時間） | 說明 |
|---|---|---|
| **London Open Kill Zone** | **02:00–05:00** NY時間 | 主要進場窗口之一；5分鐘圖案例中確認為「2:00 to 5:00 in the morning」 |
| **New York Open Kill Zone** | 未明確給出具體時間 | 與 London Open 並列為主要 Kill Zone；逐字稿提到「going into New York open」行情會在此延伸 |
| **5:00–7:00 AM 整理期** | **05:00–07:00** NY時間 | London / New York 之間通常為整理，之後才接力往 NY Open 方向奔跑（字幕明確：「5:00 to 7:00 in the morning consolidation then it starts running right up into New York open」）|
| **Asia Kill Zone** | 提及但無具體時間 | 逐字稿提到「Asia London New York trading to a specific price level」三個 Kill Zones 均可出現 setups |

> 注意：影片以 Forex 為主要示範；NQ Futures 的 NY Session 時間大致對應，但需確認 Futures 具體 Kill Zone 時間。

---

## 風控規定

1. **單筆風險固定**：1% 帳戶資金（激進上限 2%）
2. **部位計算公式**：
   ```
   Position Size = (Account Equity × R%) ÷ Stop Loss in Pips
   ```
   - Micro Lots 範例：$10,000 × 1% = $100 風險；20 pip stop × $0.10/pip = $2/lot → 50 micro lots
   - Mini Lots 範例：$10,000 × 1% = $100 風險；20 pip stop × $1/pip = $20/lot → 5 mini lots
   - Standard Lots：**不建議使用**（帳戶規模不符合）
   - 永遠**向下取整**（round down）
3. **虧損後降槓桿**：任一交易虧損全額 R% → 下筆交易 R% **減半**；待虧損回復 **50%** 後方可恢復原 R%
4. **連勝後降槓桿**：連續 **5 勝**後 → R% **減半**（防止大回撤）
5. **目標：平滑 Equity Curve**，逐步階梯式向上，避免劇烈起伏
6. **不強求週線收盤預測**：只需方向正確，捕捉 30 pips 即完成任務，不強行持倉

---

## 對「NQ 1分K、NY 開盤後3小時自動交易」的適用性

### 可機械化的規則

| 規則 | 機械化可行度 | 備註 |
|---|---|---|
| Weekly Range 方向確認（50–100 pips 距離流動性目標） | **高** | 可用程式每週日計算 |
| Dealing Range（過去 20 交易日最高/最低）計算 | **高** | 純計算，完全自動化 |
| OTE 進場：62% Fib ± 5 pips | **高** | 數學計算，可自動觸發 limit order |
| 停損設定：進場後固定 20 pips | **高** | 固定參數 |
| 停損階段調整：+15 pips → 收緊 5 pips；+20 pips → BEP | **高** | 條件式規則，可完全自動化 |
| 獲利目標：+30 pips 自動平倉 | **高** | 簡單 limit order |
| Kill Zone 時間過濾（NY Open 附近） | **高** | 時間條件可硬編碼 |
| 不在距舊低/高 < 30 pips 時進場 | **高** | 距離過濾可計算 |

### 需要主觀判斷的規則

| 規則 | 主觀程度 | 說明 |
|---|---|---|
| Weekly Institutional Order Flow 方向判斷 | **高** | 逐字稿要求讀懂週線機構流向（Bearish OB、Cy fill等），難以完全自動化 |
| FVG / OB / Void 辨識與「填補速度」判斷 | **中高** | 可以程式標記，但「快速 vs 緩慢填補」的意圖判斷有主觀成分 |
| Internal vs External Range 的正確框架 | **中** | 範圍高低點的選取（用哪個擺動高/低點定義範圍）有時需主觀判斷 |
| 經濟日曆事件的交易方向影響評估 | **高** | 需要人工判斷 news 對 institutional flow 的含意 |
| Terminus 達到後的反轉模式切換 | **高** | 進階用法，完全依賴主觀市場讀取 |

### 對 NQ 1 分 K NY 開盤場景的評估

**適用性：中等**

- **有利條件**：
  - Model 11 在所有 Kill Zones 均可運作，NY Open 是明確列出的進場窗口
  - 目標僅 30 pips（NQ 以 handles/points 換算約 30 points，亦可調整）
  - OTE 62% Fib 入場 + 固定停損的核心邏輯可完全機械化
  - 逐字稿提到「index future」為適用市場之一

- **挑戰**：
  - 本模型以 Forex pips 為設計單位，NQ 的 pips/handles 換算需重新定義
  - 1 分 K 圖比逐字稿使用的 15 分 / 5 分圖更低一層，噪音更大；逐字稿最低提到 5 分鐘圖
  - Weekly bias 判斷（50–100 pips 可用空間確認）為高機率條件，但需人工每週設定
  - 逐字稿明確最低進場時間框架為 5 分鐘，**未提及 1 分 K**，直接套用 1 分 K 需驗證

- **建議做法**：
  - 以 5 分 K 作為進場確認，以 1 分 K 輔助精確進場時機
  - Weekly bias + DOL 用半自動設定（每週一次人工確認）
  - OTE 62% Fib 進場、20 pips stop、30 pips target 的核心機制完全自動化
  - Kill Zone 限制為 NY Open 前後（08:00–11:00 NY time）

---

## 關鍵原文引述

1. **模型核心架構**（UtdXo9HJHKU）：
   > "We're using internal range liquidity to target external range liquidity. So we're going to be utilizing internal range liquidity pools — that is like a fair value gap, a void, bisi, cisi — where you get one single pass through on price higher or lower, it will look to rebalance that, and we're going to be using that to facilitate an entry in the direction of the weekly expansion and looking to exit on an opposing external range liquidity pool."

2. **週線前置條件**（UtdXo9HJHKU）：
   > "The underlying characteristic, if you will, that makes this model high probability — now if you're looking at a weekly chart and it's trading really really close to an old weekly low within 30 pips, that's not going to be high probability. You want to be able to see there's a possible range expansion still left to be fulfilled in the form of a 50 to 100 pip closer to 100 pip the better."

3. **獲利目標與紀律**（UtdXo9HJHKU）：
   > "There's your 30 pips, you're done in just a few hours. Your week is done, it's over. You've met your criteria for doubling your account every single year targeting 6% return compounded every single month."

4. **OTE 進場規則**（pblXxWhnRz4）：
   > "When we are bearish we will anticipate a 15 or 5 minute premium optimal trade entry to form on a 60-minute retracement higher during London open and or New York open kill zones."

5. **停損與出場管理**（pblXxWhnRz4）：
   > "Stop-loss opens with a 20 pip risk. When we are in profit 15 pips of our expected 30 pip objective stop loss can be reduced by five pips. When we are in process profit 20 pips of our expected 30 pip objective stop-loss can be reduced to break even."

6. **提前出場習慣**（UtdXo9HJHKU）：
   > "Even though this does breach the low and it does breach that old daily low and the low that was on the weekly by one pip, I would already be out of there 10 or 15 pips above it. If I see that level here, 10 or 15 pips, I'm getting out because I'm not trying to be Mr. Wizard."

7. **快速 FVG 填補的意義**（UtdXo9HJHKU）：
   > "The hallmark signature to them filling is speed, because it's offering an enticement to traders — they're watching price, they're seeing it take off, they want confirmation. If it's quickly getting up there, then you know you probably got a good trade and it's on the basis of internal range liquidity."

---

*筆記整理日期：2026-06-12 | 來源：ICT Charter Price Action Models 影片逐字稿 | 所有內容均源自逐字稿，未補充外部知識*
