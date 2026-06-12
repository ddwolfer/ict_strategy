# ICT NQ 1分K 回測系統

研究 ICT（Inner Circle Trader）Charter Price Action Model 1–13 教學影片，
萃取出可執行的交易規則，實作為 Python 策略引擎 + 逐根 K 棒回放的 Web 介面。

- 標的：NQ / MNQ（那斯達克 100 期貨），1 分 K
- 時段：NY 開盤 09:30–12:30 ET（台灣時間 21:30–00:30）
- 核心鏈路（Model 13「2022 Model」）：流動性掃蕩 → MSS + 位移 → 回踩 FVG 限價進場 → 流動性階梯分批停利
- 另有 Silver Bullet preset（10:00–11:00、SMT 過濾、min 1:2、每日第一個 MSS）

## 快速開始

```bash
# 1. 抓資料（yfinance 只保留 30 天 1 分 K，每天跑才能累積歷史）
python data/fetch_nq.py                      # NQ
python data/fetch_nq.py "ES=F" es_1m.csv     # ES（SMT 過濾用）

# 2. 跑回測（輸出決策日誌到 web/replay_data/）
python -m engine.backtest.runner
python -m engine.backtest.runner --preset silver_bullet   # → web/replay_data_sb/

# 3. 開回放介面
python web/serve.py 8741
# 瀏覽器開 http://127.0.0.1:8741（Silver Bullet 結果加 ?data=sb）

# 測試
python -m pytest tests -q
```

## 目錄結構

| 路徑 | 內容 |
|---|---|
| `research/` | 34 部影片字幕 + 13 份模型筆記（每條規則標注出處） |
| `docs/strategy/` | 策略規格（含與原系列的偏離清單）、偵測器量化定義、決策日誌 schema |
| `engine/detectors/` | swing / FVG / 流動性池 / 位移 / MSS / dealing range（嚴格無前視） |
| `engine/model/` | 每日偏向 + 盤中狀態機（WAIT_SWEEP → WAIT_MSS → WAIT_RETRACE → IN_POSITION） |
| `engine/sim/` | 保守撮合（同根停損優先、ambiguous 標記）+ ICT 風控（R% 減半規則） |
| `engine/backtest/` | 逐日 runner + 決策日誌 JSON 輸出 |
| `web/` | lightweight-charts 逐根回放（狀態機面板、停損/停利線、FVG 生命週期顯示） |

## 誠實聲明

目前快取僅 ~21 個交易日、5 筆交易——統計上不足以評價策略期望值。
所有參數維持影片忠實預設，未做曲線擬合。回測採保守假設
（同根 K 棒同時觸及停損與停利時以停損計，並標注 ambiguous）。
