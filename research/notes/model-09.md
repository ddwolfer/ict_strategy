# Model 9 — One Shot One Kill（週範圍單次精準交易）

## 影片清單

| ID | 標題 |
|----|------|
| twIPoG2TZ1o | ICT Charter Price Action Model 9 - One Shot One Kill |
| YIxurbDNrWM | ICT Charter Price Action Model 9 - One Shot One Kill Trade Plan & Algorithmic Theory |

---

## 模型定位

- **時間框架（分析）**：Weekly → Daily → 4-Hour → 1-Hour；執行用 15-minute chart OTE
- **交易風格**：短期方向性交易（Short-Term Directional），非 scalping、非 swing。ICT 本人定位為「week range trader」
- **適用市場**：Forex（影片以 EURUSD、GBPUSD、USDCHF 為例）；原則適用所有流動性市場（crypto、oil、stocks、commodities 均被提及）
- **目標**：每週 **50～75 pips**，傾向鎖定 50 pips 為主要目標，75 pips 為延伸目標
- **進場天數**：限制在 **週一、週二、週三**；ICT 個人傾向放棄週一，主要在 **週二、週三** 操作（原因：70% 的情況下週二形成當週 higher low）
- **每次交易總風險**：最多 **2% 帳戶資金**（雙訂單架構各 1%）

---

## 核心概念定義

### 1. External Range Liquidity（外部範圍流動性）
位於當前交易區間（dealing range）**外部**的流動性，包含：等高點（equal highs）上方的 buy stops、等低點（equal lows）下方的 sell stops、雙頂（double top）上方或雙底（double bottom）下方的停損池。進場來源為外部範圍，則出場目標為內部範圍；反之亦然。

### 2. Internal Range Liquidity（內部範圍流動性）
位於當前交易區間**內部**的流動性，包含：Fair Value Gap（FVG）、Liquidity Void（流動性空洞）、Order Block（OB）、Equilibrium（中線，50%）。

### 3. 核心法則：External ↔ Internal 對應關係
> 「If I'm entering on an external range liquidity, I'm aiming for internal range liquidity. If I'm entering on internal range, it's going to reach for external range liquidity.」

- **進場在 Internal Range** → 出場目標在 **External Range**（突破現有高/低）
- **進場在 External Range**（例如 turtle soup 掃停損後反轉）→ 出場目標在 **Internal Range**（FVG、OB、equilibrium）

### 4. Fair Value Gap (FVG) / Liquidity Void
買方失衡（buy side imbalance）= 賣方效率不足（sell side inefficiency）：市場快速上漲留下的價格空白，後續傾向回填（rebalance）。反向同理。

### 5. Consequent Encroachment（CE）
FVG 或 liquidity void 的 **中點（midpoint / 50%）**，是最敏感的反應價位；許多情況下市場只需觸及中點即反彈，不需完全填滿缺口。

### 6. Bearish Breaker（熊市 Breaker）
**前提**：先有 equal highs 被掃除（buy stops 清除），然後出現 Market Structure Break（MSB）。最後一根向下收盤的蠟燭（last down close candle，且是幅度最大的那根）即為 Bearish Breaker，後續價格回測此區域時提供空頭進場機會。（注意：是 MSB 之後的 last down-close candle，不是任意下跌蠟燭）

### 7. Optimal Trade Entry (OTE)
在 Fibonacci 回調中的最佳進場區間，對應 **61.8%～79% 回調區域**（逐字稿中提及以蠟燭實體 body 為基礎畫 Fib，而非整根蠟燭含影線）。

### 8. Weekly Range Expansion
每週的定向擴張（方向性偏差，directional bias）；Model 9 的前提假設是已確認本週方向（bullish 或 bearish），然後等待週一至週三形成回調低點（bullish 情況下的 higher low）再進場。

### 9. SMT Divergence（SMT 背離）
相關貨幣對之間的結構背離訊號：例如 DXY 能創新低但 Cable（GBPUSD）無法創新高，代表 Cable 方向性偏弱，傾向做空。（影片中以 5 分鐘圖舉例）

### 10. Standard Deviation Projection（標準差投影）
以一段「近期低點到高點」的範圍為基準，向下（或向上）投影等距離作為獲利目標：1 SD = 等幅延伸，1.5 SD 為延伸目標。（與 measured move 概念相同）

---

