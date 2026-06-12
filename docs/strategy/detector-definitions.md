# ICT 偵測器量化定義（引擎實作基準）

本文件把 ICT 概念轉成可實作、可測試的精確定義。所有偵測器嚴格遵守
**無前視原則**：事件只能在「確認 K 棒」收盤後發出，並標注 `confirmed_at`
（確認時間）與 `anchor`（結構實際所在的 K 棒）。

NQ 規格：tick = 0.25 點，每點 USD 20（1 口 = $5/tick）。
時間：資料以 UTC 儲存，引擎以 `America/New_York` 判斷時段。

## 1. Bar

`Bar(ts_utc, open, high, low, close, volume)`，1 分鐘 K 棒，ts 為開盤時間。

## 2. Swing Point（擺動點 / fractal）

參數 `n`（預設 1，即 3 根 K 棒 fractal；ICT 筆記未給精確根數，採最小定義，
可調大）。

- **Swing High**：`high[i] > high[i-k]` 且 `high[i] > high[i+k]`，k = 1..n。
  相等視為不成立（嚴格大於）。
- **Swing Low** 對稱。
- 確認時點：第 `i+n` 根收盤後發出事件；`anchor = i`。

## 3. Liquidity Pool（流動性池）

每個 pool：`(kind, side, level, created_at, swept_at | None)`。

| kind | 定義 |
|---|---|
| `PDH` / `PDL` | 前一交易日 RTH（09:30–16:00 ET）最高 / 最低 |
| `ONH` / `ONL` | 隔夜時段（前日 18:00 ET – 今日 09:29 ET）最高 / 最低 |
| `SESSION_HIGH` / `SESSION_LOW` | 今日 09:30 ET 起、至當前 K 棒為止的盤中極值（滾動更新） |
| `SWING_HIGH` / `SWING_LOW` | §2 的擺動點（buy-side 在高點上方、sell-side 在低點下方） |
| `EQUAL_HIGHS` / `EQUAL_LOWS` | 兩個以上 swing 極值差距 ≤ `eq_tol`（預設 2 ticks = 0.5 點）視為等高/等低，level 取較極端者 |

- **Sweep（掃蕩）**：某 K 棒 `high > level`（buy-side）或 `low < level`
  （sell-side），即該 pool 標記 `swept_at`。
- **Raid / Turtle Soup 條件**：sweep 當根或其後 `r` 根內（預設 r = 3）出現
  收盤回到 level 的另一側（buy-side sweep 後 `close < level`），發出
  `RAID` 事件。這是「假突破掃流動性」的量化判定。

## 4. FVG（Fair Value Gap）

三根連續 K 棒 i, i+1, i+2：

- **Bullish FVG（BISI）**：`low[i+2] > high[i]`。
  區間 `[high[i], low[i+2]]`。
- **Bearish FVG（SIBI）**：`high[i+2] < low[i]`。
  區間 `[high[i+2], low[i]]`。
- `CE`（Consequent Encroachment）= 區間中點。
- 確認時點：第 i+2 根收盤；`anchor = i+1`。
- **失效（mitigated）**：之後任一 K 棒收盤完全穿越區間遠端，或價格完整填補
  區間（觸及遠端邊界）。狀態：`fresh → touched → filled/invalidated`。
- 最小寬度過濾：`min_gap`（預設 1 tick）。

## 5. Displacement（位移）

衡量「機構式的快速移動」：

- 視窗 `w`（預設 20 根）內 K 棒實體絕對值的平均 `avg_body`。
- 某 K 棒 `|close - open| ≥ disp_mult × avg_body`（預設 2.0）即為
  displacement candle。
- ICT 筆記中 displacement 常伴隨 FVG：旗標 `left_fvg = True/False`。

## 6. MSS（Market Structure Shift）

- 向下 MSS（空方訊號）：displacement candle（§5）**收盤跌破**最近一個未被
  破壞的 swing low（§2）。「收盤跌破」= `close < swing_low.level`。
- 向上 MSS 對稱。
- 事件附帶：被破壞的 swing、displacement 候選 K 棒、是否留下 FVG。
- 出處對應：Model 7「最高 Reaccumulation 的 swing low 被跌破才算 MSS」——
  狀態機層會選定「哪一個 swing」作為判定基準，偵測器只提供事件。

## 7. Dealing Range 與 Premium / Discount

- `DealingRange(high, low)`：取 lookback `D` 個交易日（預設 20，排除週末）
  的最高高點 / 最低低點；或由狀態機指定「掃蕩點 → 對側極值」的動態 range。
- `equilibrium = (high + low) / 2`。
- Premium：價格 > equilibrium；Discount：價格 < equilibrium。
- **OTE 區**：retracement 62%–79%（核心 62%，出處 Model 1/11）。
  Fib 以 swing 的端點計算；Model 1 規定用 K 棒實體（body）端點，參數
  `use_bodies`（預設 True，依 Model 1）。

## 8. Session / Killzone（皆為 ET）

| 名稱 | 區間 |
|---|---|
| `NY_AM_KILLZONE` | 07:00–10:00（Model 1 定義） |
| `RTH_OPEN_3H` | 09:30–12:30（本專案交易窗，使用者指定） |
| `SILVER_BULLET_AM` | 10:00–11:00 |
| `OVERNIGHT` | 前日 18:00 – 今日 09:29 |
| `RTH` | 09:30–16:00 |

引擎的「可進場窗」是 config 參數，預設 `RTH_OPEN_3H`。

## 9. 事件流介面

```
engine.on_bar(bar) -> list[Event]
Event = SwingConfirmed | PoolCreated | PoolSwept | Raid
      | FVGCreated | FVGTouched | FVGFilled
      | Displacement | MSS | SessionBoundary
      | OrderPlaced | OrderFilled | OrderCancelled
      | TradeOpened | TradeClosed | StateChanged
```

無前視驗收標準（golden rule）：對任意前綴長度 t，
`run(bars[:t])` 產生的事件序列必須是 `run(bars)` 前 t 根事件的精確前綴。
