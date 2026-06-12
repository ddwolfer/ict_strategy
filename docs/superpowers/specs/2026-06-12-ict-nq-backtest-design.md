# ICT NQ 回測系統 — 設計規格

日期：2026-06-12
狀態：已獲使用者核准（對話中逐節確認）

## 1. 目標

研究指定的 34 部 ICT（Inner Circle Trader）教學影片，萃取出可執行的交易規則，
建立一套按該模式運作的 Python 策略引擎（agent），並提供逐根 K 棒回放的 web
回測介面。

- 標的：NQ（那斯達克 100 期貨，yfinance 代碼 `NQ=F`）
- 週期：1 分 K
- 交易時段：台灣時間 21:30–00:30（ET 9:30–12:30；涵蓋 NY AM Killzone 與
  Silver Bullet 時段）
- 資料：yfinance 最近約 30 天 1 分 K（每次請求上限 8 天，分段抓取後合併），
  本地 CSV 快取
- 成功標準：使用者能在 web 介面逐根回放任一交易日，看到 agent 每根 K 棒的
  判讀（狀態、標記）與進出場，且回測結果完全可重現

### 不做的事（YAGNI）

- 不接實盤／模擬盤下單（只定義 adapter 抽象介面，未來擴充）
- 不做參數優化器、機器學習
- 不做多商品、多時段

## 2. 執行分工

- **Fable（主 agent）**：寫 spec 與任務計畫、逐任務驗收（跑測試、審代碼、
  核對驗收條件）、綜合撰寫最終策略規格、親自審查無前視（no-lookahead）邏輯。
- **Sonnet subagents**：抓字幕、逐部影片整理筆記、按計畫實作各模組、寫測試。
- 任務切分原則：每個任務有明確驗收條件，subagent 照規格實作，不需自行做
  策略層面的判斷。

## 3. 階段一：影片研究

1. 用 `youtube-transcript-api`（已安裝，v1.2.4）批次下載 34 部影片字幕，
   存 `research/transcripts/`。無字幕的影片列入清單回報使用者。
2. Sonnet subagents 逐部整理筆記（`research/notes/`）：該片教的概念、規則、
   具體參數（時間窗、比例、條件）。
3. Fable 綜合所有筆記，交叉比對 ICT 已知體系（流動性、FVG、Order Block、
   MSS、Killzone、Power of 3、OTE、Silver Bullet 等），撰寫
   `docs/strategy/ict-strategy-spec.md`：明確定義進場模型（觸發 → 進場 →
   停損 → 停利 → 時段過濾），每條規則標注出處影片。
4. **使用者審查門檻：策略規格須經使用者確認與影片內容一致，才開始實作引擎。**

### 影片清單（34 部）

vCvRrINpknI, rNn0JkItAGo, 4f1vjQMlV50, s1gCDuzcukU, KQdsa7S1LoQ,
E0sA_SWIxKM, ze8jAMdmBqc, 2CWIbdP1kZw, SObhjCvXCNk, H05w52zQGdQ,
JN_uaDDZ0rc, bcp19tiJZA0, NB7Bku099tU, 2fgXDt3T3XE, BMYrtYMisnA,
fAcnhdaowME, V0TFp7AvZqw, 5FTMSC4kLZM, yC-gQhvexGg, beTnmkbuUjg,
_7oZZ2bhEGU, oheyS8MUqno, G4lhid5dh0I, fHp3JkxFFjU, F-8hPvSyIB4,
twIPoG2TZ1o, YIxurbDNrWM, CTS27DsveNs, E57WWIEjhvU, UtdXo9HJHKU,
pblXxWhnRz4, 3xgtrXok-xs, xi0N9BG1Qvs, kNlySn81dmo

## 4. 階段二：Python 策略引擎

核心介面：`engine.on_bar(bar) -> list[Event]`。逐根餵入，嚴格禁止前視——
所有 detector 只能看已收盤的 K 棒。

### 模組劃分

| 模組 | 職責 |
|---|---|
| `data/` | yfinance 抓取 + CSV 快取；輸出統一 Bar 格式（UTC 儲存，引擎內轉 ET 判斷時段） |
| `detectors/` | 擺動點、流動性池（前高低／等高低／前日高低）、掃蕩判定、位移 + MSS、FVG、Order Block、Premium/Discount |
| `model/` | 進場模型狀態機（依階段一策略規格實作；典型流程：等掃蕩 → 等 MSS/位移 → 等回踩 FVG → 進場） |
| `risk/` | 停損放掃蕩點外、目標對側流動性或固定 RR、每日最多 N 筆、當日虧損上限——全部為 config 參數 |
| `sim/` | 模擬撮合：tick 0.25、每點 USD 20、可設滑價與手續費；以 1 分 K 的 OHLC 保守規則判定觸發順序 |
| `adapters/` | `DataFeed` 與 `ExecutionBroker` 抽象介面；回測用歷史實作。未來模擬盤＝新增即時 feed + 券商 broker 實作，引擎不動 |

### 回測輸出：決策日誌 JSON

每個交易日一份，內容：

- `bars`: OHLCV 序列（含時間戳）
- `annotations`: 每根 K 棒當下的標記快照增量（流動性線、FVG 區、OB、掃蕩
  事件、狀態機狀態與「正在等什麼」）
- `trades`: 進出場紀錄（方向、價格、停損、停利、結果、R 倍數）
- `equity`: 權益曲線
- `stats`: 勝率、盈虧比、最大回撤、總 R

## 5. 階段三：Web 回放介面

純靜態頁面，lightweight-charts，讀決策日誌 JSON。不需伺服器。

- 逐根播放／暫停／單步前進後退／1x–60x 變速
- 圖上疊加：流動性線、FVG 方塊、OB、掃蕩標記、進出場箭頭、停損停利水平線
- 側欄：狀態機當前狀態、交易日誌、權益曲線、統計
- 日期選擇器切換交易日
- 視覺風格：編輯感、內容導向，避免模板化 AI 風格

## 6. 測試策略

- detector 單元測試：手工構造 K 棒序列驗證每個偵測器（TDD）
- 無前視檢查：同一段資料「逐根餵」與「截斷後重餵」結果必須一致
- golden test：固定一段真實資料的回測結果快照，防止回歸
- 前端：以一份固定的決策日誌 JSON 做手動驗收

## 7. 風險與緩解

| 風險 | 緩解 |
|---|---|
| 部分影片無字幕 | 回報清單；以其餘影片 + ICT 文獻補足，規格中標注 |
| yfinance 1m 僅約 30 天 | 資料層可替換；先驗證邏輯，更長歷史後續再接 |
| 1 分 K 無法精確模擬盤中觸發順序 | 撮合採保守規則（同根 K 棒同時觸及停損與停利時，以停損優先）並在統計中標注 |
| subagent 實作無前視出錯 | Fable 親自代碼審查 + 截斷重餵一致性測試 |