## 進場模型完整流程

### 前置條件（Preparation Stage）

1. **記錄高衝擊經濟事件**：標記當週及下週所有 medium/high impact 事件（economic calendar），以 New York 時間為準
2. **建立 IPA 20 週 Dealing Range**：
   - 在週線圖上標記**過去 20 週的最高點（highest high）和最低點（lowest low）**
   - 此範圍為當前 dealing range，作為宏觀方向判斷的框架
3. **確認週線偏差（Weekly Bias）**：
   - 判斷方向：這週是要往上突破 20 週舊高？還是往下突破 20 週舊低？
   - 找出下一個流動性吸引點（draw on liquidity）：above which old high / below which old low
4. **確認週線 PD Array**：在偏差方向上找對應的 PD array（OB、FVG、equilibrium）

### Opportunity Discovery（機會探索）

5. **圈出 50～75 pips 範圍**：在日線或週線圖上標示能形成 50～75 pip 移動的相鄰 old highs / old lows 組合
6. **等待 news catalyst 確認**：等待 economic calendar 上的 volatility injection（高衝擊事件）提供推動力，條件為「低阻力流動性奔跑（low resistance liquidity run）」

### Trade Planning（交易計劃）

7. **Bearish 場景**：
   - 在 premium 區域等候 buy side liquidity pool（等高點停損區）被掃除，形成 manipulation
   - 時機：London Open 或 New York Open kill zone 內
   - 進場：15 分鐘圖 OTE 在向上回調中形成 → 做空

8. **Bullish 場景**：
   - 在 discount 區域等候 sell side liquidity pool（等低點停損區）被掃除，形成 manipulation
   - 時機：London Open 或 New York Open kill zone 內
   - 進場：15 分鐘圖 OTE 在向下回調中形成 → 做多

### Trade Execution（執行）——雙訂單架構

ICT 明確說明使用**兩個獨立訂單（2 orders）**，總風險 2%：

**訂單一（Order 1）— Model 8 邏輯，積極獲利**
- 風險：1%
- 進場：FVG / OTE 觸碰時，賣出限價單
- 停損：進場 OTE 區域上方 1-2 pips
- 獲利目標（分步）：
  - 第一目標：近期 swing low（5-10 pips 下方）
  - 第二目標：再 10 pips 以下（total ~10-15 pips）
  - 剩餘倉位：掛限價等最終目標
- 一旦第一目標達成 → 移動停損至 break even

**訂單二（Order 2）— One Shot One Kill 核心**
- 風險：1%
- 進場：與訂單一相同的 FVG / OTE（重複相同進場）
- 停損：與訂單一相同
- **不在早期目標獲利**，直到 standard deviation projection 觸發才開始分批出場：
  - 第一分批：1 SD（從近期低到 OTE 高的等幅投影）
  - 第二分批：1.5 SD
  - 剩餘倉位（最小部分）：掛限價在 hourly relative equal lows 附近（分配在兩個相鄰等低之間的 midpoint）
- 若市場仍在 equilibrium 以上（即尚未穿越 50% 回調）→ 可**加碼（pyramid）**，每次追加原始倉位的 50%，停損設在新的 FVG 上方

### 停損位置

- 初始停損：進場區域（OTE / FVG）的**反向邊緣外 1-2 pips**
- 移動停損規則（**嚴格限制，不可隨意移動**）：
  - **只有當 lower time frame model（scalping / day trading 模型）已到達其盈利目標時，才能移動 one shot one kill 的停損**
  - 達到 50% 期望獲利 → 停損可縮減 25%
  - 達到 75% 期望獲利 → 停損移至 break even
  - 進入週五（Friday）才開始積極追蹤停損

### 停利/出場管理

- **在 50 pips 目標達成時**：關閉 80% 倉位
- **剩餘 20%**：看能否延伸至 75 pips，沿途在 short-term highs（多頭）或 short-term lows（空頭）分批出場
- 週四/週五前若 lower TF 模型到達獲利目標，確認移動停損
- 週五開始積極追蹤停損，目標鎖定週四 low（空頭）

---

## 具體參數

| 參數 | 數值 |
|------|------|
| 週範圍目標 | **50 pips**（主）/ **75 pips**（延伸） |
| 進場窗口（星期） | 週一～週三（ICT 傾向只用週二、週三） |
| Kill Zone | London Open + New York Open（詳見下節） |
| 執行時間框架 | 15-minute chart OTE |
| 每筆訂單風險 | **1%** 帳戶資金 |
| 總交易風險 | **2%**（雙訂單） |
| 停損移動條件（1） | 達到期望獲利的 50% → 停損縮減 25% |
| 停損移動條件（2） | 達到期望獲利的 75% → 停損移至 break even |
| IPA Dealing Range | 過去 **20 週** 的最高高/最低低 |
| 週二 higher low 機率 | ICT 稱 **70%** 的情況下週二形成週內 higher low |
| 標準差投影 | 1 SD（等幅）為第一目標；1.5 SD 為第二目標 |
| Fib 基礎 | 以蠟燭**實體（bodies）**畫 Fibonacci，非影線 |
| OTE Fib 區間 | 61.8%～79%（字幕中以「optimal trade entry」指稱） |
| FVG 限價策略 | 兩個相鄰等低之間的 **midpoint（50%）** 掛限價單 |
| 加碼（pyramid）條件 | 仍在 equilibrium（50% Fib）以上，每次追加原始倉位的 50% |
| 連勝後降險規則 | **連贏 5 筆後**，降低 R% 至 50%（防止大幅回撤） |
| 單筆虧損後降險規則 | 完整虧損 1 個 R 後，下一筆只用 50% 的 R；待回收 50% 損失後才恢復 |

### 倉位計算公式
```
倉位大小 = (帳戶資金 × R%) ÷ 停損 pips
```
範例（$10,000 帳戶，1% 風險，20 pips 停損）：
- 風險金額 = $100
- micro lots（$0.10/pip）→ $100 ÷ (20 × $0.10) = 50 micro lots
- mini lots（$1/pip）→ $100 ÷ (20 × $1) = 5 mini lots
- **注意：$10,000 帳戶不適合用 standard lot（風險過高）**

---

## 時段規定（Killzone）

逐字稿明確提及的 kill zones（均為 **New York 時間**）：

| Kill Zone | NY 時間 | 備註 |
|-----------|---------|------|
| **London Open Kill Zone** | （字幕未給出明確時間範圍，僅稱 "London open"） | 用於尋找 OTE retracement |
| **New York Open Kill Zone** | （字幕未給出明確時間範圍，僅稱 "New York open"） | 用於尋找 OTE retracement；影片舉例 Fed Chair 在 **10:00 AM NY 時間**講話觸發波動 |

> **(字幕不清)** 兩個 kill zone 的精確起訖時間在本段逐字稿中未明確數字化（ICT 其他課程定義為 London ~02:00-05:00 AM NY、NY Open ~07:00-10:00 AM NY，但此逐字稿本身未給出數字，僅說「London open and/or New York open kill zones」。）

---

## 風控規定

1. **最大單筆交易風險：2%**（雙訂單合計；每單 1%）
2. **完整虧損 1R 後**：下一筆交易降至 50% 的 R，直到回收 50% 損失後才恢復正常 R
3. **連贏 5 筆後**：主動將 R% 降至 50%（字幕原文：「you're likely to assume a loss eventually and this will build in equity leveling and reduce the likelihood of a large drawdown」）
4. **目標：平滑上升的資金曲線**（「smooth equity curve that slopes or stair steps higher, not jagged with deep declines」）
5. **不強制交易**：如果 Monday-Wednesday 沒有清晰 setup，改用 Model 8 或 scalping 模型小額獲利，不強行 one shot one kill
6. **停損不隨意移動**：只有 lower TF 模型（scalping/day trading）達到獲利目標時，才能移動 OSOK 停損；不可為了保護浮盈而提早收緊停損，以免被洗出週範圍擴張

---

## 對「NQ 1分K、NY 開盤後3小時自動交易」的適用性

### 可機械化（演算法友好）的規則

| 規則 | 機械化方式 |
|------|-----------|
| 20 週 IPA dealing range（最高/最低）計算 | 直接計算 20 週滾動 high/low |
| 週偏差方向（bullish/bearish） | 可依 weekly close vs dealing range midpoint、或 MSS 判斷 |
| FVG 偵測（buy-side imbalance / sell-side inefficiency） | 三根 K 棒結構：中間棒的高>前棒高且低<後棒低（或反向）|
| OB（Order Block）偵測 | 找趨勢前最後一根反向收盤棒 |
| CE（Consequent Encroachment）計算 | FVG 上下邊界的算術中點 |
| Equal lows/highs 識別 | 找距離在 N pips 以內的相鄰 swing low/high |
| OTE Fib 計算（61.8%～79%） | 以近期 swing 實體計算 Fibonacci 回調區間 |
| 標準差投影目標 | 量化 measured move 投影（swing range 複製）|
| 停損移動規則（50%/75% 獲利後） | 追蹤進場到停損距離，達閾值自動調整 |
| 倉位計算 | 公式固定，完全可自動化 |
| Kill Zone 時間窗過濾 | 限制下單時間在 NY Open 附近（07:00-10:30 AM NY）|
| 進場天數限制（週一～週三） | 日期過濾（星期四五不進新場）|
| 降險規則（虧損後 / 連贏後） | 追蹤交易歷史，動態調整風險參數 |

### 靠主觀判斷的規則（需進一步量化或接受模糊性）

| 規則 | 難點 |
|------|------|
| Weekly bias 確認 | 需結合 HTF context（月線、季線）判斷，純規則有時不夠充分 |
| Breaker 辨識（last down-close candle after MSB） | 需確認「MSB 已發生 + 幅度最大的 down-close candle」，在自動化中定義 MSB 本身就有主觀空間 |
| News catalyst 等待（economic calendar volatility injection）| 需整合外部 API（calendar），且「等待 volatility injection」本身在 1分K 難以精確定義 |
| SMT Divergence | 需同時追蹤相關市場（NQ 的 SMT partner 可能是 ES），邏輯可量化但需設計 |
| 何時加碼（pyramid）的進場時機 | 原文只說「anytime it would offer me one」，細節未完整量化 |
| 「不清晰 setup 就跳過」的判定標準 | 完全主觀，逐字稿無明確 threshold |

### 評估結論

**部分適合**。Model 9 的核心骨架（週偏差 → NY open kill zone → 15分K OTE 進場 → 50 pips 目標）在 NQ 1分K NY 開盤場景下**原則可行**，但原版設計是 Forex 15分K，移植到 NQ 1分K 需注意：
1. **pips → handles/ticks 換算**：NQ 的 50-75 pip 等效需重新定義（NQ 的 1 handle = 4 ticks；50 Forex pip 的等效波動需根據 ATR 重新校準）
2. **15分K OTE → 1分K OTE**：降一個 TF 執行，結構辨識噪音增加，假訊號率上升
3. **週一～三限制**：與「NY 開盤後3小時」的場景完全吻合（只需加入星期過濾）
4. **雙訂單架構** 完全可以在自動化系統中實現為兩個獨立策略邏輯
5. **Kill zone 時間窗** 是這個場景的核心優勢，雙方高度匹配

---

## 關鍵原文引述

1. > "This model, one shot one kill, is designed to capitalize on the weekly range. We're not trying to get in there and nickel dime the market. We really want to try to get as close as we can to the weekly high, sell short there, and cover close as we can in the lower 1/3 of the weekly range or expected weekly range and be content with that. Our objective is looking for 50 to 75 pips."

2. > "Most of the time you're going to find that internal range liquidity entries will run to external range liquidity... if you are using turtle soup entry style trading... you can use that as your entry and then you're going to target internal range liquidity for your exits."

3. > "External range liquidity entry, then internal range is offered again as an entry, but if you use external range as an entry, what's it going to be reaching for? Internal range liquidity."

4. > "When we are bearish we will anticipate a 15-minute chart optimal trade entry to form inside a retracement higher during London open and/or New York open kill zones or a buy stop raid that we will go short when it unfolds."

5. > "Stop loss can be reduced by 25% when we are in profit 75% of our expected objective stop loss can be reduced to break even."

6. > "If you take a series of five winning trades in a row drop your R percent by 50% — you're likely to assume a loss eventually and this will build in equity leveling and reduce the likelihood of a large drawdown."

7. > "Only when a scalper or day trading model is profitable — that's when you want to move your stop loss on a one shot one kill. You do not want to strangle the trade."

8. > "I taught 70% of the time Tuesday makes the higher low of the week so if there's a lot of opportunity or odds that Tuesday creates the higher low of the week is it really that big of a deal if you don't take a trade on Monday — in my opinion my view is no."
